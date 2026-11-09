"""Formats tout prêts de « Nouvelle image » (pochettes, livres, réseaux sociaux, impression, écran), unités de mesure
(pixels, pouces, cm, mm, points, picas) et formats enregistrés par l'utilisateur."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from .langue import tr

# taille d'une unité en pouces (1 pouce = 2,54 cm = 72 points = 6 picas) ; les pixels dépendent de la résolution
POUCES = {"in": 1.0, "cm": 1 / 2.54, "mm": 1 / 25.4, "pt": 1 / 72, "pc": 1 / 6}
UNITES = ("px", "in", "cm", "mm", "pt", "pc")


def nom_unite(u: str) -> str:
    return {"px": tr("pixels"), "in": tr("pouces"), "cm": tr("centimètres"), "mm": tr("millimètres"),
            "pt": tr("points"), "pc": tr("picas")}[u]


def abrege_unite(u: str) -> str:
    return {"px": "px", "in": tr("po|unité"), "cm": "cm", "mm": "mm", "pt": "pt", "pc": tr("pc|unité")}[u]


def vers_px(valeur: float, unite: str, dpi: float) -> int:
    """Longueur dans l'unité -> pixels (au moins 1)."""
    if unite == "px":
        return max(1, round(valeur))
    return max(1, round(valeur * POUCES[unite] * dpi))


def depuis_px(px: float, unite: str, dpi: float) -> float:
    if unite == "px":
        return float(px)
    return px / dpi / POUCES[unite]


def mm_vers_px(mm: float, dpi: float) -> int:
    return round(mm / 25.4 * dpi)


@dataclass(frozen=True)
class Format:
    nom: str
    largeur: float
    hauteur: float
    unite: str = "px"
    dpi: float = 72
    fond_perdu: float = 0.0      # mm, ajoutés de chaque côté (impression : coupé au massicot)
    marge: float = 0.0           # mm, zone de sécurité à l'intérieur du format fini (rien d'important au-delà)
    mode: str = ""               # « rvb » ou « gris » (vide : formats tout prêts, le choix actuel est gardé)
    fond: str = ""               # couleur du fond, #aarrggbb (#00000000 = transparent ; vide : choix actuel gardé)

    def pixels(self) -> tuple[int, int]:
        """Taille de l'image, fond perdu compris."""
        fp = 2 * mm_vers_px(self.fond_perdu, self.dpi)
        return vers_px(self.largeur, self.unite, self.dpi) + fp, vers_px(self.hauteur, self.unite, self.dpi) + fp


def formats() -> list[tuple[str, list[Format]]]:
    """Formats tout prêts, par catégorie (noms traduits)."""
    F = Format
    return [
        (tr("Pochettes"), [
            F(tr("CD : livret (12 × 12 cm)"), 120, 120, "mm", 300, 3, 3),
            F(tr("CD : jaquette arrière (15,1 × 11,8 cm)"), 151, 118, "mm", 300, 3, 3),
            F(tr("Vinyle 33 tours (31,4 × 31,4 cm)"), 314, 314, "mm", 300, 3, 5),
            F(tr("Vinyle 45 tours (18 × 18 cm)"), 180, 180, "mm", 300, 3, 4),
            F(tr("Plateformes de musique (3000 × 3000 px)"), 3000, 3000, "px", 300),
            F(tr("Pochette numérique minimum (1400 × 1400 px)"), 1400, 1400, "px", 300),
        ]),
        (tr("Livres"), [
            F(tr("Poche (11 × 18 cm)"), 110, 180, "mm", 300, 3, 5),
            F(tr("Roman (13 × 20 cm)"), 130, 200, "mm", 300, 3, 5),
            F(tr("Grand format (15,5 × 24 cm)"), 155, 240, "mm", 300, 3, 6),
            F(tr("Amazon KDP 6 × 9 pouces (15,24 × 22,86 cm)"), 6, 9, "in", 300, 3.2, 6.4),
            F(tr("A5 (14,8 × 21 cm)"), 148, 210, "mm", 300, 3, 5),
            F(tr("Livre numérique (1600 × 2560 px)"), 1600, 2560, "px", 300),
        ]),
        (tr("Réseaux sociaux"), [
            F(tr("Instagram : carré (1080 × 1080 px)"), 1080, 1080),
            F(tr("Instagram : portrait (1080 × 1350 px)"), 1080, 1350),
            F(tr("Story, Reel, TikTok (1080 × 1920 px)"), 1080, 1920),
            F(tr("Facebook : publication (1200 × 630 px)"), 1200, 630),
            F(tr("Facebook : couverture (851 × 315 px)"), 851, 315),
            F(tr("YouTube : miniature (1280 × 720 px)"), 1280, 720),
            F(tr("YouTube : bannière (2560 × 1440 px)"), 2560, 1440),
            F(tr("X (Twitter) : publication (1600 × 900 px)"), 1600, 900),
        ]),
        (tr("Impression"), [
            F("A3 (29,7 × 42 cm)", 297, 420, "mm", 300, 3, 5),
            F("A4 (21 × 29,7 cm)", 210, 297, "mm", 300, 3, 5),
            F("A5 (14,8 × 21 cm)", 148, 210, "mm", 300, 3, 5),
            F(tr("Photo 10 × 15 cm"), 100, 150, "mm", 300),
            F(tr("Photo 13 × 18 cm"), 130, 180, "mm", 300),
            F(tr("Photo 20 × 30 cm"), 200, 300, "mm", 300),
            F(tr("Affiche 40 × 60 cm"), 400, 600, "mm", 150, 3, 10),
            F(tr("Affiche 50 × 70 cm"), 500, 700, "mm", 150, 3, 10),
            F(tr("Carte de visite (8,5 × 5,5 cm)"), 85, 55, "mm", 300, 3, 3),
            F(tr("Flyer A6 (10,5 × 14,8 cm)"), 105, 148, "mm", 300, 3, 4),
        ]),
        (tr("Écran"), [
            F(tr("HD (1280 × 720 px)"), 1280, 720),
            F(tr("Full HD (1920 × 1080 px)"), 1920, 1080),
            F(tr("4K (3840 × 2160 px)"), 3840, 2160),
            F(tr("Fond d'écran de téléphone (1080 × 2400 px)"), 1080, 2400),
        ]),
    ]


# ---------------------------------------------------------- formats de l'utilisateur (réglages, en JSON)
def _format(d: dict) -> Format:
    """Format relu des réglages (les champs inconnus d'une autre version sont laissés de côté)."""
    if not isinstance(d, dict):
        raise TypeError("format illisible")
    connus = Format.__dataclass_fields__
    return Format(**{k: v for k, v in d.items() if k in connus})


def formats_perso(reglages) -> list[Format]:
    try:
        return [_format(d) for d in json.loads(reglages.value("formats_perso", "[]") or "[]")]
    except (ValueError, TypeError):
        return []


def enregistrer_formats_perso(reglages, liste: list[Format]) -> None:
    reglages.setValue("formats_perso", json.dumps([asdict(f) for f in liste], ensure_ascii=False))


def dernier_format(reglages) -> Format | None:
    try:
        return _format(json.loads(reglages.value("nouvelle_derniere", "") or "null"))
    except (ValueError, TypeError):
        return None


def retenir_dernier(reglages, f: Format) -> None:
    reglages.setValue("nouvelle_derniere", json.dumps(asdict(f), ensure_ascii=False))
