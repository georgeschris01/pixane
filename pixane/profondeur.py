"""Profondeur des couleurs : 8, 16 ou 32 bits par couche (Image > Mode).

En 16 bits, chaque calque est une QImage Format_RGBA64_Premultiplied (0..65535 par couche) ; en 32 bits, une QImage
Format_RGBA32FPx4_Premultiplied (nombres à virgule, 1.0 = blanc ; au-delà de 1 : plus clair que le blanc, pour les
photos HDR). Qt sait y peindre et les mélanger (QPainter) sans perte, et garde les valeurs au-dessus de 1.

Les valeurs 32 bits suivent la même courbe que le 8 et le 16 bits (sRVB) : passer de 16 à 32 bits ne change rien à
l'image. Les fichiers HDR (EXR, .hdr, TIFF 32 bits) sont linéaires : ils sont convertis à l'ouverture et à
l'enregistrement (lineaire_vers_srvb / srvb_vers_lineaire).

Pont pour les fonctions encore écrites en 8 bits : elles reçoivent le calque en 8 bits (tableau() le convertit) et
rendent une image 8 bits. Document.appliquer_etat la remet à la profondeur du document avec `remonter` : là où le
pixel n'a pas changé (même valeur 8 bits qu'avant), l'ancienne valeur 16 / 32 bits est gardée. Une retouche locale
(IA dans une zone, sélection…) ne fait donc perdre la précision qu'aux pixels qu'elle change vraiment.
"""
from __future__ import annotations

import numpy as np
from PySide6.QtGui import QImage

FORMAT_8 = QImage.Format_ARGB32_Premultiplied          # = document.FORMAT_CALQUE
FORMAT_16 = QImage.Format_RGBA64_Premultiplied
FORMAT_32 = QImage.Format_RGBA32FPx4_Premultiplied
FORMATS = {8: FORMAT_8, 16: FORMAT_16, 32: FORMAT_32}
# équivalent 8 bits de chaque format 16 / 32 bits (même sens : prémultiplié ou non)
_VERS_8 = {QImage.Format_RGBA64_Premultiplied: QImage.Format_ARGB32_Premultiplied,
           QImage.Format_RGBA64: QImage.Format_RGBA8888,
           QImage.Format_RGBX64: QImage.Format_RGBA8888,
           QImage.Format_Grayscale16: QImage.Format_Grayscale8,
           QImage.Format_RGBA32FPx4_Premultiplied: QImage.Format_ARGB32_Premultiplied,
           QImage.Format_RGBA32FPx4: QImage.Format_RGBA8888,
           QImage.Format_RGBX32FPx4: QImage.Format_RGBA8888,
           QImage.Format_RGBA16FPx4_Premultiplied: QImage.Format_ARGB32_Premultiplied,
           QImage.Format_RGBA16FPx4: QImage.Format_RGBA8888,
           QImage.Format_RGBX16FPx4: QImage.Format_RGBA8888}
_FLOTTANTS = {QImage.Format_RGBA32FPx4_Premultiplied, QImage.Format_RGBA32FPx4, QImage.Format_RGBX32FPx4,
              QImage.Format_RGBA16FPx4_Premultiplied, QImage.Format_RGBA16FPx4, QImage.Format_RGBX16FPx4}


def convertir(img: QImage, fmt) -> QImage:
    """img.convertToFormat(fmt), en évitant un défaut de Qt : d'ARGB32 prémultiplié vers un format à virgule, Qt
    perd la transparence (un pixel transparent devient noir opaque). On passe alors par le 16 bits (exact)."""
    if img.format() == fmt:
        return img
    if fmt in _FLOTTANTS and img.format() == QImage.Format_ARGB32_Premultiplied:
        img = img.convertToFormat(FORMAT_16)
    return img.convertToFormat(fmt)


def bits(img: QImage | None) -> int:
    """8, 16 ou 32 (nombres à virgule) bits par couche."""
    if img is None or img.isNull():
        return 8
    f = img.format()
    if f in _FLOTTANTS:
        return 32
    return 16 if f in _VERS_8 else 8


def est_16(img: QImage | None) -> bool:
    """Image de grande profondeur (16 ou 32 bits) : à garder telle quelle, pas à ramener en 8 bits."""
    return bits(img) > 8


def est_32(img: QImage | None) -> bool:
    return bits(img) == 32


def format_de(img: QImage | None):
    """Format de calque (prémultiplié) de même profondeur que img."""
    return FORMATS[bits(img)]


def en_bits(img: QImage, b: int) -> QImage:
    """img au format de calque de la profondeur b (8, 16 ou 32)."""
    return convertir(img, FORMATS[b])


def comme(img: QImage, ref: QImage | None) -> QImage:
    """img au format de calque de même profondeur que ref."""
    return en_bits(img, bits(ref))


def vers_8(img: QImage) -> QImage:
    """Image 16 / 32 bits -> son équivalent 8 bits (même ordre de prémultiplication ; au-dessus du blanc : blanc) ;
    une image 8 bits est rendue telle quelle."""
    f = _VERS_8.get(img.format())
    return img if f is None else img.convertToFormat(f)


def en_16(img: QImage) -> QImage:
    return img if img.format() == FORMAT_16 else img.convertToFormat(FORMAT_16)


def en_32(img: QImage) -> QImage:
    return convertir(img, FORMAT_32)


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


def tab32(img: QImage, premul: bool = False) -> np.ndarray:
    """Copie (h, w, 4) float32 R, V, B, A (1.0 = blanc, peut dépasser 1) ; non prémultiplié sauf si premul. Une
    image 8 ou 16 bits est convertie (0..1)."""
    src = convertir(img, FORMAT_32 if premul else QImage.Format_RGBA32FPx4)
    h, w, ligne = src.height(), src.width(), src.bytesPerLine()
    brut = np.frombuffer(src.constBits(), np.float32, count=h * ligne // 4).reshape(h, ligne // 4)
    return brut[:, : w * 4].reshape(h, w, 4).copy()


def qimage32(t: np.ndarray, premul: bool = False) -> QImage:
    """Tableau (h, w, 4) float32 R, V, B, A (non prémultiplié sauf si premul) -> QImage FORMAT_32."""
    t = np.ascontiguousarray(t, dtype=np.float32)
    h, w = t.shape[:2]
    img = QImage(t.data, w, h, w * 16, FORMAT_32 if premul else QImage.Format_RGBA32FPx4).copy()
    return en_32(img)


def tab(img: QImage, premul: bool = False) -> np.ndarray:
    """Pixels (h, w, 4) R, V, B, A dans la profondeur de l'image : uint8, uint16 ou float32."""
    b = bits(img)
    if b == 32:
        return tab32(img, premul)
    if b == 16:
        return tab16(img, premul)
    src = img.convertToFormat(FORMAT_8 if premul else QImage.Format_RGBA8888)
    h, w, ligne = src.height(), src.width(), src.bytesPerLine()
    brut = np.frombuffer(src.constBits(), np.uint8, count=h * ligne).reshape(h, ligne)
    if premul:                                          # ARGB32 prémultiplié : B, V, R, A en mémoire
        return brut[:, : w * 4].reshape(h, w, 4)[..., [2, 1, 0, 3]].copy()
    return brut[:, : w * 4].reshape(h, w, 4).copy()


def qimage(t: np.ndarray, premul: bool = False) -> QImage:
    """Tableau (h, w, 4) R, V, B, A -> QImage de calque de la profondeur de son type (uint8, uint16, float32)."""
    if t.dtype == np.float32:
        return qimage32(t, premul)
    if t.dtype == np.uint16:
        return qimage16(t, premul)
    t = np.ascontiguousarray(t, dtype=np.uint8)
    h, w = t.shape[:2]
    return QImage(t.data, w, h, w * 4, QImage.Format_RGBA8888_Premultiplied if premul
                  else QImage.Format_RGBA8888).copy().convertToFormat(FORMAT_8)


# ------------------------------------------------------------------ HDR : courbe sRVB et virage vers 8 / 16 bits
def lineaire_vers_srvb(v: np.ndarray) -> np.ndarray:
    """Valeurs linéaires (fichiers EXR, .hdr) -> courbe sRVB, prolongée au-delà de 1 (et symétrique sous 0)."""
    v = np.asarray(v, np.float32)
    a = np.abs(v)
    s = np.where(a <= 0.0031308, a * 12.92, 1.055 * np.power(np.maximum(a, 1e-12), 1 / 2.4) - 0.055)
    return (np.sign(v) * s).astype(np.float32)


def srvb_vers_lineaire(v: np.ndarray) -> np.ndarray:
    v = np.asarray(v, np.float32)
    a = np.abs(v)
    l = np.where(a <= 0.04045, a / 12.92, np.power((a + 0.055) / 1.055, 2.4))
    return (np.sign(v) * l).astype(np.float32)


# Aperçu à l'écran d'une image 32 bits (Affichage > Exposition 32 bits) : en diaphs, comme Photoshop.
exposition_ecran = 0.0


def exposer(rgb: np.ndarray, diaphs: float) -> np.ndarray:
    """Couleurs sRVB (non prémultipliées) -> même image avec l'exposition changée de `diaphs` (calcul en linéaire,
    comme un appareil photo)."""
    if not diaphs:
        return rgb
    return lineaire_vers_srvb(srvb_vers_lineaire(rgb) * np.float32(2.0 ** diaphs))


def virage(img: QImage, exposition: float = 0.0, gamma: float = 1.0, compression: bool = False) -> QImage:
    """Virage HDR : image 32 bits -> image 32 bits dont toutes les valeurs tiennent entre 0 et 1, prête pour le 16
    ou le 8 bits. exposition en diaphs ; gamma > 1 éclaircit les tons moyens ; compression : les hautes lumières
    sont ramenées en douceur sous le blanc (Reinhard étendu, sur la couche la plus claire : la plus claire de l'image
    devient tout juste blanche) au lieu d'être coupées."""
    t = tab32(img)
    rgb = np.maximum(t[..., :3], 0)
    lin = srvb_vers_lineaire(rgb) * np.float32(2.0 ** exposition)
    if compression:
        m = lin.max(axis=-1)
        blanc = max(1.0, float(m.max()) if m.size else 1.0)
        nouv = m * (1 + m / (blanc * blanc)) / (1 + m)
        lin = lin * (nouv / np.maximum(m, 1e-6))[..., None]
    rgb = lineaire_vers_srvb(np.clip(lin, 0, 1))
    if gamma and abs(gamma - 1) > 1e-3:
        rgb = np.power(rgb, np.float32(1 / gamma))
    t[..., :3] = np.clip(rgb, 0, 1)
    return qimage32(t)


# ------------------------------------------------------------------ tramage (dithering)
# Passage de 16 / 32 à 8 bits : un très léger bruit (± 1 niveau sur 255, loi triangulaire) est ajouté avant
# l'arrondi ; un dégradé lisse ne montre alors pas de marches. Motif fixe de 256 × 256 répété : même résultat à
# chaque fois.
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


def vers_8_trame(img: QImage, diaphs: float = 0.0) -> QImage:
    """Image 16 / 32 bits -> son équivalent 8 bits (comme vers_8), avec tramage si le réglage est allumé.
    diaphs : exposition (images 32 bits seulement, aperçu à l'écran)."""
    b = bits(img)
    if b == 8:
        return img
    if b == 32:
        t = tab32(img)
        rgb = exposer(np.maximum(t[..., :3], 0), diaphs) if diaphs else t[..., :3]
        v = (np.clip(rgb, 0, 1) * 65535 + 0.5).astype(np.int32)
        a = (np.clip(t[..., 3], 0, 1) * 65535 + 0.5).astype(np.uint32)
    else:
        if not tramage:
            return vers_8(img)
        t = tab16(img)
        v = t[..., :3].astype(np.int32)
        a = t[..., 3].astype(np.uint32)
    h, w = v.shape[:2]
    if tramage:
        v += _bruit(h, w)
    np.clip(v, 0, 65535, out=v)
    rgba = np.empty((h, w, 4), np.uint8)
    rgba[..., :3] = (v * 255 + 32767) // 65535                 # arrondi au plus proche
    rgba[..., 3] = (a * 255 + 32767) // 65535
    res = QImage(np.ascontiguousarray(rgba).data, w, h, w * 4, QImage.Format_RGBA8888).copy()
    return res.convertToFormat(_VERS_8.get(img.format(), FORMAT_8))


def remonter(nouveau: QImage, ancien: QImage | None, b: int = 16) -> QImage:
    """Résultat 8 bits d'une fonction du pont -> profondeur b (16 ou 32) ; là où rien n'a changé, les pixels de
    `ancien` (avec leur précision, et en 32 bits leurs valeurs au-dessus du blanc)."""
    n = en_bits(nouveau, b)
    if ancien is None or bits(ancien) != b or ancien.size() != nouveau.size():
        return n
    a = en_bits(ancien, b)
    q8, r8 = en_8(nouveau), en_8(a)               # (gardées : _octets ne fait que regarder leurs pixels)
    pareil = np.all(_octets(q8, 1) == _octets(r8, 1), axis=-1)
    if not pareil.any():
        return n
    if pareil.all():
        return a
    taille = 4 if b == 32 else 2
    res = _octets(n, taille).copy()
    res[pareil] = _octets(a, taille)[pareil]
    h, w = res.shape[:2]
    return QImage(np.ascontiguousarray(res).data, w, h, w * 4 * taille, FORMATS[b]).copy()


def _octets(img: QImage, taille: int) -> np.ndarray:
    """Vue (h, w, 4) des pixels (uint8 si taille 1, uint16 si 2, float32 si 4). Une vue seulement : l'image doit
    rester gardée tant que la vue sert."""
    h, w, ligne = img.height(), img.width(), img.bytesPerLine()
    t = {1: np.uint8, 2: np.uint16, 4: np.float32}[taille]
    return np.frombuffer(img.constBits(), t, count=h * ligne // taille).reshape(h, ligne // taille)[:, : w * 4] \
        .reshape(h, w, 4)
