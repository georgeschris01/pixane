"""Modifier avec une consigne (Flux Kontext) : « remplace le texte "X" par "Y" », « change la couleur du pull en
rouge »… sur la zone sélectionnée, en gardant le style de l'image.

Comment :
1. La zone de travail est découpée autour de la sélection (avec une marge pour que l'IA voie le contexte) : un petit
   objet ou un mot est traité avec beaucoup plus de détail que si toute l'image était réduite.
2. Ce que l'IA voit :
   - calque choisi avec de la transparence dans la zone (texte, logo sans fond) : ce calque seul, posé sur un fond
     uni qui contraste (noir ou blanc) ; le résultat retrouve sa transparence (fond uni retiré) ;
   - sinon : l'image visible (comme Photoshop), résultat opaque.
3. Le résultat n'est gardé que dans la sélection (bord adouci) et là où il change vraiment quelque chose : le reste
   garde ses pixels d'origine exacts.
"""
from __future__ import annotations

import io
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageFilter
from PySide6.QtGui import QImage

from .document import (FORMAT_CALQUE, FORMAT_IMAGE, Calque, a_plat, fond_ia, peut_recevoir_ia, poids_zone,
                       qimage_rgba, tableau)

MARGE_MIN = 48               # px autour de la sélection
MARGE_PART = 0.35            # part de la taille de la sélection ajoutée autour
COTE_MIN = 512               # zone de travail d'au moins 512 px de côté (si l'image le permet)


@dataclass
class Preparation:
    rect: tuple                    # (x, y, l, h) zone de travail dans l'image
    source: np.ndarray             # (H, W, 4) RGBA de ce que l'IA voit (calque seul ou image visible), taille image
    fond: int                      # fond uni (0 ou 255) des zones transparentes
    transparent: bool              # le résultat retrouve la transparence (calque seul)
    cible: int | None              # calque qui reçoit le résultat (None : nouveau calque)
    zone: np.ndarray | None        # sélection 0..255 (None : toute l'image)
    png: bytes                     # zone de travail, à plat, pour ComfyUI
    calque: np.ndarray | None      # (H, W, 4) RGBA du calque cible avant (None : nouveau calque)

    @property
    def taille(self) -> tuple[int, int]:
        return self.rect[2], self.rect[3]


def rect_de_travail(zone: np.ndarray | None, w: int, h: int) -> tuple[int, int, int, int]:
    if zone is None or not (zone > 0).any():
        return 0, 0, w, h
    ys, xs = np.nonzero(zone > 0)
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    m = max(MARGE_MIN, int(MARGE_PART * max(x1 - x0, y1 - y0)))
    x0, y0, x1, y1 = x0 - m, y0 - m, x1 + m, y1 + m
    for _ in range(2):                                  # au moins COTE_MIN de côté (centré), dans l'image
        if x1 - x0 < COTE_MIN:
            d = (COTE_MIN - (x1 - x0)) // 2 + 1
            x0, x1 = x0 - d, x1 + d
        if y1 - y0 < COTE_MIN:
            d = (COTE_MIN - (y1 - y0)) // 2 + 1
            y0, y1 = y0 - d, y1 + d
        if x0 < 0:
            x1, x0 = x1 - x0, 0
        if y0 < 0:
            y1, y0 = y1 - y0, 0
        if x1 > w:
            x0, x1 = x0 - (x1 - w), w
        if y1 > h:
            y0, y1 = y0 - (y1 - h), h
        x0, y0 = max(0, x0), max(0, y0)
    return int(x0), int(y0), int(x1 - x0), int(y1 - y0)


def preparer(doc, zone: np.ndarray | None, nouveau_calque: bool = False) -> Preparation:
    W, H = doc.taille()
    rect = rect_de_travail(zone, W, H)
    x, y, l, h = rect
    cible = None if nouveau_calque else doc.cible_ia(zone)
    source = None
    transparent = False
    calque = None
    if cible is not None and peut_recevoir_ia(doc.calques[cible]):
        calque = tableau(doc.calques[cible].image.convertToFormat(FORMAT_IMAGE))
        dedans = (zone > 0) if zone is not None else np.ones((H, W), bool)
        if (calque[..., 3][dedans] < 250).any() and (calque[..., 3][dedans] > 8).any():
            source, transparent = calque, True          # texte / logo sans fond : ce calque seul
    if source is None:
        source = tableau(doc.image.convertToFormat(FORMAT_IMAGE))
    morceau = source[y:y + h, x:x + l]
    fond = fond_ia(morceau) if transparent else 255
    rgb = a_plat(morceau, fond)
    o = io.BytesIO()
    Image.fromarray(np.ascontiguousarray(rgb), "RGB").save(o, "PNG", compress_level=1)
    if calque is None:
        cible = None
    return Preparation(rect, source, fond, transparent, cible, zone, o.getvalue(), calque)


def image_complete(prep: Preparation, resultat: QImage) -> QImage:
    """Le morceau traité (à la taille de la zone de travail) remis dans l'image entière (RGB à plat)."""
    x, y, l, h = prep.rect
    plat = a_plat(prep.source, prep.fond)
    r = tableau(resultat.convertToFormat(FORMAT_IMAGE))[..., :3]
    if r.shape[:2] != (h, l):
        r = np.asarray(Image.fromarray(np.ascontiguousarray(r), "RGB").resize((l, h), Image.LANCZOS))
    plat = plat.copy()
    plat[y:y + h, x:x + l] = r
    H, W = plat.shape[:2]
    rgba = np.dstack([plat, np.full((H, W), 255, np.uint8)])
    return qimage_rgba(rgba)


def _changement(avant: np.ndarray, apres: np.ndarray) -> np.ndarray:
    """0..1 : où le résultat change vraiment (les petits écarts dus à l'IA partout ailleurs sont ignorés)."""
    ecart = np.abs(apres.astype(np.int16) - avant.astype(np.int16)).max(axis=2).astype(np.uint8)
    e = Image.fromarray(ecart).filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(3))
    return np.clip((np.asarray(e, np.float32) - 14) / 18, 0, 1)


def _detourer(rgb: np.ndarray, fond: int) -> tuple[np.ndarray, np.ndarray]:
    """Retire le fond uni : (couleur, alpha 0..1). Ce qui s'écarte nettement du fond est opaque ; les bords
    adoucis gardent une transparence partielle."""
    f = np.float32(fond)
    c = rgb.astype(np.float32)
    ecart = (np.abs(c - f) / max(f, 255 - f)).max(axis=2)
    a = np.clip((ecart - 0.04) / 0.30, 0, 1)
    vraie = np.clip((c - f * (1 - a[..., None])) / np.maximum(a[..., None], 0.05), 0, 255)
    return vraie, a


def pose(prep: Preparation, image: QImage) -> np.ndarray:
    """Nouvelle image (H, W, 4) RGBA uint8 du calque cible (ou du nouveau calque) avec le résultat posé.
    image : résultat complet (image_complete)."""
    r = tableau(image.convertToFormat(FORMAT_IMAGE))[..., :3]
    H, W = r.shape[:2]
    avant_plat = a_plat(prep.source, prep.fond)
    garder = poids_zone(prep.zone, W, H) * _changement(avant_plat, r)
    x, y, l, h = prep.rect
    hors = np.ones((H, W), bool)
    hors[y:y + h, x:x + l] = False
    garder[hors] = 0
    if prep.transparent:
        couleur, alpha = _detourer(r, prep.fond)
    else:
        couleur, alpha = r.astype(np.float32), np.ones((H, W), np.float32)
    base = prep.calque if prep.calque is not None else np.zeros((H, W, 4), np.uint8)
    b = base.astype(np.float32) / 255
    bp = b[..., :3] * b[..., 3:]                       # prémultiplié
    n_a = alpha[..., None]
    np_ = couleur / 255 * n_a
    g = garder[..., None]
    out_a = b[..., 3:] * (1 - g) + n_a * g
    out_p = bp * (1 - g) + np_ * g
    out = np.dstack([np.clip(out_p / np.maximum(out_a, 1e-4), 0, 1), out_a])
    return (out * 255 + 0.5).astype(np.uint8)


def vue(prep: Preparation, image: QImage, visible: np.ndarray) -> QImage:
    """Ce que montre la fenêtre de choix. Calque transparent (texte, logo) : ce calque seul, tel qu'il sera (avec
    sa transparence). Sinon : le résultat posé sur l'image visible du lancement (visible : (H, W, 4) RGBA)."""
    nouveau = pose(prep, image)
    if prep.transparent:
        return qimage_rgba(nouveau)
    f = visible.astype(np.float32) / 255
    d = nouveau.astype(np.float32) / 255
    da = d[..., 3:]
    out_a = da + f[..., 3:] * (1 - da)
    out_c = (d[..., :3] * da + f[..., :3] * f[..., 3:] * (1 - da)) / np.maximum(out_a, 1e-4)
    return qimage_rgba((np.dstack([out_c, out_a]) * 255 + 0.5).astype(np.uint8))


def etat(doc, prep: Preparation, image: QImage, nom: str):
    """État du document avec le résultat choisi posé."""
    nouveau = qimage_rgba(pose(prep, image)).convertToFormat(FORMAT_CALQUE)
    if prep.cible is None:
        return doc.etat_avec(doc.calques + (Calque.depuis(doc.nom_libre(nom), nouveau),), len(doc.calques))
    return doc.etat_calque_modifie(prep.cible, image=nouveau)
