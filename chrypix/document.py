"""Le document : les calques, la sélection, le fichier d'origine (EXIF, profil couleur).

Les calques ont tous la taille du document. `doc.image` est l'image fusionnée (calques visibles), calculée à la
demande : c'est elle qu'on affiche, qu'on envoie à l'IA et qu'on enregistre en JPG / PNG…
Chaque état (pour Annuler / Rétablir) est un instantané : (calques, calque actif, sélection). Les calques sont
immuables : une modification crée un nouveau Calque (les QImage sont partagées tant qu'on ne les modifie pas).
"""
from __future__ import annotations

import io
import json
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageOps
from PySide6.QtCore import QObject, QPoint, QPointF, QRect, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QTransform

from . import composition
from .composition import (FORMAT_MASQUE, MODE_ORA, MODES, arbre, masque_depuis, masque_plein, masque_tableau,
                          masque_transforme, rendre_calque)
from .langue import tr
from .styles import Style
from .texte import Texte, nom_calque, rendre

COULEUR_SELECTION = QColor(255, 40, 40)
FORMAT_IMAGE = QImage.Format_RGBA8888
FORMAT_SELECTION = QImage.Format_ARGB32_Premultiplied
FORMAT_CALQUE = QImage.Format_ARGB32_Premultiplied

EXTENSIONS_LECTURE = "*.chr *.jpg *.jpeg *.png *.tif *.tiff *.webp *.bmp *.ora *.psd"
EXTENSIONS_CALQUES = (".chr", ".ora", ".psd")      # formats qui gardent les calques


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
    verrou: bool = False          # cadenas : ni gomme, ni suppression, ni fusion, ni opacité
    texte: Texte | None = None    # calque de texte : ses réglages (l'image en est le dessin)
    style: Style | None = None    # style de calque (ombres, contour…) : appliqué à l'affichage, pixels intacts
    masque: QImage | None = None  # masque de calque (gris, taille du document) : noir = caché, blanc = visible
    masque_actif: bool = True     # masque désactivé (Maj+clic sur sa vignette) : tout le calque se voit
    mode: str = "normal"          # mode de fusion (voir composition.MODES)
    reglage: dict | None = None   # calque de réglage : {"type": …, "params": {…}} (pas de pixels)
    groupe: bool = False          # en-tête d'un groupe (ses calques sont juste en dessous, avec `dans` = ident)
    ident: str | None = None      # identifiant d'un groupe
    dans: str | None = None       # groupe qui contient ce calque
    ouvert: bool = True           # groupe déplié dans le panneau Calques

    @staticmethod
    def depuis(nom: str, image: QImage, **kw) -> "Calque":
        return Calque(nom, image.convertToFormat(FORMAT_CALQUE), **kw)

    @property
    def special(self) -> bool:
        """Groupe ou calque de réglage : pas de pixels à peindre."""
        return self.groupe or self.reglage is not None


def nouvel_ident() -> str:
    import uuid
    return uuid.uuid4().hex[:12]


def fusionner(calques, largeur: int, hauteur: int, seulement_visibles: bool = True) -> QImage:
    """Image fusionnée (FORMAT_CALQUE) des calques, du bas vers le haut (masques, styles, modes, réglages,
    groupes)."""
    return composition.fusionner(calques, largeur, hauteur, seulement_visibles)


def calques_figes(calques, garder_groupes: bool = False, garder_masques: bool = False,
                  garder_modes: bool = True) -> list:
    """Pour les autres logiciels : styles mis dans les pixels ; calques de réglage remplacés par leur résultat
    (ce qui est dessous, réglé) ; masques et groupes mis dans les pixels si le format ne les garde pas."""
    w, h = calques[0].image.width(), calques[0].image.height()
    noeuds = arbre(calques)

    def figer(liste, dans):
        res = []
        for n in liste:
            c = n.calque
            if c.reglage is not None:
                dessous = composition._composer([x for x in liste[:liste.index(n)]], w, h, True)
                img = composition.appliquer_reglage(dessous, replace(c, opacite=1.0, masque=None))
                if composition.masque_utile(c):
                    img = composition.avec_masque(img, c.masque)
                res.append(Calque(c.nom, img, visible=c.visible, opacite=c.opacite, verrou=c.verrou, dans=dans))
                continue
            if n.enfants is not None:
                if garder_groupes and (garder_masques or not composition.masque_utile(c)):
                    g = replace(c, image=image_vide(w, h), style=None, dans=dans)
                    if not garder_masques:
                        g = replace(g, masque=None)       # masque désactivé : sans effet
                    res.extend(figer(n.enfants, c.ident))
                    res.append(g)
                else:
                    img = composition._composer(n.enfants, w, h, True)
                    if composition.masque_utile(c):
                        img = composition.avec_masque(img, c.masque)
                    res.append(Calque(c.nom, img, visible=c.visible, opacite=c.opacite, verrou=c.verrou,
                                      mode=c.mode if garder_modes else "normal", dans=dans))
                continue
            a_style = c.style is not None and not c.style.vide()
            if garder_masques and c.masque is not None:
                img = c.image if not a_style else _rendre_sans_masque(c)
                res.append(replace(c, image=img, style=None, dans=dans))
            else:
                img = rendre_calque(c) if (a_style or composition.masque_utile(c)) else c.image
                res.append(replace(c, image=img, style=None, masque=None, dans=dans))
            if not garder_modes:
                res[-1] = replace(res[-1], mode="normal")
        return res
    return figer(noeuds, None)


def _rendre_sans_masque(c) -> QImage:
    from .styles import rendre_style
    return rendre_style(c.image, c.style)


def _styles_a_l_echelle(calques, k: float) -> list:
    return [replace(c, style=c.style.mis_a_l_echelle(k)) if c.style is not None else c for c in calques]


def _avec_masque_transforme(c: "Calque", fonction) -> "Calque":
    """Même transformation sur le masque du calque que sur ses pixels."""
    if c.masque is None:
        return c
    return replace(c, masque=masque_transforme(c.masque, fonction))


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
            calques = [Calque.depuis(tr("Arrière-plan"), image)]
        self.calques: tuple[Calque, ...] = tuple(calques)
        self.actif = len(self.calques) - 1
        w, h = self.taille()
        self.selection = nouvelle_selection(w, h)
        self.chemin = chemin
        self.exif = exif
        self.icc = icc
        self.modifie = False
        self.remarques: list[str] = []      # à montrer après l'ouverture (ex. effets d'un PSD non repris)
        self._fusion: QImage | None = None
        self.cible_masque = False           # outils de peinture sur le masque du calque choisi (panneau)

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
        if chemin.suffix.lower() == ".psd":
            from .psd import lire_psd
            calques, icc, remarques = lire_psd(chemin)
            doc = cls(chemin=chemin, calques=calques, icc=icc)
            doc.remarques = remarques
            return doc
        if chemin.suffix.lower() in EXTENSIONS_CALQUES:
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
        if ext == ".psd":
            from .psd import ecrire_psd
            ecrire_psd(chemin, calques_figes(self.calques, garder_groupes=True, garder_masques=True),
                       self.image, self.icc)
            self.chemin = chemin
            self.modifie = False
            return
        if ext in EXTENSIONS_CALQUES:
            natif = ext == ".chr"           # .chr : styles modifiables ; .ora (Krita, GIMP) : effets figés
            ecrire_ora(chemin, self.calques if natif else calques_figes(self.calques, garder_groupes=True),
                       self.image, natif=natif)
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
            raise ValueError(tr("Format non pris en charge : {ext}", ext=ext))
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

    def apercu_calque(self, index: int, image: QImage, texte: Texte | None = None) -> None:
        """Remplace l'image d'un calque sans entrée dans Annuler (aperçu pendant un coup de gomme ou un
        déplacement de texte). Sans `texte`, un calque de texte devient un calque d'image (pixels)."""
        calques = list(self.calques)
        calques[index] = replace(calques[index], image=image, texte=texte)
        self.calques = tuple(calques)
        self._fusion = None
        self.change.emit()

    def apercu_masque(self, index: int, m: QImage) -> None:
        """Masque modifié pendant un coup de pinceau (sans entrée dans Annuler)."""
        calques = list(self.calques)
        calques[index] = replace(calques[index], masque=m)
        self.calques = tuple(calques)
        self._fusion = None
        self.change.emit()

    def apercu_style(self, index: int, style) -> None:
        """Style essayé (fenêtre Style du calque), sans entrée dans Annuler."""
        calques = list(self.calques)
        calques[index] = replace(calques[index], style=style)
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
            if c.texte is not None:                    # texte : redessiné à sa nouvelle place
                t = c.texte.deplace(dx, dy)
                nouveaux.append(replace(c, image=rendre(t, W, H), texte=t))
                continue
            img = image_vide(W, H)
            p = QPainter(img)
            p.drawImage(QPoint(dx, dy), c.image)
            p.end()
            nouveaux.append(replace(c, image=img))
        def poser(img):
            res = image_vide(W, H)
            p = QPainter(res)
            p.drawImage(QPoint(dx, dy), img)
            p.end()
            return res
        nouveaux = [_avec_masque_transforme(c, poser) for c in nouveaux]
        base = fusionner(nouveaux, W, H)
        calque = calque_des_changements(self.nom_libre(titre), resultat, base)
        return self.etat_avec(tuple(nouveaux) + (calque,), len(nouveaux))

    def etat_redimensionne(self, titre: str, resultat: QImage):
        """Upscale : tous les calques sont agrandis (lissage) ; le résultat de l'IA, complet, va en haut."""
        W, H = resultat.width(), resultat.height()
        w, h = self.taille()
        nouveaux = []
        for c in self.calques:
            if c.texte is not None:                    # texte : redessiné net à la nouvelle taille
                t = c.texte.mis_a_l_echelle(W / w, H / h)
                nouveaux.append(replace(c, image=rendre(t, W, H), texte=t))
            else:
                nouveaux.append(replace(c, image=c.image.scaled(W, H, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)))
        nouveaux = _styles_a_l_echelle(nouveaux, ((W / w) * (H / h)) ** 0.5)
        nouveaux = [_avec_masque_transforme(c, lambda im: im.scaled(W, H, Qt.IgnoreAspectRatio,
                                                                     Qt.SmoothTransformation)) for c in nouveaux]
        calque = Calque.depuis(self.nom_libre(titre), resultat)
        return self.etat_avec(tuple(nouveaux) + (calque,), len(nouveaux))

    def etat_recadre(self, r: QRect):
        """Recadrer : chaque calque (et la sélection) ne garde que le rectangle r ; les textes restent des textes."""
        r = r.intersected(QRect(0, 0, *self.taille()))
        W, H = r.width(), r.height()
        nouveaux = []
        for c in self.calques:
            if c.texte is not None:
                t = c.texte.deplace(-r.x(), -r.y())
                nouveaux.append(replace(c, image=rendre(t, W, H), texte=t))
            else:
                nouveaux.append(replace(c, image=c.image.copy(r)))
        nouveaux = [_avec_masque_transforme(c, lambda im: im.copy(r)) for c in nouveaux]
        return self.etat_avec(tuple(nouveaux), self.actif, self.selection.copy(r))

    # ---------------------------------------------------------- géométrie de toute l'image
    def etat_geometrie(self, transfo: QTransform, W: int, H: int, tourne: float | None, lisse: bool = True):
        """Chaque calque (et la sélection) redessiné par `transfo` sur une toile W × H. Les textes restent des
        textes s'ils sont seulement tournés (`tourne` = degrés ajoutés à leur angle) ; retournés en miroir
        (`tourne` None), ils deviennent des images."""
        nouveaux = []
        for c in self.calques:
            if c.texte is not None and tourne is not None:
                pt = transfo.map(QPointF(c.texte.x, c.texte.y))
                t = replace(c.texte, x=pt.x(), y=pt.y(), angle=(c.texte.angle + tourne + 180) % 360 - 180)
                nouveaux.append(replace(c, image=rendre(t, W, H), texte=t))
            else:
                nouveaux.append(replace(c, image=_transformee(c.image, transfo, W, H, lisse), texte=None))
        nouveaux = [_avec_masque_transforme(c, lambda im: _transformee(im, transfo, W, H, lisse)) for c in nouveaux]
        sel = _transformee(self.selection, transfo, W, H, lisse)
        return self.etat_avec(tuple(nouveaux), self.actif, sel)

    def etat_pivote(self, sens: int):
        """sens : 90 (horaire), -90 (antihoraire) ou 180."""
        w, h = self.taille()
        if sens == 90:
            return self.etat_geometrie(QTransform().translate(h, 0).rotate(90), h, w, 90, False)
        if sens == -90:
            return self.etat_geometrie(QTransform().translate(0, w).rotate(-90), h, w, -90, False)
        return self.etat_geometrie(QTransform().translate(w, h).rotate(180), w, h, 180, False)

    def etat_miroir(self, horizontal: bool):
        w, h = self.taille()
        t = QTransform(-1, 0, 0, 1, w, 0) if horizontal else QTransform(1, 0, 0, -1, 0, h)
        return self.etat_geometrie(t, w, h, None, False)

    def etat_redresse(self, angle: float, recadrer: bool = True):
        """Tourne de `angle` degrés autour du centre. recadrer : garde le plus grand rectangle sans coin vide (mêmes
        proportions) ; sinon la toile s'agrandit et les coins sont transparents."""
        w, h = self.taille()
        W, H = taille_redressee(w, h, angle, recadrer)
        t = QTransform().translate(W / 2, H / 2).rotate(angle).translate(-w / 2, -h / 2)
        return self.etat_geometrie(t, W, H, angle)

    def etat_taille(self, W: int, H: int):
        """Change la taille de l'image (sans IA) : calques rééchantillonnés (Lanczos), textes redessinés nets."""
        w, h = self.taille()
        nouveaux = []
        for c in self.calques:
            if c.texte is not None:
                t = c.texte.mis_a_l_echelle(W / w, H / h)
                nouveaux.append(replace(c, image=rendre(t, W, H), texte=t))
            else:
                im = qimage_vers_pil(c.image).resize((W, H), Image.LANCZOS)
                nouveaux.append(replace(c, image=pil_vers_qimage(im).convertToFormat(FORMAT_CALQUE)))
        nouveaux = _styles_a_l_echelle(nouveaux, ((W / w) * (H / h)) ** 0.5)
        nouveaux = [replace(c, masque=c.masque.scaled(W, H, Qt.IgnoreAspectRatio, Qt.SmoothTransformation))
                    if c.masque is not None else c for c in nouveaux]
        sel = self.selection.scaled(W, H, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        return self.etat_avec(tuple(nouveaux), self.actif, sel.convertToFormat(FORMAT_SELECTION))

    # ---------------------------------------------------------- sélection : agrandir, réduire, adoucir
    def selection_modifiee(self, mode: str, px: float) -> QImage:
        """Nouvelle sélection : « agrandir » / « reduire » de px pixels (bord arrondi), ou « adoucir » (flou de px)."""
        m = Image.fromarray(masque(self.selection), "L")
        if px <= 0:
            return self.selection.copy()
        if mode == "adoucir":
            m = m.filter(ImageFilter.GaussianBlur(px / 2))
        else:
            # un flou gaussien de rayon σ dépasse 2 % à 2,05 σ du bord : seuil bas = agrandir, haut = réduire
            flou = np.asarray(m.filter(ImageFilter.GaussianBlur(px / 2.05)))
            dur = flou > 5 if mode == "agrandir" else flou >= 250
            m = Image.fromarray((dur * 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(0.7))
        return _masque_vers_selection(np.asarray(m)).convertToFormat(FORMAT_SELECTION)

    def rect_selection(self) -> QRect | None:
        """Plus petit rectangle qui contient la sélection, ou None si elle est vide."""
        m = masque(self.selection) > 0
        if not m.any():
            return None
        ys, xs = np.nonzero(m)
        return QRect(int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1))

    def pixels_choisis(self) -> tuple[QImage, QPoint]:
        """Copier : pixels du calque choisi dans la sélection (tout le calque si rien n'est sélectionné), réduits au
        rectangle qui les contient, et la place de ce rectangle dans l'image."""
        img = self.calque_actif.image.copy()
        r = self.rect_selection()
        if r is None:
            r = QRect(0, 0, *self.taille())
        else:
            p = QPainter(img)
            p.setCompositionMode(QPainter.CompositionMode_DestinationIn)
            p.drawImage(0, 0, self.selection)
            p.end()
        return img.copy(r), r.topLeft()

    def etat_effacer_selection(self):
        """Supprimer : les pixels sélectionnés du calque choisi deviennent transparents (un texte devient une
        image). None si rien n'est sélectionné ou si le calque est verrouillé."""
        if self.selection_vide() or self.calque_actif.verrou:
            return None
        img = self.calque_actif.image.copy()
        p = QPainter(img)
        p.setCompositionMode(QPainter.CompositionMode_DestinationOut)
        p.drawImage(0, 0, self.selection)
        p.end()
        return self.etat_calque_modifie(self.actif, image=img, texte=None)

    def etat_coller(self, img: QImage, place: QPoint | None = None):
        """Coller : nouveau calque au-dessus du calque choisi, l'image à sa place d'origine (copiée dans Chrypix)
        ou au centre (venue d'ailleurs). La sélection est vidée."""
        w, h = self.taille()
        if place is None:
            place = QPoint((w - img.width()) // 2, (h - img.height()) // 2)
        fond = image_vide(w, h)
        p = QPainter(fond)
        p.drawImage(place, img)
        p.end()
        return self.inserer(Calque(self.nom_libre(tr("Collage")), fond), selection=nouvelle_selection(w, h))

    def etat_calque_modifie(self, index: int, **changements):
        calques = list(self.calques)
        calques[index] = replace(calques[index], **changements)
        return self.etat_avec(calques)

    def etat_nouveau_texte(self, t: Texte):
        """Nouveau calque de texte au-dessus du calque choisi."""
        w, h = self.taille()
        return self.inserer(Calque(nom_calque(t, tr("Texte")), rendre(t, w, h), texte=t))

    def etat_texte_modifie(self, index: int, t: Texte):
        """Texte modifié : redessiné ; le nom suit le texte tant qu'il n'a pas été renommé à la main."""
        c = self.calques[index]
        w, h = self.taille()
        nom = c.nom
        if c.texte is not None and c.nom == nom_calque(c.texte, tr("Texte")):
            nom = nom_calque(t, tr("Texte"))
        calques = list(self.calques)
        calques[index] = replace(c, nom=nom, image=rendre(t, w, h), texte=t)
        return self.etat_avec(calques)

    def etat_en_pixels(self, index: int):
        """Le calque de texte devient un calque d'image ordinaire (le texte n'est plus modifiable)."""
        return self.etat_calque_modifie(index, texte=None)

    def place_nouveau(self) -> tuple[int, str | None]:
        """Où poser un nouveau calque : au-dessus du calque choisi, dans son groupe (ou en haut du groupe choisi
        s'il est ouvert). -> (index d'insertion, groupe)."""
        c = self.calque_actif
        if c.groupe and c.ouvert:
            return self.actif, c.ident
        return self.actif + 1, c.dans

    def inserer(self, c: "Calque", **kw):
        """État avec le calque c ajouté à la place d'un nouveau calque."""
        pos, dans = self.place_nouveau()
        calques = list(self.calques)
        calques.insert(pos, replace(c, dans=dans))
        return self.etat_avec(calques, pos, **kw)

    def etat_nouveau_calque(self, image: QImage | None = None, nom: str | None = None):
        w, h = self.taille()
        img = image_vide(w, h) if image is None else image.convertToFormat(FORMAT_CALQUE)
        return self.inserer(Calque(self.nom_libre(nom or tr("Calque")), img))

    def etat_dupliquer(self):
        c = self.calque_actif
        bloc = composition.descendants(self.calques, self.actif) + [self.actif]
        idents = {self.calques[i].ident: nouvel_ident() for i in bloc if self.calques[i].groupe}
        copies = []
        for i in bloc:
            x = self.calques[i]
            copies.append(replace(x, image=QImage(x.image), ident=idents.get(x.ident, x.ident),
                                  dans=idents.get(x.dans, x.dans) if i != self.actif else x.dans))
        copies[-1] = replace(copies[-1], nom=tr("{nom} (copie)", nom=c.nom))
        calques = list(self.calques)
        calques[self.actif + 1:self.actif + 1] = copies
        return self.etat_avec(calques, self.actif + len(copies))

    def etat_supprimer(self):
        enlever = set(composition.descendants(self.calques, self.actif)) | {self.actif}
        if len(self.calques) - len(enlever) < 1 or any(self.calques[i].verrou for i in enlever):
            return None
        calques = [c for i, c in enumerate(self.calques) if i not in enlever]
        return self.etat_avec(calques, max(0, min(enlever) - 1))

    def etat_deplacer(self, depuis: int, vers: int):
        """Monte (vers > depuis) ou descend le calque d'une place. Dans un groupe, il en sort par le haut ou le
        bas ; contre un groupe ouvert, il y entre. Un groupe se déplace avec tous ses calques."""
        if depuis == vers or not (0 <= depuis < len(self.calques)):
            return None
        sens = 1 if vers > depuis else -1
        cible = self.calques[depuis]
        racine = arbre(self.calques)

        def chercher(liste, parent):
            for k, n in enumerate(liste):
                if n.calque is cible:
                    return liste, k, parent
                if n.enfants is not None:
                    r = chercher(n.enfants, (liste, k))
                    if r:
                        return r
            return None
        trouve = chercher(racine, None)
        if trouve is None:
            return None
        liste, k, parent = trouve
        n = liste[k]
        voisin = k + sens
        if 0 <= voisin < len(liste):
            v = liste[voisin]
            if v.enfants is not None and v.calque.ouvert:
                del liste[k]
                if sens > 0:
                    v.enfants.insert(0, n)
                else:
                    v.enfants.append(n)
            else:
                liste[k], liste[voisin] = v, n
        elif parent is not None:                          # sort du groupe
            pliste, pk = parent
            del liste[k]
            pliste.insert(pk + 1 if sens > 0 else pk, n)
        else:
            return None
        calques = composition.a_plat(racine)
        actif = next(i for i, c in enumerate(calques) if c.image is cible.image and c.nom == cible.nom
                     and c.ident == cible.ident)
        return self.etat_avec(calques, actif)

    # ---------------------------------------------------------- groupes, masques, réglages
    def etat_grouper(self):
        """Met le calque choisi (avec ses calques si c'est un groupe) dans un nouveau groupe (Ctrl+G)."""
        c = self.calque_actif
        w, h = self.taille()
        g = Calque(self.nom_libre(tr("Groupe")), image_vide(w, h), groupe=True, ident=nouvel_ident(), dans=c.dans)
        calques = list(self.calques)
        calques[self.actif] = replace(c, dans=g.ident)
        calques.insert(self.actif + 1, g)
        return self.etat_avec(calques, self.actif + 1)

    def etat_degrouper(self):
        """Défait le groupe choisi : ses calques restent à leur place (Ctrl+Maj+G)."""
        c = self.calque_actif
        if not c.groupe or c.verrou:
            return None
        calques = [replace(x, dans=c.dans) if x.dans == c.ident else x for x in self.calques]
        del calques[self.actif]
        return self.etat_avec(calques, max(0, self.actif - 1))

    def etat_nouveau_groupe(self):
        """Groupe vide au-dessus du calque choisi (dans le groupe choisi s'il est ouvert)."""
        w, h = self.taille()
        return self.inserer(Calque(self.nom_libre(tr("Groupe")), image_vide(w, h), groupe=True, ident=nouvel_ident()))

    def etat_ajouter_masque(self, quoi: str = "blanc"):
        """quoi : « blanc » (tout visible), « selection » (seule la sélection visible) ou « cacher_selection »."""
        c = self.calque_actif
        if c.masque is not None or c.verrou:
            return None
        w, h = self.taille()
        if quoi == "blanc" or self.selection_vide():
            m = masque_plein(w, h, 255)
        else:
            a = masque(self.selection)
            m = masque_depuis(a if quoi == "selection" else 255 - a)
        return self.etat_calque_modifie(self.actif, masque=m, masque_actif=True)

    def etat_appliquer_masque(self):
        """Le masque passe dans les pixels (le calque garde son aspect)."""
        c = self.calque_actif
        if c.masque is None or c.special or c.verrou:
            return None
        img = composition.avec_masque(c.image, c.masque) if c.masque_actif else c.image
        return self.etat_calque_modifie(self.actif, image=img, masque=None, texte=None)

    def etat_nouveau_reglage(self, type_: str, params: dict, nom: str):
        """Calque de réglage au-dessus du calque choisi ; la sélection, s'il y en a une, devient son masque."""
        w, h = self.taille()
        m = None if self.selection_vide() else masque_depuis(masque(self.selection))
        return self.inserer(Calque(self.nom_libre(nom), image_vide(w, h), reglage={"type": type_, "params": params},
                                   masque=m))

    def etat_fusionner_bas(self):
        if self.actif == 0 or self.calque_actif.verrou or self.calques[self.actif - 1].verrou:
            return None
        w, h = self.taille()
        dessous, dessus = self.calques[self.actif - 1], self.calque_actif
        if dessous.special or dessus.special or dessous.dans != dessus.dans:
            return None
        img = fusionner([replace(dessous, opacite=1.0, visible=True, dans=None, mode="normal"),
                         replace(dessus, dans=None)], w, h)
        fusion = replace(dessous, image=img, texte=None, style=None, masque=None)   # effets et masques : pixels
        calques = list(self.calques)
        calques[self.actif - 1:self.actif + 1] = [fusion]
        return self.etat_avec(calques, self.actif - 1)

    def etat_aplatir(self):
        if len(self.calques) <= 1 or any(c.verrou for c in self.calques):
            return None
        w, h = self.taille()
        return self.etat_avec([Calque(tr("Arrière-plan"), fusionner(self.calques, w, h))], 0)

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
# Le format de Chrypix (.chr) est le même, avec en plus les réglages des textes (attribut chrypix-texte) :
# un .chr renommé en .ora s'ouvre donc aussi dans Krita ou GIMP (les textes y sont des images).
def taille_redressee(w: int, h: int, angle: float, recadrer: bool) -> tuple[int, int]:
    import math
    a = math.radians(abs(angle))
    c, s = math.cos(a), math.sin(a)
    if recadrer:      # plus grand rectangle de mêmes proportions dans la photo tournée
        k = min(w / (w * c + h * s), h / (w * s + h * c))
        return max(1, int(w * k)), max(1, int(h * k))
    return max(1, math.ceil(w * c + h * s - 1e-6)), max(1, math.ceil(w * s + h * c - 1e-6))


def _transformee(img: QImage, transfo: QTransform, W: int, H: int, lisse: bool = True) -> QImage:
    res = QImage(W, H, img.format())
    res.fill(0)
    p = QPainter(res)
    p.setRenderHint(QPainter.SmoothPixmapTransform, lisse)
    p.setRenderHint(QPainter.Antialiasing, lisse)
    p.setTransform(transfo)
    p.drawImage(0, 0, img)
    p.end()
    return res


def _masque_vers_selection(a: np.ndarray) -> QImage:
    """Masque 0..255 -> image de sélection (rouge, transparence = masque)."""
    sel = np.zeros(a.shape + (4,), np.uint8)
    sel[..., 0] = (a.astype(np.uint16) * COULEUR_SELECTION.red() // 255).astype(np.uint8)
    sel[..., 1] = (a.astype(np.uint16) * COULEUR_SELECTION.green() // 255).astype(np.uint8)
    sel[..., 2] = (a.astype(np.uint16) * COULEUR_SELECTION.blue() // 255).astype(np.uint8)
    sel[..., 3] = a
    h, w = a.shape
    return QImage(np.ascontiguousarray(sel).data, w, h, w * 4, QImage.Format_RGBA8888_Premultiplied).copy()


def _png(img: QImage) -> bytes:
    tampon = io.BytesIO()
    qimage_vers_pil(img).save(tampon, "PNG", compress_level=6)
    return tampon.getvalue()


def ecrire_ora(chemin: Path, calques, fusion: QImage, natif: bool = False) -> None:
    """Groupes = piles imbriquées, modes de fusion = composite-op (lus par Krita et GIMP). En .chr (natif) :
    masques, calques de réglage, styles et textes gardés en attributs « chrypix-… »."""
    w, h = calques[0].image.width(), calques[0].image.height()
    pile = ET.Element("image", w=str(w), h=str(h), version="0.0.5")
    racine = ET.SubElement(pile, "stack")
    temporaire = chemin.with_name(chemin.name + ".tmp")
    compte = [0]
    with zipfile.ZipFile(temporaire, "w") as z:
        z.writestr(zipfile.ZipInfo("mimetype"), "image/openraster", compress_type=zipfile.ZIP_STORED)

        def attributs(c) -> dict:
            a = {"name": c.nom, "opacity": f"{c.opacite:.3f}", "visibility": "visible" if c.visible else "hidden"}
            if c.mode != "normal":
                a["composite-op"] = MODES.get(c.mode, MODES["normal"])[3]
            if c.verrou:
                a["edit-locked"] = "true"
            if natif:
                if c.texte is not None:
                    a["chrypix-texte"] = json.dumps(c.texte.vers_dict(), ensure_ascii=False)
                if c.style is not None and (c.style.effets or c.style.remplissage < 1):
                    a["chrypix-style"] = c.style.vers_json()
                if c.reglage is not None:
                    a["chrypix-reglage"] = json.dumps(c.reglage, ensure_ascii=False)
                if c.masque is not None:
                    compte[0] += 1
                    src = f"data/masque{compte[0]}.png"
                    tampon = io.BytesIO()
                    Image.fromarray(masque_tableau(c.masque), "L").save(tampon, "PNG", compress_level=6)
                    z.writestr(src, tampon.getvalue(), compress_type=zipfile.ZIP_STORED)
                    a["chrypix-masque"] = src
                    if not c.masque_actif:
                        a["chrypix-masque-inactif"] = "true"
                if c.groupe and not c.ouvert:
                    a["chrypix-ferme"] = "true"
            return a

        def ecrire(noeuds, parent):
            for n in reversed(noeuds):                         # stack.xml : du haut vers le bas
                c = n.calque
                if n.enfants is not None:
                    s = ET.SubElement(parent, "stack", isolation="isolate", **attributs(c))
                    ecrire(n.enfants, s)
                    continue
                compte[0] += 1
                nom_png = f"data/calque{compte[0]}.png"
                z.writestr(nom_png, _png(c.image), compress_type=zipfile.ZIP_STORED)
                ET.SubElement(parent, "layer", src=nom_png, x="0", y="0", **attributs(c))
        ecrire(arbre(calques), racine)
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

        def json_ou_rien(texte, lire):
            if not texte:
                return None
            try:
                return lire(texte)
            except (ValueError, TypeError, KeyError):
                return None                                  # réglages illisibles : on garde l'image

        def commun(e) -> dict:
            kw = dict(visible=e.get("visibility", "visible") != "hidden", opacite=float(e.get("opacity", 1)),
                      verrou=e.get("edit-locked", "false") == "true",
                      mode=MODE_ORA.get(e.get("composite-op", "svg:src-over"), "normal"))
            src = e.get("chrypix-masque")
            if src:
                try:
                    with Image.open(io.BytesIO(z.read(src))) as im:
                        a = np.asarray(im.convert("L"))
                    if a.shape == (h, w):
                        kw["masque"] = masque_depuis(a)
                        kw["masque_actif"] = e.get("chrypix-masque-inactif") != "true"
                except (KeyError, OSError):
                    pass
            return kw

        def lire(element, dans) -> list:
            res = []
            for e in element:                                  # du haut vers le bas
                if e.tag == "stack":
                    ident = nouvel_ident()
                    enfants = lire(e, ident)
                    g = Calque(e.get("name") or tr("Groupe"), image_vide(w, h), groupe=True, ident=ident, dans=dans,
                               ouvert=e.get("chrypix-ferme") != "true", **commun(e))
                    res.append(g)
                    res.extend(enfants)
                elif e.tag == "layer":
                    with Image.open(io.BytesIO(z.read(e.get("src")))) as im:
                        morceau = pil_vers_qimage(im)
                    img = image_vide(w, h)
                    p = QPainter(img)
                    p.drawImage(QPoint(int(float(e.get("x", 0))), int(float(e.get("y", 0)))), morceau)
                    p.end()
                    texte = json_ou_rien(e.get("chrypix-texte"), lambda t: Texte.depuis_dict(json.loads(t)))
                    style = json_ou_rien(e.get("chrypix-style"), Style.depuis_json)
                    reglage = json_ou_rien(e.get("chrypix-reglage"), json.loads)
                    if reglage is not None and not (isinstance(reglage, dict) and "type" in reglage
                                                    and "params" in reglage):
                        reglage = None
                    res.append(Calque(e.get("name") or tr("Calque"), img, texte=texte, style=style, reglage=reglage,
                                      dans=dans, **commun(e)))
            return res
        pile = racine.find("stack")
        calques = lire(pile if pile is not None else racine, None)
    if not calques:
        raise ValueError(tr("Ce fichier ne contient aucun calque."))
    return list(reversed(calques))
