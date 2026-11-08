"""Raccord après « Agrandir » : on remet la photo d'origine intacte et on accorde les couleurs de l'ajout.

Flux travaille sur l'image réduite (1024 px) : la partie d'origine qu'il a repeinte revient floue et un peu
délavée, ce qui faisait une bande visible à la jointure. Ici :
1. la photo d'origine est recollée au pixel près, avec un fondu étroit au bord ;
2. l'écart de couleur entre l'original et la version de Flux, mesuré le long de chaque bord, est reporté sur
   la partie ajoutée en s'atténuant vers l'extérieur.
"""
from __future__ import annotations

import numpy as np

FONDU = 16        # largeur du fondu à l'intérieur de l'original (px)
MESURE = 24       # épaisseur de la bande où l'on mesure l'écart de couleur (px)
LISSAGE = 40      # lissage de l'écart le long du bord (px)


def marges(largeur: int, hauteur: int, haut: float, bas: float, gauche: float, droite: float):
    """Mêmes calculs que l'extension « Inpaint Crop and Stitch » (pour retrouver l'original dans le résultat)."""
    fh, fb, fg, fd = (1 + haut / 100, 1 + bas / 100, 1 + gauche / 100, 1 + droite / 100)
    nouvelle_h = int(hauteur * (fh + fb - 1))
    nouvelle_l = int(largeur * (fg + fd - 1))
    m_haut = int(hauteur * (fh - 1))
    m_gauche = int(largeur * (fg - 1))
    return m_haut, nouvelle_h - hauteur - m_haut, m_gauche, nouvelle_l - largeur - m_gauche, nouvelle_l, nouvelle_h


def _lisser(profil: np.ndarray, sigma: float) -> np.ndarray:
    """Lissage gaussien 1D le long du bord (profil : longueur × 3)."""
    r = int(sigma * 2.5)
    if r < 1 or len(profil) < 3:
        return profil
    x = np.arange(-r, r + 1)
    noyau = np.exp(-(x ** 2) / (2 * sigma ** 2))
    noyau /= noyau.sum()
    bord = np.pad(profil, ((r, r), (0, 0)), mode="edge")
    return np.stack([np.convolve(bord[:, c], noyau, mode="valid") for c in range(profil.shape[1])], axis=1)


def raccorder(original: np.ndarray, resultat: np.ndarray, haut: float, bas: float, gauche: float,
              droite: float) -> np.ndarray:
    """original : (h, w, 3) uint8 ; resultat : (H, W, 3) uint8 renvoyé par Flux. Renvoie (H, W, 3) uint8."""
    h, w = original.shape[:2]
    mh, mb, mg, md, W, H = marges(w, h, haut, bas, gauche, droite)
    if resultat.shape[:2] != (H, W):
        return resultat  # tailles inattendues : on ne touche à rien
    R = resultat.astype(np.float32)
    O = original.astype(np.float32)
    y0, x0 = mh, mg
    zone = R[y0:y0 + h, x0:x0 + w]      # la version de Flux de la partie d'origine
    m = min(MESURE, h // 4, w // 4)

    # 1. accorder les couleurs de l'ajout, côté par côté
    if mh > 0:
        ecart = _lisser((O[:m] - zone[:m]).mean(axis=0), LISSAGE)                  # (w, 3)
        poids = np.linspace(0, 1, mh, dtype=np.float32)[:, None, None]            # 0 dehors -> 1 au bord
        R[:mh, x0:x0 + w] += poids * ecart[None]
    if mb > 0:
        ecart = _lisser((O[-m:] - zone[-m:]).mean(axis=0), LISSAGE)
        poids = np.linspace(1, 0, mb, dtype=np.float32)[:, None, None]
        R[y0 + h:, x0:x0 + w] += poids * ecart[None]
    if mg > 0:
        ecart = _lisser((O[:, :m] - zone[:, :m]).mean(axis=1), LISSAGE)           # (h, 3)
        poids = np.linspace(0, 1, mg, dtype=np.float32)[None, :, None]
        R[y0:y0 + h, :mg] += poids * ecart[:, None]
    if md > 0:
        ecart = _lisser((O[:, -m:] - zone[:, -m:]).mean(axis=1), LISSAGE)
        poids = np.linspace(1, 0, md, dtype=np.float32)[None, :, None]
        R[y0:y0 + h, x0 + w:] += poids * ecart[:, None]

    # 2. recoller l'original intact, avec un fondu étroit seulement du côté des bords agrandis
    f = max(1, min(FONDU, h // 4, w // 4))
    ys = np.arange(h, dtype=np.float32)[:, None]
    xs = np.arange(w, dtype=np.float32)[None, :]
    alpha = np.ones((h, w), np.float32)
    if mh > 0:
        alpha = np.minimum(alpha, np.clip((ys + 0.5) / f, 0, 1))
    if mb > 0:
        alpha = np.minimum(alpha, np.clip((h - ys - 0.5) / f, 0, 1))
    if mg > 0:
        alpha = np.minimum(alpha, np.clip((xs + 0.5) / f, 0, 1))
    if md > 0:
        alpha = np.minimum(alpha, np.clip((w - xs - 0.5) / f, 0, 1))
    alpha = alpha[:, :, None]
    R[y0:y0 + h, x0:x0 + w] = alpha * O + (1 - alpha) * R[y0:y0 + h, x0:x0 + w]
    return np.clip(R + 0.5, 0, 255).astype(np.uint8)
