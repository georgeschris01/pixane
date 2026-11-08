"""Le document : l'image, la sélection, le fichier d'origine (EXIF, profil couleur)."""
from __future__ import annotations

import io
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QColor, QImage, QPainter

COULEUR_SELECTION = QColor(255, 40, 40)
FORMAT_IMAGE = QImage.Format_RGBA8888
FORMAT_SELECTION = QImage.Format_ARGB32_Premultiplied

EXTENSIONS_LECTURE = "*.jpg *.jpeg *.png *.tif *.tiff *.webp *.bmp"


# ------------------------------------------------------------------ conversions
def pil_vers_qimage(im: Image.Image) -> QImage:
    im = im.convert("RGBA")
    donnees = im.tobytes("raw", "RGBA")
    return QImage(donnees, im.width, im.height, im.width * 4, FORMAT_IMAGE).copy()


def tableau(img: QImage) -> np.ndarray:
    """Vue numpy (h, w, 4) d'une QImage 32 bits (copie)."""
    h, w, ligne = img.height(), img.width(), img.bytesPerLine()
    brut = np.frombuffer(img.constBits(), np.uint8, count=h * ligne).reshape(h, ligne)
    return brut[:, : w * 4].reshape(h, w, 4).copy()


def qimage_vers_pil(img: QImage) -> Image.Image:
    img = img.convertToFormat(FORMAT_IMAGE)
    return Image.fromarray(tableau(img), "RGBA")


def qimage_rgb(tab: np.ndarray) -> QImage:
    """Tableau (h, w, 3) uint8 -> QImage au format du document."""
    h, w = tab.shape[:2]
    rgba = np.ascontiguousarray(np.dstack([tab, np.full((h, w), 255, np.uint8)]))
    return QImage(rgba.data, w, h, w * 4, FORMAT_IMAGE).copy()


def nouvelle_selection(largeur: int, hauteur: int) -> QImage:
    sel = QImage(largeur, hauteur, FORMAT_SELECTION)
    sel.fill(0)
    return sel


def masque(selection: QImage) -> np.ndarray:
    """Masque 0..255 (h, w) : 255 = sélectionné."""
    return tableau(selection)[:, :, 3]


# ------------------------------------------------------------------ document
class Document(QObject):
    change = Signal()          # image ou sélection modifiée (pour redessiner)
    taille_changee = Signal()  # dimensions modifiées

    def __init__(self, image: QImage, chemin: Path | None = None, exif: bytes | None = None,
                 icc: bytes | None = None):
        super().__init__()
        self.image = image.convertToFormat(FORMAT_IMAGE)
        self.selection = nouvelle_selection(image.width(), image.height())
        self.chemin = chemin
        self.exif = exif
        self.icc = icc
        self.modifie = False

    # ---------------------------------------------------------- fichiers
    @classmethod
    def ouvrir(cls, chemin: str | Path) -> "Document":
        chemin = Path(chemin)
        with Image.open(chemin) as im:
            exif = im.info.get("exif")
            icc = im.info.get("icc_profile")
            im = ImageOps.exif_transpose(im)  # remet la photo dans le bon sens
            if im.mode in ("I;16", "I;16B", "I", "F"):
                im = im.point(lambda v: v / 256).convert("L")
            qimg = pil_vers_qimage(im)
        return cls(qimg, chemin, exif, icc)

    def enregistrer(self, chemin: str | Path) -> None:
        chemin = Path(chemin)
        ext = chemin.suffix.lower()
        im = qimage_vers_pil(self.image)
        opaque = bool(np.all(np.asarray(im)[:, :, 3] == 255))
        options = {}
        if self.icc:
            options["icc_profile"] = self.icc
        if self.exif and ext in (".jpg", ".jpeg", ".tif", ".tiff", ".webp", ".png"):
            try:
                ex = Image.Exif()
                ex.load(self.exif)
                ex[0x0112] = 1  # orientation : déjà appliquée à l'image
                options["exif"] = ex.tobytes()
            except Exception:
                pass
        if ext in (".jpg", ".jpeg"):
            im = im.convert("RGB")
            options.update(quality=95, subsampling=0)
        elif ext == ".webp":
            options.update(quality=95)
            if opaque:
                im = im.convert("RGB")
        elif ext in (".tif", ".tiff"):
            options.update(compression="tiff_lzw")
            if opaque:
                im = im.convert("RGB")
        elif ext == ".png":
            options.update(compress_level=6)
            if opaque:
                im = im.convert("RGB")
        elif ext == ".bmp":
            im = im.convert("RGB")
        else:
            raise ValueError(f"Format non pris en charge : {ext}")
        im.save(chemin, **options)
        self.chemin = chemin
        self.modifie = False

    # ---------------------------------------------------------- état (annuler / rétablir)
    def etat(self) -> tuple[QImage, QImage]:
        return self.image, self.selection.copy()

    def appliquer_etat(self, etat: tuple[QImage, QImage]) -> None:
        ancienne = self.image.size()
        if etat[0].cacheKey() != self.image.cacheKey():
            self.modifie = True
        self.image, sel = etat
        self.selection = sel.copy()
        if self.image.size() != ancienne:
            self.taille_changee.emit()
        self.change.emit()

    # ---------------------------------------------------------- sélection
    def selection_vide(self) -> bool:
        return not masque(self.selection).any()

    def tout_selectionner(self):
        self.selection.fill(COULEUR_SELECTION)
        self.change.emit()

    def deselectionner(self):
        self.selection.fill(0)
        self.change.emit()

    def inverser_selection(self):
        nouvelle = QImage(self.selection.size(), FORMAT_SELECTION)
        nouvelle.fill(COULEUR_SELECTION)
        p = QPainter(nouvelle)
        p.setCompositionMode(QPainter.CompositionMode_DestinationOut)
        p.drawImage(0, 0, self.selection)
        p.end()
        self.selection = nouvelle
        self.change.emit()

    # ---------------------------------------------------------- pour l'IA
    def png_pour_ia(self, avec_selection: bool) -> bytes:
        """PNG de l'image ; la zone sélectionnée devient transparente (= zone à traiter pour ComfyUI)."""
        rgb = tableau(self.image)[:, :, :3]
        if avec_selection:
            alpha = 255 - masque(self.selection)
            im = Image.fromarray(np.dstack([rgb, alpha]), "RGBA")
        else:
            im = Image.fromarray(np.ascontiguousarray(rgb), "RGB")
        tampon = io.BytesIO()
        im.save(tampon, "PNG", compress_level=1)
        return tampon.getvalue()
