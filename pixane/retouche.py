"""Retouche à la main sur un calque : pinceau de couleur et tampon (copier une zone sur une autre).

Un coup de pinceau est d'abord dessiné dans un « trait » (masque gris de la taille du calque : blanc = touché), puis
posé sur l'image
d'origine du calque avec l'opacité choisie : repasser au même endroit pendant un même coup ne fonce pas la couleur
(comme Photoshop). Seule la partie touchée est recalculée à chaque mouvement.
"""
from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QRadialGradient

PEINTURE, TAMPON = "peinture", "tampon"


class Trait:
    """Un coup de pinceau ou de tampon sur l'image d'un calque (FORMAT_CALQUE)."""

    def __init__(self, mode: str, base: QImage, taille: float, durete: float, opacite: float,
                 couleur: QColor | None = None, source: QImage | None = None, decalage: QPointF | None = None):
        self.mode = mode
        self.base = base                        # image du calque avant le coup (jamais modifiée)
        self.image = base.copy()                # résultat en cours
        self.taille = max(1.0, float(taille))
        self.durete = max(0.0, min(1.0, durete))
        self.opacite = max(0.0, min(1.0, opacite))
        self.couleur = QColor(couleur) if couleur is not None else QColor(0, 0, 0)
        self.source = source                    # tampon : image où l'on copie (photo visible au début du coup)
        self.decalage = decalage or QPointF()   # tampon : source = point peint + décalage
        self.masque = QImage(base.size(), QImage.Format_ARGB32_Premultiplied)
        self.masque.fill(QColor(0, 0, 0))     # opaque : en mode « Éclaircir », le plus clair gagne (maximum)
        self._dernier: QPointF | None = None
        self._reste = 0.0                       # distance déjà parcourue depuis la dernière touche

    # ------------------------------------------------------------------ dessin du masque
    def _touche(self, p: QPainter, c: QPointF):
        r = self.taille / 2
        if self.durete >= 0.99:
            p.setBrush(QColor(255, 255, 255))
        else:
            g = QRadialGradient(c, r)
            g.setColorAt(0, QColor(255, 255, 255))
            g.setColorAt(self.durete, QColor(255, 255, 255))
            g.setColorAt(1, QColor(0, 0, 0))
            p.setBrush(g)
        p.drawEllipse(c, r, r)

    def ajouter(self, pt: QPointF) -> QRect:
        """Prolonge le coup jusqu'au point ; renvoie la zone de l'image modifiée."""
        p = QPainter(self.masque)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setCompositionMode(QPainter.CompositionMode_Lighten)     # le plus opaque gagne (pas d'accumulation)
        pas = max(1.0, self.taille * 0.08)
        zone = QRectF(pt, pt)
        if self._dernier is None:
            self._touche(p, pt)
        else:
            a = self._dernier
            d = math.hypot(pt.x() - a.x(), pt.y() - a.y())
            t = pas - self._reste
            while t <= d:
                self._touche(p, a + (pt - a) * (t / d))
                t += pas
            self._reste = d - (t - pas)
            zone = QRectF(a, pt).normalized()
        p.end()
        self._dernier = pt
        r = self.taille / 2 + 2
        zone = zone.adjusted(-r, -r, r, r).toAlignedRect().intersected(self.image.rect())
        if not zone.isEmpty():
            self._composer(zone)
        return zone

    # ------------------------------------------------------------------ rendu
    def _composer(self, zone: QRect):
        """Recalcule la zone : image d'origine + (couleur ou copie) à travers le masque, avec l'opacité."""
        pose = QImage(zone.size(), QImage.Format_ARGB32_Premultiplied)
        if self.mode == PEINTURE:
            pose.fill(self.couleur)
        else:
            pose.fill(Qt.transparent)
            pp = QPainter(pose)
            pp.drawImage(QPointF(-zone.x(), -zone.y()) - self.decalage, self.source)   # pixel p <- source(p + décalage)
            pp.end()
        gris = self.masque.copy(zone).convertToFormat(QImage.Format_Grayscale8)
        alpha = QImage(gris.constBits(), gris.width(), gris.height(), gris.bytesPerLine(), QImage.Format_Alpha8).copy()
        pp = QPainter(pose)
        pp.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        pp.drawImage(0, 0, alpha)
        pp.end()
        p = QPainter(self.image)
        p.setCompositionMode(QPainter.CompositionMode_Source)
        p.drawImage(zone.topLeft(), self.base, zone)
        p.setCompositionMode(QPainter.CompositionMode_SourceOver)
        p.setOpacity(self.opacite)
        p.drawImage(zone.topLeft(), pose)
        p.end()
