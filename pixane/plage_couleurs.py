"""Plage de couleurs (menu Sélection) et Remplacer la couleur (Image > Réglages), comme Photoshop.

On clique dans un aperçu de la photo sur la couleur voulue (Maj+clic : en ajouter une, Alt+clic : en retirer une) ;
la « tolérance » dit jusqu'où les couleurs voisines sont prises, avec des bords doux.
- Plage de couleurs : sélectionne tous les points de ces couleurs, dans toute l'image (pas seulement les voisins
  comme la baguette magique).
- Remplacer la couleur : change la teinte, la saturation et la clarté de ces points seulement (un pull rouge devient
  bleu en gardant ses plis et ses ombres).
"""
from __future__ import annotations

import numpy as np
from PySide6.QtCore import QPointF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
                               QWidget)

from .langue import tr

TAILLE_APERCU = 360
# clarté (Y) et couleur (Cb, Cr) ; l'écart de clarté compte moitié : un rouge à l'ombre reste « du rouge »
_YCC = np.array([[0.299, 0.587, 0.114], [-0.169, -0.331, 0.5], [0.5, -0.419, -0.081]], np.float32)
_POIDS_YCC = np.array([0.5, 1.0, 1.0], np.float32)


# ------------------------------------------------------------------ calcul
def echantillon(rgba: np.ndarray, x: int, y: int) -> list[int]:
    """Couleur moyenne d'un carré de 5 × 5 px autour du point (moins sensible au grain qu'un seul pixel)."""
    h, w = rgba.shape[:2]
    x0, x1 = max(0, x - 2), min(w, x + 3)
    y0, y1 = max(0, y - 2), min(h, y + 3)
    bloc = rgba[y0:y1, x0:x1, :3].reshape(-1, 3).astype(np.float32)
    return [int(round(v)) for v in bloc.mean(axis=0)]


def _proche(rgb: np.ndarray, couleurs, tolerance: float) -> np.ndarray:
    """0..1 : ressemblance de chaque point à la plus proche des couleurs (1 = même couleur, 0 = plus loin que la
    tolérance). Écart de couleur plus important que l'écart de clarté ; décroissance douce."""
    res = np.zeros(rgb.shape[:2], np.float32)
    if not couleurs:
        return res
    tol = max(1.0, float(tolerance)) * 0.9
    f = rgb.astype(np.float32) @ (_YCC.T * _POIDS_YCC)
    for c in couleurs:
        ref = (np.array(c[:3], np.float32) @ _YCC.T) * _POIDS_YCC
        d = ((f - ref) ** 2).sum(axis=-1)
        p = np.clip(1 - np.sqrt(d) / tol, 0, 1)
        np.maximum(res, p * p * (3 - 2 * p), out=res)
    return res


def masque_couleurs(rgba: np.ndarray, p: dict) -> np.ndarray:
    """(h, w) uint8 0..255 : points des couleurs choisies, moins ceux des couleurs retirées ; points transparents
    jamais pris."""
    rgb = rgba[..., :3]
    m = _proche(rgb, p.get("couleurs", []), p.get("tolerance", 40))
    if p.get("retirees"):
        m = m * (1 - _proche(rgb, p["retirees"], p.get("tolerance", 40)))
    if p.get("inverser"):
        m = 1 - m
    m = m * (rgba[..., 3] > 0)
    return np.clip(np.round(m * 255), 0, 255).astype(np.uint8)


def _hsv(f: np.ndarray):
    mx, mn = f.max(axis=-1), f.min(axis=-1)
    d = mx - mn
    h = np.zeros_like(mx)
    r, g, b = f[..., 0], f[..., 1], f[..., 2]
    ok = d > 1e-6
    i = ok & (mx == r)
    h[i] = ((g - b)[i] / d[i]) % 6
    i = ok & (mx == g) & (mx != r)
    h[i] = (b - r)[i] / d[i] + 2
    i = ok & (mx == b) & (mx != r) & (mx != g)
    h[i] = (r - g)[i] / d[i] + 4
    s = np.where(mx > 1e-6, d / np.maximum(mx, 1e-6), 0)
    return h * 60, s, mx


def _rgb(h, s, v):
    h = (h % 360) / 60
    c = v * s
    x = c * (1 - np.abs(h % 2 - 1))
    z = np.zeros_like(h)
    i = np.floor(h).astype(np.int8) % 6
    choix = [(c, x, z), (x, c, z), (z, c, x), (z, x, c), (x, z, c), (c, z, x)]
    out = np.zeros(h.shape + (3,), np.float32)
    for k, (r, g, b) in enumerate(choix):
        m = i == k
        out[m] = np.stack([r[m], g[m], b[m]], axis=-1)
    return out + (v - c)[..., None]


def changer_couleur(rgb: np.ndarray, teinte: float, saturation: float, clarte: float) -> np.ndarray:
    """Teinte décalée (degrés), saturation et clarté de -100 à +100 ; (h, w, 3) uint8 -> float32 0..255."""
    f = rgb.astype(np.float32) / 255
    h, s, v = _hsv(f)
    h = h + teinte
    s = np.clip(s * (1 + saturation / 100) if saturation < 0 else s + (1 - s) * saturation / 100, 0, 1)
    out = _rgb(h, s, v)
    if clarte > 0:
        out = out + (1 - out) * clarte / 100
    elif clarte < 0:
        out = out * (1 + clarte / 100)
    return np.clip(out * 255, 0, 255)


def defaut_remplacer() -> dict:
    return {"couleurs": [], "retirees": [], "tolerance": 40, "teinte": 0, "saturation": 0, "clarte": 0}


def remplacer_couleur(t: np.ndarray, p: dict) -> np.ndarray:
    """Tableau RGBA -> RGBA : couleurs choisies changées (teinte, saturation, clarté), avec des bords doux."""
    m = masque_couleurs(t, p).astype(np.float32)[..., None] / 255
    if not m.any():
        return t.copy()
    nouv = changer_couleur(t[..., :3], p.get("teinte", 0), p.get("saturation", 0), p.get("clarte", 0))
    out = t.copy()
    out[..., :3] = np.clip(np.round(t[..., :3] + (nouv - t[..., :3]) * m), 0, 255).astype(np.uint8)
    return out


# ------------------------------------------------------------------ aperçu cliquable
class ApercuCliquable(QLabel):
    """Petite image de la photo (ou du masque) : clic = point choisi, en coordonnées de la photo."""
    clic = Signal(int, int, object)          # x, y, modificateurs

    def __init__(self, rgba: np.ndarray):
        super().__init__()
        self.rgba = rgba
        h, w = rgba.shape[:2]
        self.k = min(1.0, TAILLE_APERCU / max(w, h))
        self.pw, self.ph = max(1, round(w * self.k)), max(1, round(h * self.k))
        pas = max(1, int(1 / self.k))
        self.petit = np.ascontiguousarray(rgba[::pas, ::pas])
        self.setFixedSize(self.pw, self.ph)
        self.setCursor(Qt.CrossCursor)
        self.setToolTip(tr("Clic : choisir la couleur. Maj+clic : en ajouter une. Alt+clic : en retirer une."))
        self.montrer_image()

    def _poser(self, img: QImage):
        fond = QPixmap(self.pw, self.ph)
        fond.fill(QColor(128, 128, 128))
        p = QPainter(fond)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.drawImage(fond.rect(), img)
        p.end()
        self.setPixmap(fond)

    def montrer_image(self):
        t = self.petit
        self._poser(QImage(t.data, t.shape[1], t.shape[0], t.shape[1] * 4, QImage.Format_RGBA8888).copy())

    def montrer_masque(self, m: np.ndarray):
        m = np.ascontiguousarray(m)
        self._poser(QImage(m.data, m.shape[1], m.shape[0], m.shape[1], QImage.Format_Grayscale8).copy())

    def mousePressEvent(self, e):
        h, w = self.rgba.shape[:2]
        x = int(min(w - 1, max(0, e.position().x() / self.k)))
        y = int(min(h - 1, max(0, e.position().y() / self.k)))
        self.clic.emit(x, y, e.modifiers())


class _ChoixCouleurs(QWidget):
    """Aperçu cliquable + pastilles des couleurs choisies + tolérance. `p` est partagé avec le panneau."""
    change = Signal()

    def __init__(self, rgba: np.ndarray, p: dict, avec_inverser: bool = False):
        super().__init__()
        from .dialogues_reglage import Curseur
        self.p = p
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        info = QLabel(tr("Cliquez sur la couleur voulue dans l'image ci-dessous (Maj+clic : ajouter une couleur, "
                         "Alt+clic : en retirer une)."))
        info.setWordWrap(True)
        lay.addWidget(info)
        ligne = QHBoxLayout()
        self.apercu = ApercuCliquable(rgba)
        self.apercu.clic.connect(self._clic)
        ligne.addStretch(1)
        ligne.addWidget(self.apercu)
        ligne.addStretch(1)
        lay.addLayout(ligne)
        ligne = QHBoxLayout()
        self.voir = QComboBox()
        self.voir.addItem(tr("Montrer : la sélection (blanc = pris)"), "masque")
        self.voir.addItem(tr("Montrer : l'image"), "image")
        self.voir.currentIndexChanged.connect(lambda *_: self.rafraichir())
        ligne.addWidget(self.voir, 1)
        self.pastilles = QLabel()
        ligne.addWidget(self.pastilles)
        b = QPushButton(tr("Effacer les couleurs"))
        b.clicked.connect(self._effacer)
        ligne.addWidget(b)
        lay.addLayout(ligne)
        self.tol = Curseur(tr("Tolérance"), 1, 200, self.p.get("tolerance", 40))
        self.tol.change.connect(self._tol)
        lay.addWidget(self.tol)
        self.inv = None
        if avec_inverser:
            self.inv = QCheckBox(tr("Inverser (tout sauf ces couleurs)"))
            self.inv.setChecked(bool(self.p.get("inverser")))
            self.inv.toggled.connect(self._inv)
            lay.addWidget(self.inv)
        self._minuterie = QTimer(self)
        self._minuterie.setSingleShot(True)
        self._minuterie.setInterval(60)
        self._minuterie.timeout.connect(self._maj_apercu)
        self.rafraichir()

    def _clic(self, x, y, mods):
        c = echantillon(self.apercu.rgba, x, y)
        if mods & Qt.AltModifier:
            self.p.setdefault("retirees", []).append(c)
        elif mods & Qt.ShiftModifier:
            self.p.setdefault("couleurs", []).append(c)
        else:
            self.p["couleurs"], self.p["retirees"] = [c], []
        self.rafraichir()
        self.change.emit()

    def _effacer(self):
        self.p["couleurs"], self.p["retirees"] = [], []
        self.rafraichir()
        self.change.emit()

    def _tol(self):
        self.p["tolerance"] = int(self.tol.valeur())
        self.rafraichir()
        self.change.emit()

    def _inv(self, v):
        self.p["inverser"] = bool(v)
        self.rafraichir()
        self.change.emit()

    def rafraichir(self):
        self._dessiner_pastilles()
        self._minuterie.start()

    def _maj_apercu(self):
        if self.voir.currentData() == "image" or not self.p.get("couleurs"):
            self.apercu.montrer_image()
        else:
            self.apercu.montrer_masque(masque_couleurs(self.apercu.petit, self.p))

    def _dessiner_pastilles(self):
        cs = self.p.get("couleurs", [])[-6:]
        rs = self.p.get("retirees", [])[-3:]
        n = len(cs) + len(rs)
        pix = QPixmap(max(1, n) * 20, 18)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        for i, c in enumerate(cs + rs):
            p.fillRect(i * 20 + 1, 1, 16, 16, QColor(*c))
            if i >= len(cs):                             # couleur retirée : barrée
                p.setPen(QColor(220, 40, 40))
                p.drawLine(i * 20 + 1, 17, i * 20 + 17, 1)
        p.end()
        self.pastilles.setPixmap(pix)
        self.pastilles.setToolTip(tr("Couleurs choisies (barrées : retirées)"))


# ------------------------------------------------------------------ Remplacer la couleur
def panneau_remplacer(rgba: np.ndarray):
    """Panneau pour la fenêtre de réglage (DialogueReglage) : choix des couleurs + teinte, saturation, clarté."""
    from .dialogues_reglage import Curseur, _Panneau

    class PanneauRemplacer(_Panneau):
        def __init__(self, params, histo):
            super().__init__(params, histo)
            lay = QVBoxLayout(self)
            self.choix = _ChoixCouleurs(rgba, self.p)
            self.choix.change.connect(self.change.emit)
            lay.addWidget(self.choix)
            lay.addWidget(QLabel(tr("Remplacement :")))
            self.c = {}
            for cle, nom, mini, maxi, unite in (("teinte", tr("Teinte"), -180, 180, "°"),
                                                ("saturation", tr("Saturation"), -100, 100, ""),
                                                ("clarte", tr("Clarté"), -100, 100, "")):
                c = Curseur(nom, mini, maxi, self.p.get(cle, 0), unite)
                c.change.connect(self._lire)
                lay.addWidget(c)
                self.c[cle] = c
            self.resultat = QLabel()
            lay.addWidget(self.resultat)
            self.choix.change.connect(self._montrer_resultat)
            self._montrer_resultat()

        def _lire(self):
            for k, c in self.c.items():
                self.p[k] = int(c.valeur())
            self._montrer_resultat()
            self.change.emit()

        def _montrer_resultat(self):
            cs = self.p.get("couleurs") or []
            if not cs:
                self.resultat.setText(tr("Aucune couleur choisie : cliquez dans l'image."))
                return
            a = np.array([[cs[0][:3]]], np.uint8)
            b = changer_couleur(a, self.p.get("teinte", 0), self.p.get("saturation", 0), self.p.get("clarte", 0))
            b = [int(round(v)) for v in b[0, 0]]
            self.resultat.setText(tr("Avant → après :") + f"  <span style='background:rgb{tuple(cs[0][:3])}'>"
                                  "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span> → "
                                  f"<span style='background:rgb{tuple(b)}'>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>")

        def params(self):
            import copy
            return copy.deepcopy(self.p)

    return PanneauRemplacer


# ------------------------------------------------------------------ Plage de couleurs (sélection)
class DialoguePlage(QDialog):
    """Sélection > Plage de couleurs. `apercu(masque | None)` montre la sélection sur la photo pendant qu'on règle ;
    après exec() : `masque()` (h, w) uint8 et `mode()` (« nouvelle », « ajouter », « retirer »)."""
    apercu = Signal(object)

    def __init__(self, parent, rgba: np.ndarray, depart: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle(tr("Plage de couleurs"))
        self.rgba = rgba
        self.p = dict(depart or {"couleurs": [], "retirees": [], "tolerance": 40, "inverser": False})
        lay = QVBoxLayout(self)
        self.choix = _ChoixCouleurs(rgba, self.p, avec_inverser=True)
        self.choix.change.connect(self._plus_tard)
        lay.addWidget(self.choix)
        ligne = QHBoxLayout()
        ligne.addWidget(QLabel(tr("Sélection :")))
        self.l_mode = QComboBox()
        for m, nom in (("nouvelle", tr("Nouvelle")), ("ajouter", tr("Ajouter à la sélection")),
                       ("retirer", tr("Retirer de la sélection"))):
            self.l_mode.addItem(nom, m)
        ligne.addWidget(self.l_mode, 1)
        lay.addLayout(ligne)
        boutons = QHBoxLayout()
        boutons.addStretch(1)
        self.b_ok = QPushButton(tr("Sélectionner"))
        self.b_ok.setDefault(True)
        self.b_ok.clicked.connect(self.accept)
        annuler = QPushButton(tr("Annuler"))
        annuler.clicked.connect(self.reject)
        boutons.addWidget(self.b_ok)
        boutons.addWidget(annuler)
        lay.addLayout(boutons)
        self._minuterie = QTimer(self)
        self._minuterie.setSingleShot(True)
        self._minuterie.setInterval(200)
        self._minuterie.timeout.connect(self._montrer)
        self._maj_bouton()

    def _plus_tard(self):
        self._maj_bouton()
        self._minuterie.start()

    def _maj_bouton(self):
        self.b_ok.setEnabled(bool(self.p.get("couleurs")))

    def _montrer(self):
        self.apercu.emit(self.masque() if self.p.get("couleurs") else None)

    def masque(self) -> np.ndarray:
        return masque_couleurs(self.rgba, self.p)

    def mode(self) -> str:
        return self.l_mode.currentData()

    def params(self) -> dict:
        return dict(self.p)
