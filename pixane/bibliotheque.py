"""Bibliothèque de pinceaux et de motifs : ceux livrés avec Pixane (paquets de Krita, licence CC-0) et ceux que
l'utilisateur ajoute (.abr, .gbr, .gih, .pat, .bundle, images).

Les fichiers ajoutés sont rangés dans %LOCALAPPDATA%\\Pixane\\bibliotheque\\{pinceaux,motifs} sous forme de
« paquets » (.pixpaquet) : chaque fichier devient un groupe (un .abr de 50 pinceaux = un groupe de 50). Le paquet
contient chaque pinceau ou motif en PNG (sans perte, à sa taille d'origine), sa vignette, et la liste des noms. Au
démarrage, seule la liste est lue ; un pinceau n'est ouvert que quand on s'en sert : pas d'attente, même pour un
.abr de plus d'un Go. Les anciennes copies telles quelles (avant le 14/11/2026) sont converties une fois, en
arrière-plan (convertir_anciens).

Un pinceau d'un .gih (pinceau animé de GIMP / Krita) garde toutes ses formes : elles alternent pendant le trait.
"""
from __future__ import annotations

import io
import json
import os
import tempfile
import threading
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .formats_pinceaux import (EXT_IMAGES, EXT_MOTIFS, EXT_PAQUETS, EXT_PINCEAUX, Contenu, lire_fichier)

BASE = Path(__file__).resolve().parent / "ressources" / "base"
GROUPES_BASE = [("krita4", "Krita 4"), ("krita3", "Krita 3")]
PINCEAUX, MOTIFS = "pinceaux", "motifs"
GROS = 50 * 1024 * 1024    # au-delà (fichiers d'un groupe), lecture en arrière-plan : Pixane reste utilisable
SIMPLES = "Simples"                     # premier groupe de pinceaux : les formes de base, dessinées par Pixane


def _formes_simples() -> list:
    """Les pinceaux de tous les jours (comme les premiers de Photoshop) : rond dur, rond doux, aérographe, carré,
    plat, biseau. Formes en gris (blanc = peint), 256 px."""
    from .pointe import forme_ronde
    t = 256
    yy, xx = np.mgrid[0:t, 0:t].astype(np.float32)
    c = (t - 1) / 2
    u, v = (xx - c) / (t / 2), (yy - c) / (t / 2)

    def bord(d):                                       # 1 dedans, 0 dehors, bord adouci de ~2 px
        return (np.clip(0.5 - d * t / 4, 0, 1) * 255 + 0.5).astype(np.uint8)

    r = np.hypot(u, v)
    plat = bord(np.hypot(u, v / 0.3) - 1)
    a = np.radians(45)
    ub, vb = u * np.cos(a) + v * np.sin(a), -u * np.sin(a) + v * np.cos(a)
    biseau = bord(np.hypot(ub, vb / 0.14) - 1)
    return [
        ("rond_dur", "Rond dur", forme_ronde(0.92, t), 0.08),
        ("rond_doux", "Rond doux", forme_ronde(0.0, t), 0.1),
        ("aerographe", "Aérographe", (np.exp(-2.5 * r ** 2) * np.clip(1 - r, 0, 1) ** 0.5 * 255 + 0.5).astype(np.uint8), 0.06),
        ("carre", "Carré", bord(np.maximum(np.abs(u), np.abs(v)) * 1.02 - 1), 0.08),
        ("plat", "Plat", plat, 0.06),
        ("biseau", "Biseau (calligraphie)", biseau, 0.04),
    ]


def groupe_simples() -> "Groupe":
    from .langue import tr
    g = Groupe(SIMPLES, PINCEAUX, True, [])
    g._elements = [Pinceau(tr(nom), [forme], esp, f"{SIMPLES}/{cle}#0") for cle, nom, forme, esp in _formes_simples()]
    return g


@dataclass
class Pinceau:
    """Forme(s) d'un pinceau ; une forme : (h, w) gris (prend la couleur du pinceau) ou (h, w, 4) en couleur."""
    nom: str
    formes: list
    espacement: float = 0.25
    cle: str = ""                       # identifiant stable : « groupe/fichier#n »
    reglages: dict | None = None        # style prêt : réglages appliqués en le choisissant

    @property
    def en_couleur(self) -> bool:
        return self.formes[0].ndim == 3


@dataclass
class Motif:
    nom: str
    image: np.ndarray                   # (h, w, 4) RGBA
    cle: str = ""


@dataclass
class Groupe:
    nom: str
    genre: str                          # PINCEAUX ou MOTIFS
    de_base: bool
    fichiers: list                      # chemins (Path)
    _elements: list | None = field(default=None, repr=False)
    ignores: list = field(default_factory=list)
    fabrique: object = field(default=None, repr=False)     # fonction qui donne les éléments (groupes calculés)

    def a_lire_lentement(self) -> bool:
        """Fichiers de l'utilisateur pas encore lus et gros (plus de GROS octets) : à lire en arrière-plan."""
        if self._elements is not None or self.fabrique is not None or self.de_base:
            return False
        try:
            return sum(f.stat().st_size for f in self.fichiers) > GROS
        except OSError:
            return False

    @property
    def elements(self) -> list:
        """Pinceaux ou motifs du groupe (lus à la première demande)."""
        if self._elements is None and self.fabrique is not None:
            self._elements = self.fabrique()
        if self._elements is None:
            liste = []                               # publiée seulement complète (lecture en arrière-plan possible)
            for f in self.fichiers:
                try:
                    c = lire_fichier(f, "motif" if self.genre == MOTIFS else "forme")
                except Exception as e:               # fichier abîmé : on le signale, on continue
                    self.ignores.append((f.name, str(e)))
                    continue
                self.ignores += c.ignores
                liste += elements_de(c, self.genre, f, self.nom)
            self._elements = liste
        return self._elements


def elements_de(c: Contenu, genre: str, fichier: Path, groupe: str) -> list:
    if genre == MOTIFS:
        return [Motif(m.nom, m.image, f"{groupe}/{fichier.name}#{i}") for i, m in enumerate(c.motifs)]
    if fichier.suffix.lower() == ".gih" and c.formes:     # pinceau animé : un seul pinceau à plusieurs formes
        nom = c.formes[0].nom.rsplit(" ", 1)[0] if len(c.formes) > 1 else c.formes[0].nom
        return [Pinceau(nom, [f.image for f in c.formes], c.formes[0].espacement, f"{groupe}/{fichier.name}#0")]
    return [Pinceau(f.nom, [f.image], f.espacement, f"{groupe}/{fichier.name}#{i}") for i, f in enumerate(c.formes)]


# ------------------------------------------------------------------ paquets (.pixpaquet)
PAQUET = ".pixpaquet"
APERCU = 256                    # côté maximal de la vignette rangée dans le paquet
_verrou_zip = threading.Lock()
_MODES = {2: "L", 3: "RGB", 4: "RGBA"}


def _encoder(a: np.ndarray) -> tuple[str, bytes]:
    """Image sans perte : PNG (8 bits) ; sinon le tableau tel quel (.npy). Renvoie (extension, octets)."""
    b = io.BytesIO()
    mode = "L" if a.ndim == 2 else _MODES.get(a.shape[2]) if a.ndim == 3 and a.shape[2] > 2 else None
    if a.dtype == np.uint8 and mode:
        from PIL import Image
        Image.fromarray(np.ascontiguousarray(a), mode).save(b, "PNG", compress_level=6)
        return ".png", b.getvalue()
    np.save(b, a, allow_pickle=False)
    return ".npy", b.getvalue()


def _decoder(nom: str, donnees: bytes) -> np.ndarray:
    if nom.endswith(".npy"):
        return np.load(io.BytesIO(donnees), allow_pickle=False)
    from PIL import Image
    return np.asarray(Image.open(io.BytesIO(donnees))).copy()


def _petite(a: np.ndarray) -> np.ndarray:
    """Vignette (APERCU px au plus) : seulement pour l'affichage dans la liste."""
    h, w = a.shape[:2]
    if max(h, w) <= APERCU:
        return a
    from PIL import Image
    a8 = a if a.dtype == np.uint8 else (a.astype(np.float32) / max(1.0, float(a.max())) * 255).astype(np.uint8)
    if a8.ndim == 3 and a8.shape[2] not in (3, 4):
        a8 = a8[..., 0]
    k = APERCU / max(h, w)
    return np.asarray(Image.fromarray(np.ascontiguousarray(a8)).resize((max(1, round(w * k)), max(1, round(h * k))),
                                                                       Image.LANCZOS))


class _Paquet:
    """Un fichier .pixpaquet : ouvert le temps d'une lecture (le fichier reste libre, on peut le retirer)."""

    def __init__(self, chemin: Path):
        self.chemin = chemin
        self._apercus = None

    def lire(self, nom: str) -> np.ndarray:
        with _verrou_zip, zipfile.ZipFile(self.chemin) as z:
            return _decoder(nom, z.read(nom))

    def apercu(self, nom: str):
        if self._apercus is None:                   # toutes les vignettes d'un coup (petites)
            with _verrou_zip, zipfile.ZipFile(self.chemin) as z:
                self._apercus = {n: _decoder(n, z.read(n)) for n in z.namelist() if n.startswith("v/")}
        return self._apercus.get(nom)


class PinceauPaquet(Pinceau):
    """Pinceau rangé dans un paquet : ses formes ne sont lues qu'à la première utilisation."""

    def __init__(self, nom, espacement, cle, paquet: _Paquet, fichiers: list, couleur: bool, apercu: str):
        self._formes = None
        super().__init__(nom, None, espacement, cle)
        self._paquet, self._fichiers, self._couleur, self._apercu = paquet, fichiers, couleur, apercu

    @property
    def formes(self):
        if self._formes is None:
            self._formes = [self._paquet.lire(n) for n in self._fichiers]
        return self._formes

    @formes.setter
    def formes(self, valeur):
        if valeur is not None:
            self._formes = valeur

    @property
    def en_couleur(self) -> bool:
        return self._couleur

    @property
    def apercu(self):
        return self._paquet.apercu(self._apercu)


class MotifPaquet(Motif):
    """Motif rangé dans un paquet : son image n'est lue qu'à la première utilisation."""

    def __init__(self, nom, cle, paquet: _Paquet, fichier: str, apercu: str):
        self._image = None
        super().__init__(nom, None, cle)
        self._paquet, self._fichier, self._apercu = paquet, fichier, apercu

    @property
    def image(self):
        if self._image is None:
            self._image = self._paquet.lire(self._fichier)
        return self._image

    @image.setter
    def image(self, valeur):
        if valeur is not None:
            self._image = valeur

    @property
    def apercu(self):
        return self._paquet.apercu(self._apercu)


def ecrire_paquet(cible: Path, groupe: str, genre: str, elements: list, ignores: list, source: str) -> None:
    """Range les éléments (lus en pleine taille) dans un paquet. Écrit à côté puis renomme : un paquet à moitié
    écrit n'existe jamais sous son vrai nom."""
    index = {"version": 1, "groupe": groupe, "genre": genre, "source": source,
             "ignores": [list(i) for i in ignores], "elements": []}
    tmp = cible.with_name(cible.name + ".part")
    try:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_STORED) as z:     # PNG : déjà compressé
            def ranger(nom, a):
                ext, octets = _encoder(a)
                z.writestr(nom + ext, octets)
                return nom + ext
            for i, e in enumerate(elements):
                premiere = e.image if genre == MOTIFS else e.formes[0]
                d = {"nom": e.nom, "cle": e.cle, "apercu": ranger(f"v/{i}", _petite(premiere))}
                if genre == MOTIFS:
                    d["fichier"] = ranger(f"m/{i}", e.image)
                else:
                    d["formes"] = [ranger(f"f/{i}_{k}", f) for k, f in enumerate(e.formes)]
                    d["espacement"] = e.espacement
                    d["couleur"] = bool(premiere.ndim == 3)
                index["elements"].append(d)
            z.writestr("index.json", json.dumps(index, ensure_ascii=False))
        os.replace(tmp, cible)
    finally:
        tmp.unlink(missing_ok=True)


def lire_paquet(chemin: Path) -> "Groupe":
    """Groupe d'après la liste du paquet (rapide) : pinceaux, motifs et vignettes sont lus à la demande."""
    with _verrou_zip, zipfile.ZipFile(chemin) as z:
        index = json.loads(z.read("index.json"))
    pq = _Paquet(chemin)
    genre = index["genre"]
    if genre == MOTIFS:
        elements = [MotifPaquet(e["nom"], e["cle"], pq, e["fichier"], e["apercu"]) for e in index["elements"]]
    else:
        elements = [PinceauPaquet(e["nom"], e.get("espacement", 0.25), e["cle"], pq, e["formes"],
                                  e.get("couleur", False), e["apercu"]) for e in index["elements"]]
    return Groupe(index["groupe"], genre, False, [chemin], _elements=elements,
                  ignores=[tuple(i) for i in index.get("ignores", [])])


def paquet_depuis_fichier(fichier: Path, cible: Path, groupe: str, genre: str) -> int:
    """Lit un fichier de pinceaux / motifs à sa taille d'origine et le range dans un paquet. Renvoie le nombre
    d'éléments ; ValueError s'il n'y a rien de lisible."""
    c = lire_fichier(fichier, "motif" if genre == MOTIFS else "forme", pleine_taille=True)
    elements = elements_de(c, genre, fichier, groupe)
    if not elements:
        raise ValueError("aucun pinceau ni motif lisible dans ce fichier")
    ecrire_paquet(cible, groupe, genre, elements, c.ignores, fichier.name)
    return len(elements)


def verifier_paquet(cible: Path, nombre: int) -> None:
    """Le paquet se relit et contient bien `nombre` éléments (sinon ValueError)."""
    g = lire_paquet(cible)
    if len(g.elements) != nombre:
        raise ValueError(f"paquet incomplet ({len(g.elements)} sur {nombre})")
    for e in (g.elements[0], g.elements[-1]):
        if (e.image if g.genre == MOTIFS else e.formes[0]) is None:
            raise ValueError("paquet illisible")


def dossier_utilisateur() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Pixane"
    nom = "bibliotheque"
    if os.environ.get("PIXANE_REGLAGES"):            # essais : à part
        nom += "-" + os.environ["PIXANE_REGLAGES"]
    return base / nom


def _accepte(f: Path, genre: str) -> bool:
    ext = f.suffix.lower()
    return ext in (EXT_PINCEAUX if genre == PINCEAUX else EXT_MOTIFS) + EXT_IMAGES


class Bibliotheque:
    def __init__(self, dossier: Path | None = None):
        self._en_cours: dict = {}         # lectures en arrière-plan : groupe -> fonctions à rappeler
        self._fini: list = []
        self.dossier = Path(dossier) if dossier else dossier_utilisateur()
        self.groupes: dict[str, list[Groupe]] = {}
        self.recharger()

    def recharger(self) -> None:
        for genre in (PINCEAUX, MOTIFS):
            liste = []
            if genre == PINCEAUX:                 # styles prêts, simples, puis les pinceaux de Krita par familles
                liste.append(Groupe(STYLES, PINCEAUX, True, [], fabrique=lambda: styles_prets(self)))
                liste.append(groupe_simples())
                fichiers = [f for court, _n in GROUPES_BASE if (BASE / court / genre).is_dir()
                            for f in (BASE / court / genre).iterdir() if _accepte(f, genre)]
                par_famille: dict[str, list] = {}
                for f in fichiers:
                    par_famille.setdefault(famille(f.name), []).append(f)
                for nom, _mots in FAMILLES + [(DIVERS, ())]:
                    if par_famille.get(nom):
                        liste.append(Groupe(nom, genre, True, sorted(par_famille[nom], key=lambda p: p.name.lower())))
            else:
                for court, nom in GROUPES_BASE:
                    d = BASE / court / genre
                    if d.is_dir():
                        liste.append(Groupe(nom, genre, True, sorted(f for f in d.iterdir() if _accepte(f, genre))))
            for f in self._fichiers_utilisateur(genre):
                if f.name.endswith(PAQUET):
                    try:
                        liste.append(lire_paquet(f))
                    except Exception:             # paquet abîmé : on le saute (la liste reste utilisable)
                        continue
                elif not f.with_name(f.name + PAQUET).is_file():     # ancienne copie pas encore convertie
                    liste.append(Groupe(f.stem, genre, False, [f]))
            self.groupes[genre] = liste

    def _fichiers_utilisateur(self, genre: str) -> list:
        d = self.dossier / genre
        if not d.is_dir():
            return []
        return [f for f in sorted(d.iterdir(), key=lambda p: p.name.lower()) if f.is_file()
                and not f.name.endswith(".part")]

    def anciens(self) -> list:
        """Copies telles quelles (d'avant les paquets) encore à convertir : [(genre, chemin)]."""
        return [(genre, f) for genre in (PINCEAUX, MOTIFS) for f in self._fichiers_utilisateur(genre)
                if not f.name.endswith(PAQUET)]

    def convertir_anciens(self, fini=None) -> None:
        """Convertit en arrière-plan les anciennes copies en paquets (taille d'origine, sans perte). Chaque copie
        n'est effacée qu'une fois son paquet écrit et relu. À la fin (dans la boucle de Qt) : recharger, puis
        fini(nombre_converti). Une copie illisible reste telle quelle."""
        from PySide6.QtCore import QTimer
        travail = self.anciens()
        if not travail or getattr(self, "_conversion", False):
            return
        self._conversion = True
        faits: list = []
        termine: list = []

        def convertir():
            try:
                for genre, f in travail:
                    cible = f.with_name(f.name + PAQUET)
                    try:
                        if not cible.is_file():
                            n = paquet_depuis_fichier(f, cible, f.stem, genre)
                            verifier_paquet(cible, n)
                        else:
                            lire_paquet(cible)            # déjà converti (copie pas encore effacée)
                        faits.append(f)
                    except Exception:             # paquet raté ou abîmé : retiré, la copie reste
                        try:
                            cible.unlink(missing_ok=True)
                        except OSError:
                            pass
            finally:
                termine.append(1)

        threading.Thread(target=convertir, daemon=True).start()

        def surveiller():
            if not termine:
                QTimer.singleShot(500, surveiller)
                return
            self._conversion = False
            self.recharger()                          # les groupes lisent maintenant les paquets
            for f in faits:
                try:
                    _effacer(f)
                except OSError:                       # encore ouvert : effacé au prochain démarrage
                    pass
            if fini is not None:
                fini(len(faits))
        QTimer.singleShot(500, surveiller)

    def elements(self, genre: str) -> list:
        return [e for g in self.groupes[genre] for e in g.elements]

    def trouver(self, genre: str, cle: str):
        groupe, _, reste = cle.partition("/")
        for g in self.groupes[genre]:
            if g.nom == groupe:
                for e in g.elements:
                    if e.cle == cle:
                        return e
        if groupe in ANCIENS_GROUPES and genre == PINCEAUX:     # clé d'avant le classement par familles
            return self.par_fichier(reste)
        return None

    def _groupe_de(self, genre: str, cle: str):
        nom = cle.partition("/")[0]
        return next((g for g in self.groupes[genre] if g.nom == nom), None)

    def connu(self, genre: str, cle: str) -> bool:
        """Le groupe de cette clé existe encore (sans lire ses fichiers : un .abr peut faire plus d'un Go)."""
        g = self._groupe_de(genre, cle)
        if g is not None and g._elements is None and g.fabrique is None:
            return all(f.is_file() for f in g.fichiers)
        return self.trouver(genre, cle) is not None

    def pret(self, genre: str, cle: str) -> bool:
        """Faux si trouver(cle) devrait d'abord lire un fichier de l'utilisateur (lent pour un gros fichier)."""
        g = self._groupe_de(genre, cle)
        return g is None or not g.a_lire_lentement()

    def charger_en_fond(self, genre: str, cle: str, fini) -> None:
        """Lit en arrière-plan le groupe de cette clé, puis appelle fini() dans la boucle de Qt (une seule
        lecture à la fois par groupe)."""
        import threading
        from PySide6.QtCore import QTimer
        g = self._groupe_de(genre, cle)
        if g is None:
            fini()
            return
        attente = self._en_cours.setdefault(id(g), [])
        attente.append(fini)
        if len(attente) > 1:
            return

        def lire():
            try:
                g.elements
            finally:
                self._fini.append(id(g))

        threading.Thread(target=lire, daemon=True).start()

        def surveiller():
            if id(g) not in self._fini:
                QTimer.singleShot(200, surveiller)
                return
            self._fini.remove(id(g))
            for f in self._en_cours.pop(id(g), []):
                f()
        QTimer.singleShot(200, surveiller)

    def par_fichier(self, nom: str):
        """Pinceau de base d'après « fichier#n » (quelle que soit sa famille)."""
        fichier = nom.split("#", 1)[0]
        g = next((g for g in self.groupes[PINCEAUX] if g.de_base and g.fabrique is None
                  and any(f.name == fichier for f in g.fichiers)), None)
        return next((e for e in g.elements if e.cle.endswith("/" + nom)), None) if g else None

    def importer(self, chemin: str | Path, image_comme: str = PINCEAUX) -> dict:
        """Ajoute un fichier : copié dans la bibliothèque (pinceaux et/ou motifs selon ce qu'il contient ; une
        image devient un pinceau ou un motif selon image_comme). Renvoie {"pinceaux": n, "motifs": n, "ignores": [...]}; ValueError si le fichier n'apporte rien."""
        chemin = Path(chemin)
        ext = chemin.suffix.lower()
        if ext not in EXT_PINCEAUX + EXT_MOTIFS + EXT_IMAGES + EXT_PAQUETS:
            raise ValueError("format de fichier inconnu")
        comme = "motif" if ext in EXT_MOTIFS or (ext in EXT_IMAGES and image_comme == MOTIFS) else "forme"
        bilan = {PINCEAUX: 0, MOTIFS: 0, "ignores": []}
        if ext in EXT_PAQUETS:                   # paquet : chacun de ses fichiers de pinceaux / motifs, à part
            with zipfile.ZipFile(chemin) as z, tempfile.TemporaryDirectory(prefix="pixane-") as tmp:
                for n in z.namelist():
                    d, _, f = n.partition("/")
                    genre = {"brushes": PINCEAUX, "patterns": MOTIFS}.get(d)
                    if not (genre and f and "/" not in f and _accepte(Path(f), genre)):
                        continue
                    nom = self._nom_libre(genre, f"{chemin.stem} - {f}")
                    source = Path(tmp) / nom
                    source.write_bytes(z.read(n))
                    try:
                        bilan[genre] += self._ranger(source, genre, nom, bilan)
                    except ValueError as e:
                        bilan["ignores"].append((f, str(e)))
                    finally:
                        source.unlink(missing_ok=True)
        else:
            c = lire_fichier(chemin, comme, pleine_taille=True)     # une seule lecture, à la taille d'origine
            if not c.formes and not c.motifs:
                raise ValueError("aucun pinceau ni motif lisible dans ce fichier")
            genre = MOTIFS if c.motifs else PINCEAUX
            nom = self._nom_libre(genre, chemin.name)
            elements = elements_de(c, genre, Path(nom), Path(nom).stem)
            cible = self.dossier / genre / (nom + PAQUET)
            ecrire_paquet(cible, Path(nom).stem, genre, elements, c.ignores, chemin.name)
            verifier_paquet(cible, len(elements))
            bilan[genre] = len(elements)
            bilan["ignores"] += list(c.ignores)
        if not bilan[PINCEAUX] and not bilan[MOTIFS]:
            raise ValueError("aucun pinceau ni motif lisible dans ce fichier")
        self.recharger()
        return bilan

    def _ranger(self, source: Path, genre: str, nom: str, bilan: dict) -> int:
        """Un fichier (tiré d'un paquet de Krita) devient un paquet de la bibliothèque. Renvoie le nombre."""
        cible = self.dossier / genre / (nom + PAQUET)
        n = paquet_depuis_fichier(source, cible, Path(nom).stem, genre)
        verifier_paquet(cible, n)
        bilan["ignores"] += lire_paquet(cible).ignores
        return n

    def _nom_libre(self, genre: str, nom: str) -> str:
        """Nom de fichier pas encore pris (ni copie ancienne ni paquet) : « nom (2).abr »…"""
        d = self.dossier / genre
        d.mkdir(parents=True, exist_ok=True)
        essai, k = nom, 2
        while (d / essai).exists() or (d / (essai + PAQUET)).exists():
            essai = f"{Path(nom).stem} ({k}){Path(nom).suffix}"
            k += 1
        return essai

    def retirer(self, groupe: Groupe) -> None:
        """Retire un groupe ajouté par l'utilisateur (les groupes de base restent)."""
        if groupe.de_base:
            raise ValueError("groupe de base")
        for f in groupe.fichiers:
            _effacer(f)
            ancien = f.with_name(f.name[:-len(PAQUET)]) if f.name.endswith(PAQUET) else None
            if ancien is not None and ancien.exists():   # copie d'origine pas encore effacée
                _effacer(ancien)
        self.recharger()


def _effacer(f: Path) -> None:
    import stat
    if f.exists():
        f.chmod(stat.S_IWRITE | stat.S_IREAD)            # lecture seule (copié d'un original protégé)
    f.unlink(missing_ok=True)


# ---- familles (comme les dossiers de pinceaux de Photoshop) : d'après le nom du fichier
STYLES = "Styles prêts"
DIVERS = "Divers"
ANCIENS_GROUPES = ("Krita 4", "Krita 3")
FAMILLES = [
    ("Crayon et fusain", ("pencil", "graphite", "crayon", "sketch", "study", "chalk", "charcoal")),
    ("Peinture", ("oil", "bristle", "rake", "brush", "smear", "knife", "chisel", "watercolor", "flat_textured",
                  "impressionism", "smudge", "eroded", "dynamic", "3_dotted", "3_splat", "rect_textured", "fibers")),
    ("Nature", ("grass", "leaves", "leaf", "vegetal", "bamboo", "foliage", "herbs", "flowers", "trees", "rock",
                "mountain", "water", "snow", "smoke", "cloud", "floor", "fur", "hair", "scales", "reptile",
                "mineral", "provencal", "coroballs", "spines")),
    ("Effets", ("sparkle", "star", "fairy", "bokey", "splat", "hearts", "dust", "particles", "debris", "sparks",
                "freckles", "lucky", "snowman")),
    ("Textures", ("texture", "noise", "concrete", "wall", "brick", "abstract", "rough", "scratch", "crackle",
                  "dirty", "spike", "square", "gradient", "scribbles", "circle_hard")),
    ("Formes", ("shape", "m_0", "u_circle", "z_", "te_", "pipe", "triangle", "arrow", "chain", "braids", "church",
                "cage", "bulb", "pin.", "a_pin", "techno")),
]


def famille(nom_fichier: str) -> str:
    n = nom_fichier.lower()
    for nom, mots in FAMILLES:
        if any(m in n for m in mots):
            return nom
    return DIVERS


# ---- styles prêts : une forme et ses réglages, en un clic (comme les préréglages d'outils de Photoshop)
_PAPIER = "Krita 4/04_paper-C-grain.png#0"
_TOILE = "Krita 4/02_rough-canvas.png#0"
_AQUARELLE = "Krita 4/03_default-paper.png#0"
STYLES_PRETS = [
    ("crayon", "Crayon", "Simples/rond_dur#0",
     dict(espacement=0.06, texture=_PAPIER, texture_force=0.7, texture_echelle=0.6, flux=0.85, pression_opacite=True)),
    ("fusain", "Fusain", "graphite_grain.gih#0",
     dict(espacement=0.06, texture=_PAPIER, texture_force=0.5, var_angle=0.1)),
    ("craie", "Craie", "chalk_round_hard.png#0",
     dict(espacement=0.08, texture=_PAPIER, texture_force=0.75, texture_echelle=1.5, var_angle=0.15,
          var_taille=0.1)),
    ("encre", "Encre (plume)", "Simples/rond_dur#0", dict(espacement=0.04, pression_taille=True, taille_min=0.15)),
    ("feutre", "Feutre", "Simples/rond_dur#0", dict(espacement=0.05, rondeur=0.75, angle=30, flux=0.6)),
    ("calligraphie", "Calligraphie", "Simples/biseau#0", dict(espacement=0.03)),
    ("aquarelle", "Aquarelle", "watercolor.gih#0",
     dict(espacement=0.12, flux=0.3, texture=_AQUARELLE, texture_force=0.45, var_luminosite=0.04,
          var_angle=0.3)),
    ("huile", "Peinture à l'huile", "oil_bristle.png#0",
     dict(espacement=0.08, suivre=True, var_luminosite=0.05)),
    ("couteau", "Couteau à peindre", "oil_knife.png#0", dict(espacement=0.06, suivre=True, var_luminosite=0.04)),
    ("sec", "Pinceau sec", "bristles_circle_sparse.png#0",
     dict(espacement=0.06, suivre=True, texture=_TOILE, texture_force=0.5)),
    ("aerographe", "Aérographe", "Simples/aerographe#0", dict(espacement=0.05, flux=0.15)),
    ("bombe", "Bombe (spray)", "random_particles.png#0",
     dict(espacement=0.25, dispersion=0.3, deux_axes=True, var_angle=1.0, flux=0.8)),
    ("feuillage", "Feuillage", "leaves.png#0",
     dict(espacement=0.45, dispersion=1.0, deux_axes=True, nombre=2, var_taille=0.5, var_angle=1.0,
          var_teinte=0.04, var_luminosite=0.25, melange_fond=0.3)),
    ("herbe", "Herbe", "grass.gih#0",
     dict(espacement=0.3, dispersion=0.4, var_taille=0.4, var_luminosite=0.15, var_teinte=0.03)),
    ("etoiles", "Étoiles et paillettes", "sparkle.png#0",
     dict(espacement=0.6, dispersion=1.0, deux_axes=True, nombre=2, var_taille=0.6, taille_min=0.4, var_angle=1.0)),
    ("fumee", "Nuages et fumée", "smoke.png#0",
     dict(espacement=0.3, flux=0.3, dispersion=0.3, var_taille=0.5, var_angle=1.0)),
    ("eclaboussures", "Éclaboussures", "splats_large.gih#0",
     dict(espacement=0.7, dispersion=0.6, deux_axes=True, var_taille=0.5, taille_min=0.4, var_angle=1.0)),
]


def styles_prets(biblio: "Bibliotheque") -> list:
    from .langue import tr
    liste = []
    for cle, nom, base, reglages in STYLES_PRETS:
        e = biblio.trouver(PINCEAUX, base) if base.startswith(SIMPLES + "/") else biblio.par_fichier(base)
        if e is not None:
            liste.append(Pinceau(tr(nom), e.formes, e.espacement, f"{STYLES}/{cle}#0", dict(reglages)))
    return liste


_unique: Bibliotheque | None = None


def bibliotheque() -> Bibliotheque:
    """La bibliothèque de Pixane (une seule, créée à la première demande)."""
    global _unique
    if _unique is None:
        _unique = Bibliotheque()
    return _unique
