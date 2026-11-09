"""Agrandir en pleine définition : après la première passe (faite à ~1 mégapixel puis agrandie, donc plus floue que
la photo), l'ajout est redessiné par Flux Fill en morceaux de 1024 px, à la vraie taille, avec une force légère :
la forme reste celle choisie, mais les détails et la netteté rejoignent ceux de la photo. Puis le grain de la
photo est ajouté à l'ajout s'il en manque.

Fonctions pures (numpy) : la fenêtre envoie chaque morceau au moteur et recolle le résultat.
"""
from __future__ import annotations

import io
import math

import numpy as np
from PIL import Image

MORCEAU = 1024          # côté d'un morceau (px réels)
RECOUVREMENT = 160      # chevauchement entre deux morceaux (fondu)
MAX_MORCEAUX = 12       # au-delà, on travaille un peu en dessous de la pleine taille (temps raisonnable)
GAIN_MINI = 1.25        # en dessous (photo déjà proche de 1 mégapixel), l'affinage n'apporte rien
FORCE = 0.4             # part redessinée par Flux (0 : rien, 1 : tout)


def utile(taille: tuple[int, int], travail: tuple[int, int]) -> bool:
    """Vrai si l'ajout a été calculé nettement plus petit que la photo (il est donc plus flou)."""
    return taille[0] / max(1, travail[0]) >= GAIN_MINI


def masque_ajout(taille, marges, taille_orig, bande: float) -> np.ndarray:
    """(H, W) float32 : 1 dans l'ajout, descend à 0 en `bande` px dans la photo d'origine (côtés agrandis)."""
    W, H = taille
    mh, mb, mg, md = marges
    h, w = taille_orig
    m = np.ones((H, W), np.float32)
    ys = np.arange(h, dtype=np.float32)[:, None]
    xs = np.arange(w, dtype=np.float32)[None, :]
    dedans = np.zeros((h, w), np.float32)
    b = max(2.0, bande)
    for actif, d in ((mh > 0, ys), (mb > 0, h - 1 - ys), (mg > 0, xs), (md > 0, w - 1 - xs)):
        if actif:
            dedans = np.maximum(dedans, np.clip(1 - d / b, 0, 1))
    m[mh:mh + h, mg:mg + w] = dedans
    return m


def _positions(n: int, t: int, pas: int) -> list[int]:
    if n <= t:
        return [0]
    k = math.ceil((n - t) / pas) + 1
    return sorted({round(i * (n - t) / (k - 1)) for i in range(k)})


def morceaux(m: np.ndarray, cote: int = MORCEAU, recouvrement: int = RECOUVREMENT) -> list[tuple[int, int, int, int]]:
    """Rectangles (x, y, l, h) qui couvrent la zone à affiner ; côtés multiples de 16."""
    H, W = m.shape
    tw, th = min(cote, W // 16 * 16), min(cote, H // 16 * 16)
    res = []
    for y in _positions(H, th, th - recouvrement):
        for x in _positions(W, tw, tw - recouvrement):
            if m[y:y + th, x:x + tw].max() > 0.02:
                res.append((x, y, tw, th))
    return res


def plan(img: np.ndarray, m: np.ndarray):
    """-> (échelle, image de travail, masque de travail, morceaux). Échelle 1 : pleine taille ; plus petite sur
    une très grande photo, pour ne pas dépasser MAX_MORCEAUX (toujours bien plus fin que la première passe)."""
    s = 1.0
    while True:
        if s < 1:
            H, W = m.shape
            w, h = max(64, round(W * s)), max(64, round(H * s))
            img_t = np.asarray(Image.fromarray(img).resize((w, h), Image.LANCZOS))
            m_t = np.asarray(Image.fromarray(m).resize((w, h), Image.BILINEAR), np.float32)
        else:
            img_t, m_t = img, m
        r = morceaux(m_t)
        if len(r) <= MAX_MORCEAUX or s < 0.3:
            return s, img_t, m_t, r
        s *= 0.85


def terminer(img: np.ndarray, travail: np.ndarray, m: np.ndarray, s: float) -> np.ndarray:
    """Remet le résultat de travail à la taille de la photo (si besoin) et ne garde que la zone affinée."""
    if s >= 1:
        return travail
    H, W = m.shape
    grand = np.asarray(Image.fromarray(travail).resize((W, H), Image.LANCZOS), np.float32)
    a = m[:, :, None]
    return np.clip(a * grand + (1 - a) * img.astype(np.float32) + 0.5, 0, 255).astype(np.uint8)


def png_morceau(img: np.ndarray, m: np.ndarray, r) -> bytes:
    """Morceau pour ComfyUI : RGB de la photo, transparent là où Flux doit retravailler (masque doux)."""
    x, y, w, h = r
    rgb = img[y:y + h, x:x + w]
    alpha = np.clip((1 - m[y:y + h, x:x + w]) * 255 + 0.5, 0, 255).astype(np.uint8)
    tampon = io.BytesIO()
    Image.fromarray(np.dstack([rgb, alpha]), "RGBA").save(tampon, "PNG", compress_level=1)
    return tampon.getvalue()


def coller(img: np.ndarray, res: np.ndarray, m: np.ndarray, r, recouvrement: int = RECOUVREMENT) -> np.ndarray:
    """Recolle le morceau retravaillé : seulement dans la zone à affiner, fondu sur les bords intérieurs."""
    x, y, w, h = r
    H, W = m.shape
    if res.shape[:2] != (h, w):
        res = np.asarray(Image.fromarray(res).resize((w, h), Image.LANCZOS))
    f = recouvrement / 2

    def rampe(n, debut_libre, fin_libre):
        v = np.ones(n, np.float32)
        i = np.arange(n, dtype=np.float32)
        if not debut_libre:
            v = np.minimum(v, np.clip(i / f, 0, 1))
        if not fin_libre:
            v = np.minimum(v, np.clip((n - 1 - i) / f, 0, 1))
        return v
    poids = rampe(h, y == 0, y + h >= H)[:, None] * rampe(w, x == 0, x + w >= W)[None, :]
    a = (m[y:y + h, x:x + w] * poids)[:, :, None]
    sortie = img.copy()
    zone = sortie[y:y + h, x:x + w].astype(np.float32)
    sortie[y:y + h, x:x + w] = np.clip(a * res.astype(np.float32) + (1 - a) * zone + 0.5, 0, 255).astype(np.uint8)
    return sortie


def _flou2(a: np.ndarray, sigma: float) -> np.ndarray:
    """Flou gaussien d'un tableau 2D de nombres (float32)."""
    r = max(1, int(sigma * 3))
    x = np.arange(-r, r + 1, dtype=np.float32)
    k = np.exp(-(x ** 2) / (2 * sigma ** 2))
    k /= k.sum()
    b = np.pad(a.astype(np.float32), r, mode="edge")
    b = sum(k[i] * b[:, i:i + a.shape[1]] for i in range(2 * r + 1))
    return sum(k[i] * b[i:i + a.shape[0], :] for i in range(2 * r + 1))


def _bruit(img: np.ndarray, zone: np.ndarray) -> float:
    """Écart-type robuste du grain (fines variations) dans la zone (booléen)."""
    if zone.sum() < 400:
        return 0.0
    lum = (img[..., 0] * 0.299 + img[..., 1] * 0.587 + img[..., 2] * 0.114).astype(np.float32)
    flou = _flou2(lum, 1.2)
    d = (lum - flou)[zone]
    return float(1.4826 * np.median(np.abs(d - np.median(d))))


def accorder_grain(img: np.ndarray, m: np.ndarray, graine: int = 1) -> np.ndarray:
    """Ajoute à l'ajout le grain qui lui manque par rapport à la photo (même finesse, en douceur)."""
    photo, ajout = m < 0.01, m > 0.95
    g_photo, g_ajout = _bruit(img, photo), _bruit(img, ajout)
    manque = math.sqrt(max(0.0, g_photo ** 2 - g_ajout ** 2))
    if manque < 0.5:
        return img
    rng = np.random.default_rng(graine)
    bruit = rng.normal(0, 1, img.shape[:2]).astype(np.float32)
    # grain un peu plus gros qu'un pixel, comme celui d'une vraie photo, remis à la bonne force
    bruit = _flou2(bruit, 0.6)
    bruit *= manque / max(1e-3, _ecart(bruit))
    return np.clip(img.astype(np.float32) + (bruit * m)[:, :, None] + 0.5, 0, 255).astype(np.uint8)


def _ecart(b: np.ndarray) -> float:
    flou = _flou2(b, 1.2)
    d = b - flou
    return float(1.4826 * np.median(np.abs(d - np.median(d))))
