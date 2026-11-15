"""Mise à l'échelle d'après le contenu (comme dans Photoshop) : changer les proportions d'une image (carré vers 16:9…)
en étirant ou en tassant surtout les zones sans détails (ciel, mur, fond uni) ; le sujet garde ses proportions.

Méthode : un étirement variable, colonne par colonne puis ligne par ligne. Chaque colonne reçoit une part du
changement de largeur d'autant plus petite qu'elle est importante (détails, ou sélection à protéger) ; les lignes
droites restent droites, sans les cassures de la méthode « par coutures ».
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageFilter


def importance(rgb: np.ndarray, protection: np.ndarray | None = None) -> np.ndarray:
    """0..1 (h, w) : ce qu'il faut garder sans déformation. Les détails (contours, textures fines) comptent ; la
    zone protégée (sélection, 0..1) compte en entier."""
    gris = np.asarray(Image.fromarray(rgb[..., :3].astype(np.uint8)).convert("L"), np.float32)
    gy, gx = np.gradient(gris)
    e = np.sqrt(gx * gx + gy * gy)
    r = max(2.0, max(gris.shape) / 150)
    e = np.asarray(Image.fromarray(np.clip(e * 4, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r)),
                   np.float32)
    haut = max(1.0, float(np.percentile(e, 98)))
    e = np.clip(e / haut, 0, 1)
    if protection is not None:
        e = np.maximum(e, np.clip(protection, 0, 1))
    return e


def _parts(poids: np.ndarray, n_sortie: int, force: float) -> np.ndarray:
    """Largeur de chaque colonne après coup (somme = n_sortie). force 0 : étirement égal partout ; 1 : seules les
    colonnes peu importantes changent (tant que c'est possible)."""
    n = len(poids)
    d = n_sortie - n
    if d == 0:
        return np.ones(n, np.float64)
    souple = (1 - np.clip(poids, 0, 1)) ** 2
    w = force * souple + (1 - force) * np.full(n, souple.mean() if souple.mean() > 0 else 1.0)
    w = np.maximum(w, 1e-4)
    s = 1 + d * w / w.sum()
    for _ in range(20):                                # tassement : pas de colonne plus fine que 5 %
        trop = s < 0.05
        if not trop.any():
            break
        manque = (0.05 - s[trop]).sum()
        s[trop] = 0.05
        libres = ~trop
        if not libres.any():
            break
        s[libres] -= manque * w[libres] / w[libres].sum()
    return s * (n_sortie / s.sum())


def carte_axe(imp_axe: np.ndarray, n_sortie: int, force: float = 1.0) -> np.ndarray:
    """Pour chaque pixel de sortie : sa position (réelle) dans l'image de départ, le long d'un axe."""
    n = len(imp_axe)
    k = max(1, n // 60)                               # importance lissée : pas de saut d'une colonne à l'autre
    lisse = np.convolve(np.pad(imp_axe, k, mode="edge"), np.ones(2 * k + 1) / (2 * k + 1), mode="valid")
    s = _parts(lisse, n_sortie, force)
    bords = np.concatenate([[0], np.cumsum(s)])       # bords des colonnes de départ, dans la sortie
    centres = np.arange(n_sortie) + 0.5
    return np.interp(centres, bords, np.arange(n + 1, dtype=np.float64)) - 0.5


def cartes(rgb: np.ndarray, largeur: int, hauteur: int, protection: np.ndarray | None = None,
           force: float = 1.0) -> tuple[np.ndarray, np.ndarray]:
    """(carte x, carte y) pour passer de l'image rgb (h, w) à largeur × hauteur."""
    imp = importance(rgb, protection)
    # une colonne compte par ce qu'elle a de plus important (un sujet petit mais net est protégé)
    col = np.maximum(imp.mean(axis=0), np.percentile(imp, 90, axis=0))
    lig = np.maximum(imp.mean(axis=1), np.percentile(imp, 90, axis=1))
    return carte_axe(col, largeur, force), carte_axe(lig, hauteur, force)


def _reechantillonner(a: np.ndarray, carte: np.ndarray, axe: int) -> np.ndarray:
    n = a.shape[axe]
    p = np.clip(carte, 0, n - 1)
    i0 = np.floor(p).astype(np.int64)
    i1 = np.minimum(i0 + 1, n - 1)
    t = (p - i0).astype(np.float32)
    forme = [1] * a.ndim
    forme[axe] = len(carte)
    t = t.reshape(forme)
    return np.take(a, i0, axis=axe) * (1 - t) + np.take(a, i1, axis=axe) * t


def deformer(a: np.ndarray, cx: np.ndarray, cy: np.ndarray) -> np.ndarray:
    """a (h, w[, c]) passé par les cartes ; même type que a. Les couleurs sont mélangées prémultipliées si a est
    RGBA (pas de liseré aux bords transparents)."""
    f = a.astype(np.float32)
    rgba = f.ndim == 3 and f.shape[2] == 4
    if rgba:
        f[..., :3] *= f[..., 3:4] / 255
    r = _reechantillonner(_reechantillonner(f, cx, 1), cy, 0)
    if rgba:
        al = r[..., 3:4]
        r[..., :3] = np.where(al > 0.5, r[..., :3] * 255 / np.maximum(al, 1e-3), 0)
    if a.dtype == np.uint8:
        return np.clip(np.round(r), 0, 255).astype(np.uint8)
    return r.astype(a.dtype)
