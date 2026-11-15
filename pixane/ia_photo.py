"""IA pour la photo : sélectionner / remplacer le ciel (SAM 3.1 + Flux Fill), coloriser et changer la lumière
(Flux Kontext), flou selon la profondeur (Depth Anything 3 : carte de profondeur, puis flou calculé par Pixane).

Mélangé à la fenêtre (Fenetre) : utilise moteur, doc, historique, _tache, _lancer, Attente…
"""
from __future__ import annotations

import threading

import numpy as np
from PIL import Image, ImageFilter
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QLabel, QMessageBox, QVBoxLayout

from . import choix_exemple, recettes
from .document import FORMAT_IMAGE, tableau
from .langue import tr
from .moteur import ErreurMoteur


def noms_ciels() -> dict:
    return {"bleu": tr("Ciel bleu avec quelques nuages"), "nuages": tr("Grands nuages"),
            "coucher": tr("Coucher de soleil"), "orage": tr("Ciel d'orage"), "nuit": tr("Nuit étoilée"),
            "aube": tr("Aube (couleurs pastel)")}


def noms_lumieres() -> dict:
    return {"doree": tr("Lumière dorée de fin de journée"), "studio": tr("Lumière douce de studio"),
            "gauche": tr("Lumière venant de la gauche"),
            "droite": tr("Lumière venant de la droite"), "contre_jour": tr("Contre-jour"),
            "nuit": tr("Nuit, éclairée par des lampadaires"), "neon": tr("Néons colorés"),
            "nuageux": tr("Temps couvert, sans ombres")}


# ------------------------------------------------------------------ bord du ciel (calcul)
def _flou_boite(a: np.ndarray, r: int, passes: int = 3) -> np.ndarray:
    """Flou rapide (moyenne glissante, répétée : proche d'un flou gaussien) d'un tableau (h, w) ou (h, w, c)."""
    r = max(1, int(r))
    for _ in range(passes):
        for axe in (0, 1):
            n = a.shape[axe]
            c = np.cumsum(np.pad(a, [(r + 1, r) if i == axe else (0, 0) for i in range(a.ndim)], mode="edge"),
                          axis=axe, dtype=np.float64)
            a = ((np.take(c, range(2 * r + 1, 2 * r + 1 + n), axis=axe)
                  - np.take(c, range(0, n), axis=axe)) / (2 * r + 1)).astype(np.float32)
    return a


def _petit(a: np.ndarray, pw: int, ph: int) -> np.ndarray:
    return np.asarray(Image.fromarray(a.astype(np.float32), "F").resize((pw, ph), Image.BILINEAR), np.float32)


def _grand(a: np.ndarray, w: int, h: int) -> np.ndarray:
    return np.asarray(Image.fromarray(a.astype(np.float32), "F").resize((w, h), Image.BILINEAR), np.float32)


def couleur_ciel(rgb: np.ndarray, ciel: np.ndarray) -> np.ndarray:
    """Couleur du ciel autour de chaque point (moyenne du ciel sûr, prolongée sous les objets), (h, w, 3)."""
    h, w = ciel.shape
    k = min(1.0, 512 / max(h, w))
    pw, ph = max(1, round(w * k)), max(1, round(h * k))
    sur = (_flou_boite(_petit(ciel.astype(np.float32), pw, ph), 2, 1) > 0.99).astype(np.float32)
    if sur.sum() < 20:
        sur = _petit(ciel.astype(np.float32), pw, ph)
    f = np.dstack([_petit(rgb[..., i], pw, ph) for i in range(3)])
    r = max(3, round(max(pw, ph) * 0.06))
    den = np.maximum(_flou_boite(sur, r), 1e-4)[..., None]
    moy = _flou_boite(f * sur[..., None], r) / den
    return np.dstack([_grand(moy[..., i], w, h) for i in range(3)])


def composer_ciel(original: np.ndarray, nouveau: np.ndarray, sam: np.ndarray, fin: np.ndarray) -> np.ndarray:
    """Nouveau ciel recollé : là où l'IA a trouvé le ciel (sam, 0..1), les pixels du nouveau ciel ; dans le bord
    affiné (fin, 0..1 : entre les branches…), seulement un décalage des couleurs de l'ancien ciel vers le nouveau
    (comme « Décontaminer les couleurs ») : les branches gardent leur couleur. Tableaux (h, w, 3 ou 4)."""
    ciel = sam > 0.5
    o = original[..., :3].astype(np.float32)
    n = nouveau[..., :3].astype(np.float32)
    decale = o + (couleur_ciel(n, ciel) - couleur_ciel(o, ciel)) * fin[..., None]
    res = n * sam[..., None] + decale * (1 - sam[..., None])
    out = original.copy()
    out[..., :3] = np.clip(np.round(res), 0, 255).astype(np.uint8)
    return out


def affiner_ciel(ciel: np.ndarray, rgb: np.ndarray) -> np.ndarray:
    """Bord du ciel affiné d'après les couleurs (comme « Améliorer le contour ») : près du ciel trouvé par l'IA, la
    part de ciel de chaque pixel (le ciel entre les branches d'un arbre nu, que SAM laisse avec l'arbre ; les pixels
    mi-branche mi-ciel comptent pour moitié). ciel : booléens (h, w) ; rgb : (h, w, 3). Renvoie 0..1."""
    h, w = ciel.shape
    if ciel.all() or not ciel.any():
        return ciel.astype(np.float32)
    k = min(1.0, 512 / max(h, w))                                   # couleurs du ciel calculées en petit
    pw, ph = max(1, round(w * k)), max(1, round(h * k))
    sur = (_flou_boite(_petit(ciel.astype(np.float32), pw, ph), 2, 1) > 0.99).astype(np.float32)
    if sur.sum() < 20:
        return ciel.astype(np.float32)
    f = np.dstack([_petit(rgb[..., i], pw, ph) for i in range(3)])
    r = max(3, round(max(pw, ph) * 0.06))
    den = _flou_boite(sur, r)
    moy = _flou_boite(f * sur[..., None], r) / np.maximum(den, 1e-4)[..., None]
    var = _flou_boite(f * f * sur[..., None], r) / np.maximum(den, 1e-4)[..., None] - moy * moy
    ecart = np.sqrt(np.maximum(var, 0).mean(axis=2))
    proche = _flou_boite(_petit(ciel.astype(np.float32), pw, ph), max(2, round(max(pw, ph) * 0.05)), 2)
    moy = np.dstack([_grand(moy[..., i], w, h) for i in range(3)])
    seuil = 22 + 2 * _grand(ecart, w, h)
    d = np.sqrt(((rgb.astype(np.float32) - moy) ** 2).sum(axis=2))   # écart à la couleur du ciel
    # démélange : distance de la couleur « objet » (branche, mur…) autour, mesurée sur ce qui n'est sûrement pas
    # du ciel ; un pixel à mi-chemin est à moitié ciel
    k2 = min(1.0, 1024 / max(h, w))
    qw, qh = max(1, round(w * k2)), max(1, round(h * k2))
    d2 = _petit(d, qw, qh)
    s2 = _petit(seuil, qw, qh)
    objet = (d2 > 2 * s2).astype(np.float32)
    r2 = max(2, round(max(qw, qh) * 0.02))
    loin = _flou_boite(d2 * objet, r2) / np.maximum(_flou_boite(objet, r2), 1e-4)
    loin = _grand(np.maximum(loin, 2 * s2), w, h)
    part = np.clip(1 - (d - 0.5 * seuil) / np.maximum(loin - 0.5 * seuil, 1), 0, 1)
    # seulement là où il y a des trous de ciel tout près (un arbre nu, pas un mur clair)
    trous = _flou_boite((d2 < s2).astype(np.float32), max(2, round(max(qw, qh) * 0.008)))
    part = part * np.clip(_grand(trous, w, h) * 3, 0, 1)
    zone = (_grand(proche, w, h) > 0.01) & (_grand(den, w, h) > 0.02)
    return np.where(ciel, 1.0, np.where(zone, part, 0.0)).astype(np.float32)


# ------------------------------------------------------------------ flou selon la profondeur (calcul)
def _a_la_taille(carte: np.ndarray, w: int, h: int) -> np.ndarray:
    if carte.shape == (h, w):
        return carte
    return np.asarray(Image.fromarray((carte * 255).astype(np.uint8)).resize((w, h), Image.BILINEAR),
                      np.float32) / 255


def _appliquer_traits(quantite: np.ndarray, traits: list) -> np.ndarray:
    """Coups de pinceau de la fenêtre : ("net" | "flou", x, y, rayon) en pixels de l'image. « net » : pas de flou
    là ; « flou » : flou maximal là. Bord adouci."""
    from PIL import ImageDraw
    h, w = quantite.shape
    masques = {"net": Image.new("L", (w, h), 0), "flou": Image.new("L", (w, h), 0)}
    dessins = {k: ImageDraw.Draw(m) for k, m in masques.items()}
    rmin = None
    for genre, x, y, r in traits:
        if genre in dessins:
            dessins[genre].ellipse((x - r, y - r, x + r, y + r), fill=255)
            rmin = r if rmin is None else min(rmin, r)
    doux = max(1.0, (rmin or 4) / 4)
    # bord adouci, mais franc au milieu du coup de pinceau (exactement net ou exactement flou)
    net, flou = (np.clip(np.asarray(masques[k].filter(ImageFilter.GaussianBlur(doux)), np.float32) / 255 * 1.25, 0, 1)
                 for k in ("net", "flou"))
    return np.maximum(quantite * (1 - net), flou)


def flou_profondeur(rgba: np.ndarray, prof: np.ndarray, p: dict, sujet: np.ndarray | None = None) -> np.ndarray:
    """rgba (h, w, 4) ; prof (h, w) 0..1 (proche = 1). p : x, y (point net), flou (rayon max, px), zone (0..100 :
    profondeur gardée nette autour du point), arriere (seulement ce qui est plus loin que le point), sujet (garder
    net tout le sujet : masque `sujet` 0..1, 1 = sujet, donné par le détourage), traits (pinceau « garder net » /
    « rendre flou », voir _appliquer_traits)."""
    h, w = rgba.shape[:2]
    prof = _a_la_taille(prof, w, h)
    x = int(min(w - 1, max(0, p.get("x", w // 2))))
    y = int(min(h - 1, max(0, p.get("y", h // 2))))
    net = float(np.median(prof[max(0, y - 2):y + 3, max(0, x - 2):x + 3]))
    zone = p.get("zone", 15) / 100 * 0.5
    ecart = net - prof if p.get("arriere", False) else np.abs(prof - net)
    quantite = np.clip((ecart - zone) / max(1e-3, 1 - zone) * 2.0, 0, 1)        # 0 = net, 1 = flou maximal
    traits = p.get("traits") or []
    if traits:
        quantite = _appliquer_traits(quantite, traits)
    if sujet is not None and p.get("sujet", True):
        # la carte de profondeur se trompe parfois sur une partie du sujet (veste grise devant un mur gris) :
        # le détourage la rattrape
        quantite = quantite * (1 - _a_la_taille(sujet, w, h))
    rmax = float(p.get("flou", 20))
    if rmax <= 0.3 or not quantite.any():
        return rgba.copy()
    f = rgba.astype(np.float32)
    f[..., :3] *= f[..., 3:4] / 255                                            # prémultiplié : pas de halo
    niveaux = [0.0, 0.15, 0.35, 0.6, 1.0]
    # le flou ne prend que ce qui est lui-même flou : les parties nettes (le sujet) ne bavent pas en halo clair
    # autour d'elles
    poids = np.clip(quantite / niveaux[1], 0, 1)[..., None]
    fp = Image.fromarray(np.clip(np.round(f * poids), 0, 255).astype(np.uint8), "RGBA")
    pp = Image.fromarray(np.round(poids[..., 0] * 255).astype(np.uint8), "L")
    flous = []
    for k in niveaux:
        r = rmax * k
        if r < 0.3:
            flous.append(f)
            continue
        bf = np.asarray(fp.filter(ImageFilter.GaussianBlur(r)), np.float32)       # canaux flous un à un
        bp = np.asarray(pp.filter(ImageFilter.GaussianBlur(r)), np.float32)[..., None] / 255
        flous.append(np.where(bp > 0.01, bf / np.maximum(bp, 0.01), f))
    # entre deux niveaux : mélange selon la quantité de flou du point
    pos = quantite * (len(niveaux) - 1)
    i0 = np.clip(pos.astype(np.int32), 0, len(niveaux) - 2)
    t = (pos - i0)[..., None]
    res = np.zeros_like(f)
    for i in range(len(niveaux) - 1):
        m = (i0 == i)[..., None]
        if m.any():
            res = np.where(m, flous[i] * (1 - t) + flous[i + 1] * t, res)
    a = res[..., 3:4]
    res[..., :3] = np.where(a > 0.5, res[..., :3] * 255 / np.maximum(a, 1e-3), 0)
    return np.clip(np.round(res), 0, 255).astype(np.uint8)


def panneau_profondeur(rgba: np.ndarray, prof: np.ndarray, avec_sujet: bool = False):
    """Panneau de la fenêtre de réglage : clic = point qui reste net ; flou ; zone nette ; arrière seulement."""
    from PySide6.QtCore import Signal
    from PySide6.QtWidgets import QButtonGroup, QCheckBox, QHBoxLayout, QPushButton, QRadioButton
    from .dialogues_reglage import Curseur, _Panneau
    from .plage_couleurs import ApercuCliquable

    class ApercuPinceau(ApercuCliquable):
        """Aperçu cliquable qui suit aussi le glisser (pinceau)."""
        glisse = Signal(int, int)
        lache = Signal()

        def _point(self, e):
            h, w = self.rgba.shape[:2]
            return (int(min(w - 1, max(0, e.position().x() / self.k))),
                    int(min(h - 1, max(0, e.position().y() / self.k))))

        def mouseMoveEvent(self, e):
            if e.buttons() & Qt.LeftButton:
                self.glisse.emit(*self._point(e))

        def mouseReleaseEvent(self, e):
            self.lache.emit()

    class PanneauProfondeur(_Panneau):
        def __init__(self, params, histo):
            super().__init__(params, histo)
            lay = QVBoxLayout(self)
            info = QLabel(tr("Cliquez sur ce qui doit rester net. Clair = proche, foncé = loin."))
            info.setWordWrap(True)
            lay.addWidget(info)
            # l'IA se trompe parfois : pinceau pour garder net ou rendre flou à la main
            modes = QHBoxLayout()
            self.modes = QButtonGroup(self)
            for i, texte in enumerate((tr("Point net"), tr("Pinceau : garder net"), tr("Pinceau : rendre flou"))):
                b = QRadioButton(texte)
                b.setChecked(i == 0)
                self.modes.addButton(b, i)
                modes.addWidget(b)
            modes.addStretch(1)
            lay.addLayout(modes)
            gris = np.dstack([(prof * 255).astype(np.uint8)] * 3 + [np.full(prof.shape, 255, np.uint8)])
            self.apercu = ApercuPinceau(gris)
            self.apercu.setToolTip(tr("Clic : le point qui reste net. Avec un pinceau : peindre les endroits à "
                                      "corriger."))
            self.apercu.clic.connect(self._clic)
            self.apercu.glisse.connect(self._peindre)
            self.apercu.lache.connect(self._fin_trait)
            lay.addWidget(self.apercu, 0, Qt.AlignHCenter)
            pinceau = QHBoxLayout()
            self.c_pinceau = Curseur(tr("Taille du pinceau"), 1, 30, 6, " %")
            self.effacer_traits = QPushButton(tr("Effacer les coups de pinceau"))
            self.effacer_traits.clicked.connect(self._effacer_traits)
            pinceau.addWidget(self.c_pinceau, 1)
            pinceau.addWidget(self.effacer_traits)
            lay.addLayout(pinceau)
            self._trait_en_cours = False
            self.c_flou = Curseur(tr("Flou"), 0, 80, self.p.get("flou", 20), " px")
            self.c_zone = Curseur(tr("Zone nette"), 0, 100, self.p.get("zone", 15), " %")
            self.sujet = QCheckBox(tr("Garder net tout le sujet (personnes, objet principal)"))
            self.sujet.setToolTip(tr("Le détourage rattrape ce que la carte de profondeur met à tort au loin (par "
                                     "exemple une veste grise devant un mur gris)."))
            self.sujet.setChecked(bool(self.p.get("sujet", True)))
            self.sujet.setVisible(avec_sujet)
            self.arriere = QCheckBox(tr("Ne pas flouter ce qui est plus proche que le point net"))
            self.arriere_info = QLabel()
            self.arriere_info.setWordWrap(True)
            self.arriere.setChecked(bool(self.p.get("arriere", False)))
            for c in (self.c_flou, self.c_zone):
                c.change.connect(self._lire)
                lay.addWidget(c)
            for c in (self.sujet, self.arriere):
                c.toggled.connect(self._lire)
                lay.addWidget(c)
            lay.addWidget(self.arriere_info)
            self._montrer_point()

        def _clic(self, x, y, _mods):
            if self.modes.checkedId() != 0:
                self._peindre(x, y)
                return
            ph, pw = prof.shape
            h, w = rgba.shape[:2]
            self.p["x"], self.p["y"] = int(x * w / pw), int(y * h / ph)
            self._montrer_point()
            self.change.emit()

        def _peindre(self, x, y):
            if self.modes.checkedId() == 0:
                return
            ph, pw = prof.shape
            h, w = rgba.shape[:2]
            r = max(1, round(self.c_pinceau.valeur() / 100 * max(w, h) / 2))
            genre = "net" if self.modes.checkedId() == 1 else "flou"
            # une nouvelle liste : les valeurs gardées par la fenêtre (Réinitialiser, aperçu) ne bougent pas
            self.p["traits"] = list(self.p.get("traits") or []) + [(genre, int(x * w / pw), int(y * h / ph), r)]
            self._trait_en_cours = True
            self._montrer_point()

        def _fin_trait(self):
            if self._trait_en_cours:
                self._trait_en_cours = False
                self.change.emit()                   # aperçu recalculé au lâcher (pas à chaque mouvement)

        def _effacer_traits(self):
            if self.p.get("traits"):
                self.p["traits"] = []
                self._montrer_point()
                self.change.emit()

        def _lire(self):
            self.p["flou"] = int(self.c_flou.valeur())
            self.p["zone"] = int(self.c_zone.valeur())
            self.p["arriere"] = self.arriere.isChecked()
            self.p["sujet"] = self.sujet.isChecked()
            self.change.emit()

        def _montrer_point(self):
            # la case « plus proche » ne change rien si le point net est déjà ce qu'il y a de plus proche
            ph, pw = prof.shape
            h, w = rgba.shape[:2]
            px = min(pw - 1, int(self.p.get("x", w // 2) * pw / w))
            py = min(ph - 1, int(self.p.get("y", h // 2) * ph / h))
            rien_devant = prof[py, px] >= np.percentile(prof, 97) - 0.02
            self.arriere_info.setText(
                tr("Rien n'est plus proche que ce point : cette case ne change rien ici. Elle sert quand vous "
                   "cliquez sur quelque chose au loin.") if rien_devant else
                tr("Cochée : ce qui est devant le point net reste net aussi."))
            self.apercu.montrer_image()
            pm = QPixmap(self.apercu.pixmap())
            ph, pw = prof.shape
            h, w = rgba.shape[:2]
            k = self.apercu.k
            pt = QPointF(self.p.get("x", w // 2) * pw / w * k, self.p.get("y", h // 2) * ph / h * k)
            q = QPainter(pm)
            q.setRenderHint(QPainter.Antialiasing)
            q.setPen(Qt.NoPen)
            for genre, tx, ty, r in self.p.get("traits") or []:      # vert : garder net ; rouge : rendre flou
                q.setBrush(QColor(60, 200, 90, 110) if genre == "net" else QColor(230, 60, 60, 110))
                q.drawEllipse(QPointF(tx * pw / w * k, ty * ph / h * k), r * pw / w * k, r * ph / h * k)
            q.setBrush(Qt.NoBrush)
            for couleur, ep in ((QColor(0, 0, 0), 4), (QColor(255, 80, 40), 2)):
                q.setPen(QPen(couleur, ep))
                q.drawEllipse(pt, 7, 7)
            q.end()
            self.apercu.setPixmap(pm)

        def params(self):
            return dict(self.p)

    return PanneauProfondeur


# ------------------------------------------------------------------ actions
class ActionsPhotoIA:
    # ---------------------------------------------------------- calcul d'une carte (masque, profondeur)
    def _carte_ia(self, titre: str, fabriquer, suite, toutes: bool = False, vide_ok: bool = False):
        """Le moteur calcule une image grise (sur l'image visible) ; suite(tableau 0..255 à la taille de l'image).
        toutes : la recette a plusieurs sorties, suite reçoit la liste des tableaux. vide_ok : une recette qui peut
        ne rien trouver (SAM, masques séparés) donne une liste vide au lieu d'une erreur."""
        from .dialogues import Attente
        doc = self.doc
        png = doc.png_pour_ia(False)
        annuler = threading.Event()

        def calcul(progres):
            nom = self.moteur.envoyer_image(png)
            prompt, sorties = fabriquer(nom)
            try:
                res = self.moteur.executer(prompt, sorties, annuler, progres)
            except ErreurMoteur as e:
                if vide_ok and "size 0" in str(e):        # SAM n'a rien trouvé : lot de masques vide
                    return []
                raise
            if not res:
                if vide_ok:
                    return []
                raise ErreurMoteur(tr("Le calcul s'est arrêté sans résultat."))
            cartes = []
            for _nom, octets in (res if toutes else res[:1]):
                img = QImage.fromData(octets)
                if img.isNull():
                    raise ErreurMoteur(tr("Résultat illisible."))
                w, h = doc.taille()
                if (img.width(), img.height()) != (w, h):
                    img = img.scaled(w, h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
                cartes.append(tableau(img.convertToFormat(FORMAT_IMAGE))[:, :, 0].copy())
            return cartes if toutes else cartes[0]

        attente = Attente(titre, self)
        attente.annuler.connect(annuler.set)

        def ok(m):
            attente.hide()
            attente.deleteLater()
            if doc is self.doc:
                suite(m)

        def echec(message):
            attente.hide()
            attente.deleteLater()
            if message:
                QMessageBox.warning(self, titre, message)

        t = self._tache(calcul, ok, echec)
        t.progres.connect(attente.maj)
        t.lancer()
        attente.show()

    def _sam_present(self, titre: str) -> bool:
        if recettes.sam_disponible():
            return True
        QMessageBox.information(self, titre, tr(
            "Cette action a besoin du modèle SAM 3.1, qui n'est pas installé. Menu IA > Installer le moteur IA "
            "permet de l'ajouter."))
        return False

    @staticmethod
    def _masque_ciel(m: np.ndarray, rgb: np.ndarray | None = None) -> np.ndarray:
        """Masque 0..255 de la sélection du ciel (voir _masques_ciel)."""
        douce, fin = ActionsPhotoIA._masques_ciel(m, rgb)
        return np.round(np.maximum(douce, fin) * 255).astype(np.uint8)

    @staticmethod
    def _masques_ciel(m: np.ndarray, rgb: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
        """Masque du ciel, nuages compris, bord affiné d'après les couleurs (rgb : l'image visible) et adouci. SAM
        laisse de côté les nuages et les oiseaux : tout ce qui n'est pas du ciel mais n'est pas relié au bas de
        l'image (entouré de ciel) en fait partie."""
        from PIL import ImageDraw
        h, w = m.shape
        ciel = m > 127
        img = Image.fromarray(np.where(ciel, 0, 255).astype(np.uint8)).copy()   # 255 = pas du ciel (copie : modifiable)
        for x in range(0, w, max(1, w // 400)):                               # ce qui touche le bas : le sol
            if img.getpixel((x, h - 1)) == 255:
                ImageDraw.floodfill(img, (x, h - 1), 128)
        sol = np.asarray(img) == 128
        if sol.any():
            ciel = ~sol
        r = max(1.0, max(w, h) / 900)
        # adoucir seulement ce que l'IA a trouvé ; le détail de l'affinage (les branches) reste fin
        douce = np.asarray(Image.fromarray(np.where(ciel, 255, 0).astype(np.uint8)).filter(
            ImageFilter.GaussianBlur(r)), np.float32) / 255
        fin = affiner_ciel(ciel, rgb) if rgb is not None and rgb.shape[:2] == (h, w) else douce
        return douce, np.maximum(douce, fin)

    def _poser_selection(self, m: np.ndarray, titre: str):
        from .document import _masque_vers_selection
        from .fenetre import CommandeEtat
        avant = self.doc.etat()
        sel = _masque_vers_selection(m).convertToFormat(QImage.Format_ARGB32_Premultiplied)
        self.historique.push(CommandeEtat(self.doc, avant, (self.doc.calques, self.doc.actif, sel), titre))

    def ia_selection_ciel(self):
        titre = tr("Sélectionner le ciel")
        if not self.doc or not self._sam_present(titre):
            return

        def suite(m):
            if (m > 127).mean() < 0.002:
                QMessageBox.information(self, titre, tr("Pas de ciel trouvé dans cette image."))
                return
            self._poser_selection(self._masque_ciel(m, self.doc.rgb_pour_ia()), titre)
        self._carte_ia(titre, recettes.ciel, suite)

    def ia_remplacer_ciel(self):
        titre = tr("Remplacer le ciel")
        if not self.doc or not self._sam_present(titre) or not self._verifier_verrou(titre)                 or not self._kontext_present(titre):
            return
        cle = choix_exemple.choisir(self, titre, tr("Nouveau ciel :"), noms_ciels(), "ciel",
                                    self.reglages.value("ciel_style", "bleu"))
        if cle is None:
            return
        self.reglages.setValue("ciel_style", cle)
        texte = recettes.CIELS[cle]

        def suite(m):
            if (m > 127).mean() < 0.002:
                QMessageBox.information(self, titre, tr("Pas de ciel trouvé dans cette image."))
                return
            # Flux Kontext redessine la photo avec le nouveau ciel (lumière et horizon cohérents) ; seul le ciel
            # sélectionné en est gardé : le reste garde ses pixels d'origine
            douce, fin = self._masques_ciel(m, self.doc.rgb_pour_ia())
            self._poser_selection(np.round(fin * 255).astype(np.uint8), tr("Sélectionner le ciel"))
            taille = self.doc.taille()
            self._lancer(titre, False, lambda n: recettes.restaurer(n, taille, texte=recettes.TEXTE_CIEL.format(
                ciel=texte)), apres=self._ciel_recolle(douce, fin), nom_calque=tr("Ciel"), suffixe=tr("_ciel"))
        self._carte_ia(tr("Recherche du ciel"), recettes.ciel, suite)

    def _ciel_recolle(self, douce: np.ndarray, fin: np.ndarray):
        """Résultat de Kontext remis à la taille de la photo, seul le ciel gardé (voir composer_ciel)."""
        doc = self.doc
        w, h = doc.taille()
        original = tableau(doc.image.convertToFormat(FORMAT_IMAGE)).copy()

        def apres(img: QImage) -> QImage:
            if (img.width(), img.height()) != (w, h):
                img = img.scaled(w, h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            n = tableau(img.convertToFormat(FORMAT_IMAGE))
            res = np.ascontiguousarray(composer_ciel(original, n, douce, fin))
            return QImage(res.data, w, h, w * 4, FORMAT_IMAGE).copy()
        return apres

    # ---------------------------------------------------------- Flux Kontext : coloriser, lumière
    def _kontext_present(self, titre: str) -> bool:
        if recettes.restauration_disponible():
            return True
        QMessageBox.information(self, titre, tr(
            "Cette action a besoin du modèle Flux Kontext (11,9 Go), qui n'est pas installé. Menu IA > Installer "
            "le moteur IA permet de l'ajouter (case « Flux Kontext »)."))
        return False

    def _kontext(self, titre: str, consigne: str, nom_calque: str, suffixe: str):
        """Consigne toute prête (en anglais) envoyée à Flux Kontext, comme « Modifier avec une consigne » : sur la
        sélection s'il y en a une, sinon sur toute l'image."""
        from . import modifier_ia
        from .document import masque
        doc = self.doc
        zone = None if doc.selection_vide() else masque(doc.selection).copy()
        prep = modifier_ia.preparer(doc, zone, self.a_ia_nouveau_calque.isChecked())
        visible = tableau(doc.image.convertToFormat(FORMAT_IMAGE))
        self._lancer(titre, False, lambda nom: recettes.restaurer(nom, prep.taille, texte=consigne),
                     png=prep.png, apres=lambda img: modifier_ia.image_complete(prep, img),
                     placer=lambda image: modifier_ia.etat(doc, prep, image, nom_calque),
                     vue=lambda img: modifier_ia.vue(prep, img, visible), nom_calque=nom_calque, suffixe=suffixe)

    def ia_coloriser(self):
        titre = tr("Coloriser")
        if self.doc and self._verifier_verrou(titre) and self._kontext_present(titre):
            self._kontext(titre, recettes.TEXTE_COLORISER_SEUL, tr("Colorisé"), tr("_colorise"))

    def ia_lumiere(self):
        titre = tr("Changer la lumière")
        if not self.doc or not self._verifier_verrou(titre) or not self._kontext_present(titre):
            return
        cle = choix_exemple.choisir(self, titre, tr("Nouvelle lumière :"), noms_lumieres(), "lumiere",
                                    self.reglages.value("lumiere_style", "doree"))
        if cle is None:
            return
        self.reglages.setValue("lumiere_style", cle)
        self._kontext(titre, recettes.TEXTE_LUMIERE.format(lumiere=recettes.LUMIERES[cle]), tr("Lumière"),
                      tr("_lumiere"))

    # ---------------------------------------------------------- supprimer les personnes
    def ia_supprimer_personnes(self):
        """IA > Supprimer les personnes : SAM 3.1 trouve chaque personne, on coche celles à effacer (pas le sujet
        principal, au départ), puis Effacer reconstruit le fond derrière elles."""
        titre = tr("Supprimer les personnes")
        if not self.doc or not self._sam_present(titre) or not self._verifier_verrou(titre):
            return

        def suite(cartes):
            masques = [c > 127 for c in cartes]
            masques = [m for m in masques if m.mean() > 0.0002]
            if not masques:
                QMessageBox.information(self, titre, tr("Aucune personne trouvée dans cette image."))
                return
            from .choix_personnes import ChoixPersonnes, union
            d = ChoixPersonnes(self.doc.image, masques, self)
            if not d.exec():
                return
            coches = d.coches()
            if not any(coches):
                return
            w, h = self.doc.taille()
            self._poser_selection(union(masques, coches, max(3.0, max(w, h) / 250)), titre)
            if d.resultat() == "effacer":
                self.ia_effacer()
            else:
                self.statusBar().showMessage(tr("Personnes sélectionnées. Complète la sélection si besoin (Sélection "
                                                "d'objet, Maj + clic), puis IA > Effacer."), 8000)
        self._carte_ia(titre, recettes.personnes, suite, toutes=True, vide_ok=True)

    # ---------------------------------------------------------- retouche portrait
    def ia_portrait(self):
        """IA > Retouche portrait : SAM 3.1 trouve le visage, les yeux, les dents… ; peau lissée (grain gardé),
        yeux éclaircis, dents blanchies, avec un aperçu en direct, dans le calque choisi."""
        from . import portrait
        titre = tr("Retouche portrait")
        if not self.doc or not self._verifier_pixels(titre) or not self._sam_present(titre):
            return

        def suite(cartes):
            parties = dict(zip([nom for nom, _t in recettes.PARTIES_VISAGE], cartes))
            if "visage" not in parties or (parties["visage"] > 127).mean() < 0.0005:
                QMessageBox.information(self, titre, tr("Aucun visage trouvé dans cette image."))
                return
            z = portrait.zones(parties)
            depart = {k: int(self.reglages.value("portrait_" + k, v)) for k, v in portrait.DEPART.items()}
            panneau = portrait.panneau_portrait()(depart, {})

            def calcul(a, p):
                for k, v in p.items():
                    self.reglages.setValue("portrait_" + k, v)
                return portrait.retoucher(a, z, p)
            self._dialogue_pixels(titre, panneau, dict(portrait.NEUTRES), calcul)
        self._carte_ia(tr("Recherche du visage"), recettes.visage, suite, toutes=True)

    # ---------------------------------------------------------- créer une image d'après un texte
    def ia_creer(self):
        """IA > Créer une image d'après un texte (Flux Schnell) : une nouvelle image, ou un nouveau calque de l'image
        ouverte, à sa taille. Plusieurs propositions ; « Partir de celle-ci » pour des variantes."""
        titre = tr("Créer une image d'après un texte")
        if not recettes.schnell_disponible():
            QMessageBox.information(self, titre, tr(
                "Cette action a besoin du modèle Flux Schnell, qui n'est pas installé. Menu IA > Installer le moteur "
                "IA permet de l'ajouter (case « Flux Schnell »)."))
            return
        from .consigne import DialogueConsigne
        from .document import Document
        d = DialogueConsigne(self, nb=recettes.NB_CREER, creer=True, image_ouverte=self.doc is not None)
        if not d.exec():
            return
        texte, nb = d.consigne(), d.nombre()
        if d.nouvelle_image() or self.doc is None:
            w, h = d.taille()
            fond = QImage(w, h, QImage.Format_ARGB32_Premultiplied)
            fond.fill(QColor(255, 255, 255))
            doc = Document(fond)
            doc.nom = tr("Image créée")
            self._installer_document(doc)
            self._actualiser()
            placer = lambda image: doc.etat_calque_modifie(0, image=image.convertToFormat(
                QImage.Format_ARGB32_Premultiplied), nom=tr("Image créée"))
        else:
            doc = self.doc
            placer = lambda image: doc.etat_nouveau_calque(image, tr("Image créée"))
        taille = doc.taille()
        self._lancer(titre, False, lambda nom: recettes.creer(texte, taille, nb=nb), placer=placer,
                     vue=lambda img: img, nom_calque=tr("Image créée"), suffixe=tr("_creee"),
                     variante=lambda nom, force: recettes.creer(texte, taille, nb=nb, image=nom,
                                                                force=min(0.9, max(0.3, force))))

    # ---------------------------------------------------------- flou selon la profondeur
    def ia_flou_profondeur(self):
        titre = tr("Flou selon la profondeur")
        if not self.doc or not self._verifier_pixels(titre):
            return
        if not recettes.profondeur_disponible():
            QMessageBox.information(self, titre, tr(
                "Cette action a besoin du modèle Depth Anything 3 (137 Mo), qui n'est pas installé. Menu IA > "
                "Installer le moteur IA permet de l'ajouter (case « Flou selon la profondeur »)."))
            return

        avec_sujet = recettes.detourage_disponible()

        def suite(cartes):
            carte = cartes[0]
            sujet = cartes[1].astype(np.float32) / 255 if len(cartes) > 1 else None
            prof = carte.astype(np.float32) / 255
            rgba = tableau(self.doc.calque_actif.image.convertToFormat(FORMAT_IMAGE))
            w, h = self.doc.taille()
            # point net de départ : le plus proche (le sujet, en général)
            ys, xs = np.nonzero(prof >= np.percentile(prof, 97))
            neutres = {"x": int(np.median(xs)) if len(xs) else w // 2, "y": int(np.median(ys)) if len(ys) else h // 2,
                       "flou": 0, "zone": 15, "arriere": False, "sujet": True, "traits": []}
            depart = dict(neutres, flou=int(self.reglages.value("profondeur_flou", 20)))
            petite = prof
            if max(w, h) > 700:                       # la carte montrée dans le panneau : réduite
                k = 700 / max(w, h)
                petite = np.asarray(Image.fromarray(carte).resize((max(1, round(w * k)), max(1, round(h * k))),
                                                                  Image.BILINEAR), np.float32) / 255
            panneau = panneau_profondeur(rgba, petite, sujet is not None)(depart, {})

            def calcul(a, p):
                self.reglages.setValue("profondeur_flou", p.get("flou", 20))
                return flou_profondeur(a, prof, p, sujet)
            self._dialogue_pixels(titre, panneau, neutres, calcul)
        self._carte_ia(tr("Calcul de la profondeur"), lambda nom: recettes.profondeur(nom, sujet=avec_sujet), suite,
                       toutes=True)
