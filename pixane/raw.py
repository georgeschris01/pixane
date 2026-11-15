"""Fichiers RAW des appareils photo (Canon .CR2 / .CR3, Nikon .NEF, Sony .ARW, Adobe .DNG, Fujifilm .RAF…) :
développés à l'ouverture par LibRaw (bibliothèque rawpy), avec la balance des blancs de l'appareil.

Le résultat est une photo ordinaire (8 bits par couleur), à retoucher ensuite avec les réglages de Pixane. Le
fichier RAW n'est jamais remplacé : Enregistrer propose un autre fichier.
"""
from __future__ import annotations

import io
from pathlib import Path

import numpy as np

EXTENSIONS_RAW = (".cr2", ".cr3", ".crw", ".nef", ".nrw", ".arw", ".srf", ".sr2", ".dng", ".raf", ".orf", ".rw2",
                  ".pef", ".srw", ".rwl", ".raw", ".3fr", ".erf", ".kdc", ".mrw", ".x3f", ".iiq", ".mos")


def est_raw(chemin) -> bool:
    return Path(chemin).suffix.lower() in EXTENSIONS_RAW


def filtre() -> str:
    """Extensions pour la fenêtre Ouvrir (« *.cr2 *.nef … »)."""
    return " ".join("*" + e for e in EXTENSIONS_RAW)


def _exif_vignette(r) -> bytes | None:
    """Les informations de prise de vue (EXIF) de la vignette JPEG incluse dans le RAW, sens remis à « normal »
    (LibRaw a déjà tourné la photo)."""
    try:
        import rawpy
        from PIL import Image
        v = r.extract_thumb()
        if v.format != rawpy.ThumbFormat.JPEG:
            return None
        with Image.open(io.BytesIO(v.data)) as im:
            exif = im.getexif()
            if not exif:
                return None
            exif[0x0112] = 1
            return exif.tobytes()
    except Exception:
        return None


def developper(chemin, demi: bool = False) -> tuple[np.ndarray, bytes | None]:
    """-> (tableau RGB uint8, EXIF ou None). demi : moitié de la taille (beaucoup plus rapide : aperçus, essais)."""
    import rawpy
    with rawpy.imread(str(chemin)) as r:
        rgb = r.postprocess(use_camera_wb=True, half_size=demi, output_bps=8, bright=1.0,
                            auto_bright_thr=0.001)
        exif = _exif_vignette(r)
    return np.ascontiguousarray(rgb), exif
