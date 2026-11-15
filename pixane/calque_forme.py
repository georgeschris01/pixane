"""Calque de forme (comme les calques de forme de Photoshop) : le calque garde le tracé de la forme (points et
poignées de courbe), son remplissage et son contour, pas seulement les pixels. Changer la couleur, le contour ou son
épaisseur redessine la forme ; la déplacer, la redimensionner ou la tourner la garde nette et modifiable ; la Plume
peut en déplacer les points.

Comme le calque de pinceau : le calque n'est un calque de forme que tant que son image est celle dessinée ici (même
objet) ; une gomme, un filtre, l'IA… en font un calque d'image ordinaire.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen, QPolygonF, QTransform

FORMAT = QImage.Format_ARGB32_Premultiplied
GENRES = ("rectangle", "arrondi", "ellipse", "ligne", "fleche", "etoile", "polygone")
OUVERTS = ("ligne", "fleche")


def noms_genres() -> dict:
    from .langue import tr
    return {"rectangle": tr("Rectangle"), "arrondi": tr("Rectangle arrondi"), "ellipse": tr("Ellipse"),
            "ligne": tr("Ligne"), "fleche": tr("Flèche"), "etoile": tr("Étoile"), "polygone": tr("Polygone")}


# Un point du tracé : (x, y, ax, ay, bx, by) : le point, la poignée d'arrivée (a) et celle de départ (b), en px de
# l'image. Poignée = point lui-même : angle vif. Un sous-tracé : (ferme, (point, point, …)).

def _point(x, y, ax=None, ay=None, bx=None, by=None) -> tuple:
    return (float(x), float(y), float(x if ax is None else ax), float(y if ay is None else ay),
            float(x if bx is None else bx), float(y if by is None else by))


@dataclass(frozen=True, eq=False)
class Forme:
    traces: tuple = ()              # ((ferme, (point, …)), …)
    remplissage: str = "#ff000000"  # #aarrggbb ; "" : pas de remplissage
    contour: str = ""               # "" : pas de contour
    epaisseur: float = 4.0          # du contour (px)
    fleche: bool = False            # pointe de flèche au bout des tracés ouverts
    genre: str = "plume"            # d'où vient la forme (nom du calque, rien d'autre)
    rendu: QImage | None = None     # l'image du calque dessinée d'après cette forme (même objet que Calque.image)

    def avec(self, **changements) -> "Forme":
        return replace(self, rendu=None, **changements)

    # ---------------------------------------------------------- géométrie
    def transforme(self, t: QTransform) -> "Forme":
        det = t.m11() * t.m22() - t.m12() * t.m21()
        k = math.sqrt(abs(det)) or 1.0

        def m(x, y):
            q = t.map(QPointF(x, y))
            return q.x(), q.y()
        traces = tuple((ferme, tuple(m(x, y) + m(ax, ay) + m(bx, by) for (x, y, ax, ay, bx, by) in pts))
                       for ferme, pts in self.traces)
        return replace(self, rendu=None, traces=traces, epaisseur=max(0.5, self.epaisseur * k))

    def deplace(self, dx: float, dy: float) -> "Forme":
        return self.transforme(QTransform.fromTranslate(dx, dy))

    def chemin(self) -> QPainterPath:
        ch = QPainterPath()
        ch.setFillRule(Qt.WindingFill)
        for ferme, pts in self.traces:
            if not pts:
                continue
            ch.moveTo(pts[0][0], pts[0][1])
            suite = list(pts[1:]) + ([pts[0]] if ferme and len(pts) > 1 else [])
            prec = pts[0]
            for p in suite:
                if (prec[4], prec[5]) == (prec[0], prec[1]) and (p[2], p[3]) == (p[0], p[1]):
                    ch.lineTo(p[0], p[1])
                else:
                    ch.cubicTo(prec[4], prec[5], p[2], p[3], p[0], p[1])
                prec = p
            if ferme:
                ch.closeSubpath()
        return ch

    def ouverts(self) -> bool:
        return any(not ferme for ferme, _pts in self.traces)

    # ---------------------------------------------------------- fichier
    def vers_dict(self) -> dict:
        return {"traces": [{"f": ferme, "p": [[round(v, 2) for v in p] for p in pts]} for ferme, pts in self.traces],
                "remplissage": self.remplissage, "contour": self.contour, "epaisseur": self.epaisseur,
                "fleche": self.fleche, "genre": self.genre}

    @classmethod
    def depuis_dict(cls, d: dict) -> "Forme":
        traces = tuple((bool(t.get("f")), tuple(_point(*p[:6]) for p in t.get("p", []) if len(p) >= 6))
                       for t in d.get("traces", []))
        return cls(traces=traces, remplissage=str(d.get("remplissage", "")), contour=str(d.get("contour", "")),
                   epaisseur=float(d.get("epaisseur", 4)), fleche=bool(d.get("fleche", False)),
                   genre=str(d.get("genre", "plume")))


def valide(c) -> Forme | None:
    """La forme du calque, s'il est encore un calque de forme (son image n'a pas été changée autrement)."""
    f = getattr(c, "forme", None)
    return f if f is not None and f.rendu is not None and f.rendu is c.image else None


# ---------------------------------------------------------------- construction
def traces_depuis_chemin(ch: QPainterPath) -> tuple:
    """QPainterPath (lignes et courbes) -> sous-tracés de points avec poignées."""
    traces = []
    pts: list = []
    i, n = 0, ch.elementCount()

    def finir():
        if not pts:
            return
        ferme = len(pts) > 2 and abs(pts[0][0] - pts[-1][0]) < 1e-6 and abs(pts[0][1] - pts[-1][1]) < 1e-6
        if ferme:                                  # dernier point = premier : on fusionne leurs poignées
            der = pts.pop()
            x, y, _ax, _ay, bx, by = pts[0]
            pts[0] = (x, y, der[2], der[3], bx, by)
        traces.append((ferme, tuple(pts)))

    while i < n:
        e = ch.elementAt(i)
        if e.isMoveTo():
            finir()
            pts = [_point(e.x, e.y)]
            i += 1
        elif e.isLineTo():
            pts.append(_point(e.x, e.y))
            i += 1
        else:                                      # courbe : 2 poignées puis le point
            c1, c2, fin = e, ch.elementAt(i + 1), ch.elementAt(i + 2)
            x, y, ax, ay, _bx, _by = pts[-1]
            pts[-1] = (x, y, ax, ay, c1.x, c1.y)
            pts.append(_point(fin.x, fin.y, c2.x, c2.y))
            i += 3
    finir()
    return tuple(traces)


def chemin_genre(genre: str, a: QPointF, b: QPointF, cotes: int = 5) -> QPainterPath:
    r = QRectF(a, b).normalized()
    ch = QPainterPath()
    if genre == "rectangle":
        ch.addRect(r)
    elif genre == "arrondi":
        k = min(r.width(), r.height()) * 0.18
        ch.addRoundedRect(r, k, k)
    elif genre == "ellipse":
        ch.addEllipse(r)
    elif genre in ("etoile", "polygone"):
        c, rx, ry = r.center(), r.width() / 2, r.height() / 2
        n = max(3, cotes)
        sommets = n * 2 if genre == "etoile" else n
        poly = QPolygonF()
        for i in range(sommets):
            ang = -math.pi / 2 + i * 2 * math.pi / sommets
            k = 0.45 if genre == "etoile" and i % 2 else 1.0
            poly.append(QPointF(c.x() + math.cos(ang) * rx * k, c.y() + math.sin(ang) * ry * k))
        ch.addPolygon(poly)
        ch.closeSubpath()
    else:                                          # ligne, flèche
        ch.moveTo(a)
        ch.lineTo(b)
    return ch


def depuis_genre(genre: str, a: QPointF, b: QPointF, couleur: QColor, remplir: bool, epaisseur: float,
                 cotes: int = 5, contour: QColor | None = None) -> Forme:
    """La forme dessinée d'un glissé de a à b. Ligne et flèche : un trait (contour) de la couleur choisie."""
    traces = traces_depuis_chemin(chemin_genre(genre, a, b, cotes))
    nom = couleur.name(QColor.HexArgb)
    if genre in OUVERTS:
        return Forme(traces, "", nom, max(1.0, epaisseur), genre == "fleche", genre)
    trait = contour.name(QColor.HexArgb) if contour is not None else ("" if remplir else nom)
    return Forme(traces, nom if remplir else "", trait, max(1.0, epaisseur), False, genre)


# ---------------------------------------------------------------- rendu
def _pointe(a: QPointF, b: QPointF, epaisseur: float) -> QPolygonF:
    t = max(12.0, epaisseur * 3.5)
    ang = math.atan2(b.y() - a.y(), b.x() - a.x())
    g, d = ang + math.radians(150), ang - math.radians(150)
    return QPolygonF([b, b + QPointF(math.cos(g), math.sin(g)) * t, b + QPointF(math.cos(d), math.sin(d)) * t])


def dessiner(p: QPainter, f: Forme):
    """La forme sur un peintre déjà placé (image du calque ou aperçu)."""
    p.setRenderHint(QPainter.Antialiasing)
    ch = f.chemin()
    if f.remplissage:
        p.fillPath(ch, QColor(f.remplissage))
    if f.contour and f.epaisseur > 0:
        couleur = QColor(f.contour)
        ouvert = f.ouverts()
        trace = ch
        if f.fleche:                           # le trait s'arrête avant la pointe, pour qu'elle reste fine
            trace = QPainterPath()
            for ferme, pts in f.traces:
                sous = Forme(((ferme, pts),)).chemin()
                if not ferme and len(pts) >= 2:
                    t = max(12.0, f.epaisseur * 3.5) * 0.8
                    long = sous.length()
                    if long > t:
                        fin = sous.percentAtLength(long - t)
                        coupe = QPainterPath()
                        coupe.moveTo(sous.pointAtPercent(0))
                        for i in range(1, 41):
                            coupe.lineTo(sous.pointAtPercent(fin * i / 40))
                        sous = coupe
                trace.addPath(sous)
        p.setPen(QPen(couleur, f.epaisseur, Qt.SolidLine, Qt.RoundCap if ouvert else Qt.SquareCap,
                      Qt.RoundJoin if ouvert else Qt.MiterJoin))
        p.setBrush(Qt.NoBrush)
        p.drawPath(trace)
        if f.fleche:
            p.setPen(Qt.NoPen)
            p.setBrush(couleur)
            for ferme, pts in f.traces:
                if not ferme and len(pts) >= 2:
                    sous = Forme(((ferme, pts),)).chemin()
                    long = sous.length()
                    avant = sous.pointAtPercent(sous.percentAtLength(max(0.0, long - 2)))
                    fin = QPointF(pts[-1][0], pts[-1][1])
                    p.drawPolygon(_pointe(avant, fin, f.epaisseur))


def rendre(f: Forme, W: int, H: int) -> QImage:
    img = QImage(W, H, FORMAT)
    img.fill(Qt.transparent)
    p = QPainter(img)
    dessiner(p, f)
    p.end()
    return img


def calque(c, f: Forme, W: int, H: int):
    """Le calque c devenu (ou resté) calque de forme f, redessiné sur W × H."""
    img = rendre(f, W, H)
    return replace(c, image=img, forme=replace(f, rendu=img), texte=None, hors=None, pinceau=None)


# ---------------------------------------------------------------- édition des points (Plume)
def deplacer_point(f: Forme, i: int, j: int, quoi: str, x: float, y: float, symetrique: bool = True) -> Forme:
    """Point j du sous-tracé i : quoi = "p" (le point et ses poignées), "a" ou "b" (une poignée ; l'autre suit en
    miroir si `symetrique` et si elle n'était pas un angle vif)."""
    traces = [list(t) for t in f.traces]
    ferme, pts = traces[i]
    pts = list(pts)
    px, py, ax, ay, bx, by = pts[j]
    if quoi == "p":
        dx, dy = x - px, y - py
        pts[j] = (x, y, ax + dx, ay + dy, bx + dx, by + dy)
    elif quoi == "a":
        if symetrique and (bx, by) != (px, py):
            bx, by = 2 * px - x, 2 * py - y
        pts[j] = (px, py, x, y, bx, by)
    else:
        if symetrique and (ax, ay) != (px, py):
            ax, ay = 2 * px - x, 2 * py - y
        pts[j] = (px, py, ax, ay, x, y)
    traces[i] = (ferme, tuple(pts))
    return replace(f, rendu=None, traces=tuple(tuple(t) for t in traces))
