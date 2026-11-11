"""Garde-fou des aplats pour l'Upscale net : Flux redessine les détails sans consigne ; sur un aplat (couleur unie, ciel
lisse, fond de pochette), il n'a rien à redessiner et invente (taches, gribouillis, ombres). On ne garde son travail
que là où l'image d'origine a vraiment du détail ; ailleurs, l'origine simplement agrandie (rien d'inventé).
Là où il est gardé, on garde sa netteté mais les couleurs de l'origine (Flux teinte parfois un dessin)."""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageFilter
from PySide6.QtGui import QImage

from .document import FORMAT_IMAGE, qimage_rgba, tableau

RAYON = 3            # px de l'origine : fenêtre où l'on mesure le détail
SEUIL_BAS = 4.0      # écart de luminosité en dessous duquel c'est un aplat (bruit de JPEG compris)
SEUIL_HAUT = 14.0    # au-dessus : vrai détail, le travail de Flux est gardé en entier


def _moyenne(a: np.ndarray, rayon: int) -> np.ndarray:
    """Moyenne sur un carré de (2 rayon + 1) px (calcul exact, sans dépassement)."""
    k = 2 * rayon + 1
    p = np.pad(a.astype(np.float64), rayon + 1, mode="edge")
    c = p.cumsum(0).cumsum(1)
    s = c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]
    return (s / (k * k))[: a.shape[0], : a.shape[1]].astype(np.float32)


def part_aplats(rgb: np.ndarray) -> float:
    """Part de l'image faite d'aplats (0..1), mesurée sur une version réduite : beaucoup d'aplats = image graphique
    (pochette, logo, affiche), où une force douce est conseillée."""
    h, w = rgb.shape[:2]
    k = max(1, round(max(h, w) / 800))
    petit = rgb[::k, ::k]
    return float((poids_detail(petit) < 0.5).mean())


def _flou(a: np.ndarray, rayon: float) -> np.ndarray:
    """Flou presque gaussien (3 moyennes successives) d'un tableau (h, w, 3) float32."""
    r = max(1, round(rayon))
    sortie = np.empty_like(a)
    for c in range(a.shape[2]):
        b = a[..., c]
        for _ in range(3):
            b = _moyenne(b, r)
        sortie[..., c] = b
    return sortie


def poids_detail(rgb: np.ndarray) -> np.ndarray:
    """(h, w) 0..1 : 1 là où l'origine a du détail (traits, texte, matière), 0 sur les aplats ; bord doux."""
    lum = rgb[..., :3].astype(np.float32) @ np.array([0.299, 0.587, 0.114], np.float32)
    m = _moyenne(lum, RAYON)
    ecart = np.sqrt(np.maximum(_moyenne(lum * lum, RAYON) - m * m, 0))
    p = np.clip((ecart - SEUIL_BAS) / (SEUIL_HAUT - SEUIL_BAS), 0, 1)
    im = Image.fromarray((p * 255 + 0.5).astype(np.uint8), "L")
    im = im.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(2))   # un peu autour des traits
    return np.asarray(im).astype(np.float32) / 255


def garder_aplats(origine: np.ndarray, resultat: QImage) -> QImage:
    """origine : (h, w, 3) RGB envoyée à l'IA ; resultat : l'Upscale net (plus grand). Renvoie le résultat où les
    aplats de l'origine sont repris de l'origine agrandie (Lanczos), et le détail de Flux gardé ailleurs."""
    W, H = resultat.width(), resultat.height()
    r = tableau(resultat.convertToFormat(FORMAT_IMAGE)).astype(np.float32)
    o = np.ascontiguousarray(origine[..., :3]).astype(np.uint8)
    agrandie = np.asarray(Image.fromarray(o, "RGB").resize((W, H), Image.LANCZOS)).astype(np.float32)
    p = poids_detail(o)
    p = np.asarray(Image.fromarray((p * 255 + 0.5).astype(np.uint8), "L").resize((W, H), Image.BILINEAR))
    p = p.astype(np.float32)[..., None] / 255
    # couleurs de l'origine, netteté de Flux : ses écarts de couleur « en grand » sont retirés
    echelle = W / max(1, o.shape[1])
    r3 = r[..., :3] + _flou(agrandie - r[..., :3], max(2.0, 3.0 * echelle))
    rgb = agrandie + p * (r3 - agrandie)
    sortie = np.empty((H, W, 4), np.uint8)
    sortie[..., :3] = np.clip(rgb + 0.5, 0, 255).astype(np.uint8)
    sortie[..., 3] = r[..., 3].astype(np.uint8)
    return qimage_rgba(sortie)
