"""Transformer un calque (Ctrl+T, comme Photoshop) : agrandir, réduire, tourner, déplacer avec un cadre à poignées.

Le cadre entoure tous les pixels du calque, même ceux qui dépassent de la feuille, ou seulement ceux de la sélection
(le reste du calque, `fond`, ne bouge pas). Rien n'est coupé : `rendu_entier` donne le calque entier, la feuille
n'en montre qu'une partie. Coin : taille proportionnelle (Maj : libre), autour du coin opposé.
Milieu d'un côté : une seule direction. Dedans : déplacer. Dehors : tourner autour du centre, degré par degré
(Maj : par 15°) ; la barre d'options permet aussi de taper l'angle, la largeur et la hauteur.
"""
from __future__ import annotations

import math

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF
from PySide6.QtGui import QImage, QPainter, QTransform

POIGNEES = {"hg": (-1, -1), "h": (0, -1), "hd": (1, -1), "d": (1, 0), "bd": (1, 1), "b": (0, 1), "bg": (-1, 1),
            "g": (-1, 0)}


def _rot(v: QPointF, degres: float) -> QPointF:
    a = math.radians(degres)
    c, s = math.cos(a), math.sin(a)
    return QPointF(v.x() * c - v.y() * s, v.x() * s + v.y() * c)


class Transformation:
    def __init__(self, image: QImage, rect: QRect, fond: QImage | None = None, origine: QPoint = QPoint(0, 0)):
        """image : le calque entier, posé en `origine` dans la feuille ; rect : la partie à transformer (dans
        `image`) ; fond : le reste du calque (même taille et même place que `image`), qui ne bouge pas."""
        self.source = image.copy(rect)
        self.fond = fond                    # reste du calque, sous l'élément transformé (sélection)
        self.origine = QPoint(origine)
        self.bw, self.bh = rect.width(), rect.height()
        self.centre = QPointF(origine.x() + rect.x() + rect.width() / 2,
                              origine.y() + rect.y() + rect.height() / 2)
        self.sx = self.sy = 1.0
        self.angle = 0.0
        self._depart = None

    # ---------------------------------------------------------- géométrie
    def transfo(self) -> QTransform:
        return (QTransform().translate(self.centre.x(), self.centre.y()).rotate(self.angle)
                .scale(self.sx, self.sy).translate(-self.bw / 2, -self.bh / 2))

    def demi(self) -> tuple[float, float]:
        return self.sx * self.bw / 2, self.sy * self.bh / 2

    def point(self, gx: float, gy: float) -> QPointF:
        """Point du cadre : gx, gy dans -1..1 (coins, milieux)."""
        hw, hh = self.demi()
        return self.centre + _rot(QPointF(gx * hw, gy * hh), self.angle)

    def coins(self) -> list[QPointF]:
        return [self.point(-1, -1), self.point(1, -1), self.point(1, 1), self.point(-1, 1)]

    def local(self, p: QPointF) -> QPointF:
        return _rot(p - self.centre, -self.angle)

    def dedans(self, p: QPointF) -> bool:
        l = self.local(p)
        hw, hh = self.demi()
        return abs(l.x()) <= hw and abs(l.y()) <= hh

    def rendu(self, W: int, H: int, lisse: bool = True) -> QImage:
        """La feuille W × H (aperçu) : ce qui dépasse n'est pas dessiné."""
        return self._dessiner(QRect(0, 0, W, H), lisse)

    def rendu_entier(self, lisse: bool = True) -> tuple[QImage, int, int]:
        """Le calque entier après transformation, même ce qui dépasse de la feuille -> (image, x, y)."""
        r = self.transfo().mapRect(QRectF(0, 0, self.bw, self.bh)).toAlignedRect()
        if self.fond is not None:
            r = r.united(QRect(self.origine, self.fond.size()))
        return self._dessiner(r, lisse), r.x(), r.y()

    def _dessiner(self, r: QRect, lisse: bool) -> QImage:
        img = QImage(max(1, r.width()), max(1, r.height()), QImage.Format_ARGB32_Premultiplied)
        img.fill(0)
        p = QPainter(img)
        if self.fond is not None:
            p.drawImage(self.origine - r.topLeft(), self.fond)
        p.setRenderHint(QPainter.SmoothPixmapTransform, lisse)
        p.setRenderHint(QPainter.Antialiasing, lisse)
        p.setTransform(self.transfo() * QTransform().translate(-r.x(), -r.y()))
        p.drawImage(QRectF(0, 0, self.bw, self.bh), self.source)
        p.end()
        return img

    def resume(self) -> tuple[float, float, float]:
        """Largeur %, hauteur %, angle (degrés, -180..180)."""
        return self.sx * 100, self.sy * 100, (self.angle + 180) % 360 - 180

    # ---------------------------------------------------------- glisser
    def commencer(self, mode, p: QPointF):
        """mode : « deplacer », « tourner » ou le nom d'une poignée (voir POIGNEES)."""
        self._depart = (mode, p, QPointF(self.centre), self.sx, self.sy, self.angle)

    def glisser(self, p: QPointF, maj: bool):
        if self._depart is None:
            return
        mode, p0, c0, sx0, sy0, a0 = self._depart
        if mode == "deplacer":
            self.centre = c0 + (p - p0)
            return
        if mode == "tourner":
            v0, v = p0 - c0, p - c0
            a = a0 + math.degrees(math.atan2(v.y(), v.x()) - math.atan2(v0.y(), v0.x()))
            self.angle = round(a / 15) * 15 if maj else round(a)      # au degré près
            return
        gx, gy = POIGNEES[mode]
        w0, h0 = sx0 * self.bw, sy0 * self.bh
        # point fixe : coin ou côté opposé
        fixe = c0 + _rot(QPointF(-gx * w0 / 2, -gy * h0 / 2), a0)
        d = _rot(p - fixe, -a0)
        w, h = w0, h0
        if gx and gy and not maj:                     # coin : proportions gardées
            k = (d.x() * gx * w0 + d.y() * gy * h0) / (w0 * w0 + h0 * h0)
            w, h = max(1.0, k * w0), max(1.0, k * h0)
        else:
            if gx:
                w = max(1.0, d.x() * gx)
            if gy:
                h = max(1.0, d.y() * gy)
        self.sx, self.sy = w / self.bw, h / self.bh
        self.centre = fixe + _rot(QPointF(gx * w / 2, gy * h / 2), a0)

    def finir(self):
        self._depart = None
