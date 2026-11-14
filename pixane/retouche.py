"""Retouche à la main sur un calque : pinceau de couleur et tampon (copier une zone sur une autre).

Un coup de pinceau est d'abord dessiné dans un « trait » (masque gris de la taille du calque : blanc = touché), puis
posé sur l'image
d'origine du calque avec l'opacité choisie : repasser au même endroit pendant un même coup ne fonce pas la couleur
(comme Photoshop). Seule la partie touchée est recalculée à chaque mouvement.
"""
from __future__ import annotations

import math

import numpy as np
from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QRadialGradient

from .pointe import Placement, Pointe, Reglages, dessiner, texture_grise, texture_zone

PEINTURE, TAMPON, GOMME = "peinture", "tampon", "gomme"


def _vue(img: QImage, zone: QRect) -> np.ndarray:
    """Pixels (h, w, 4) float32 0..1 d'une zone d'une image ARGB32 prémultipliée (ordre B, V, R, A)."""
    c = img.copy(zone)
    h, w, ligne = c.height(), c.width(), c.bytesPerLine()
    brut = np.frombuffer(c.constBits(), np.uint8, count=h * ligne).reshape(h, ligne)
    return brut[:, : w * 4].reshape(h, w, 4).astype(np.float32) / 255


def _qimage(a: np.ndarray) -> QImage:
    a = np.ascontiguousarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8))
    h, w = a.shape[:2]
    return QImage(a.data, w, h, 4 * w, QImage.Format_ARGB32_Premultiplied).copy()


class Trait:
    """Un coup de pinceau ou de tampon sur l'image d'un calque (FORMAT_CALQUE)."""

    def __init__(self, mode: str, base: QImage, taille: float, durete: float, opacite: float,
                 couleur: QColor | None = None, source: QImage | None = None, decalage: QPointF | None = None,
                 pointe: Pointe | None = None, reglages: Reglages | None = None, fond: QColor | None = None,
                 texture: np.ndarray | None = None, double: Pointe | None = None, graine: int | None = None,
                 origine: QPoint | None = None):
        """pointe : forme du pinceau (None : rond, réglé par durete). reglages : espacement, dispersion, texture…
        (voir pointe.Reglages). texture : motif (h, w, 4) ; double : deuxième forme. mode GOMME : efface.
        origine : place de `base` dans l'image (trait dessiné seul dans son rectangle : la texture reste alignée)."""
        self.origine = QPoint(origine) if origine is not None else QPoint(0, 0)
        self._differer = False                  # tracer() : composer une seule fois, à la fin
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
        self.formes = pointe is not None or reglages is not None or mode == GOMME   # sinon : rond d'avant
        if self.formes:                         # moteur à formes : touches tamponnées dans une couche
            self.reglages = reglages or Reglages()
            self.pointe = pointe or Pointe([_rond(self.durete)], 0.08)
            self.couche = QImage(base.size(), QImage.Format_ARGB32_Premultiplied)
            self.couche.fill(Qt.transparent)
            self.placement = Placement(self.pointe, self.reglages, self.taille, self.couleur, fond, graine)
            self.texture = (texture_grise(texture, self.reglages.texture_echelle)
                            if texture is not None and self.reglages.texture else None)
            self.double = None
            if double is not None and self.reglages.double:
                self.double = QImage(base.size(), QImage.Format_ARGB32_Premultiplied)
                self.double.fill(Qt.transparent)
                r2 = Reglages(espacement=self.reglages.double_espacement, dispersion=self.reglages.double_dispersion,
                              deux_axes=True, pression_taille=False)
                self.placement_double = Placement(double, r2, self.taille * self.reglages.double_taille,
                                                  QColor(255, 255, 255), graine=None if graine is None else graine + 1)

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

    def ajouter(self, pt: QPointF, pression: float = 1.0) -> QRect:
        """Prolonge le coup jusqu'au point ; renvoie la zone de l'image modifiée. pression : tablette (0..1)."""
        if self.formes:
            return self._ajouter_formes(pt, pression)
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
            if not self._differer:
                self._composer(zone)
        return zone

    def tracer(self, points) -> None:
        """Tout un trait d'un coup (points : [(QPointF, pression)]) : même résultat que des ajouter() successifs,
        mais l'image n'est composée qu'une fois (calque de pinceau redessiné)."""
        self._differer = True
        try:
            for pt, pression in points:
                self.ajouter(pt, pression)
        finally:
            self._differer = False
        tout = self.image.rect()
        if self.formes:
            self._composer_formes(tout)
        else:
            self._composer(tout)

    # ------------------------------------------------------------------ moteur à formes
    def _ajouter_formes(self, pt: QPointF, pression: float) -> QRect:
        touches = self.placement.ajouter(pt, pression)
        zone = QRectF()
        if touches:
            p = QPainter(self.couche)
            p.setRenderHint(QPainter.Antialiasing)
            couleur = self.mode == PEINTURE
            for t in touches:
                if self.reglages.pression_opacite:            # pression -> opacité : portée par la touche
                    t.flux *= max(0.0, min(1.0, pression))
                if self.reglages.var_opacite:
                    t.flux *= 1 - self.placement.hasard.random() * self.reglages.var_opacite
                zone = zone.united(dessiner(p, self.pointe, t, couleur))
            p.end()
        if self.double is not None:
            p = QPainter(self.double)
            p.setRenderHint(QPainter.Antialiasing)
            for t in self.placement_double.ajouter(pt, pression):
                zone = zone.united(dessiner(p, self.placement_double.pointe, t, False))
            p.end()
        zone = zone.toAlignedRect().intersected(self.image.rect())
        if not zone.isEmpty():
            if not self._differer:
                self._composer_formes(zone)
        return zone

    def _composer_formes(self, zone: QRect):
        couche = _vue(self.couche, zone)
        a = couche[..., 3]
        facteur = np.ones_like(a)
        if self.texture is not None:
            tex = texture_zone(self.texture, zone.x() + self.origine.x(), zone.y() + self.origine.y(),
                               zone.width(), zone.height())
            if self.reglages.texture_inverser:
                tex = 1 - tex
            facteur *= 1 - self.reglages.texture_force * (1 - tex)
        if self.double is not None:
            facteur *= _vue(self.double, zone)[..., 3]
        base = _vue(self.base, zone)
        k = (facteur * self.opacite)[..., None]
        if self.mode == GOMME:
            res = base * (1 - a[..., None] * k)
        elif self.mode == PEINTURE:
            res = couche * k + base * (1 - a[..., None] * k)
        else:                                                   # tampon : la source à travers la couche
            src = QImage(zone.size(), QImage.Format_ARGB32_Premultiplied)
            src.fill(Qt.transparent)
            pp = QPainter(src)
            pp.drawImage(QPointF(-zone.x(), -zone.y()) - self.decalage, self.source)
            pp.end()
            s = _vue(src, QRect(0, 0, zone.width(), zone.height()))
            m = a[..., None] * k
            res = s * m + base * (1 - m)
        p = QPainter(self.image)
        p.setCompositionMode(QPainter.CompositionMode_Source)
        p.drawImage(zone.topLeft(), _qimage(res))
        p.end()

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


_ronds: dict = {}


def _rond(durete: float) -> np.ndarray:
    """Forme ronde (pinceau par défaut dans le moteur à formes), gardée en mémoire par dureté."""
    from .pointe import forme_ronde
    cle = round(durete, 2)
    if cle not in _ronds:
        _ronds[cle] = forme_ronde(cle)
    return _ronds[cle]
