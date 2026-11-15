"""Profondeur des couleurs : 8 ou 16 bits par couche (Image > Mode).

En 16 bits, chaque calque est une QImage Format_RGBA64_Premultiplied (0..65535 par couche). Qt sait y peindre et
les mélanger (QPainter) en 16 bits.

Pont pour les fonctions encore écrites en 8 bits : elles reçoivent le calque en 8 bits (tableau() le convertit) et
rendent une image 8 bits. Document.appliquer_etat la remet en 16 bits avec `remonter` : là où le pixel n'a pas changé
(même valeur 8 bits qu'avant), l'ancienne valeur 16 bits est gardée. Une retouche locale (pinceau, IA dans une zone,
gomme…) ne fait donc perdre la précision qu'aux pixels qu'elle change vraiment.
"""
from __future__ import annotations

import numpy as np
from PySide6.QtGui import QImage

FORMAT_8 = QImage.Format_ARGB32_Premultiplied          # = document.FORMAT_CALQUE
FORMAT_16 = QImage.Format_RGBA64_Premultiplied
# équivalent 8 bits de chaque format 16 bits (même sens : prémultiplié ou non)
_VERS_8 = {QImage.Format_RGBA64_Premultiplied: QImage.Format_ARGB32_Premultiplied,
           QImage.Format_RGBA64: QImage.Format_RGBA8888,
           QImage.Format_RGBX64: QImage.Format_RGBA8888,
           QImage.Format_Grayscale16: QImage.Format_Grayscale8}


def est_16(img: QImage | None) -> bool:
    return img is not None and not img.isNull() and img.format() in _VERS_8


def vers_8(img: QImage) -> QImage:
    """Image 16 bits -> son équivalent 8 bits (même ordre de prémultiplication) ; une image 8 bits est rendue telle
    quelle."""
    f = _VERS_8.get(img.format())
    return img if f is None else img.convertToFormat(f)


def en_16(img: QImage) -> QImage:
    return img if img.format() == FORMAT_16 else img.convertToFormat(FORMAT_16)


def en_8(img: QImage) -> QImage:
    return img if img.format() == FORMAT_8 else img.convertToFormat(FORMAT_8)


def tab16(img: QImage, premul: bool = False) -> np.ndarray:
    """Copie (h, w, 4) uint16 R, V, B, A ; couleurs non prémultipliées sauf si premul."""
    src = img.convertToFormat(FORMAT_16 if premul else QImage.Format_RGBA64)
    h, w, ligne = src.height(), src.width(), src.bytesPerLine()
    brut = np.frombuffer(src.constBits(), np.uint16, count=h * ligne // 2).reshape(h, ligne // 2)
    return brut[:, : w * 4].reshape(h, w, 4).copy()


def qimage16(t: np.ndarray, premul: bool = False) -> QImage:
    """Tableau (h, w, 4) uint16 R, V, B, A (non prémultiplié sauf si premul) -> QImage FORMAT_16."""
    t = np.ascontiguousarray(t, dtype=np.uint16)
    h, w = t.shape[:2]
    img = QImage(t.data, w, h, w * 8, FORMAT_16 if premul else QImage.Format_RGBA64).copy()
    return en_16(img)


# ------------------------------------------------------------------ tramage (dithering)
# Passage de 16 à 8 bits : un très léger bruit (± 1 niveau sur 255, loi triangulaire) est ajouté avant l'arrondi ;
# un dégradé lisse ne montre alors pas de marches. Motif fixe de 256 × 256 répété : même résultat à chaque fois.
tramage = True                    # réglage (Image > Mode > Tramage vers 8 bits), mis par la fenêtre
_motif = None


def _bruit(h: int, w: int) -> np.ndarray:
    """Bruit triangulaire (h, w, 3) en int16, sur l'échelle 16 bits (± 257 = ± 1 niveau 8 bits) ; gardé pour la
    dernière taille demandée."""
    global _motif
    if _motif is None or _motif.shape[:2] != (h, w):
        g = np.random.default_rng(1234)
        tuile = ((g.random((256, 256, 3)) - g.random((256, 256, 3))) * 257).round().astype(np.int16)
        _motif = np.ascontiguousarray(np.tile(tuile, (h // 256 + 1, w // 256 + 1, 1))[:h, :w])
    return _motif


def vers_8_trame(img: QImage) -> QImage:
    """Image 16 bits -> son équivalent 8 bits (comme vers_8), avec tramage si le réglage est allumé."""
    if not est_16(img) or not tramage:
        return vers_8(img)
    t = tab16(img)
    h, w = t.shape[:2]
    v = t[..., :3].astype(np.int32)
    v += _bruit(h, w)
    np.clip(v, 0, 65535, out=v)
    rgba = np.empty(t.shape, np.uint8)
    rgba[..., :3] = (v * 255 + 32767) // 65535                 # arrondi au plus proche
    rgba[..., 3] = (t[..., 3].astype(np.uint32) * 255 + 32767) // 65535
    res = QImage(np.ascontiguousarray(rgba).data, w, h, w * 4, QImage.Format_RGBA8888).copy()
    return res.convertToFormat(_VERS_8[img.format()])


def remonter(nouveau: QImage, ancien: QImage | None) -> QImage:
    """Résultat 8 bits d'une fonction du pont -> 16 bits ; là où rien n'a changé, les pixels 16 bits de `ancien`."""
    n16 = en_16(nouveau)
    if ancien is None or not est_16(ancien) or ancien.size() != nouveau.size():
        return n16
    a16 = en_16(ancien)
    n8 = _octets(en_8(nouveau), 1)
    a8 = _octets(en_8(a16), 1)
    pareil = np.all(n8 == a8, axis=-1)
    if not pareil.any():
        return n16
    if pareil.all():
        return a16
    res = _octets(n16, 2).copy()
    res[pareil] = _octets(a16, 2)[pareil]
    h, w = res.shape[:2]
    return QImage(np.ascontiguousarray(res).data, w, h, w * 8, FORMAT_16).copy()


def _octets(img: QImage, taille: int) -> np.ndarray:
    """Vue (h, w, 4) des pixels (uint8 si taille 1, uint16 si 2)."""
    h, w, ligne = img.height(), img.width(), img.bytesPerLine()
    t = np.uint8 if taille == 1 else np.uint16
    return np.frombuffer(img.constBits(), t, count=h * ligne // taille).reshape(h, ligne // taille)[:, : w * 4] \
        .reshape(h, w, 4)
