"""Calque de pinceau modifiable : le calque garde le tracé de chaque coup de pinceau (points, pression, hasard), pas
seulement les pixels. Changer sa couleur, sa taille, son opacité, sa dureté, la rotation ou la forme du pinceau
redessine tous ses traits ; le déplacer, le redimensionner ou le tourner le garde modifiable.

Le calque n'est un calque de pinceau que tant que son image est celle dessinée ici (même objet) : une gomme, un
filtre, l'IA… changent l'image, et il devient un calque d'image ordinaire, sans rien à faire de plus.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field, replace

from PySide6.QtCore import QPoint, QPointF, QRect, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QTransform

from .pointe import Pointe, Reglages

FORMAT = QImage.Format_ARGB32_Premultiplied


@dataclass(frozen=True, eq=False)
class TraitEnr:
    points: tuple            # ((x, y, pression), …) en px de l'image
    graine: int              # hasard du trait (dispersion, variations) : redessiné à l'identique


@dataclass(frozen=True, eq=False)
class Pinceau:
    couleur: str = "#ff000000"      # #aarrggbb
    taille: float = 60.0
    durete: float = 0.8
    opacite: float = 1.0
    cle: str | None = None          # forme de la bibliothèque (None : rond)
    reglages: dict = field(default_factory=dict)   # pointe.Reglages (angle = rotation, espacement…)
    traits: tuple = ()
    rendu: QImage | None = None     # l'image du calque dessinée d'après ce pinceau (même objet que Calque.image)

    # ---------------------------------------------------------- réglages
    def r(self) -> Reglages:
        return Reglages.depuis_dict(self.reglages)

    def avec(self, **changements) -> "Pinceau":
        if "reglages" in changements and isinstance(changements["reglages"], Reglages):
            changements["reglages"] = changements["reglages"].vers_dict()
        return replace(self, rendu=None, **changements)

    def avec_trait(self, points, graine: int) -> "Pinceau":
        return replace(self, rendu=None, traits=self.traits + (TraitEnr(tuple(points), int(graine)),))

    # ---------------------------------------------------------- géométrie
    def transforme(self, t: QTransform) -> "Pinceau":
        """Traits passés par t (déplacer, redimensionner, tourner, miroir) : la taille suit l'échelle, la rotation
        du pinceau suit celle du calque."""
        det = t.m11() * t.m22() - t.m12() * t.m21()
        k = math.sqrt(abs(det)) or 1.0
        tourne = math.degrees(math.atan2(t.m12(), t.m11()))
        r = self.r()
        miroir = det < 0
        angle = r.angle + tourne
        if miroir:
            angle = -r.angle + tourne
        r = replace(r, angle=(angle + 180) % 360 - 180, retourner=r.retourner != miroir)
        traits = tuple(TraitEnr(tuple((q.x(), q.y(), p) for (x, y, p) in tr.points
                                      for q in (t.map(QPointF(x, y)),)), tr.graine) for tr in self.traits)
        return replace(self, rendu=None, taille=max(1.0, self.taille * k), reglages=r.vers_dict(), traits=traits)

    def deplace(self, dx: float, dy: float) -> "Pinceau":
        return self.transforme(QTransform.fromTranslate(dx, dy))

    # ---------------------------------------------------------- fichier
    def vers_dict(self) -> dict:
        return {"couleur": self.couleur, "taille": self.taille, "durete": self.durete, "opacite": self.opacite,
                "cle": self.cle, "reglages": self.reglages,
                "traits": [{"g": t.graine, "p": [[round(x, 2), round(y, 2), round(p, 3)] for x, y, p in t.points]}
                           for t in self.traits]}

    @classmethod
    def depuis_dict(cls, d: dict) -> "Pinceau":
        return cls(couleur=str(d.get("couleur", "#ff000000")), taille=float(d.get("taille", 60)),
                   durete=float(d.get("durete", 0.8)), opacite=float(d.get("opacite", 1.0)), cle=d.get("cle") or None,
                   reglages=dict(d.get("reglages") or {}),
                   traits=tuple(TraitEnr(tuple((float(x), float(y), float(p)) for x, y, p in t.get("p", [])),
                                         int(t.get("g", 0))) for t in d.get("traits", [])))


def nouvelle_graine() -> int:
    return random.randrange(1, 2 ** 31)


def valide(c) -> Pinceau | None:
    """Le pinceau du calque, s'il est encore un calque de pinceau (son image n'a pas été changée autrement)."""
    p = getattr(c, "pinceau", None)
    return p if p is not None and p.rendu is not None and p.rendu is c.image else None


# ---------------------------------------------------------------- rendu
_pointes: dict = {}


def _pointe(cle: str | None) -> Pointe | None:
    if not cle:
        return None
    from .bibliotheque import PINCEAUX, bibliotheque
    if cle not in _pointes:
        e = bibliotheque().trouver(PINCEAUX, cle)
        _pointes[cle] = Pointe(e.formes, e.espacement) if e is not None else None
    p = _pointes[cle]
    if p is not None:
        p.indice = 0                 # pinceau animé : chaque trait repart de la première forme
    return p


def parametres(p: Pinceau, tablette: bool = False) -> dict:
    """Ce que retouche.Trait reçoit (comme Canevas.parametres_pinceau) : {} = le rond simple."""
    r = p.r()
    if p.cle is None and r == Reglages() and not tablette:
        return {}
    kw = {"reglages": r, "fond": QColor(255, 255, 255)}
    pt = _pointe(p.cle)
    if pt is not None:
        kw["pointe"] = pt
    from .bibliotheque import MOTIFS, bibliotheque
    if r.texture:
        m = bibliotheque().trouver(MOTIFS, r.texture)
        if m is not None:
            kw["texture"] = m.image
    if r.double:
        d = _pointe(r.double)
        if d is not None:
            kw["double"] = d
    return kw


def _marge(p: Pinceau) -> float:
    r = p.r()
    m = p.taille * (0.75 + r.dispersion * (1.5 if r.deux_axes else 1.0))
    if r.double:
        m = max(m, p.taille * r.double_taille * (0.75 + r.double_dispersion))
    return m + 4


def rendre_trait(p: Pinceau, t: TraitEnr, W: int, H: int) -> tuple[QImage, QPoint] | None:
    """Un trait dessiné seul, dans le rectangle qui le contient (rapide même sur une grande image)."""
    from .retouche import Trait
    if not t.points:
        return None
    m = _marge(p)
    xs = [x for x, _y, _p in t.points]
    ys = [y for _x, y, _p in t.points]
    zone = QRect(math.floor(min(xs) - m), math.floor(min(ys) - m), 0, 0)
    zone.setRight(math.ceil(max(xs) + m))
    zone.setBottom(math.ceil(max(ys) + m))
    zone = zone.intersected(QRect(0, 0, W, H))
    if zone.isEmpty():
        return None
    base = QImage(zone.size(), FORMAT)
    base.fill(Qt.transparent)
    tablette = any(pr != 1.0 for _x, _y, pr in t.points)
    trait = Trait("peinture", base, p.taille, p.durete, p.opacite, couleur=QColor(p.couleur),
                  graine=t.graine, origine=zone.topLeft(), **parametres(p, tablette))
    ox, oy = zone.x(), zone.y()
    trait.tracer((QPointF(x - ox, y - oy), pr) for x, y, pr in t.points)
    return trait.image, zone.topLeft()


def rendre(p: Pinceau, W: int, H: int) -> QImage:
    """Tous les traits, dans l'ordre, sur un calque transparent W × H."""
    img = QImage(W, H, FORMAT)
    img.fill(Qt.transparent)
    q = QPainter(img)
    for t in p.traits:
        r = rendre_trait(p, t, W, H)
        if r is not None:
            q.drawImage(r[1], r[0])
    q.end()
    return img


def calque(c, p: Pinceau, W: int, H: int):
    """Le calque c devenu (ou resté) calque de pinceau p, redessiné sur W × H."""
    img = rendre(p, W, H)
    return replace(c, image=img, pinceau=replace(p, rendu=img), texte=None, hors=None)
