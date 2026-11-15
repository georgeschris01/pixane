"""Fichiers d'images 32 bits (HDR) : OpenEXR (.exr, bibliothèque OpenEXR, BSD-3), Radiance (.hdr, écrit ici) et
TIFF 32 bits à virgule (Qt).

Ces fichiers gardent des valeurs linéaires (proportionnelles à la lumière), parfois bien au-dessus de 1. Dans Pixane,
le 32 bits suit la courbe sRVB comme le 8 et le 16 bits : conversion à l'ouverture et à l'enregistrement
(profondeur.lineaire_vers_srvb / srvb_vers_lineaire).

lire(chemin) -> tableau (h, w, 4) float32 R, V, B, A non prémultiplié, sur la courbe sRVB ; ou None si le fichier
n'est pas une image 32 bits.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np

from .profondeur import lineaire_vers_srvb, srvb_vers_lineaire

EXTENSIONS_HDR = (".exr", ".hdr")


def _vers_srvb(t: np.ndarray) -> np.ndarray:
    t = t.astype(np.float32, copy=True)
    t[..., :3] = lineaire_vers_srvb(t[..., :3])
    return t


def _vers_lineaire(t: np.ndarray) -> np.ndarray:
    t = t.astype(np.float32, copy=True)
    t[..., :3] = srvb_vers_lineaire(t[..., :3])
    return t


def lire(chemin: str | Path) -> np.ndarray | None:
    chemin = Path(chemin)
    ext = chemin.suffix.lower()
    if ext == ".exr":
        return _vers_srvb(lire_exr(chemin))
    if ext == ".hdr":
        return _vers_srvb(lire_radiance(chemin))
    if ext in (".tif", ".tiff"):
        return lire_tiff32(chemin)
    return None


def ecrire(chemin: str | Path, t: np.ndarray, dpi: float = 72.0) -> None:
    """t : (h, w, 4) float32 R, V, B, A non prémultiplié, courbe sRVB."""
    chemin = Path(chemin)
    ext = chemin.suffix.lower()
    lin = _vers_lineaire(t)
    if ext == ".exr":
        ecrire_exr(chemin, lin)
    elif ext == ".hdr":
        ecrire_radiance(chemin, lin)
    elif ext in (".tif", ".tiff"):
        ecrire_tiff32(chemin, lin, dpi)
    else:
        raise ValueError(ext)


# ------------------------------------------------------------------ OpenEXR
def lire_exr(chemin: Path) -> np.ndarray:
    import OpenEXR
    with OpenEXR.File(str(chemin), separate_channels=True) as f:
        ch = {k: v.pixels for k, v in f.channels().items()}
    # canaux R, G, B, A (ou Y : gris) ; les noms peuvent porter un préfixe de calque (« diffuse.R ») : le premier
    # jeu complet est pris
    def canal(nom):
        if nom in ch:
            return ch[nom]
        for k, v in ch.items():
            if k.split(".")[-1] == nom:
                return v
        return None
    r, g, b, a = canal("R"), canal("G"), canal("B"), canal("A")
    if r is None or g is None or b is None:
        y = canal("Y")
        if y is None:
            if not ch:
                raise OSError("EXR : aucun canal")
            y = next(iter(ch.values()))
        r = g = b = y
    h, w = r.shape[:2]
    t = np.empty((h, w, 4), np.float32)
    t[..., 0], t[..., 1], t[..., 2] = r, g, b
    t[..., 3] = 1.0 if a is None else a
    return np.nan_to_num(t, nan=0.0, posinf=65504.0, neginf=0.0)


def ecrire_exr(chemin: Path, lin: np.ndarray) -> None:
    """Demi-flottants (16 bits à virgule, l'usage courant des EXR), compression ZIP ; sans A si l'image est
    opaque."""
    import OpenEXR
    opaque = bool(np.all(lin[..., 3] >= 1.0))
    donnees = np.ascontiguousarray(np.clip(lin[..., :3] if opaque else lin, -65504, 65504).astype(np.float16))
    entete = {"compression": OpenEXR.ZIP_COMPRESSION, "type": OpenEXR.scanlineimage}
    with OpenEXR.File(entete, {"RGB" if opaque else "RGBA": donnees}) as f:
        f.write(str(chemin))


# ------------------------------------------------------------------ Radiance (.hdr, RGBE)
def lire_radiance(chemin: Path) -> np.ndarray:
    data = Path(chemin).read_bytes()
    pos = 0
    taille = None
    while pos < len(data):
        fin = data.index(b"\n", pos)
        ligne = data[pos:fin].strip()
        pos = fin + 1
        m = re.match(rb"^([-+])Y\s+(\d+)\s+([-+])X\s+(\d+)$", ligne)
        if m:
            taille = (m.group(1), int(m.group(2)), m.group(3), int(m.group(4)))
            break
        if ligne.startswith(b"FORMAT=") and b"32-bit_rle_rgbe" not in ligne:
            raise OSError("HDR : format non pris en charge (" + ligne.decode("latin-1") + ")")
    if taille is None:
        raise OSError("HDR : taille introuvable")
    sy, h, sx, w = taille
    rgbe = np.zeros((h, w, 4), np.uint8)
    for y in range(h):
        if pos + 4 <= len(data) and data[pos] == 2 and data[pos + 1] == 2 and data[pos + 2] < 128 \
                and (data[pos + 2] << 8 | data[pos + 3]) == w and 8 <= w < 32768:
            pos += 4                                    # ligne compressée (RLE par canal)
            for c in range(4):
                x = 0
                ligne = rgbe[y, :, c]
                while x < w:
                    n = data[pos]
                    pos += 1
                    if n > 128:
                        n -= 128
                        ligne[x:x + n] = data[pos]
                        pos += 1
                    else:
                        ligne[x:x + n] = np.frombuffer(data, np.uint8, n, pos)
                        pos += n
                    x += n
        else:                                           # ligne à plat
            rgbe[y] = np.frombuffer(data, np.uint8, w * 4, pos).reshape(w, 4)
            pos += w * 4
    if sy == b"+":
        rgbe = rgbe[::-1]
    if sx == b"-":
        rgbe = rgbe[:, ::-1]
    e = rgbe[..., 3].astype(np.int32)
    f = np.where(e > 0, np.ldexp(1.0, e - 136), 0.0).astype(np.float32)
    t = np.empty((h, w, 4), np.float32)
    t[..., :3] = np.where(e[..., None] > 0, (rgbe[..., :3].astype(np.float32) + 0.5) * f[..., None], 0)
    t[..., 3] = 1.0
    return t


def ecrire_radiance(chemin: Path, lin: np.ndarray) -> None:
    """RGBE compressé par ligne (morceaux recopiés tels quels : toujours lisible). Le .hdr n'a pas de transparence :
    l'image est posée sur du noir."""
    rgb = np.maximum(lin[..., :3] * np.clip(lin[..., 3:4], 0, 1), 0).astype(np.float32)
    h, w = rgb.shape[:2]
    m = rgb.max(axis=-1)
    mant, ex = np.frexp(m)
    echelle = np.where(m > 1e-32, mant * 256.0 / np.maximum(m, 1e-38), 0)
    rgbe = np.zeros((h, w, 4), np.uint8)
    rgbe[..., :3] = np.clip(np.floor(rgb * echelle[..., None]), 0, 255).astype(np.uint8)
    rgbe[..., 3] = np.where(m > 1e-32, np.clip(ex + 128, 0, 255), 0).astype(np.uint8)
    morceaux = [b"#?RADIANCE\nFORMAT=32-bit_rle_rgbe\nSOFTWARE=Pixane Photo\n\n",
                f"-Y {h} +X {w}\n".encode("ascii")]
    rle = 8 <= w < 32768
    for y in range(h):
        if not rle:
            morceaux.append(rgbe[y].tobytes())
            continue
        morceaux.append(bytes((2, 2, w >> 8, w & 255)))
        for c in range(4):
            ligne = rgbe[y, :, c].tobytes()
            for x in range(0, w, 128):
                bout = ligne[x:x + 128]
                morceaux.append(bytes((len(bout),)) + bout)
    Path(chemin).write_bytes(b"".join(morceaux))


# ------------------------------------------------------------------ TIFF 32 bits à virgule (Qt)
def lire_tiff32(chemin: Path) -> np.ndarray | None:
    """TIFF à virgule (16 ou 32 bits) ; None pour un TIFF ordinaire. Sans profil, ou avec un profil linéaire
    (l'usage des TIFF 32 bits, Photoshop compris), les valeurs sont prises comme linéaires."""
    from PySide6.QtGui import QColorSpace, QImageReader
    from .profondeur import est_32, tab32
    r = QImageReader(str(chemin))
    img = r.read()
    if img.isNull() or not est_32(img):
        return None
    cs = img.colorSpace()
    lineaire = (not cs.isValid()) or cs.transferFunction() == QColorSpace.TransferFunction.Linear
    t = tab32(img)
    return _vers_srvb(t) if lineaire else t


def ecrire_tiff32(chemin: Path, lin: np.ndarray, dpi: float) -> None:
    from PySide6.QtGui import QColorSpace, QImage, QImageWriter
    lin = np.ascontiguousarray(lin, np.float32)
    h, w = lin.shape[:2]
    opaque = bool(np.all(lin[..., 3] >= 1.0))
    img = QImage(lin.data, w, h, w * 16, QImage.Format_RGBA32FPx4).copy()
    if opaque:
        img = img.convertToFormat(QImage.Format_RGBX32FPx4)
    img.setColorSpace(QColorSpace(QColorSpace.SRgbLinear))
    dpm = round(dpi / 0.0254)
    img.setDotsPerMeterX(dpm)
    img.setDotsPerMeterY(dpm)
    wr = QImageWriter(str(chemin), b"tiff")
    wr.setCompression(1)
    if not wr.write(img):
        raise OSError(wr.errorString())
