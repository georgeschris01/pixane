"""Filtres (menu Filtres) : flou gaussien, flou de mouvement, réduction du bruit, netteté, vignette.

Calcul pur sur des tableaux RGBA uint8 (couleurs non prémultipliées). Les flous travaillent en couleurs
prémultipliées : un bord transparent ne fait pas de halo sombre. `appliquer_calque` pose le résultat sur le calque,
seulement dans la sélection (bords doux) s'il y en a une.
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageFilter
from PySide6.QtGui import QImage

from .langue import tr

# type -> liste de (clé, libellé, min, max, défaut, unité)
FILTRES = {
    "flou": [("rayon", "Rayon", 1, 250, 6, " px")],
    "mouvement": [("angle", "Angle", -180, 180, 0, "°"), ("distance", "Distance", 2, 500, 30, " px")],
    "bruit": [("force", "Force", 1, 100, 40, ""), ("details", "Garder les détails", 0, 100, 40, " %"),
              ("couleur", "Bruit de couleur", 0, 100, 60, " %")],
    "nettete": [("quantite", "Quantité", 1, 500, 120, " %"), ("rayon", "Rayon", 1, 50, 2, " px"),
                ("seuil", "Seuil", 0, 50, 2, "")],
    "vignette": [("force", "Force (− assombrit, + éclaircit)", -100, 100, -45, ""),
                 ("taille", "Taille du centre", 0, 100, 50, " %"), ("douceur", "Douceur", 0, 100, 60, " %"),
                 ("rond", "Rond (0 = suit le cadre)", 0, 100, 40, " %")],
}


def noms() -> dict:
    return {"flou": tr("Flou gaussien"), "mouvement": tr("Flou de mouvement"), "bruit": tr("Réduction du bruit"),
            "nettete": tr("Netteté"), "vignette": tr("Vignette")}


def libelles() -> dict:
    """Libellés (écrits en entier pour la traduction)."""
    return {"Rayon": tr("Rayon"), "Angle": tr("Angle"), "Distance": tr("Distance"), "Force": tr("Force"),
            "Garder les détails": tr("Garder les détails"), "Bruit de couleur": tr("Bruit de couleur"),
            "Quantité": tr("Quantité"), "Seuil": tr("Seuil"),
            "Force (− assombrit, + éclaircit)": tr("Force (− assombrit, + éclaircit)"),
            "Taille du centre": tr("Taille du centre"), "Douceur": tr("Douceur"),
            "Rond (0 = suit le cadre)": tr("Rond (0 = suit le cadre)")}


def defauts(type_: str) -> dict:
    return {r[0]: r[4] for r in FILTRES[type_]}


# ------------------------------------------------------------------ outils
def _premul(t: np.ndarray) -> np.ndarray:
    f = t.astype(np.float32)
    f[..., :3] *= f[..., 3:4] / 255
    return f


def _depremul(f: np.ndarray) -> np.ndarray:
    a = f[..., 3:4]
    rgb = np.where(a > 0.5, f[..., :3] * 255 / np.maximum(a, 1e-3), 0)
    return np.clip(np.round(np.concatenate([rgb, a], axis=-1)), 0, 255).astype(np.uint8)


def boite(a: np.ndarray, r: int) -> np.ndarray:
    """Moyenne sur un carré de côté 2r+1 (bords répétés), en temps constant quel que soit r."""
    if r < 1:
        return a.astype(np.float32)
    p = np.pad(a.astype(np.float64), [(r + 1, r)] + [(r + 1, r)] + [(0, 0)] * (a.ndim - 2), mode="edge")
    c = np.cumsum(p, axis=0)
    c = c[2 * r + 1:] - c[:-2 * r - 1]
    c = np.cumsum(c, axis=1)
    c = c[:, 2 * r + 1:] - c[:, :-2 * r - 1]
    return (c / (2 * r + 1) ** 2).astype(np.float32)


def _flou_pil(f: np.ndarray, rayon: float) -> np.ndarray:
    """Flou gaussien d'un tableau float (h, w[, c]) : trois flous en boîte de suite (très proche d'une gaussienne,
    en temps constant quel que soit le rayon)."""
    sigma = max(0.3, float(rayon))
    r = max(1, int(round((np.sqrt(12 * sigma * sigma / 3 + 1) - 1) / 2)))
    res = f.astype(np.float32)
    for _ in range(3):
        res = boite(res, r)
    return res


# ------------------------------------------------------------------ filtres
def flou_gaussien(t: np.ndarray, p: dict) -> np.ndarray:
    """Pillow, en couleurs prémultipliées (mode « RGBa ») : rapide, sans halo au bord des zones transparentes."""
    im = Image.fromarray(np.ascontiguousarray(t), "RGBA").convert("RGBa")
    return np.asarray(im.filter(ImageFilter.GaussianBlur(float(p["rayon"]))).convert("RGBA")).copy()


def flou_mouvement(t: np.ndarray, p: dict) -> np.ndarray:
    """L'image est tournée pour que le mouvement soit horizontal, floutée en ligne, puis remise droite."""
    h, w = t.shape[:2]
    f = _premul(t)
    d = max(2, int(p["distance"]))
    angle = float(p["angle"])
    couches = []
    for k in range(4):
        im = Image.fromarray(f[..., k], "F").rotate(-angle, Image.BILINEAR, expand=True)
        a = np.asarray(im, np.float32)
        r = d // 2
        pad = np.pad(a.astype(np.float64), [(0, 0), (r + 1, r)], mode="edge")
        c = np.cumsum(pad, axis=1)
        a = ((c[:, 2 * r + 1:] - c[:, :-2 * r - 1]) / (2 * r + 1)).astype(np.float32)
        im = Image.fromarray(a, "F").rotate(angle, Image.BILINEAR, expand=True)
        W, H = im.size
        x0, y0 = (W - w) // 2, (H - h) // 2
        couches.append(np.asarray(im, np.float32)[y0:y0 + h, x0:x0 + w])
    res = np.stack(couches, axis=-1)
    if np.all(t[..., 3] == 255):          # photo opaque : les bords tournés ne doivent pas devenir transparents
        res[..., :3] = res[..., :3] * 255 / np.maximum(res[..., 3:4], 1e-3)
        res[..., 3] = 255
    return _depremul(res)


def _guide(I: np.ndarray, P: np.ndarray, r: int, eps: float) -> np.ndarray:
    """Filtre guidé (He et al.) : lisse P en suivant les bords de I."""
    mI, mP = boite(I, r), boite(P, r)
    cov = boite(I * P, r) - mI * mP
    var = boite(I * I, r) - mI * mI
    a = cov / (var + eps)
    b = mP - a * mI
    return boite(a, r) * I + boite(b, r)


def reduire_bruit(t: np.ndarray, p: dict) -> np.ndarray:
    """Clarté : filtre guidé sur elle-même (lisse le grain, garde les bords). Couleur : bruit de couleur lissé plus
    fort (l'œil y est peu sensible)."""
    f = t[..., :3].astype(np.float32) / 255
    y = f @ np.array([0.299, 0.587, 0.114], np.float32)
    cb, cr = f[..., 2] - y, f[..., 0] - y
    force = p["force"] / 100
    r = max(1, round(1 + 4 * force))
    eps = (0.004 + 0.05 * force) ** 2
    y2 = _guide(y, y, r, eps)
    y2 = y2 + (y - y2) * (p["details"] / 100) * 0.6
    rc = max(1, round(2 + 8 * p["couleur"] / 100))
    k = p["couleur"] / 100
    cb2 = cb + (_guide(y, cb, rc, 0.01) - cb) * k
    cr2 = cr + (_guide(y, cr, rc, 0.01) - cr) * k
    g = (y2 - 0.299 * (cr2 + y2) - 0.114 * (cb2 + y2)) / 0.587
    rgb = np.stack([cr2 + y2, g, cb2 + y2], axis=-1)
    out = t.copy()
    out[..., :3] = np.clip(np.round(rgb * 255), 0, 255).astype(np.uint8)
    return out


def nettete(t: np.ndarray, p: dict) -> np.ndarray:
    im = Image.fromarray(np.ascontiguousarray(t[..., :3]), "RGB").filter(
        ImageFilter.UnsharpMask(radius=float(p["rayon"]), percent=int(p["quantite"]), threshold=int(p["seuil"])))
    out = t.copy()
    out[..., :3] = np.asarray(im)
    return out


def vignette(t: np.ndarray, p: dict) -> np.ndarray:
    h, w = t.shape[:2]
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    nx, ny = (x + 0.5) / w * 2 - 1, (y + 0.5) / h * 2 - 1
    rond = p["rond"] / 100
    if rond < 1:            # forme : du rectangle (suit le cadre) au cercle
        e = 2 + 10 * (1 - rond) ** 2
        d = (np.abs(nx) ** e + np.abs(ny) ** e) ** (1 / e)
    else:
        d = np.hypot(nx, ny) / math.sqrt(2) * 1.25
    centre = 0.2 + 0.8 * p["taille"] / 100
    douceur = 0.05 + 0.95 * p["douceur"] / 100
    v = np.clip((d - centre * (1 - douceur * 0.5)) / (douceur * 0.9 + 1e-3), 0, 1)
    v = v * v * (3 - 2 * v)                                 # transition douce
    force = p["force"] / 100
    f = t[..., :3].astype(np.float32)
    if force < 0:
        f = f * (1 + force * v)[..., None]
    else:
        f = f + (255 - f) * (force * v)[..., None]
    out = t.copy()
    out[..., :3] = np.clip(np.round(f), 0, 255).astype(np.uint8)
    return out


# ------------------------------------------------------------------ teinte d'une photo (restauration IA)
def _ycbcr(rgb: np.ndarray):
    f = rgb[..., :3].astype(np.float32)
    y = 0.299 * f[..., 0] + 0.587 * f[..., 1] + 0.114 * f[..., 2]
    return y, 0.564 * (f[..., 2] - y), 0.713 * (f[..., 0] - y)


def garder_teinte(original: np.ndarray, resultat: np.ndarray) -> np.ndarray:
    """Lumière et détails du résultat, teinte de l'original (adoucie pour ne pas reprendre les taches) :
    une restauration ne peut pas coloriser. Tableaux RGBA de même taille ; l'alpha du résultat est gardé."""
    y, _, _ = _ycbcr(resultat)
    _, cb, cr = _ycbcr(original)
    sigma = max(2.0, max(original.shape[:2]) / 250)
    cb, cr = _flou_pil(cb, sigma), _flou_pil(cr, sigma)
    r = y + cr / 0.713
    b = y + cb / 0.564
    g = (y - 0.299 * r - 0.114 * b) / 0.587
    out = resultat.copy()
    for i, c in enumerate((r, g, b)):
        out[..., i] = np.clip(np.round(c), 0, 255).astype(np.uint8)
    return out


FONCTIONS = {"flou": flou_gaussien, "mouvement": flou_mouvement, "bruit": reduire_bruit, "nettete": nettete,
             "vignette": vignette}


def appliquer_calque(img: QImage, calcul, selection: QImage | None) -> QImage:
    """calcul : tableau RGBA -> tableau RGBA. Résultat posé dans la sélection (avec ses bords doux) s'il y en a."""
    from .document import FORMAT_CALQUE, FORMAT_IMAGE, masque, qimage_rgba, tableau
    t = tableau(img.convertToFormat(FORMAT_IMAGE))
    res = calcul(t)
    if selection is not None:
        m = masque(selection)
        if m.any():
            w = m.astype(np.float32)[..., None] / 255
            res = np.clip(np.round(t + (res.astype(np.float32) - t) * w), 0, 255).astype(np.uint8)
    return qimage_rgba(res).convertToFormat(FORMAT_CALQUE)
