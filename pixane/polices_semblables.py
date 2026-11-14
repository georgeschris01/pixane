"""Trouver, parmi les polices installées, celles qui ressemblent le plus aux lettres d'une image.

Sans téléchargement : l'utilisateur tape les lettres de l'image (ex. « DISCO ») ; Pixane les écrit avec chaque police
(normal, gras, italique, gras italique) et compare avec la forme des lettres (masque : la sélection du texte).

Comparaison, sur des images ramenées à la même hauteur :
- la forme générale du bloc de texte (largeur / hauteur : polices étroites ou larges) ;
- le recouvrement des lettres (adouci, pour pardonner les petits décalages) ;
- l'épaisseur des traits (part d'encre).
Trois passes : un tri rapide de toutes les polices (style normal, petite taille), puis les 4 styles des meilleures,
puis une comparaison plus fine des toutes meilleures.

Le tri rapide n'ouvre pas les polices : il assemble les lettres d'une « mémoire des polices » (alphabet et chiffres de
chaque police, écrits une fois ; fichier polices.memoire dans le dossier de Pixane, environ 15 Mo). Les polices
ajoutées ensuite sont mises en mémoire à la recherche suivante.
"""
from __future__ import annotations

import os
import pickle
import string
import time
import unicodedata
import zlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QFont, QFontDatabase, QFontMetrics, QImage, QPainter

HAUT_RAPIDE, HAUT_FIN = 32, 72          # hauteur des images comparées (passe rapide, passe fine)
GARDER = 40                             # polices gardées pour la passe fine
PREMIERS = 100                          # polices gardées après le tri rapide (style normal seul)
TAILLE_TRI, HAUT_TRI = 40, 24           # tri rapide : taille d'écriture, hauteur comparée
STYLES = ((QFont.Normal, False), (QFont.Bold, False), (QFont.Normal, True), (QFont.Bold, True))


@dataclass
class Resultat:
    famille: str
    gras: bool
    italique: bool
    score: float                        # 0 à 100 (100 : identique)

    def police(self, taille: int = 40) -> QFont:
        f = QFont(self.famille)
        f.setPixelSize(taille)
        f.setBold(self.gras)
        f.setItalic(self.italique)
        return f


def _recadrer(m: np.ndarray) -> np.ndarray | None:
    ys, xs = np.nonzero(m > 0.5)
    if not len(ys):
        return None
    return m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def _vers_hauteur(m: np.ndarray, h: int, w: int | None = None) -> np.ndarray:
    """Masque (0..1) redimensionné à la hauteur h (largeur w, ou proportionnelle)."""
    from PIL import Image
    hh, ww = m.shape
    if w is None:
        w = max(1, round(ww * h / hh))
    im = Image.fromarray((m * 255).astype(np.uint8)).resize((w, h), Image.BILINEAR)
    return np.asarray(im, np.float32) / 255


def _adoucir(m: np.ndarray, r: int) -> np.ndarray:
    """Flou en boîte (rayon r) : deux formes presque superposées se recouvrent bien."""
    if r <= 0:
        return m
    k = 2 * r + 1
    p = np.pad(m, r, mode="constant")
    c = np.cumsum(np.cumsum(p, 0), 1)
    c = np.pad(c, ((1, 0), (1, 0)))
    return (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]) / (k * k)


def masque_texte(texte: str, police: QFont) -> np.ndarray | None:
    """Les lettres écrites avec cette police : masque 0..1 recadré sur l'encre."""
    fm = QFontMetrics(police)
    lignes = texte.split("\n")
    larg = max(fm.horizontalAdvance(l) for l in lignes) + fm.height()
    haut = fm.lineSpacing() * len(lignes) + fm.height()
    if larg <= 0 or haut <= 0 or larg * haut > 40_000_000:
        return None
    img = QImage(larg, haut, QImage.Format_Grayscale8)
    img.fill(0)
    p = QPainter(img)
    p.setRenderHint(QPainter.TextAntialiasing)
    p.setFont(police)
    p.setPen(Qt.white)
    p.drawText(QRect(0, 0, larg, haut), Qt.AlignCenter, texte)
    p.end()
    a = np.frombuffer(img.constBits(), np.uint8).reshape(haut, img.bytesPerLine())[:, :larg]
    return _recadrer(a.astype(np.float32) / 255)


def _comparer(cible: np.ndarray, essai: np.ndarray, h: int) -> float:
    """Ressemblance 0..1 entre deux masques recadrés."""
    rc = cible.shape[1] / cible.shape[0]
    re = essai.shape[1] / essai.shape[0]
    forme = min(rc, re) / max(rc, re)                       # même allure générale (étroite, large)
    w = max(1, round(h * rc))
    a = _vers_hauteur(cible, h, w)
    b = _vers_hauteur(essai, h, w)
    r = max(1, h // 24)
    fa, fb = _adoucir(a, r), _adoucir(b, r)
    recouvrement = float((fa * fb).sum() / max(1e-6, np.sqrt((fa * fa).sum() * (fb * fb).sum())))
    ea, eb = a.mean(), b.mean()                              # épaisseur des traits
    epaisseur = min(ea, eb) / max(ea, eb, 1e-6)
    return recouvrement ** 2 * forme ** 0.5 * epaisseur ** 0.5


def familles() -> list[str]:
    """Polices installées utilisables pour du texte (sans les polices de symboles ni les variantes cachées)."""
    db = QFontDatabase
    res = []
    for f in db.families():
        if f.startswith("@") or db.isPrivateFamily(f):
            continue
        if QFontDatabase.WritingSystem.Latin not in db.writingSystems(f):
            continue
        if db.isSmoothlyScalable(f) is False:
            continue
        res.append(f)
    return res


# ------------------------------------------------------------------ mémoire des polices
CARACTERES = string.ascii_letters + string.digits
VERSION_MEMOIRE = 3
LENTE = 1.0                     # s : police très décorée (ex. St. Andrew, 30 s) : jamais réécrite pendant une recherche
_memoire: dict | None = None
_date_memoire = None


def fichier_memoire() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Pixane"
    nom = "polices.memoire"
    if os.environ.get("PIXANE_REGLAGES"):                 # essais : à part
        nom = f"polices-{os.environ['PIXANE_REGLAGES']}.memoire"
    return base / nom


def memoire() -> dict:
    """{famille: (hauteur de ligne, ligne de base, {caractère: (avance, décalage, lettre uint8)}, espace, durée)}.
    Relue si le fichier a changé (complété par le processus d'arrière-plan)."""
    global _memoire, _date_memoire
    try:
        date = fichier_memoire().stat().st_mtime
    except OSError:
        date = None
    if _memoire is None or (date is not None and date != _date_memoire):
        ancienne = _memoire or {}
        _memoire = {}
        try:
            d = pickle.loads(zlib.decompress(fichier_memoire().read_bytes()))
            if d.get("version") == VERSION_MEMOIRE and d.get("taille") == TAILLE_TRI:
                _memoire = d["familles"]
        except Exception:                                  # absente ou abîmée : refaite
            _memoire = {}
        for k, v in ancienne.items():                      # ce qui a été fait ici entre-temps reste
            _memoire.setdefault(k, v)
        _date_memoire = date
    return _memoire


def lente(fam: str) -> bool:
    v = memoire().get(fam)
    return v is not None and v[4] > LENTE


def enregistrer_memoire() -> None:
    global _date_memoire
    f = fichier_memoire()
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f"{f.name}.{os.getpid()}.part")
    tmp.write_bytes(zlib.compress(pickle.dumps({"version": VERSION_MEMOIRE, "taille": TAILLE_TRI,
                                                "familles": memoire()}, protocol=4), 6))
    os.replace(tmp, f)
    _date_memoire = f.stat().st_mtime


def mettre_en_memoire(fam: str) -> None:
    """Écrit l'alphabet de la police d'un seul coup, puis découpe chaque lettre (avec de la marge : les lettres
    penchées ou qui débordent restent entières)."""
    debut = time.time()
    f = QFont(fam)
    f.setPixelSize(TAILLE_TRI)
    fm = QFontMetrics(f)
    sep = "   "
    chaine = sep.join(CARACTERES)
    marge = max(4, fm.horizontalAdvance(sep) // 2)
    larg, haut = fm.horizontalAdvance(chaine) + 2 * marge, fm.ascent() + fm.descent() + 2
    lettres = {}
    if 0 < larg < 30000 and haut > 0:
        img = QImage(larg, haut, QImage.Format_Grayscale8)
        img.fill(0)
        p = QPainter(img)
        p.setFont(f)
        p.setPen(Qt.white)
        p.drawText(marge, fm.ascent() + 1, chaine)
        p.end()
        a = np.frombuffer(img.constBits(), np.uint8).reshape(haut, img.bytesPerLine())[:, :larg]
        x, pas_sep = marge, fm.horizontalAdvance(sep)
        for c in CARACTERES:
            av = fm.horizontalAdvance(c)
            g, d = max(0, x - marge), min(larg, x + av + marge)
            lettres[c] = (av, g - x, a[:, g:d].copy())
            x += av + pas_sep
    memoire()[fam] = (fm.lineSpacing(), fm.ascent() + 1, lettres, fm.horizontalAdvance(" "), time.time() - debut)


def _lettre(c: str) -> str:
    """É -> E, ç -> c… (le tri rapide n'a que les lettres sans accent)."""
    return unicodedata.normalize("NFD", c)[0] if c not in CARACTERES else c


def assembler(texte: str, fam: str) -> np.ndarray | None:
    """Le texte écrit avec les lettres en mémoire (sans crénage : assez pour un premier tri)."""
    ligne_h, _base, lettres, espace, _duree = memoire()[fam]
    if not lettres:
        return None
    lignes = texte.split("\n")
    haut = next(iter(lettres.values()))[2].shape[0]
    larg = [sum(lettres[_lettre(c)][0] if _lettre(c) in lettres else espace for c in l) for l in lignes]
    bord = max(g.shape[1] for _a, _d, g in lettres.values()) + 4
    W = max(larg) + 2 * bord
    toile = np.zeros((ligne_h * (len(lignes) - 1) + haut, W), np.uint8)
    for n, l in enumerate(lignes):
        x, y = bord + (max(larg) - larg[n]) // 2, n * ligne_h
        for c in l:
            c = _lettre(c)
            if c in lettres:
                av, dec, g = lettres[c]
                x0 = max(0, x + dec)
                x1 = min(W, x0 + g.shape[1])
                if x1 > x0:
                    zone = toile[y:y + haut, x0:x1]
                    np.maximum(zone, g[:, :x1 - x0], out=zone)
                x += av
            else:
                x += espace
    return _recadrer(toile.astype(np.float32) / 255)


def chercher(masque: np.ndarray, texte: str, nombre: int = 10, progres=None, liste: list | None = None) -> list[Resultat]:
    """Les `nombre` polices les plus proches des lettres du masque (0..1 ou 0..255). progres(fait, total) peut
    renvoyer False pour arrêter."""
    texte = texte.strip()
    m = masque.astype(np.float32)
    if m.max() > 1:
        m /= 255
    cible = _recadrer(m)
    if cible is None or not texte:
        return []
    liste = familles() if liste is None else liste
    total = len(liste) + PREMIERS * (len(STYLES) - 1)
    fait = 0
    # passe 1 : toutes les polices, style normal, petite taille
    tri = []
    mem = memoire()
    nouvelles = False
    for fam in liste:
        fait += 1
        if fam not in mem:                              # première fois : la police est mise en mémoire
            mettre_en_memoire(fam)
            nouvelles = True
        e = assembler(texte, fam)
        if e is not None:
            tri.append((_comparer(cible, e, HAUT_TRI), fam))
        if progres is not None and fait % 20 == 0 and progres(fait, total) is False:
            if nouvelles:
                enregistrer_memoire()
            return []
    if nouvelles:
        enregistrer_memoire()
    tri.sort(reverse=True)
    # passe 2 : les meilleures, avec gras, italique, gras italique
    notes, lentes = [], []
    for n_tri, fam in tri[:PREMIERS]:
        if lente(fam):                       # très lente à écrire : on garde sa note du tri
            lentes.append((n_tri, Resultat(fam, False, False, 0)))
            continue
        vus = set()
        for poids, ital in STYLES:
            fait += 1
            f = QFont(fam)
            f.setPixelSize(HAUT_RAPIDE * 2)
            f.setWeight(poids)
            f.setItalic(ital)
            e = masque_texte(texte, f)
            if e is None:
                continue
            cle = (e.shape, float(e.sum()))      # style absent : même rendu que « normal », sauté
            if cle in vus:
                continue
            vus.add(cle)
            notes.append((_comparer(cible, e, HAUT_RAPIDE), fam, poids == QFont.Bold, ital))
        if progres is not None and progres(fait, total) is False:
            return []
    notes.sort(reverse=True)
    fins = []
    for _n, fam, gras, ital in notes[:GARDER]:
        r = Resultat(fam, gras, ital, 0)
        e = masque_texte(texte, r.police(HAUT_FIN * 2))
        if e is not None:
            fins.append((_comparer(cible, e, HAUT_FIN), r))
    fins += lentes
    fins.sort(key=lambda t: -t[0])
    res, familles_vues = [], set()
    for n, r in fins:                    # une famille une fois (sa meilleure variante)
        if r.famille in familles_vues:
            continue
        familles_vues.add(r.famille)
        r.score = round(n * 100, 1)
        res.append(r)
        if len(res) >= nombre:
            break
    return res


def completer_memoire() -> int:
    """Met en mémoire les polices qui n'y sont pas encore (enregistré toutes les 100). Renvoie leur nombre."""
    faites = 0
    for fam in familles():
        if fam in memoire():
            continue
        mettre_en_memoire(fam)
        faites += 1
        if faites % 100 == 0:
            enregistrer_memoire()
    if faites:
        enregistrer_memoire()
    return faites


def lancer_en_fond() -> None:
    """Complète la mémoire dans un processus à part, en priorité basse et sans fenêtre (le calcul garde Python
    occupé : dans Pixane même, la fenêtre se figerait). Rien ne se passe si c'est déjà fait."""
    import subprocess
    import sys
    racine = Path(__file__).resolve().parents[1]
    exe = Path(sys.executable)
    if exe.name.lower() == "python.exe" and (exe.parent / "pythonw.exe").is_file():
        exe = exe.parent / "pythonw.exe"
    drapeaux = 0
    if os.name == "nt":
        drapeaux = subprocess.BELOW_NORMAL_PRIORITY_CLASS | subprocess.CREATE_NO_WINDOW
    try:
        subprocess.Popen([str(exe), "-m", "pixane.polices_semblables", "--memoire"], cwd=str(racine),
                         creationflags=drapeaux, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, close_fds=True)
    except OSError:
        pass


if __name__ == "__main__":                       # mesure rapide : python -m pixane.polices_semblables
    import sys
    from PySide6.QtGui import QGuiApplication
    app = QGuiApplication(sys.argv)
    if "--memoire" in sys.argv:                  # processus d'arrière-plan lancé par Pixane
        verrou = fichier_memoire().with_suffix(".verrou")
        try:
            verrou.parent.mkdir(parents=True, exist_ok=True)
            if verrou.exists() and time.time() - verrou.stat().st_mtime < 1800:
                sys.exit(0)                      # un autre est déjà en route
            verrou.write_text(str(os.getpid()))
            completer_memoire()
        finally:
            verrou.unlink(missing_ok=True)
        sys.exit(0)
    for fam, gras in (("Impact", False), ("Times New Roman", True), ("Comic Sans MS", False), ("Consolas", False)):
        f = QFont(fam)
        f.setPixelSize(90)
        f.setBold(gras)
        cible = masque_texte("DISCO Night", f)
        t = time.time()
        r = chercher(cible, "DISCO Night", 5)
        print(f"{fam}{' gras' if gras else ''} : {time.time() - t:.1f} s ->",
              ", ".join(f"{x.famille}{' G' if x.gras else ''}{' I' if x.italique else ''} {x.score}" for x in r))
