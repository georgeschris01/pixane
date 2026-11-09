"""Impression : conversion en CMJN avec un profil couleur (fichiers .icc / .icm fournis par Windows, rien à
télécharger) et aperçu à l'écran des couleurs « comme à l'impression ». Pixane travaille en RVB ; le CMJN n'est fait
qu'au moment d'exporter, comme le conseillent les imprimeurs et Adobe."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageCms
from PySide6.QtGui import QImage

from .document import FORMAT_IMAGE, pil_vers_qimage, qimage_vers_pil, tableau

DOSSIER_PROFILS = Path(os.environ.get("WINDIR", r"C:\Windows")) / "System32" / "spool" / "drivers" / "color"
PREFERES = ("CoatedFOGRA39", "ISOcoated_v2", "CoatedFOGRA27", "USWebCoatedSWOP", "RSWOP")   # le premier trouvé
INTENTIONS = {"perceptive": ImageCms.Intent.PERCEPTUAL, "relative": ImageCms.Intent.RELATIVE_COLORIMETRIC}


@lru_cache(maxsize=1)
def profils_cmjn() -> tuple[tuple[str, str], ...]:
    """(nom lisible, chemin) des profils CMJN installés dans Windows, du plus courant au moins courant."""
    res = []
    for f in sorted(DOSSIER_PROFILS.glob("*.ic[cm]")):
        try:
            p = ImageCms.getOpenProfile(str(f))
            if p.profile.xcolor_space.strip() == "CMYK":
                res.append(((ImageCms.getProfileDescription(p) or f.stem).strip(), str(f)))
        except (OSError, ImageCms.PyCMSError, AttributeError):
            continue
    def rang(e):
        nom = Path(e[1]).stem.lower()
        for i, pref in enumerate(PREFERES):
            if nom == pref.lower():
                return (i, e[0])
        return (len(PREFERES), e[0])
    return tuple(sorted(res, key=rang))


def profil_defaut() -> str | None:
    p = profils_cmjn()
    return p[0][1] if p else None


@lru_cache(maxsize=8)
def _transformation(profil: str, intention: str, compensation: bool):
    flags = ImageCms.Flags.BLACKPOINTCOMPENSATION if compensation else ImageCms.Flags.NONE
    return ImageCms.buildTransform(ImageCms.createProfile("sRGB"), ImageCms.getOpenProfile(profil), "RGB", "CMYK",
                                   INTENTIONS[intention], flags=flags)


@lru_cache(maxsize=8)
def _retour(profil: str):
    return ImageCms.buildTransform(ImageCms.getOpenProfile(profil), ImageCms.createProfile("sRGB"), "CMYK", "RGB",
                                   ImageCms.Intent.RELATIVE_COLORIMETRIC)


def sur_blanc(img: QImage) -> Image.Image:
    """Image RVB opaque (la transparence est posée sur du blanc, comme sur le papier)."""
    t = tableau(img.convertToFormat(FORMAT_IMAGE)).astype(np.uint16)
    a = t[:, :, 3:4]
    rgb = (t[:, :, :3] * a + 255 * (255 - a) + 127) // 255
    return Image.fromarray(rgb.astype(np.uint8), "RGB")


def vers_cmjn(img: QImage, profil: str, intention: str = "perceptive", compensation: bool = True) -> Image.Image:
    return ImageCms.applyTransform(sur_blanc(img), _transformation(profil, intention, compensation))


def octets_profil(profil: str) -> bytes:
    return Path(profil).read_bytes()


def apercu_impression(img: QImage, profil: str, intention: str = "perceptive", compensation: bool = True) -> QImage:
    """Couleurs à l'écran comme une fois imprimées (RVB -> CMJN -> RVB) ; la transparence est gardée."""
    t = tableau(img.convertToFormat(FORMAT_IMAGE))
    cmjn = ImageCms.applyTransform(Image.fromarray(np.ascontiguousarray(t[:, :, :3]), "RGB"),
                                   _transformation(profil, intention, compensation))
    rgb = np.asarray(ImageCms.applyTransform(cmjn, _retour(profil)))
    res = np.dstack([rgb, t[:, :, 3]])
    return pil_vers_qimage(Image.fromarray(np.ascontiguousarray(res), "RGBA")).convertToFormat(FORMAT_IMAGE)


def enregistrer_cmjn(img: QImage, chemin: Path, profil: str, intention: str = "perceptive", compensation: bool = True,
                     dpi: float = 300, qualite: int = 95) -> None:
    """TIFF, JPEG ou PDF en CMJN, avec le profil intégré (TIFF, JPEG) et la résolution."""
    chemin = Path(chemin)
    ext = chemin.suffix.lower()
    im = vers_cmjn(img, profil, intention, compensation)
    icc = octets_profil(profil)
    if ext in (".tif", ".tiff"):
        im.save(chemin, compression="tiff_lzw", icc_profile=icc, dpi=(dpi, dpi))
    elif ext in (".jpg", ".jpeg"):
        im.save(chemin, quality=qualite, subsampling=0, icc_profile=icc, dpi=(dpi, dpi))
    elif ext == ".pdf":
        im.save(chemin, "PDF", resolution=dpi, quality=qualite)
    else:
        raise ValueError(ext)


__all__ = ["profils_cmjn", "profil_defaut", "vers_cmjn", "apercu_impression", "enregistrer_cmjn", "qimage_vers_pil"]
