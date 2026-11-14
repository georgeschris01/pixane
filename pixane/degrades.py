"""Dégradés à plusieurs points (comme l'éditeur de dégradé de Photoshop) : des points de couleur sous la barre, des
points d'opacité au-dessus, et entre deux points un milieu (losange) qui règle où se trouve la moitié du passage.

Un dégradé est un simple dict (gardé tel quel dans les réglages, les styles et les fichiers .pixane) :
    {"couleurs": [{"pos": 0..1, "couleur": "#rrggbb" ou "peinture", "milieu": 0.05..0.95}, ...],
     "opacites": [{"pos": 0..1, "opacite": 0..1, "milieu": 0.05..0.95}, ...]}
« peinture » : le point prend la couleur de peinture du moment. « milieu » d'un point : milieu du passage entre le
point précédent et lui (comme Photoshop)."""
from __future__ import annotations

import copy
import json
import math
import os

import numpy as np
from PySide6.QtCore import QPointF, QRectF, QSettings, QSize, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QIcon, QImage, QPainter, QPainterPath, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import (QCheckBox, QColorDialog, QDialog, QDialogButtonBox, QGroupBox, QHBoxLayout,
                               QInputDialog, QLabel, QListWidget, QListWidgetItem, QPushButton, QSpinBox,
                               QStackedWidget, QToolButton, QVBoxLayout, QWidget)

from .langue import tr

PEINTURE = "peinture"
MILIEU_MIN, MILIEU_MAX = 0.05, 0.95


# ------------------------------------------------------------------ données
def _c(pos, couleur, milieu=0.5):
    return {"pos": float(pos), "couleur": couleur, "milieu": float(milieu)}


def _o(pos, opacite, milieu=0.5):
    return {"pos": float(pos), "opacite": float(opacite), "milieu": float(milieu)}


def defaut() -> dict:
    """Couleur de peinture vers le transparent (l'ancien réglage par défaut de l'outil)."""
    return {"couleurs": [_c(0, PEINTURE), _c(1, PEINTURE)], "opacites": [_o(0, 1), _o(1, 0)]}


def deux_couleurs(c1: str, c2: str | None) -> dict:
    """c1 vers c2 ; c2 None : c1 vers le transparent."""
    if c2 is None:
        return {"couleurs": [_c(0, c1), _c(1, c1)], "opacites": [_o(0, 1), _o(1, 0)]}
    return {"couleurs": [_c(0, c1), _c(1, c2)], "opacites": [_o(0, 1), _o(1, 1)]}


def _nom_couleur(v) -> str:
    if v == PEINTURE:
        return PEINTURE
    c = QColor(str(v)) if v is not None else QColor()
    return c.name() if c.isValid() else "#000000"


def _nombre(v, defaut_, mini, maxi) -> float:
    try:
        v = float(v)
    except (TypeError, ValueError):
        return defaut_
    if math.isnan(v):
        return defaut_
    return min(maxi, max(mini, v))


def normaliser(d) -> dict:
    """Copie propre : points triés, valeurs bornées, au moins un point de chaque sorte. Accepte n'importe quoi
    (fichier abîmé, version plus récente) sans planter."""
    if isinstance(d, str):
        try:
            d = json.loads(d)
        except ValueError:
            d = None
    if not isinstance(d, dict):
        return defaut()
    couleurs, opacites = [], []
    for p in d.get("couleurs") or []:
        if isinstance(p, dict):
            couleurs.append(_c(_nombre(p.get("pos"), 0, 0, 1), _nom_couleur(p.get("couleur")),
                               _nombre(p.get("milieu"), 0.5, MILIEU_MIN, MILIEU_MAX)))
    for p in d.get("opacites") or []:
        if isinstance(p, dict):
            opacites.append(_o(_nombre(p.get("pos"), 0, 0, 1), _nombre(p.get("opacite"), 1, 0, 1),
                               _nombre(p.get("milieu"), 0.5, MILIEU_MIN, MILIEU_MAX)))
    if not couleurs:
        couleurs = defaut()["couleurs"]
    if not opacites:
        opacites = [_o(0, 1), _o(1, 1)]
    couleurs.sort(key=lambda p: p["pos"])
    opacites.sort(key=lambda p: p["pos"])
    return {"couleurs": couleurs, "opacites": opacites}


def inverse(d: dict) -> dict:
    """Le même dégradé à l'envers (le milieu de chaque passage suit son passage)."""
    d = normaliser(d)
    res = {}
    for cle in ("couleurs", "opacites"):
        pts = d[cle]
        neufs = []
        for i, p in enumerate(reversed(pts)):
            q = dict(p, pos=1 - p["pos"])
            # le passage qui arrivait sur le point suivant (dans l'ordre d'origine) arrive maintenant sur celui-ci
            j = len(pts) - i                      # indice d'origine du point suivant
            q["milieu"] = 1 - pts[j]["milieu"] if j < len(pts) else 0.5
            neufs.append(q)
        res[cle] = neufs
    return normaliser(res)


def utilise_peinture(d: dict) -> bool:
    return any(p["couleur"] == PEINTURE for p in normaliser(d)["couleurs"])


# ------------------------------------------------------------------ calcul
def _interpoler(pos: np.ndarray, val: np.ndarray, mil: np.ndarray, t: np.ndarray) -> np.ndarray:
    k = len(pos)
    i = np.searchsorted(pos, t, side="right")
    i0 = np.clip(i - 1, 0, k - 1)
    i1 = np.clip(i, 0, k - 1)
    ecart = pos[i1] - pos[i0]
    u = np.where(ecart > 1e-9, (t - pos[i0]) / np.maximum(ecart, 1e-9), 0.0)
    u = np.clip(u, 0, 1)
    m = np.clip(mil[i1], MILIEU_MIN, MILIEU_MAX)          # courbe qui passe par 0,5 au milieu, symétrique
    u = u * (1 - m) / np.maximum(u * (1 - m) + (1 - u) * m, 1e-9)   # (le dégradé inversé reste identique)
    return val[i0] + (val[i1] - val[i0]) * u[:, None]


def table(d: dict, peinture=None, n: int = 256) -> np.ndarray:
    """(n, 4) float32 RGBA 0..1 le long du dégradé (couleurs non prémultipliées)."""
    d = normaliser(d)
    pc = QColor(peinture) if peinture is not None else QColor(0, 0, 0)
    t = np.linspace(0, 1, n, dtype=np.float64)
    cs = d["couleurs"]
    rgb = np.array([[q.redF(), q.greenF(), q.blueF()] for q in
                    (pc if p["couleur"] == PEINTURE else QColor(p["couleur"]) for p in cs)], np.float64)
    couleur = _interpoler(np.array([p["pos"] for p in cs]), rgb, np.array([p["milieu"] for p in cs]), t)
    os_ = d["opacites"]
    alpha = _interpoler(np.array([p["pos"] for p in os_]), np.array([[p["opacite"]] for p in os_]),
                        np.array([p["milieu"] for p in os_]), t)
    return np.concatenate([couleur, alpha], axis=1).astype(np.float32)


def remplir_qgradient(g, d: dict, peinture=None, gris: bool = False):
    """Pose les couleurs du dégradé sur un QGradient de Qt (257 étapes : le milieu et les points sont respectés).
    gris : peinture sur un masque : couleurs changées en gris, et le transparent devient le gris opposé à la couleur
    de peinture (blanc pour une couleur foncée, noir sinon), comme avant l'éditeur de dégradé."""
    tab = table(d, peinture, 257)
    pc = QColor(peinture) if peinture is not None else QColor(0, 0, 0)
    oppose = 1.0 if pc.lightnessF() < 0.5 else 0.0
    pas = []
    for i, (r, v, b, a) in enumerate(tab):
        if gris:
            gr = QColor.fromRgbF(float(r), float(v), float(b)).lightnessF()
            r = v = b = gr * a + oppose * (1 - a)
            a = 1.0
        pas.append((i / 256, QColor.fromRgbF(float(r), float(v), float(b), float(a))))
    g.setStops(pas)
    return g


def image_apercu(d: dict, w: int, h: int, peinture=None, case: int = 5) -> QImage:
    """Bande du dégradé sur un damier (montre la transparence)."""
    img = QImage(w, h, QImage.Format_ARGB32_Premultiplied)
    img.fill(QColor(235, 235, 235))
    p = QPainter(img)
    for y in range(0, h, case):
        for x in range(0, w, case):
            if (x // case + y // case) % 2:
                p.fillRect(x, y, case, case, QColor(200, 200, 200))
    from PySide6.QtGui import QLinearGradient
    g = remplir_qgradient(QLinearGradient(0, 0, w, 0), d, peinture)
    p.fillRect(0, 0, w, h, QBrush(g))
    p.setPen(QColor(0, 0, 0, 90))
    p.drawRect(0, 0, w - 1, h - 1)
    p.end()
    return img


# ------------------------------------------------------------------ dégradés tout prêts et enregistrés
def _plusieurs(*couleurs) -> dict:
    n = len(couleurs) - 1
    return {"couleurs": [_c(i / n, c) for i, c in enumerate(couleurs)], "opacites": [_o(0, 1), _o(1, 1)]}


def tout_prets() -> list[tuple[str, dict]]:
    halo = {"couleurs": [_c(0, "#ffffff"), _c(1, "#ffffff")], "opacites": [_o(0, 1), _o(1, 0, 0.3)]}
    return [
        (tr("Couleur de peinture vers transparent"), defaut()),
        (tr("Couleur de peinture vers blanc"), deux_couleurs(PEINTURE, "#ffffff")),
        (tr("Couleur de peinture vers noir"), deux_couleurs(PEINTURE, "#000000")),
        (tr("Noir vers blanc"), deux_couleurs("#000000", "#ffffff")),
        (tr("Noir vers transparent"), deux_couleurs("#000000", None)),
        (tr("Blanc vers transparent"), deux_couleurs("#ffffff", None)),
        (tr("Halo blanc"), halo),
        (tr("Arc-en-ciel"), _plusieurs("#ff0000", "#ffa500", "#ffff00", "#00c000", "#0080ff", "#4b0082", "#ee00ee")),
        (tr("Or"), _plusieurs("#7a5512", "#e8c25a", "#fff3c0", "#c99a2e", "#6b4a10")),
        (tr("Chrome"), _plusieurs("#2b3036", "#f4f7fa", "#8a939c", "#ffffff", "#3a3f45")),
        (tr("Cuivre"), _plusieurs("#5a2a12", "#d98a52", "#ffd0a8", "#a8562a")),
        (tr("Argent"), _plusieurs("#7d7d7d", "#f0f0f0", "#a6a6a6", "#e0e0e0")),
        (tr("Feu"), _plusieurs("#3a0000", "#c00000", "#ff7a00", "#ffe14d")),
        (tr("Coucher de soleil"), _plusieurs("#2b1055", "#a4277a", "#ff6f3c", "#ffd36e")),
        (tr("Ciel"), _plusieurs("#0b3d91", "#4a90d9", "#bfe3ff")),
        (tr("Mer"), _plusieurs("#003f5c", "#00838f", "#7ee0d3")),
        (tr("Néon"), _plusieurs("#ff00cc", "#7a00ff", "#00e5ff")),
        (tr("Sépia"), _plusieurs("#2e1d0e", "#a67b4d", "#f3e2c3")),
    ]


def _reglages() -> QSettings:
    return QSettings("Pixane", os.environ.get("PIXANE_REGLAGES", "Pixane"))


def enregistres() -> list[tuple[str, dict]]:
    """Les dégradés enregistrés par l'utilisateur (réglage degrades_perso)."""
    try:
        liste = json.loads(_reglages().value("degrades_perso", "[]") or "[]")
    except (ValueError, TypeError):
        return []
    return [(str(x.get("nom") or tr("Sans nom")), normaliser(x.get("points"))) for x in liste
            if isinstance(x, dict)]


def mettre_enregistres(liste: list[tuple[str, dict]]):
    _reglages().setValue("degrades_perso", json.dumps([{"nom": n, "points": normaliser(d)} for n, d in liste],
                                                      ensure_ascii=False))


# ------------------------------------------------------------------ barre à points
MARGE = 10            # place à gauche et à droite pour les points des bouts
HAUT_POINT = 16       # hauteur de la rangée des points (au-dessus : opacité ; en dessous : couleur)
HAUT_BARRE = 30


class BarreDegrade(QWidget):
    """La barre du dégradé et ses points. Clic au-dessus : point d'opacité ; clic en dessous : point de couleur ;
    glisser pour déplacer ; tirer loin de la barre pour retirer ; double-clic sur un point de couleur : sa couleur.
    Losanges : milieux du passage de part et d'autre du point choisi."""
    change = Signal()
    choix_change = Signal()

    def __init__(self, d: dict, peinture=None, parent=None):
        super().__init__(parent)
        self.d = normaliser(d)
        self.peinture = QColor(peinture) if peinture is not None else None
        self.choix: tuple[str, dict] | None = ("couleurs", self.d["couleurs"][0])
        self._glisse = None          # ("point", rangée, point) ou ("milieu", rangée, point)
        self._a_retirer = False
        self.setMinimumSize(360, 2 * (HAUT_POINT + 12) + HAUT_BARRE + 8)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setToolTip(tr("Clic sous la barre : ajouter une couleur. Clic au-dessus : ajouter un point d'opacité.\n"
                           "Glisser un point pour le déplacer, loin de la barre pour le retirer.\n"
                           "Double-clic sur un point de couleur : choisir sa couleur. Losange : milieu du passage."))

    # géométrie
    def _largeur(self) -> float:
        return max(1.0, self.width() - 2 * MARGE)

    def _x(self, pos: float) -> float:
        return MARGE + pos * self._largeur()

    def _pos(self, x: float) -> float:
        return min(1.0, max(0.0, (x - MARGE) / self._largeur()))

    def _barre(self) -> QRectF:
        return QRectF(MARGE, HAUT_POINT + 16, self._largeur(), HAUT_BARRE)

    def _y_rangee(self, rangee: str) -> float:
        b = self._barre()
        return b.top() - HAUT_POINT / 2 - 1 if rangee == "opacites" else b.bottom() + HAUT_POINT / 2 + 1

    def _y_milieu(self, rangee: str) -> float:
        """Rangée des losanges : juste au-delà des points (un clic sur la rangée des points en ajoute un)."""
        b = self._barre()
        return b.top() - HAUT_POINT - 6 if rangee == "opacites" else b.bottom() + HAUT_POINT + 6

    def _couleur_point(self, p) -> QColor:
        if p["couleur"] == PEINTURE:
            return QColor(self.peinture) if self.peinture is not None else QColor(0, 0, 0)
        return QColor(p["couleur"])

    def _milieux(self, rangee: str, point) -> list[tuple[dict, float]]:
        """Losanges montrés : (point qui porte le milieu, x) autour du point choisi."""
        pts = self.d[rangee]
        if point not in pts:
            return []
        i = next(k for k, q in enumerate(pts) if q is point)
        res = []
        for a, b in ((i - 1, i), (i, i + 1)):
            if 0 <= a and b < len(pts) and pts[b]["pos"] - pts[a]["pos"] > 0.02:
                pos = pts[a]["pos"] + (pts[b]["pos"] - pts[a]["pos"]) * pts[b]["milieu"]
                res.append((pts[b], self._x(pos)))
        return res

    # dessin
    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        b = self._barre()
        p.drawImage(b.toRect(), image_apercu(self.d, int(b.width()), int(b.height()), self.peinture, 7))
        for rangee in ("opacites", "couleurs"):
            for pt in self.d[rangee]:
                self._dessiner_point(p, rangee, pt)
        if self.choix is not None:
            rangee, pt = self.choix
            y = self._y_milieu(rangee)
            p.setPen(QPen(QColor(60, 60, 60), 1))
            for _porteur, x in self._milieux(rangee, pt):
                p.setBrush(QColor(255, 255, 255))
                p.drawPolygon(QPolygonF([QPointF(x, y - 4), QPointF(x + 4, y), QPointF(x, y + 4), QPointF(x - 4, y)]))
        p.end()

    def _dessiner_point(self, p: QPainter, rangee: str, pt):
        x = self._x(pt["pos"])
        b = self._barre()
        choisi = self.choix is not None and self.choix[1] is pt
        retire = choisi and self._a_retirer
        if rangee == "opacites":
            g = round(255 * (1 - pt["opacite"]))
            rempli = QColor(g, g, g)
            pointe = QPolygonF([QPointF(x - 5, b.top() - 6), QPointF(x + 5, b.top() - 6), QPointF(x, b.top() - 1)])
            carre = QRectF(x - 5, b.top() - 16, 10, 10)
        else:
            rempli = self._couleur_point(pt)
            pointe = QPolygonF([QPointF(x - 5, b.bottom() + 6), QPointF(x + 5, b.bottom() + 6), QPointF(x, b.bottom() + 1)])
            carre = QRectF(x - 5, b.bottom() + 6, 10, 10)
        if retire:
            p.setOpacity(0.35)
        p.setPen(QPen(QColor(0, 120, 215) if choisi else QColor(40, 40, 40), 2 if choisi else 1))
        p.setBrush(QColor(0, 120, 215) if choisi else QColor(90, 90, 90))
        p.drawPolygon(pointe)
        p.setBrush(rempli)
        p.drawRect(carre)
        if rangee == "couleurs" and pt["couleur"] == PEINTURE:      # point « couleur de peinture » : petit P
            p.setPen(QColor(255, 255, 255) if rempli.lightnessF() < 0.5 else QColor(0, 0, 0))
            f = p.font()
            f.setPixelSize(8)
            f.setBold(True)
            p.setFont(f)
            p.drawText(carre, Qt.AlignCenter, "P")
        p.setOpacity(1)

    # souris
    def _rangee_a(self, y: float) -> str | None:
        b = self._barre()
        if y < b.top():
            return "opacites"
        if y > b.bottom():
            return "couleurs"
        return None

    def _point_a(self, rangee: str, x: float):
        meilleur, ecart = None, 7.0
        for pt in self.d[rangee]:
            e = abs(self._x(pt["pos"]) - x)
            if e <= ecart:
                meilleur, ecart = pt, e
        return meilleur

    def valeur_a(self, rangee: str, pos: float):
        """Couleur (« #rrggbb ») ou opacité du dégradé à cet endroit (pour un nouveau point)."""
        r, v, b_, a = table(self.d, self.peinture, 1025)[round(pos * 1024)]
        if rangee == "couleurs":
            return QColor.fromRgbF(float(r), float(v), float(b_)).name()
        return round(float(a), 3)

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        x, y = e.position().x(), e.position().y()
        rangee = self._rangee_a(y)
        if rangee is None:
            return
        if self.choix is not None and self.choix[0] == rangee and abs(y - self._y_milieu(rangee)) <= 6:
            for porteur, mx in self._milieux(rangee, self.choix[1]):
                if abs(mx - x) <= 6:
                    self._glisse = ("milieu", rangee, porteur)
                    return
        pt = self._point_a(rangee, x)
        if pt is None:
            pos = self._pos(x)
            if rangee == "couleurs":
                pt = _c(pos, self.valeur_a(rangee, pos))
            else:
                pt = _o(pos, self.valeur_a(rangee, pos))
            self.d[rangee].append(pt)
            self.d[rangee].sort(key=lambda q: q["pos"])
            self.change.emit()
        self.choix = (rangee, pt)
        self._glisse = ("point", rangee, pt)
        self._a_retirer = False
        self.choix_change.emit()
        self.update()

    def mouseMoveEvent(self, e):
        if self._glisse is None:
            return
        genre, rangee, pt = self._glisse
        x, y = e.position().x(), e.position().y()
        if genre == "milieu":
            pts = self.d[rangee]
            i = next(k for k, q in enumerate(pts) if q is pt)
            a, b = pts[i - 1]["pos"], pt["pos"]
            if b - a > 1e-6:
                pt["milieu"] = min(MILIEU_MAX, max(MILIEU_MIN, (self._pos(x) - a) / (b - a)))
        else:
            pt["pos"] = round(self._pos(x), 4)
            self.d[rangee].sort(key=lambda q: q["pos"])
            self._a_retirer = abs(y - self._y_rangee(rangee)) > 40 and len(self.d[rangee]) > 2
            self.choix_change.emit()
        self.change.emit()
        self.update()

    def mouseReleaseEvent(self, e):
        if self._glisse is not None and self._glisse[0] == "point" and self._a_retirer:
            self.retirer()
        self._glisse = None
        self._a_retirer = False
        self.update()

    def mouseDoubleClickEvent(self, e):
        rangee = self._rangee_a(e.position().y())
        pt = self._point_a(rangee, e.position().x()) if rangee == "couleurs" else None
        if pt is not None:
            self.choix = ("couleurs", pt)
            self.choix_change.emit()
            self.choisir_couleur()

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self.retirer()
        else:
            super().keyPressEvent(e)

    # actions
    def retirer(self) -> bool:
        """Retire le point choisi (il en reste toujours deux par rangée)."""
        if self.choix is None:
            return False
        rangee, pt = self.choix
        pts = self.d[rangee]
        if len(pts) <= 2 or pt not in pts:
            return False
        pts.remove(pt)
        self.choix = (rangee, pts[0])
        self.change.emit()
        self.choix_change.emit()
        self.update()
        return True

    def choisir_couleur(self):
        if self.choix is None or self.choix[0] != "couleurs":
            return
        pt = self.choix[1]
        c = QColorDialog.getColor(self._couleur_point(pt), self.window(), tr("Couleur du point"))
        if c.isValid():
            pt["couleur"] = c.name()
            self.change.emit()
            self.choix_change.emit()
            self.update()

    def definir(self, d: dict):
        self.d = normaliser(d)
        self.choix = ("couleurs", self.d["couleurs"][0])
        self.change.emit()
        self.choix_change.emit()
        self.update()


# ------------------------------------------------------------------ fenêtre
class EditeurDegrade(QDialog):
    """Éditeur de dégradé. Après exec() : self.degrade (dict normalisé). Signal en_direct(dict) à chaque
    changement (aperçu sur le calque pendant qu'on règle)."""
    en_direct = Signal(object)

    def __init__(self, d: dict, peinture=None, parent=None, avec_peinture: bool = True):
        super().__init__(parent)
        self.setWindowTitle(tr("Éditeur de dégradé"))
        self.avec_peinture = avec_peinture          # « couleur de peinture » proposée (pas dans les styles)
        self.peinture = QColor(peinture) if peinture is not None else None
        lay = QVBoxLayout(self)

        lay.addWidget(QLabel(tr("Dégradés tout prêts et enregistrés :")))
        self.liste = QListWidget()
        self.liste.setViewMode(QListWidget.IconMode)
        self.liste.setIconSize(QSize(64, 22))
        self.liste.setGridSize(QSize(72, 30))
        self.liste.setMovement(QListWidget.Static)
        self.liste.setResizeMode(QListWidget.Adjust)
        self.liste.setFixedHeight(110)
        self.liste.itemClicked.connect(self._pret_choisi)
        self.liste.currentItemChanged.connect(lambda *_: self._maj_boutons_liste())
        lay.addWidget(self.liste)
        ligne = QHBoxLayout()
        self.b_enregistrer = QPushButton(tr("Enregistrer dans la liste…"))
        self.b_enregistrer.clicked.connect(self._enregistrer)
        self.b_retirer_liste = QPushButton(tr("Retirer de la liste"))
        self.b_retirer_liste.clicked.connect(self._retirer_liste)
        ligne.addWidget(self.b_enregistrer)
        ligne.addWidget(self.b_retirer_liste)
        ligne.addStretch(1)
        lay.addLayout(ligne)

        self.barre = BarreDegrade(d, self.peinture)
        lay.addWidget(self.barre)
        aide = QLabel(tr("Clic sous la barre : ajouter une couleur. Clic au-dessus : ajouter un point d'opacité. "
                         "Glisser un point pour le déplacer ; le tirer loin de la barre (ou touche Suppr) pour le "
                         "retirer. Double-clic sur un point de couleur : choisir sa couleur. Les losanges règlent le "
                         "milieu du passage d'un point à l'autre."))
        aide.setWordWrap(True)
        f = aide.font()
        f.setPointSizeF(f.pointSizeF() * 0.9)
        aide.setFont(f)
        lay.addWidget(aide)

        boite = QGroupBox(tr("Point choisi"))
        bl = QHBoxLayout(boite)
        self.pile = QStackedWidget()
        # point de couleur
        pc = QWidget()
        l1 = QHBoxLayout(pc)
        l1.setContentsMargins(0, 0, 0, 0)
        self.b_couleur = QToolButton()
        self.b_couleur.setIconSize(QSize(34, 16))
        self.b_couleur.setToolTip(tr("Couleur du point"))
        self.b_couleur.clicked.connect(self.barre.choisir_couleur)
        self.c_peinture = QCheckBox(tr("Couleur de peinture"))
        self.c_peinture.setToolTip(tr("Le point prend la couleur de peinture du moment"))
        self.c_peinture.toggled.connect(self._peinture_cochee)
        self.c_peinture.setVisible(avec_peinture)
        l1.addWidget(QLabel(tr("Couleur")))
        l1.addWidget(self.b_couleur)
        l1.addWidget(self.c_peinture)
        l1.addStretch(1)
        # point d'opacité
        po = QWidget()
        l2 = QHBoxLayout(po)
        l2.setContentsMargins(0, 0, 0, 0)
        self.s_opacite = QSpinBox()
        self.s_opacite.setRange(0, 100)
        self.s_opacite.setSuffix(" %")
        self.s_opacite.valueChanged.connect(self._opacite_tapee)
        l2.addWidget(QLabel(tr("Opacité")))
        l2.addWidget(self.s_opacite)
        l2.addStretch(1)
        self.pile.addWidget(pc)
        self.pile.addWidget(po)
        bl.addWidget(self.pile, 1)
        bl.addWidget(QLabel(tr("Position")))
        self.s_pos = QSpinBox()
        self.s_pos.setRange(0, 100)
        self.s_pos.setSuffix(" %")
        self.s_pos.valueChanged.connect(self._position_tapee)
        bl.addWidget(self.s_pos)
        self.b_retirer = QPushButton(tr("Supprimer"))
        self.b_retirer.clicked.connect(self.barre.retirer)
        bl.addWidget(self.b_retirer)
        lay.addWidget(boite)

        bas = QHBoxLayout()
        inverser = QPushButton(tr("Inverser"))
        inverser.setToolTip(tr("Le dégradé à l'envers"))
        inverser.clicked.connect(lambda: self.barre.definir(inverse(self.barre.d)))
        bas.addWidget(inverser)
        bas.addStretch(1)
        ok = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        ok.button(QDialogButtonBox.Ok).setText(tr("OK"))
        ok.button(QDialogButtonBox.Cancel).setText(tr("Annuler"))
        ok.accepted.connect(self.accept)
        ok.rejected.connect(self.reject)
        bas.addWidget(ok)
        lay.addLayout(bas)

        self.barre.choix_change.connect(self._maj_choix)
        self.barre.change.connect(lambda: self.en_direct.emit(self.degrade))
        self._remplir_liste()
        self._maj_choix()
        self.resize(560, 470)

    @property
    def degrade(self) -> dict:
        return normaliser(self.barre.d)

    # liste
    def _remplir_liste(self):
        self.liste.clear()
        for nom, d in tout_prets():
            if not self.avec_peinture and utilise_peinture(d):
                continue
            self._ajouter_item(nom, d, None)
        for i, (nom, d) in enumerate(enregistres()):
            self._ajouter_item(nom, d, i)
        self._maj_boutons_liste()

    def _ajouter_item(self, nom, d, perso):
        it = QListWidgetItem(QIcon(QPixmap.fromImage(image_apercu(d, 64, 22, self.peinture, 4))), "")
        it.setToolTip(nom + ("  (" + tr("enregistré") + ")" if perso is not None else ""))
        it.setData(Qt.UserRole, d)
        it.setData(Qt.UserRole + 1, perso)
        self.liste.addItem(it)

    def _pret_choisi(self, it):
        self.barre.definir(copy.deepcopy(it.data(Qt.UserRole)))

    def _maj_boutons_liste(self):
        it = self.liste.currentItem()
        self.b_retirer_liste.setEnabled(it is not None and it.data(Qt.UserRole + 1) is not None)

    def _enregistrer(self):
        nom, ok = QInputDialog.getText(self, tr("Enregistrer le dégradé"), tr("Nom du dégradé :"))
        if ok and nom.strip():
            mettre_enregistres(enregistres() + [(nom.strip(), self.degrade)])
            self._remplir_liste()
            self.liste.setCurrentRow(self.liste.count() - 1)

    def _retirer_liste(self):
        it = self.liste.currentItem()
        if it is None or it.data(Qt.UserRole + 1) is None:
            return
        liste = enregistres()
        i = it.data(Qt.UserRole + 1)
        if 0 <= i < len(liste):
            del liste[i]
            mettre_enregistres(liste)
        self._remplir_liste()

    # point choisi
    def _maj_choix(self):
        ch = self.barre.choix
        if ch is None:
            return
        rangee, pt = ch
        for w in (self.s_pos, self.s_opacite, self.c_peinture):
            w.blockSignals(True)
        self.s_pos.setValue(round(pt["pos"] * 100))
        if rangee == "couleurs":
            self.pile.setCurrentIndex(0)
            self.c_peinture.setChecked(pt["couleur"] == PEINTURE)
            self.b_couleur.setEnabled(pt["couleur"] != PEINTURE)
            ic = QPixmap(34, 16)
            ic.fill(self.barre._couleur_point(pt))
            self.b_couleur.setIcon(QIcon(ic))
        else:
            self.pile.setCurrentIndex(1)
            self.s_opacite.setValue(round(pt["opacite"] * 100))
        self.b_retirer.setEnabled(len(self.barre.d[rangee]) > 2)
        for w in (self.s_pos, self.s_opacite, self.c_peinture):
            w.blockSignals(False)

    def _position_tapee(self, v):
        if self.barre.choix is None:
            return
        rangee, pt = self.barre.choix
        pt["pos"] = v / 100
        self.barre.d[rangee].sort(key=lambda q: q["pos"])
        self.barre.change.emit()
        self.barre.update()

    def _opacite_tapee(self, v):
        if self.barre.choix is None or self.barre.choix[0] != "opacites":
            return
        self.barre.choix[1]["opacite"] = v / 100
        self.barre.change.emit()
        self.barre.update()

    def _peinture_cochee(self, oui):
        if self.barre.choix is None or self.barre.choix[0] != "couleurs":
            return
        pt = self.barre.choix[1]
        if oui:
            pt["couleur"] = PEINTURE
        elif pt["couleur"] == PEINTURE:
            pt["couleur"] = self.barre._couleur_point(pt).name()
        self.barre.change.emit()
        self._maj_choix()
        self.barre.update()


# ------------------------------------------------------------------ bouton (barre du haut, styles)
class BoutonDegrade(QToolButton):
    """Aperçu du dégradé ; un clic ouvre l'éditeur. Signal change(dict)."""
    change = Signal(object)

    def __init__(self, d: dict | None = None, peinture=None, parent=None, largeur: int = 64,
                 avec_peinture: bool = True, en_direct: bool = False):
        super().__init__(parent)
        self.en_direct = en_direct        # change émis à chaque réglage dans l'éditeur (et l'ancien remis si Annuler)
        self.peinture = peinture          # fonction qui donne la couleur de peinture du moment (ou None)
        self.avec_peinture = avec_peinture
        self.largeur = largeur
        self.setIconSize(QSize(largeur, 16))
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(tr("Dégradé : clic pour modifier ses couleurs (éditeur de dégradé)"))
        self.clicked.connect(self.choisir)
        self.degrade = normaliser(d)
        self.rafraichir()

    def _couleur_peinture(self):
        return self.peinture() if callable(self.peinture) else self.peinture

    def definir(self, d: dict):
        self.degrade = normaliser(d)
        self.rafraichir()

    def rafraichir(self):
        self.setIcon(QIcon(QPixmap.fromImage(image_apercu(self.degrade, self.largeur, 16,
                                                          self._couleur_peinture(), 4))))

    def choisir(self):
        depart = copy.deepcopy(self.degrade)
        dlg = EditeurDegrade(copy.deepcopy(self.degrade), self._couleur_peinture(), self.window(), self.avec_peinture)
        if self.en_direct:
            dlg.en_direct.connect(self.change.emit)
        ok = dlg.exec()
        choisi = dlg.degrade
        if self.en_direct:
            dlg.en_direct.disconnect()
        dlg.deleteLater()                    # fenêtre détruite (sinon elle reste attachée à sa fenêtre parente)
        if ok:
            self.definir(choisi)
            self.change.emit(self.degrade)
        elif self.en_direct:                 # Annuler : le dégradé d'avant revient sur le calque
            self.definir(depart)
            self.change.emit(depart)
