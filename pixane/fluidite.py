"""Filtres > Fluidité (comme Photoshop) : pousser, gonfler, contracter, faire tourbillonner l'image au pinceau,
ou la reconstruire par endroits.

Le travail est gardé dans un « champ de déplacement » : pour chaque point de l'image finale, l'endroit de l'image
d'origine où aller chercher sa couleur (point + décalage). Pendant le réglage, ce champ est tenu sur une image réduite
(rapide) ; à la fin, il est agrandi à la taille du calque et l'image d'origine est reprise en pleine définition :
rien n'est flouté par des passages successifs.
"""
from __future__ import annotations

import math

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen
from PySide6.QtWidgets import (QButtonGroup, QDialog, QHBoxLayout, QLabel, QPushButton, QToolButton, QVBoxLayout,
                               QWidget)

from .langue import tr

POUSSER, GONFLER, CONTRACTER, TOURBILLON, RECONSTRUIRE = "pousser", "gonfler", "contracter", "tourbillon", "reconstruire"
OUTILS = (POUSSER, GONFLER, CONTRACTER, TOURBILLON, RECONSTRUIRE)
APERCU_MAX = 1100                      # côté maximal de l'image de travail


def noms() -> dict:
    return {POUSSER: tr("Pousser"), GONFLER: tr("Gonfler"), CONTRACTER: tr("Contracter"),
            TOURBILLON: tr("Tourbillon"), RECONSTRUIRE: tr("Reconstruire")}


# ------------------------------------------------------------------ calcul
def echantillonner(t: np.ndarray, sx: np.ndarray, sy: np.ndarray) -> np.ndarray:
    """Couleur de t (h, w, c) aux points (sx, sy) (flottants), bilinéaire, bords répétés. -> float32."""
    h, w = t.shape[:2]
    sx = np.clip(sx, 0, w - 1.001)
    sy = np.clip(sy, 0, h - 1.001)
    x0 = sx.astype(np.int32)
    y0 = sy.astype(np.int32)
    fx = (sx - x0)[..., None]
    fy = (sy - y0)[..., None]
    f = t.astype(np.float32)
    a = f[y0, x0]
    b = f[y0, x0 + 1]
    c = f[y0 + 1, x0]
    d = f[y0 + 1, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def deformer(t: np.ndarray, champ: np.ndarray) -> np.ndarray:
    """t (h, w, 4) uint8 non prémultiplié ; champ (h, w, 2) : décalage (dx, dy) de chaque point. Les couleurs sont
    prises en prémultiplié (pas de halo au bord des zones transparentes)."""
    h, w = t.shape[:2]
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    f = t.astype(np.float32)
    f[..., :3] *= f[..., 3:4] / 255
    r = echantillonner(f, xs + champ[..., 0], ys + champ[..., 1])
    a = r[..., 3:4]
    r[..., :3] = np.where(a > 0.5, r[..., :3] * 255 / np.maximum(a, 1e-3), 0)
    return np.clip(np.round(r), 0, 255).astype(np.uint8)


def agrandir_champ(champ: np.ndarray, w: int, h: int) -> np.ndarray:
    """Champ de l'image de travail -> champ à la taille (w, h) du calque (décalages mis à l'échelle)."""
    ph, pw = champ.shape[:2]
    if (pw, ph) == (w, h):
        return champ
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    sx = (xs + 0.5) * pw / w - 0.5
    sy = (ys + 0.5) * ph / h - 0.5
    res = echantillonner(champ, sx, sy)
    res[..., 0] *= w / pw
    res[..., 1] *= h / ph
    return res


def touche(champ: np.ndarray, outil: str, cx: float, cy: float, rayon: float, force: float,
           vx: float = 0.0, vy: float = 0.0, origine: np.ndarray | None = None):
    """Une touche du pinceau sur le champ, en place. (vx, vy) : déplacement de la souris (Pousser)."""
    h, w = champ.shape[:2]
    r = max(1.0, rayon)
    x0, x1 = max(0, int(cx - r)), min(w, int(cx + r) + 2)
    y0, y1 = max(0, int(cy - r)), min(h, int(cy + r) + 2)
    if x0 >= x1 or y0 >= y1:
        return
    ys, xs = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    dx, dy = xs - cx, ys - cy
    d2 = (dx * dx + dy * dy) / (r * r)
    poids = np.clip(1 - d2, 0, 1) ** 2 * force                    # doux vers le bord
    zone = champ[y0:y1, x0:x1]
    if outil == POUSSER:
        # le point va chercher sa couleur là d'où vient la souris : l'image suit le geste
        zone[..., 0] -= vx * poids
        zone[..., 1] -= vy * poids
    elif outil in (GONFLER, CONTRACTER):
        k = 0.06 * poids * (1 if outil == GONFLER else -1)          # gonfler : couleur prise plus près du centre
        zone[..., 0] -= dx * k
        zone[..., 1] -= dy * k
    elif outil == TOURBILLON:
        a = 0.08 * poids                                           # sens des aiguilles d'une montre
        co, si = np.cos(a), np.sin(a)
        zone[..., 0] += dx * co - dy * si - dx
        zone[..., 1] += dx * si + dy * co - dy
    elif outil == RECONSTRUIRE:
        cible = origine[y0:y1, x0:x1] if origine is not None else 0
        zone += (cible - zone) * np.minimum(1.0, poids * 0.25)[..., None]


# ------------------------------------------------------------------ fenêtre
class _Apercu(QWidget):
    """Image de travail déformée ; on y peint avec l'outil choisi. Le cercle montre la taille du pinceau."""
    peint = Signal()

    def __init__(self, fenetre):
        super().__init__()
        self.f = fenetre
        self.setMouseTracking(True)
        self.setCursor(Qt.CrossCursor)
        self._souris = None
        self._dernier = None
        self.setMinimumSize(640, 460)

    def _cadre(self) -> QRectF:
        h, w = self.f.travail.shape[:2]
        k = min(self.width() / w, self.height() / h)
        return QRectF((self.width() - w * k) / 2, (self.height() - h * k) / 2, w * k, h * k)

    def vers_image(self, p: QPointF) -> QPointF:
        c = self._cadre()
        k = c.width() / self.f.travail.shape[1]
        return QPointF((p.x() - c.x()) / k, (p.y() - c.y()) / k)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(40, 40, 40))
        c = self._cadre()
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.drawImage(c, self.f.image_apercu())
        if self._souris is not None:
            k = c.width() / self.f.travail.shape[1]
            r = self.f.rayon() * k
            p.setRenderHint(QPainter.Antialiasing)
            p.setPen(QPen(QColor(0, 0, 0, 160), 2))
            p.drawEllipse(self._souris, r, r)
            p.setPen(QPen(QColor(255, 255, 255), 1))
            p.drawEllipse(self._souris, r, r)
        p.end()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.f.commencer()
            self._dernier = self.vers_image(e.position())
            self.f.peindre(self._dernier, QPointF(0, 0))
            self.update()

    def mouseMoveEvent(self, e):
        self._souris = e.position()
        if self._dernier is not None and e.buttons() & Qt.LeftButton:
            pt = self.vers_image(e.position())
            d = pt - self._dernier
            pas = max(1.0, self.f.rayon() * 0.2)
            n = max(1, int(math.hypot(d.x(), d.y()) / pas))
            for i in range(1, n + 1):
                self.f.peindre(self._dernier + d * (i / n), d / n)
            self._dernier = pt
        self.update()

    def mouseReleaseEvent(self, _e):
        self._dernier = None

    def leaveEvent(self, _e):
        self._souris = None
        self.update()


class DialogueFluidite(QDialog):
    """Après exec() accepté : `resultat()` donne le calque déformé (tableau RGBA à sa taille)."""

    def __init__(self, parent, rgba: np.ndarray):
        super().__init__(parent)
        from .dialogues_reglage import Curseur
        self.setWindowTitle(tr("Fluidité"))
        self.origine = rgba
        h, w = rgba.shape[:2]
        self.k = min(1.0, APERCU_MAX / max(w, h))
        pw, ph = max(1, round(w * self.k)), max(1, round(h * self.k))
        from PIL import Image
        self.travail = np.asarray(Image.fromarray(np.ascontiguousarray(rgba), "RGBA").resize((pw, ph), Image.LANCZOS))
        self.champ = np.zeros((ph, pw, 2), np.float32)
        self.annulations: list[np.ndarray] = []
        self._image = None
        self.outil = POUSSER
        lay = QHBoxLayout(self)
        gauche = QVBoxLayout()
        self.groupe = QButtonGroup(self)
        aides = {POUSSER: tr("Pousser : l'image suit le geste (allonger, affiner, déplacer un contour)"),
                 GONFLER: tr("Gonfler : agrandit ce qui est sous le pinceau (garder le bouton appuyé)"),
                 CONTRACTER: tr("Contracter : rétrécit ce qui est sous le pinceau"),
                 TOURBILLON: tr("Tourbillon : fait tourner ce qui est sous le pinceau"),
                 RECONSTRUIRE: tr("Reconstruire : revient peu à peu à l'image d'origine sous le pinceau")}
        for o in OUTILS:
            b = QToolButton()
            b.setText(noms()[o])
            b.setCheckable(True)
            b.setToolTip(aides[o])
            b.setMinimumWidth(130)
            b.clicked.connect(lambda _=False, o=o: self._choisir(o))
            self.groupe.addButton(b)
            gauche.addWidget(b)
            if o == POUSSER:
                b.setChecked(True)
        gauche.addSpacing(10)
        self.taille = Curseur(tr("Taille"), 5, 600, 80, " px")
        self.pression = Curseur(tr("Pression"), 1, 100, 50, " %")
        for c in (self.taille, self.pression):
            c.etiquette.setMinimumWidth(60)
            c.c.setMinimumWidth(120)
            gauche.addWidget(c)
        self.b_annuler_geste = QPushButton(tr("Défaire le dernier geste"))
        self.b_annuler_geste.clicked.connect(self.defaire)
        gauche.addWidget(self.b_annuler_geste)
        b = QPushButton(tr("Tout reconstruire"))
        b.setToolTip(tr("Revenir à l'image d'origine"))
        b.clicked.connect(self.tout_reconstruire)
        gauche.addWidget(b)
        gauche.addStretch(1)
        info = QLabel(tr("Peignez sur l'image. Le résultat est calculé en pleine définition à la fin."))
        info.setObjectName("discret")
        info.setWordWrap(True)
        info.setMaximumWidth(220)
        gauche.addWidget(info)
        ligne = QHBoxLayout()
        self.b_ok = QPushButton(tr("Appliquer"))
        self.b_ok.setDefault(True)
        self.b_ok.clicked.connect(self.accept)
        non = QPushButton(tr("Annuler"))
        non.clicked.connect(self.reject)
        ligne.addWidget(self.b_ok)
        ligne.addWidget(non)
        gauche.addLayout(ligne)
        lay.addLayout(gauche)
        self.apercu = _Apercu(self)
        lay.addWidget(self.apercu, 1)
        self._maj_boutons()

    def _choisir(self, o: str):
        self.outil = o

    def rayon(self) -> float:
        """Rayon du pinceau sur l'image de travail (la taille est donnée en pixels de la photo)."""
        return self.taille.valeur() / 2 * self.k

    def commencer(self):
        self.annulations.append(self.champ.copy())
        del self.annulations[:-30]
        self._maj_boutons()

    def peindre(self, pt: QPointF, d: QPointF):
        force = self.pression.valeur() / 100
        touche(self.champ, self.outil, pt.x(), pt.y(), self.rayon(), force, d.x(), d.y(),
               origine=np.zeros_like(self.champ))
        self._image = None

    def defaire(self):
        if self.annulations:
            self.champ = self.annulations.pop()
            self._image = None
            self._maj_boutons()
            self.apercu.update()

    def tout_reconstruire(self):
        if self.champ.any():
            self.commencer()
            self.champ[:] = 0
            self._image = None
            self.apercu.update()

    def _maj_boutons(self):
        self.b_annuler_geste.setEnabled(bool(self.annulations))

    def image_apercu(self) -> QImage:
        if self._image is None:
            t = deformer(self.travail, self.champ) if self.champ.any() else self.travail
            t = np.ascontiguousarray(t)
            self._image = QImage(t.data, t.shape[1], t.shape[0], t.shape[1] * 4, QImage.Format_RGBA8888).copy()
        return self._image

    def resultat(self) -> np.ndarray:
        """Le calque entier déformé, en pleine définition."""
        if not self.champ.any():
            return self.origine.copy()
        h, w = self.origine.shape[:2]
        return deformer(self.origine, agrandir_champ(self.champ, w, h))
