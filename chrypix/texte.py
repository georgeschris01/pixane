"""Calques de texte : réglages (police, couleur, effets…) et dessin du texte sur un calque.

Un calque de texte garde ses réglages (`Texte`) en plus de son image : on peut le modifier à tout moment.
Les tailles des effets (contour, ombre, fond) sont en % de la taille des lettres : ils suivent le texte
quand on change sa taille ou qu'on agrandit l'image.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, fields, replace

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QColor, QFont, QFontMetricsF, QImage, QPainter, QPainterPath, QPainterPathStroker, QPen,
                           QPolygonF, QTransform)

GAUCHE, CENTRE, DROITE = "gauche", "centre", "droite"


@dataclass(frozen=True)
class Texte:
    texte: str = "Texte"
    police: str = "Segoe UI"
    taille: float = 80.0             # hauteur des lettres, en px de l'image
    gras: bool = False
    italique: bool = False
    souligne: bool = False
    barre: bool = False
    couleur: str = "#ffffffff"       # #AARRGGBB
    alignement: str = GAUCHE
    x: float = 0.0                   # centre du bloc de texte, en px de l'image
    y: float = 0.0
    angle: float = 0.0               # rotation, en degrés (sens des aiguilles d'une montre)
    lettres: float = 0.0             # espacement des lettres, en % de la taille
    interligne: float = 1.2          # écart entre les lignes, × la taille
    courbe: float = 0.0              # arc en degrés : > 0 en voûte, < 0 en creux, 360 = cercle
    contour: bool = False
    contour_couleur: str = "#ff000000"
    contour_epaisseur: float = 6.0   # % de la taille
    ombre: bool = False
    ombre_couleur: str = "#b4000000"
    ombre_distance: float = 8.0      # % de la taille
    ombre_direction: float = 45.0    # degrés : 0 = vers la droite, 90 = vers le bas
    ombre_flou: float = 8.0          # % de la taille
    fond: bool = False
    fond_couleur: str = "#b4000000"
    fond_marge: float = 25.0         # % de la taille
    fond_arrondi: float = 20.0       # % de la taille

    # ---------------------------------------------------------- fichiers (.chr)
    def vers_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def depuis_dict(d: dict) -> "Texte":
        connus = {f.name for f in fields(Texte)}
        return Texte(**{k: v for k, v in d.items() if k in connus})

    # ---------------------------------------------------------- géométrie
    def deplace(self, dx: float, dy: float) -> "Texte":
        return replace(self, x=self.x + dx, y=self.y + dy)

    def mis_a_l_echelle(self, fx: float, fy: float) -> "Texte":
        return replace(self, x=self.x * fx, y=self.y * fy, taille=self.taille * (fx + fy) / 2)

    def pct(self, valeur: float) -> float:
        """% de la taille des lettres -> px."""
        return self.taille * valeur / 100


def nom_calque(t: Texte, defaut: str) -> str:
    """Nom automatique d'un calque de texte : sa première ligne (comme Photoshop)."""
    ligne = next((l.strip() for l in t.texte.splitlines() if l.strip()), "")
    return (ligne[:30] + "…") if len(ligne) > 30 else (ligne or defaut)


def police(t: Texte) -> QFont:
    f = QFont(t.police)
    f.setPixelSize(max(1, round(t.taille)))
    f.setBold(t.gras)
    f.setItalic(t.italique)
    f.setLetterSpacing(QFont.AbsoluteSpacing, t.pct(t.lettres))
    f.setHintingPreference(QFont.PreferNoHinting)
    f.setStyleStrategy(QFont.PreferAntialias)
    return f


# ------------------------------------------------------------------ mise en page
def forme(t: Texte) -> tuple[QPainterPath, QRectF]:
    """(tracé des lettres, rectangle du bloc), centrés sur (0, 0), avant rotation."""
    f = police(t)
    fm = QFontMetricsF(f)
    lignes = t.texte.split("\n") or [""]
    pas = t.taille * t.interligne
    largeurs = [fm.horizontalAdvance(l) for l in lignes]
    L = max(largeurs + [1.0])
    trait = max(1.0, fm.lineWidth())
    decalages = [{GAUCHE: 0.0, CENTRE: (L - w) / 2, DROITE: L - w}.get(t.alignement, 0.0) for w in largeurs]
    chemin = QPainterPath()
    chemin.setFillRule(Qt.WindingFill)

    def deco(c: QPainterPath, x: float, base: float, w: float):
        if t.souligne:
            c.addRect(QRectF(x, base + fm.underlinePos(), w, trait))
        if t.barre:
            c.addRect(QRectF(x, base - fm.strikeOutPos() - trait / 2, w, trait))

    if abs(t.courbe) < 0.5:
        hauteur = fm.height() + pas * (len(lignes) - 1)
        for i, (l, w, x0) in enumerate(zip(lignes, largeurs, decalages)):
            base = fm.ascent() + i * pas
            chemin.addText(x0, base, f, l)
            if l:
                deco(chemin, x0, base, w)
        chemin.translate(-L / 2, -hauteur / 2)
        bloc = QRectF(-L / 2, -hauteur / 2, L, hauteur)
        return chemin, bloc

    # texte en courbe : chaque lettre est posée et tournée le long d'un arc de cercle
    k = 1 if t.courbe > 0 else -1                       # 1 = voûte (∩), -1 = creux (∪)
    R = L / math.radians(min(360.0, abs(t.courbe)))     # rayon de la ligne la plus longue
    for i, (l, x0) in enumerate(zip(lignes, decalages)):
        r = max(pas * 0.5, R - k * i * pas)
        for j, ch in enumerate(l):
            if ch.isspace():
                continue
            avance = fm.horizontalAdvance(ch)
            s = x0 + fm.horizontalAdvance(l[:j]) + avance / 2 - L / 2      # abscisse du centre de la lettre
            theta = s / r
            px, py = r * math.sin(theta), k * (R - r * math.cos(theta))
            lettre = QPainterPath()
            lettre.addText(-avance / 2, 0, f, ch)
            deco(lettre, -avance / 2, 0, avance)
            tr = QTransform()
            tr.translate(px, py)
            tr.rotate(math.degrees(k * theta))
            chemin.addPath(tr.map(lettre))
    bloc = chemin.boundingRect()
    if bloc.isEmpty():
        bloc = QRectF(-L / 2, -fm.height() / 2, L, fm.height())
    centre = bloc.center()
    chemin.translate(-centre)
    bloc.translate(-centre)
    return chemin, bloc


def transformation(t: Texte) -> QTransform:
    tr = QTransform()
    tr.translate(t.x, t.y)
    tr.rotate(t.angle)
    return tr


def contour_bloc(t: Texte) -> QPolygonF:
    """Rectangle du bloc (fond compris), tourné, en coordonnées de l'image : pour le cadre et les clics."""
    _, bloc = forme(t)
    m = t.pct(t.fond_marge) if t.fond else 0.0
    m = max(m, t.taille * 0.1)
    return transformation(t).map(QPolygonF(bloc.adjusted(-m, -m, m, m)))


def contient(t: Texte, pt: QPointF) -> bool:
    return contour_bloc(t).containsPoint(pt, Qt.OddEvenFill)


# ------------------------------------------------------------------ dessin
def _flou_alpha(a: np.ndarray, rayon: float) -> np.ndarray:
    """Flou proche d'un flou gaussien (3 flous en boîte) sur un tableau 2D float."""
    r = int(round(rayon / 1.7))
    if r < 1:
        return a
    for _ in range(3):
        for axe in (0, 1):
            b = np.moveaxis(a, axe, 0)
            p = np.pad(b, ((r + 1, r), (0, 0)), mode="constant")
            c = np.cumsum(p, axis=0)
            b = (c[2 * r + 1:] - c[:-2 * r - 1]) / (2 * r + 1)
            a = np.moveaxis(b, 0, axe)
    return a


def _silhouette(t: Texte, chemin: QPainterPath, bloc: QRectF) -> QPainterPath:
    """Forme complète (fond, contour, lettres) : sert à l'ombre."""
    s = QPainterPath()
    s.setFillRule(Qt.WindingFill)
    if t.fond:
        m, r = t.pct(t.fond_marge), t.pct(t.fond_arrondi)
        s.addRoundedRect(bloc.adjusted(-m, -m, m, m), r, r)
    s.addPath(chemin)
    if t.contour and t.contour_epaisseur > 0:
        st = QPainterPathStroker()
        st.setWidth(2 * t.pct(t.contour_epaisseur))
        st.setJoinStyle(Qt.RoundJoin)
        st.setCapStyle(Qt.RoundCap)
        s.addPath(st.createStroke(chemin))
    return s


def _dessiner_ombre(p: QPainter, t: Texte, silhouette: QPainterPath, largeur: int, hauteur: int):
    flou = t.pct(t.ombre_flou)
    d = t.pct(t.ombre_distance)
    a = math.radians(t.ombre_direction)
    dx, dy = d * math.cos(a), d * math.sin(a)
    zone = transformation(t).map(silhouette).boundingRect().translated(dx, dy)
    marge = flou * 1.6 + 2
    zone = zone.adjusted(-marge, -marge, marge, marge).toAlignedRect()
    zone = zone.intersected(QRectF(0, 0, largeur, hauteur).toAlignedRect())
    if zone.isEmpty():
        return
    masque = QImage(zone.width(), zone.height(), QImage.Format_Alpha8)
    masque.fill(0)
    q = QPainter(masque)
    q.setRenderHint(QPainter.Antialiasing)
    tr = QTransform()
    tr.translate(-zone.x() + dx, -zone.y() + dy)
    q.setTransform(transformation(t) * tr)
    q.fillPath(silhouette, QColor(0, 0, 0, 255))
    q.end()
    lb = masque.bytesPerLine()
    brut = np.frombuffer(masque.constBits(), np.uint8, count=zone.height() * lb).reshape(zone.height(), lb)
    alpha = _flou_alpha(brut[:, :zone.width()].astype(np.float32), flou)
    c = QColor(t.ombre_couleur)
    alpha = np.clip(alpha * (c.alpha() / 255), 0, 255).astype(np.uint8)
    rgba = np.empty((zone.height(), zone.width(), 4), np.uint8)
    rgba[:, :, 0], rgba[:, :, 1], rgba[:, :, 2], rgba[:, :, 3] = c.red(), c.green(), c.blue(), alpha
    img = QImage(rgba.data, zone.width(), zone.height(), zone.width() * 4, QImage.Format_RGBA8888)
    p.save()
    p.resetTransform()
    p.drawImage(zone.topLeft(), img)
    p.restore()


def dessiner(p: QPainter, t: Texte, largeur: int, hauteur: int):
    """Dessine le texte et ses effets avec le peintre `p` (coordonnées de l'image)."""
    chemin, bloc = forme(t)
    p.setRenderHint(QPainter.Antialiasing)
    if t.ombre:
        _dessiner_ombre(p, t, _silhouette(t, chemin, bloc), largeur, hauteur)
    p.save()
    p.setTransform(transformation(t), True)
    if t.fond:
        m, r = t.pct(t.fond_marge), t.pct(t.fond_arrondi)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(t.fond_couleur))
        p.drawRoundedRect(bloc.adjusted(-m, -m, m, m), r, r)
    if t.contour and t.contour_epaisseur > 0:
        p.strokePath(chemin, QPen(QColor(t.contour_couleur), 2 * t.pct(t.contour_epaisseur), Qt.SolidLine,
                                  Qt.RoundCap, Qt.RoundJoin))
    p.fillPath(chemin, QColor(t.couleur))
    p.restore()


def rendre(t: Texte, largeur: int, hauteur: int) -> QImage:
    """Image du calque de texte (transparente autour), à la taille du document."""
    img = QImage(largeur, hauteur, QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)
    p = QPainter(img)
    dessiner(p, t, largeur, hauteur)
    p.end()
    return img
