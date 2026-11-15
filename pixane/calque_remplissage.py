"""Calque de remplissage (comme les calques de remplissage de Photoshop) : couleur unie, dégradé ou motif sur toute
la feuille, modifiable à tout moment (double-clic sur le calque). Pratique pour un fond de pochette : changer sa
couleur ne demande pas de repeindre. Avec une sélection au moment de le créer, il reçoit un masque de calque.

Comme le calque de forme : le calque n'est un calque de remplissage que tant que son image est celle dessinée ici
(même objet) ; une gomme, un filtre, l'IA… en font un calque d'image ordinaire. Il suit la taille de la feuille
(redimensionner, agrandir la zone de travail, pivoter : il est redessiné).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace

import numpy as np
from PySide6.QtGui import QColor, QImage

from . import degrades, motifs

FORMAT = QImage.Format_ARGB32_Premultiplied
GENRES = ("couleur", "degrade", "motif")
STYLES = ("lineaire", "radial", "angle", "reflechi", "losange")
NOIR_BLANC = degrades.deux_couleurs("#000000", "#ffffff")


def noms_genres() -> dict:
    from .langue import tr
    return {"couleur": tr("Couleur unie"), "degrade": tr("Dégradé"), "motif": tr("Motif")}


def noms_styles() -> dict:
    from .langue import tr
    return {"lineaire": tr("Linéaire"), "radial": tr("Radial"), "angle": tr("Angulaire"), "reflechi": tr("Réfléchi"),
            "losange": tr("Losange")}


@dataclass(frozen=True, eq=False)
class Remplissage:
    genre: str = "couleur"
    couleur: str = "#ff3a7bd5"          # #aarrggbb
    degrade: dict | None = None         # dégradé (format de degrades.py) ; None : noir vers blanc
    style: str = "lineaire"
    angle: float = 90.0                 # degrés, 90 = de bas en haut (comme Photoshop)
    echelle: float = 100.0              # %
    inverser: bool = False
    motif: str | None = None            # clé du motif dans la bibliothèque
    motif_echelle: float = 100.0        # %
    rendu: QImage | None = None         # l'image du calque dessinée d'après ce remplissage (même objet que Calque.image)

    def avec(self, **changements) -> "Remplissage":
        return replace(self, rendu=None, **changements)

    def vers_dict(self) -> dict:
        return {"genre": self.genre, "couleur": self.couleur, "degrade": self.degrade, "style": self.style,
                "angle": self.angle, "echelle": self.echelle, "inverser": self.inverser, "motif": self.motif,
                "motif_echelle": self.motif_echelle}

    @staticmethod
    def depuis_dict(d: dict) -> "Remplissage":
        r = Remplissage()
        genre = d.get("genre") if d.get("genre") in GENRES else "couleur"
        style = d.get("style") if d.get("style") in STYLES else "lineaire"
        couleur = d.get("couleur") if isinstance(d.get("couleur"), str) and QColor(d.get("couleur")).isValid() \
            else r.couleur
        nombre = lambda k, defaut, mini, maxi: min(maxi, max(mini, float(d.get(k, defaut))))
        return Remplissage(genre, couleur, d.get("degrade") if isinstance(d.get("degrade"), dict) else None, style,
                           nombre("angle", 90, -360, 360), nombre("echelle", 100, 10, 1000), bool(d.get("inverser")),
                           d.get("motif") if isinstance(d.get("motif"), str) else None,
                           nombre("motif_echelle", 100, 1, 1000))

    def __eq__(self, autre):
        return isinstance(autre, Remplissage) and self.vers_dict() == autre.vers_dict()

    __hash__ = None


def _position(style: str, w: int, h: int, angle: float, echelle: float) -> np.ndarray:
    """Position 0..1 dans le dégradé pour chaque pixel (h, w), centré sur la feuille, comme Photoshop."""
    a = math.radians(angle)
    ux, uy = math.cos(a), -math.sin(a)                      # y vers le bas dans l'image
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    x = xs + 0.5 - w / 2
    y = ys + 0.5 - h / 2
    k = max(0.1, echelle / 100)
    if style in ("lineaire", "reflechi"):
        demi = (abs(ux) * w + abs(uy) * h) / 2 * k          # le dégradé couvre toute la feuille dans sa direction
        p = (x * ux + y * uy) / max(demi, 1e-3)              # -1..1
        return np.abs(p) if style == "reflechi" else (p + 1) / 2
    if style == "radial":
        return np.sqrt(x * x + y * y) / max(math.hypot(w, h) / 2 * k, 1e-3)
    if style == "losange":
        vx, vy = -uy, ux
        return (np.abs(x * ux + y * uy) + np.abs(x * vx + y * vy)) / max(max(w, h) / 2 * k, 1e-3)
    return ((np.arctan2(-y, x) - a) / (2 * math.pi)) % 1.0      # angulaire : un tour complet


def rendre(r: Remplissage, w: int, h: int, seize: bool | int = False) -> QImage:
    """seize : dégradé calculé en 16 bits (document 16 bits) ; 32 : image 32 bits (document 32 bits)."""
    b = 32 if seize == 32 and not isinstance(seize, bool) else 16 if seize else 8
    if r.genre == "motif":
        img = motifs.image_pavee(r.motif or motifs.DEFAUT, w, h, r.motif_echelle / 100)
        if img is not None:
            if b < 32:
                return img.convertToFormat(FORMAT)
            from .profondeur import en_32
            return en_32(img)
        r = r.avec(genre="couleur", couleur="#ff808080")    # motif introuvable : gris
    if r.genre == "degrade":
        d = degrades.normaliser(r.degrade if r.degrade is not None else NOIR_BLANC)
        if r.inverser:
            d = degrades.inverse(d)
        n = 1024
        tab = degrades.table(d, None, n)                   # (n, 4) RGBA 0..1, non prémultiplié
        pos = np.clip(_position(r.style, w, h, r.angle, r.echelle), 0, 1)
        if seize:                                          # 16 bits : couleurs interpolées, sans marches
            from .profondeur import qimage16, qimage32
            x = pos * (n - 1)
            c = np.stack([np.interp(x, np.arange(n), tab[:, k]) for k in range(4)], axis=-1)
            a = c[..., 3:4]
            if b == 32:
                return qimage32(np.concatenate([c[..., :3] * a, a], axis=2).astype(np.float32), premul=True)
            rgba = np.round(np.concatenate([c[..., :3] * a, a], axis=2) * 65535).astype(np.uint16)
            return qimage16(rgba, premul=True)
        i = np.round(pos * (n - 1)).astype(np.int32)
        c = tab[i]
        a = c[..., 3:4]
        rgba = np.round(np.concatenate([c[..., :3] * a, a], axis=2) * 255).astype(np.uint8)
        rgba = np.ascontiguousarray(rgba)
        return QImage(rgba.data, w, h, 4 * w, QImage.Format_RGBA8888_Premultiplied).convertToFormat(FORMAT)
    img = QImage(w, h, FORMAT if b == 8 else QImage.Format_RGBA64_Premultiplied if b == 16
                 else QImage.Format_RGBA32FPx4_Premultiplied)
    img.fill(QColor(r.couleur))
    return img


def calque(c, r: Remplissage, w: int, h: int):
    """Le calque c devient (ou reste) le calque de remplissage r, redessiné à la taille de la feuille."""
    from .profondeur import bits
    b = bits(c.image)
    img = rendre(r, w, h, b if b == 32 else b == 16)
    return replace(c, image=img, remplissage=replace(r, rendu=img), texte=None, pinceau=None, forme=None,
                   hors=None, hors_x=0, hors_y=0, origine=None)


def valide(c) -> Remplissage | None:
    r = getattr(c, "remplissage", None)
    return r if r is not None and r.rendu is c.image else None
