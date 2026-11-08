"""Le document : les calques, la sélection, le fichier d'origine (EXIF, profil couleur).

Les calques ont tous la taille du document. `doc.image` est l'image fusionnée (calques visibles), calculée à la
demande : c'est elle qu'on affiche, qu'on envoie à l'IA et qu'on enregistre en JPG / PNG…
Chaque état (pour Annuler / Rétablir) est un instantané : (calques, calque actif, sélection). Les calques sont
immuables : une modification crée un nouveau Calque (les QImage sont partagées tant qu'on ne les modifie pas).
"""
from __future__ import annotations

import io
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps
from PySide6.QtCore import QObject, QPoint, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter

COULEUR_SELECTION = QColor(255, 40, 40)
FORMAT_IMAGE = QImage.Format_RGBA8888
FORMAT_SELECTION = QImage.Format_ARGB32_Premultiplied
FORMAT_CALQUE = QImage.Format_ARGB32_Premultiplied

EXTENSIONS_LECTURE = "*.jpg *.jpeg *.png *.tif *.tiff *.webp *.bmp *.ora"


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


def qimage_rgba(tab: np.ndarray) -> QImage:
    """Tableau (h, w, 4) uint8 RGBA -> QImage au format du document."""
    h, w = tab.shape[:2]
    tab = np.ascontiguousarray(tab)
    return QImage(tab.data, w, h, w * 4, FORMAT_IMAGE).copy()


def qimage_rgb(tab: np.ndarray) -> QImage:
    """Tableau (h, w, 3) uint8 -> QImage au format du document."""
    h, w = tab.shape[:2]
    return qimage_rgba(np.dstack([tab, np.full((h, w), 255, np.uint8)]))


def nouvelle_selection(largeur: int, hauteur: int) -> QImage:
    sel = QImage(largeur, hauteur, FORMAT_SELECTION)
    sel.fill(0)
    return sel


def masque(selection: QImage) -> np.ndarray:
    """Masque 0..255 (h, w) : 255 = sélectionné."""
    return tableau(selection)[:, :, 3]


def image_vide(largeur: int, hauteur: int) -> QImage:
    img = QImage(largeur, hauteur, FORMAT_CALQUE)
    img.fill(Qt.transparent)
    return img


# ------------------------------------------------------------------ calque
@dataclass(frozen=True, eq=False)   # comparés par identité (pas pixel par pixel)
class Calque:
    nom: str
    image: QImage                 # FORMAT_CALQUE, taille du document
    visible: bool = True
    opacite: float = 1.0          # 0..1

    @staticmethod
    def depuis(nom: str, image: QImage, **kw) -> "Calque":
        return Calque(nom, image.convertToFormat(FORMAT_CALQUE), **kw)


def fusionner(calques, largeur: int, hauteur: int, seulement_visibles: bool = True) -> QImage:
    """Image fusionnée (FORMAT_CALQUE) des calques, du bas vers le haut."""
    res = image_vide(largeur, hauteur)
    p = QPainter(res)
    for c in calques:
        if c.visible or not seulement_visibles:
            p.setOpacity(c.opacite)
            p.drawImage(0, 0, c.image)
    p.end()
    return res


def calque_des_changements(nom: str, resultat: QImage, base: QImage) -> Calque:
    """Calque qui ne contient que les pixels où `resultat` diffère de `base` (même taille).
    Posé sur `base`, il redonne exactement `resultat`."""
    r = tableau(resultat.convertToFormat(FORMAT_IMAGE))
    b = tableau(base.convertToFormat(FORMAT_IMAGE))
    change = np.any(r != b, axis=2)
    r[:, :, 3] = np.where(change, r[:, :, 3], 0)
    return Calque.depuis(nom, qimage_rgba(r))


# ------------------------------------------------------------------ document
class Document(QObject):
    change = Signal()          # image ou sélection modifiée (pour redessiner)
    taille_changee = Signal()  # dimensions modifiées
    calques_changes = Signal() # liste, ordre, noms, visibilité, opacité ou calque actif modifiés

    def __init__(self, image: QImage | None = None, chemin: Path | None = None, exif: bytes | None = None,
                 icc: bytes | None = None, calques: list[Calque] | None = None):
        super().__init__()
        if calques is None:
            calques = [Calque.depuis("Arrière-plan", image)]
        self.calques: tuple[Calque, ...] = tuple(calques)
        self.actif = len(self.calques) - 1
        w, h = self.taille()
        self.selection = nouvelle_selection(w, h)
        self.chemin = chemin
        self.exif = exif
        self.icc = icc
        self.modifie = False
        self._fusion: QImage | None = None

    # ---------------------------------------------------------- image fusionnée
    def taille(self) -> tuple[int, int]:
        img = self.calques[0].image
        return img.width(), img.height()

    @property
    def image(self) -> QImage:
        if self._fusion is None:
            w, h = self.taille()
            self._fusion = fusionner(self.calques, w, h).convertToFormat(FORMAT_IMAGE)
        return self._fusion

    @property
    def calque_actif(self) -> Calque:
        return self.calques[self.actif]

    # ---------------------------------------------------------- fichiers
    @classmethod
    def ouvrir(cls, chemin: str | Path) -> "Document":
        chemin = Path(chemin)
        if chemin.suffix.lower() == ".ora":
            return cls(chemin=chemin, calques=lire_ora(chemin))
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
        if ext == ".ora":
            ecrire_ora(chemin, self.calques, self.image)
            self.chemin = chemin
            self.modifie = False
            return
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
    def etat(self):
        return (self.calques, self.actif, self.selection.copy())

    def appliquer_etat(self, etat) -> None:
        calques, actif, sel = etat
        ancienne = self.taille()
        if len(calques) != len(self.calques) or any(a is not b for a, b in zip(calques, self.calques)):
            self.modifie = True
        self.calques = tuple(calques)
        self.actif = max(0, min(actif, len(self.calques) - 1))
        self.selection = sel.copy()
        self._fusion = None
        if self.taille() != ancienne:
            self.taille_changee.emit()
        self.calques_changes.emit()
        self.change.emit()

    def apercu_calque(self, index: int, image: QImage) -> None:
        """Remplace l'image d'un calque sans entrée dans Annuler (aperçu pendant un coup de gomme)."""
        calques = list(self.calques)
        calques[index] = replace(calques[index], image=image)
        self.calques = tuple(calques)
        self._fusion = None
        self.change.emit()

    def etat_avec(self, calques, actif: int | None = None, selection: QImage | None = None):
        """Nouvel état construit à partir de l'actuel (pour les commandes annulables)."""
        calques = tuple(calques)
        if actif is None:
            actif = min(self.actif, len(calques) - 1)
        if selection is None:
            w, h = calques[0].image.width(), calques[0].image.height()
            selection = self.selection.copy() if (w, h) == self.taille() else nouvelle_selection(w, h)
        return (calques, actif, selection)

    def nom_libre(self, base: str) -> str:
        noms = {c.nom for c in self.calques}
        i = 1
        while f"{base} {i}" in noms:
            i += 1
        return f"{base} {i}"

    # ---------------------------------------------------------- états proposés par les actions sur les calques
    def etat_resultat_ia(self, titre: str, resultat: QImage):
        """Résultat de l'IA de même taille : nouveau calque (en haut) avec seulement les pixels changés."""
        calque = calque_des_changements(self.nom_libre(titre), resultat, self.image)
        return self.etat_avec(self.calques + (calque,), len(self.calques))

    def etat_agrandi(self, titre: str, resultat: QImage, decalage: tuple[int, int]):
        """Agrandir : chaque calque est posé, décalé, sur la nouvelle toile ; l'ajout de l'IA va dans un nouveau
        calque en haut (seulement les pixels qui diffèrent de la photo d'origine)."""
        W, H = resultat.width(), resultat.height()
        dx, dy = decalage
        nouveaux = []
        for c in self.calques:
            img = image_vide(W, H)
            p = QPainter(img)
            p.drawImage(QPoint(dx, dy), c.image)
            p.end()
            nouveaux.append(replace(c, image=img))
        base = fusionner(nouveaux, W, H)
        calque = calque_des_changements(self.nom_libre(titre), resultat, base)
        return self.etat_avec(tuple(nouveaux) + (calque,), len(nouveaux))

    def etat_redimensionne(self, titre: str, resultat: QImage):
        """Upscale : tous les calques sont agrandis (lissage) ; le résultat de l'IA, complet, va en haut."""
        W, H = resultat.width(), resultat.height()
        nouveaux = [replace(c, image=c.image.scaled(W, H, Qt.IgnoreAspectRatio, Qt.SmoothTransformation))
                    for c in self.calques]
        calque = Calque.depuis(self.nom_libre(titre), resultat)
        return self.etat_avec(tuple(nouveaux) + (calque,), len(nouveaux))

    def etat_calque_modifie(self, index: int, **changements):
        calques = list(self.calques)
        calques[index] = replace(calques[index], **changements)
        return self.etat_avec(calques)

    def etat_nouveau_calque(self):
        w, h = self.taille()
        c = Calque(self.nom_libre("Calque"), image_vide(w, h))
        calques = list(self.calques)
        calques.insert(self.actif + 1, c)
        return self.etat_avec(calques, self.actif + 1)

    def etat_dupliquer(self):
        c = self.calque_actif
        copie = replace(c, nom=f"{c.nom} (copie)", image=QImage(c.image))
        calques = list(self.calques)
        calques.insert(self.actif + 1, copie)
        return self.etat_avec(calques, self.actif + 1)

    def etat_supprimer(self):
        if len(self.calques) <= 1:
            return None
        calques = list(self.calques)
        del calques[self.actif]
        return self.etat_avec(calques, max(0, self.actif - 1))

    def etat_deplacer(self, depuis: int, vers: int):
        if depuis == vers or not (0 <= vers < len(self.calques)):
            return None
        calques = list(self.calques)
        c = calques.pop(depuis)
        calques.insert(vers, c)
        actif = vers if self.actif == depuis else calques.index(self.calque_actif)
        return self.etat_avec(calques, actif)

    def etat_fusionner_bas(self):
        if self.actif == 0:
            return None
        w, h = self.taille()
        dessous, dessus = self.calques[self.actif - 1], self.calque_actif
        img = fusionner([replace(dessous, opacite=1.0, visible=True), dessus], w, h)
        fusion = replace(dessous, image=img)
        calques = list(self.calques)
        calques[self.actif - 1:self.actif + 1] = [fusion]
        return self.etat_avec(calques, self.actif - 1)

    def etat_aplatir(self):
        if len(self.calques) <= 1:
            return None
        w, h = self.taille()
        return self.etat_avec([Calque("Arrière-plan", fusionner(self.calques, w, h))], 0)

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
        """PNG de l'image visible ; la zone sélectionnée devient transparente (= zone à traiter pour ComfyUI)."""
        rgb = tableau(self.image)[:, :, :3]
        if avec_selection:
            alpha = 255 - masque(self.selection)
            im = Image.fromarray(np.dstack([rgb, alpha]), "RGBA")
        else:
            im = Image.fromarray(np.ascontiguousarray(rgb), "RGB")
        tampon = io.BytesIO()
        im.save(tampon, "PNG", compress_level=1)
        return tampon.getvalue()


# ------------------------------------------------------------------ format OpenRaster (.ora)
# Format ouvert à calques (lu aussi par Krita, GIMP, MyPaint) : une archive zip avec un PNG par calque,
# la liste des calques (stack.xml), l'image fusionnée et une vignette.
def _png(img: QImage) -> bytes:
    tampon = io.BytesIO()
    qimage_vers_pil(img).save(tampon, "PNG", compress_level=6)
    return tampon.getvalue()


def ecrire_ora(chemin: Path, calques, fusion: QImage) -> None:
    w, h = calques[0].image.width(), calques[0].image.height()
    pile = ET.Element("image", w=str(w), h=str(h), version="0.0.5")
    pile_calques = ET.SubElement(pile, "stack")
    temporaire = chemin.with_name(chemin.name + ".tmp")
    with zipfile.ZipFile(temporaire, "w") as z:
        z.writestr(zipfile.ZipInfo("mimetype"), "image/openraster", compress_type=zipfile.ZIP_STORED)
        for i, c in enumerate(reversed(calques)):          # stack.xml : du haut vers le bas
            nom_png = f"data/calque{len(calques) - 1 - i}.png"
            z.writestr(nom_png, _png(c.image), compress_type=zipfile.ZIP_STORED)
            ET.SubElement(pile_calques, "layer", name=c.nom, src=nom_png, x="0", y="0",
                          opacity=f"{c.opacite:.3f}", visibility="visible" if c.visible else "hidden")
        z.writestr("stack.xml", ET.tostring(pile, encoding="utf-8", xml_declaration=True),
                   compress_type=zipfile.ZIP_DEFLATED)
        z.writestr("mergedimage.png", _png(fusion), compress_type=zipfile.ZIP_STORED)
        vignette = fusion.scaled(256, 256, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        z.writestr("Thumbnails/thumbnail.png", _png(vignette), compress_type=zipfile.ZIP_STORED)
    temporaire.replace(chemin)


def lire_ora(chemin: Path) -> list[Calque]:
    with zipfile.ZipFile(chemin) as z:
        racine = ET.fromstring(z.read("stack.xml"))
        w, h = int(racine.get("w")), int(racine.get("h"))
        calques = []
        for couche in racine.iter("layer"):                 # du haut vers le bas
            with Image.open(io.BytesIO(z.read(couche.get("src")))) as im:
                morceau = pil_vers_qimage(im)
            img = image_vide(w, h)
            p = QPainter(img)
            p.drawImage(QPoint(int(float(couche.get("x", 0))), int(float(couche.get("y", 0)))), morceau)
            p.end()
            calques.append(Calque(couche.get("name") or "Calque", img,
                                  visible=couche.get("visibility", "visible") != "hidden",
                                  opacite=float(couche.get("opacity", 1))))
    if not calques:
        raise ValueError("Ce fichier .ora ne contient aucun calque.")
    return list(reversed(calques))
