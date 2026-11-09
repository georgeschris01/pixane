"""Règles (en pixels de l'image), repères et grille.

Les règles entourent le canevas ; on tire un repère depuis une règle (bouton gauche, glisser dans la photo).
Avec l'outil Déplacer, un repère se déplace ; tiré hors de la photo, il disparaît. Les repères sont propres à
chaque photo (enregistrés dans le .pixane). Avec le magnétisme, les sélections rectangle, les formes, le dégradé et le
recadrage s'accrochent aux repères (et à la grille si elle est affichée).
"""
from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QGridLayout, QWidget

EPAISSEUR = 20
COULEUR_REPERE = QColor(0, 200, 255)


def pas_regle(zoom: float) -> tuple[float, int]:
    """(pas des graduations en pixels de l'image, nombre de sous-graduations) : environ 80 px d'écran entre deux
    nombres."""
    cible = 80 / max(zoom, 1e-6)
    p = 10 ** math.floor(math.log10(cible))
    for k in (1, 2, 5, 10):
        if p * k >= cible:
            return p * k, (5 if k in (1, 5, 10) else 4)
    return p * 10, 5


class Regle(QWidget):
    """Règle horizontale ou verticale ; glisser depuis elle crée un repère."""

    def __init__(self, canevas, horizontale: bool):
        super().__init__()
        self.c = canevas
        self.h = horizontale
        if horizontale:
            self.setFixedHeight(EPAISSEUR)
        else:
            self.setFixedWidth(EPAISSEUR)
        self.setCursor(Qt.SplitVCursor if horizontale else Qt.SplitHCursor)
        self.setToolTip("")

    def paintEvent(self, _e):
        p = QPainter(self)
        pal = self.palette()
        p.fillRect(self.rect(), pal.window().color().darker(104))
        p.setPen(pal.mid().color())
        if self.h:
            p.drawLine(0, self.height() - 1, self.width(), self.height() - 1)
        else:
            p.drawLine(self.width() - 1, 0, self.width() - 1, self.height())
        c = self.c
        if c.doc is None:
            return
        # origine : coin haut-gauche de la photo, dans le repère du canevas puis de cette règle
        decal = self.c.mapTo(self.parentWidget(), QPointF(0, 0).toPoint())
        moi = self.mapTo(self.parentWidget(), QPointF(0, 0).toPoint())
        o = (c.decalage.x() + decal.x() - moi.x()) if self.h else (c.decalage.y() + decal.y() - moi.y())
        pas, sous = pas_regle(c.zoom)
        longueur = self.width() if self.h else self.height()
        debut = math.floor((-o / c.zoom) / pas) * pas
        f = QFont(self.font())
        f.setPointSizeF(max(6.5, f.pointSizeF() * 0.75))
        p.setFont(f)
        p.setPen(pal.text().color())
        v = debut
        while (v * c.zoom + o) <= longueur:
            for k in range(sous):
                x = (v + k * pas / sous) * c.zoom + o
                t = EPAISSEUR * (0.55 if k == 0 else 0.25)
                if self.h:
                    p.drawLine(QPointF(x, EPAISSEUR - t), QPointF(x, EPAISSEUR))
                else:
                    p.drawLine(QPointF(EPAISSEUR - t, x), QPointF(EPAISSEUR, x))
            x = v * c.zoom + o
            texte = f"{v:g}"
            if self.h:
                p.drawText(QPointF(x + 2, 9), texte)
            else:
                p.save()
                p.translate(9, x + 2)
                p.rotate(90)
                p.drawText(QPointF(0, 0), texte)
                p.restore()
            v += pas
        # position de la souris
        s = c._souris
        if s is not None:
            cp = s.x() + decal.x() - moi.x() if self.h else s.y() + decal.y() - moi.y()
            p.setPen(QPen(COULEUR_REPERE, 1))
            if self.h:
                p.drawLine(QPointF(cp, 0), QPointF(cp, EPAISSEUR))
            else:
                p.drawLine(QPointF(0, cp), QPointF(EPAISSEUR, cp))
        p.end()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and self.c.doc is not None:
            self.c.commencer_repere("h" if self.h else "v")

    def mouseMoveEvent(self, e):
        if self.c.repere_tire is not None:
            self.c.bouger_repere(self.c.mapFromGlobal(e.globalPosition().toPoint()))

    def mouseReleaseEvent(self, e):
        if self.c.repere_tire is not None:
            self.c.finir_repere(self.c.mapFromGlobal(e.globalPosition().toPoint()))


class Coin(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(EPAISSEUR, EPAISSEUR)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.fillRect(self.rect(), self.palette().window().color().darker(104))
        p.end()


def entourer(canevas) -> tuple[QWidget, Regle, Regle, Coin]:
    """Canevas entouré de ses règles (cachables)."""
    w = QWidget()
    g = QGridLayout(w)
    g.setContentsMargins(0, 0, 0, 0)
    g.setSpacing(0)
    coin = Coin()
    rh = Regle(canevas, True)
    rv = Regle(canevas, False)
    g.addWidget(coin, 0, 0)
    g.addWidget(rh, 0, 1)
    g.addWidget(rv, 1, 0)
    g.addWidget(canevas, 1, 1)
    canevas.vue_peinte.connect(rh.update)
    canevas.vue_peinte.connect(rv.update)
    return w, rh, rv, coin


# ------------------------------------------------------------------ dessin et magnétisme (appelés par le canevas)
def dessiner(p: QPainter, c):
    doc = c.doc
    W, H = doc.image.width(), doc.image.height()
    haut_gauche = c.vers_ecran(QPointF(0, 0))
    bas_droite = c.vers_ecran(QPointF(W, H))
    if c.grille_visible:
        pas = c.pas_grille
        if pas * c.zoom >= 4:
            stylo = QPen(QColor(128, 128, 128, 110), 1)
            p.setPen(stylo)
            x = pas
            while x < W:
                e = c.vers_ecran(QPointF(x, 0)).x()
                p.drawLine(QPointF(e, haut_gauche.y()), QPointF(e, bas_droite.y()))
                x += pas
            y = pas
            while y < H:
                e = c.vers_ecran(QPointF(0, y)).y()
                p.drawLine(QPointF(haut_gauche.x(), e), QPointF(bas_droite.x(), e))
                y += pas
    if c.reperes_visibles:
        p.setPen(QPen(COULEUR_REPERE, 1))
        for sens, v in list(getattr(doc, "reperes", [])) + ([c.repere_tire] if c.repere_tire and
                                                             c.repere_tire[1] is not None else []):
            if sens == "h":
                y = c.vers_ecran(QPointF(0, v)).y()
                p.drawLine(QPointF(0, y), QPointF(c.width(), y))
            else:
                x = c.vers_ecran(QPointF(v, 0)).x()
                p.drawLine(QPointF(x, 0), QPointF(x, c.height()))


def aimanter(c, pt: QPointF) -> QPointF:
    """Point accroché au repère (ou à la ligne de grille) le plus proche, à moins de 8 px d'écran."""
    if not c.magnetisme or c.doc is None:
        return pt
    seuil = 8 / max(c.zoom, 1e-6)
    W, H = c.doc.image.width(), c.doc.image.height()
    xs, ys = [0.0, float(W)], [0.0, float(H)]
    if c.reperes_visibles:
        for sens, v in getattr(c.doc, "reperes", []):
            (ys if sens == "h" else xs).append(float(v))
    if c.grille_visible and c.pas_grille > 0:
        xs.append(round(pt.x() / c.pas_grille) * c.pas_grille)
        ys.append(round(pt.y() / c.pas_grille) * c.pas_grille)
    x, y = pt.x(), pt.y()
    bx = min(xs, key=lambda v: abs(v - x))
    by = min(ys, key=lambda v: abs(v - y))
    return QPointF(bx if abs(bx - x) <= seuil else x, by if abs(by - y) <= seuil else y)
