"""Outils de dessin : dégradé, pot de peinture, formes (rectangle, ellipse, ligne, flèche), pinceau correcteur.

Calcul pur sur des QImage (FORMAT_CALQUE) ; le canevas s'occupe de la souris et d'Annuler.
"""
from __future__ import annotations

import math

import numpy as np
from PySide6.QtCore import QLineF, QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QImage, QLinearGradient, QPainter, QPainterPath, QPen, QPolygonF,
                           QRadialGradient)

FORMES = ("rectangle", "arrondi", "ellipse", "ligne", "fleche")


def noms_formes() -> dict:
    from .langue import tr
    return {"rectangle": tr("Rectangle"), "arrondi": tr("Rectangle arrondi"), "ellipse": tr("Ellipse"),
            "ligne": tr("Ligne"), "fleche": tr("Flèche")}


def _alpha_selection(selection: QImage | None) -> QImage | None:
    return selection


def _poser(base: QImage, calque: QImage, opacite: float, selection: QImage | None,
           garder_alpha: bool = False) -> QImage:
    """calque (taille de base) posé sur base, seulement dans la sélection s'il y en a une.
    garder_alpha : seulement sur les pixels déjà peints, sans changer leur transparence (« Garder la transparence »)."""
    if selection is not None:
        p = QPainter(calque)
        p.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        p.drawImage(0, 0, selection)
        p.end()
    res = base.copy()
    p = QPainter(res)
    if garder_alpha:
        p.setCompositionMode(QPainter.CompositionMode_SourceAtop)
    p.setOpacity(opacite)
    p.drawImage(0, 0, calque)
    p.end()
    return res


# ------------------------------------------------------------------ dégradé
def degrade(base: QImage, a: QPointF, b: QPointF, forme: str, points: dict, peinture: QColor, opacite: float,
            selection: QImage | None = None, gris: bool = False, garder_alpha: bool = False) -> QImage:
    """Dégradé à plusieurs points (pixane.degrades) du point a au point b ; peinture : couleur des points
    « couleur de peinture » ; gris : couleurs changées en gris (sur un masque) ; garder_alpha : seulement sur les
    pixels déjà peints (lettres d'un texte, objet détouré), leur transparence ne change pas."""
    from .degrades import remplir_qgradient
    if forme == "radial":
        g = QRadialGradient(a, max(1.0, QLineF(a, b).length()))
    else:
        g = QLinearGradient(a, b)
    remplir_qgradient(g, points, peinture, gris)
    from .profondeur import FORMAT_16, est_16
    tmp = QImage(base.size(), FORMAT_16 if est_16(base) else QImage.Format_ARGB32_Premultiplied)
    tmp.fill(Qt.transparent)
    p = QPainter(tmp)
    p.fillRect(tmp.rect(), QBrush(g))
    p.end()
    return _poser(base, tmp, opacite, selection, garder_alpha)


# ------------------------------------------------------------------ pot de peinture
def seau(base: QImage, visible_rgba: np.ndarray, x: int, y: int, tolerance: float, couleur: QColor, opacite: float,
         selection: QImage | None = None, remplissage: QImage | None = None) -> QImage | None:
    """Remplit la zone de couleur proche du point, d'après `visible_rgba` (le calque choisi, ou l'image visible avec
    « Tous les calques »). remplissage : image de la taille de base (un motif répété) à la place de la couleur.
    None si le point est hors image."""
    from .selection_auto import baguette
    h, w = visible_rgba.shape[:2]
    if not (0 <= x < w and 0 <= y < h):
        return None
    m = baguette(visible_rgba, x, y, tolerance, contigu=True, doux=True)
    m = np.clip(np.asarray(m, np.float32), 0, 255).astype(np.uint8)
    a = np.ascontiguousarray(m)
    alpha = QImage(a.data, w, h, w, QImage.Format_Alpha8).copy()
    if remplissage is not None:
        tmp = remplissage.convertToFormat(QImage.Format_ARGB32_Premultiplied).copy()
    else:
        tmp = QImage(base.size(), QImage.Format_ARGB32_Premultiplied)
        tmp.fill(couleur)
    p = QPainter(tmp)
    p.setCompositionMode(QPainter.CompositionMode_DestinationIn)
    p.drawImage(0, 0, alpha)
    p.end()
    return _poser(base, tmp, opacite, selection)


def remplir_motif(base: QImage, motif: QImage, opacite: float, selection: QImage | None = None) -> QImage:
    """Édition > Remplir avec un motif : le motif posé sur tout le calque, ou seulement dans la sélection."""
    return _poser(base, motif.convertToFormat(QImage.Format_ARGB32_Premultiplied).copy(), opacite, selection)


# ------------------------------------------------------------------ formes
def contraindre(a: QPointF, b: QPointF, forme: str) -> QPointF:
    """Maj : carré / cercle, ou ligne à 45° près."""
    d = b - a
    if forme in ("ligne", "fleche"):
        ang = math.atan2(d.y(), d.x())
        ang = round(ang / (math.pi / 4)) * (math.pi / 4)
        r = math.hypot(d.x(), d.y())
        return a + QPointF(math.cos(ang) * r, math.sin(ang) * r)
    c = max(abs(d.x()), abs(d.y()))
    return a + QPointF(math.copysign(c, d.x() or 1), math.copysign(c, d.y() or 1))


def chemin_forme(forme: str, a: QPointF, b: QPointF, epaisseur: float) -> QPainterPath:
    r = QRectF(a, b).normalized()
    ch = QPainterPath()
    if forme == "rectangle":
        ch.addRect(r)
    elif forme == "arrondi":
        k = min(r.width(), r.height()) * 0.18
        ch.addRoundedRect(r, k, k)
    elif forme == "ellipse":
        ch.addEllipse(r)
    else:
        fin = b
        if forme == "fleche":
            t = max(12.0, epaisseur * 3.5)
            ang = math.atan2(b.y() - a.y(), b.x() - a.x())
            fin = b - QPointF(math.cos(ang), math.sin(ang)) * t * 0.8
        ch.moveTo(a)
        ch.lineTo(fin)
    return ch


def pointe(a: QPointF, b: QPointF, epaisseur: float) -> QPolygonF:
    t = max(12.0, epaisseur * 3.5)
    ang = math.atan2(b.y() - a.y(), b.x() - a.x())
    g = ang + math.radians(150)
    d = ang - math.radians(150)
    return QPolygonF([b, b + QPointF(math.cos(g), math.sin(g)) * t, b + QPointF(math.cos(d), math.sin(d)) * t])


def forme(w: int, h: int, genre: str, a: QPointF, b: QPointF, couleur: QColor, remplir: bool,
          epaisseur: float) -> QImage:
    """Nouveau calque transparent avec la forme dessinée (bords lissés)."""
    img = QImage(w, h, QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    ch = chemin_forme(genre, a, b, epaisseur)
    if genre in ("ligne", "fleche"):
        p.setPen(QPen(couleur, max(1.0, epaisseur), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPath(ch)
        if genre == "fleche":
            p.setPen(Qt.NoPen)
            p.setBrush(couleur)
            p.drawPolygon(pointe(a, b, epaisseur))
    else:
        if remplir:
            p.fillPath(ch, couleur)
        else:
            p.setPen(QPen(couleur, max(1.0, epaisseur), Qt.SolidLine, Qt.SquareCap, Qt.MiterJoin))
            p.drawPath(ch)
    p.end()
    return img


# ------------------------------------------------------------------ pinceau correcteur
def corriger(avant: QImage, source: QImage, decalage: QPointF, masque_trait: QImage, opacite: float) -> QImage:
    """Pinceau correcteur (comme Photoshop) : la texture vient de l'endroit copié, mais la lumière et la couleur
    sont raccordées à celles autour de la zone peinte. Différence (autour − copie) mesurée juste au bord de la zone,
    puis étalée en douceur vers l'intérieur (interpolation par flous normalisés de plus en plus fins)."""
    from .document import FORMAT_CALQUE, FORMAT_IMAGE, qimage_rgba, tableau
    from .filtres import _flou_pil
    g = masque_trait.convertToFormat(QImage.Format_Grayscale8)
    h, w = g.height(), g.width()
    m = np.frombuffer(g.constBits(), np.uint8, count=h * g.bytesPerLine()).reshape(h, -1)[:, :w].astype(
        np.float32) / 255
    ys, xs = np.nonzero(m > 0.01)
    if not len(ys):
        return avant.copy()
    marge = 8
    y0, y1 = max(0, ys.min() - marge), min(h, ys.max() + 1 + marge)
    x0, x1 = max(0, xs.min() - marge), min(w, xs.max() + 1 + marge)
    A = tableau(avant.convertToFormat(FORMAT_IMAGE)).astype(np.float32)
    # copie brute (sans opacité) : pixel p <- source(p + décalage)
    S_img = QImage(avant.size(), QImage.Format_ARGB32_Premultiplied)
    S_img.fill(Qt.transparent)
    p = QPainter(S_img)
    p.drawImage(QPointF(0, 0) - decalage, source)
    p.end()
    S = tableau(S_img.convertToFormat(FORMAT_IMAGE)).astype(np.float32)
    a, s, mm = A[y0:y1, x0:x1], S[y0:y1, x0:x1], m[y0:y1, x0:x1]
    dedans = mm > 0.01
    from .styles import dilater
    autour = (dilater(dedans.astype(np.float32), 3) > 0.5) & ~dedans
    if not autour.any():
        autour = ~dedans
    diff = np.zeros_like(a)
    diff[autour] = a[autour] - s[autour]
    poids = autour.astype(np.float32)
    D = None
    sigma = max(2.0, max(dedans.shape) / 4)
    while sigma >= 1.5:                                   # du large vers le fin : la membrane se précise au bord
        num = _flou_pil(diff * poids[..., None], sigma)
        den = _flou_pil(np.repeat(poids[..., None], 4, axis=-1), sigma)[..., :1]
        est = num / np.maximum(den, 1e-4)
        if D is None:
            D = est
        else:
            k = np.clip(den * 4, 0, 1)                    # près du bord, l'estimation fine prend le dessus
            D = D * (1 - k) + est * k
        sigma /= 2
    res = np.clip(s + D, 0, 255)
    res[..., 3] = np.maximum(res[..., 3], s[..., 3])
    k = (mm * opacite * s[..., 3] / 255)[..., None]           # hors de l'image copiée : rien ne change
    out = A.copy()
    out[y0:y1, x0:x1] = a + (res - a) * k
    return qimage_rgba(np.clip(np.round(out), 0, 255).astype(np.uint8)).convertToFormat(FORMAT_CALQUE)
