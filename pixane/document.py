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
from PySide6.QtCore import QObject, QPoint, QPointF, QRect, QRectF, Qt, Signal
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

EXTENSIONS_LECTURE = "*.pixane *.jpg *.jpeg *.png *.tif *.tiff *.webp *.bmp *.ora *.psd"
EXTENSIONS_CALQUES = (".pixane", ".ora", ".psd")    # formats qui gardent les calques


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
    image: QImage                 # FORMAT_CALQUE, taille du document : la partie du calque dans la feuille
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
    # pixels qui dépassent de la feuille (comme Photoshop, rien n'est coupé en déplaçant ou en transformant) : le
    # calque entier, posé en (hors_x, hors_y) ; sa partie dans la feuille est remplacée par `image` (voir
    # image_entiere). None : tout le calque est dans la feuille.
    hors: QImage | None = None
    hors_x: int = 0
    hors_y: int = 0

    @staticmethod
    def depuis(nom: str, image: QImage, **kw) -> "Calque":
        return Calque(nom, image.convertToFormat(FORMAT_CALQUE), **kw)

    @property
    def special(self) -> bool:
        """Groupe ou calque de réglage : pas de pixels à peindre."""
        return self.groupe or self.reglage is not None


def rect_entier(c: Calque) -> QRect:
    """Place du calque entier dans la feuille (plus grand qu'elle si des pixels dépassent)."""
    feuille = QRect(0, 0, c.image.width(), c.image.height())
    if c.hors is None:
        return feuille
    return QRect(c.hors_x, c.hors_y, c.hors.width(), c.hors.height()).united(feuille)


def image_entiere(c: Calque) -> tuple[QImage, int, int]:
    """Le calque entier : sa partie dans la feuille (`image`) et ce qui dépasse (`hors`) -> (image, x, y)."""
    if c.hors is None:
        return c.image, 0, 0
    r = rect_entier(c)
    img = image_vide(r.width(), r.height())
    p = QPainter(img)
    p.drawImage(c.hors_x - r.x(), c.hors_y - r.y(), c.hors)
    p.setCompositionMode(QPainter.CompositionMode_Source)      # dans la feuille : `image` fait foi
    p.drawImage(-r.x(), -r.y(), c.image)
    p.end()
    return img, r.x(), r.y()


def avec_image_entiere(c: Calque, img: QImage, x: int, y: int, W: int, H: int, **changements) -> Calque:
    """Le calque dont l'image entière est `img`, posée en (x, y) : la partie dans la feuille W × H va dans `image`,
    ce qui dépasse est gardé dans `hors` (réduit aux pixels non transparents)."""
    img = img.convertToFormat(FORMAT_CALQUE)
    dedans = image_vide(W, H)
    p = QPainter(dedans)
    p.drawImage(x, y, img)
    p.end()
    hors, hx, hy = None, 0, 0
    feuille = QRect(0, 0, W, H)
    if not feuille.contains(QRect(x, y, img.width(), img.height())):
        ys, xs = np.nonzero(tableau(img)[:, :, 3])
        if len(ys):
            r = QRect(int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1))
            if not feuille.contains(r.translated(x, y)):
                hors, hx, hy = img.copy(r), x + r.x(), y + r.y()
    return replace(c, image=dedans, hors=hors, hors_x=hx, hors_y=hy, **changements)


def _decale(c: Calque, dx: int, dy: int, W: int, H: int) -> Calque:
    """Calque posé, décalé de (dx, dy), sur une feuille W × H (ce qui dépasse est gardé)."""
    img, x, y = image_entiere(c)
    return avec_image_entiere(c, img, x + dx, y + dy, W, H)


def _transforme_entier(c: Calque, transfo: QTransform, W: int, H: int, lisse: bool) -> Calque:
    """Calque entier redessiné par `transfo` sur une feuille W × H (ce qui dépasse est gardé)."""
    img, x, y = image_entiere(c)
    t = QTransform().translate(x, y) * transfo
    r = t.mapRect(QRectF(0, 0, img.width(), img.height())).toAlignedRect()
    res = image_vide(max(1, r.width()), max(1, r.height()))
    p = QPainter(res)
    p.setRenderHint(QPainter.SmoothPixmapTransform, lisse)
    p.setRenderHint(QPainter.Antialiasing, lisse)
    p.setTransform(t * QTransform().translate(-r.x(), -r.y()))
    p.drawImage(0, 0, img)
    p.end()
    return avec_image_entiere(c, res, r.x(), r.y(), W, H, texte=None)


def _mis_a_l_echelle(c: Calque, w: int, h: int, W: int, H: int, lanczos: bool) -> Calque:
    """Calque entier agrandi ou réduit (feuille w × h -> W × H ; ce qui dépasse suit)."""
    img, x, y = image_entiere(c)
    kx, ky = W / w, H / h
    nw, nh = max(1, round(img.width() * kx)), max(1, round(img.height() * ky))
    if lanczos:
        res = pil_vers_qimage(qimage_vers_pil(img).resize((nw, nh), Image.LANCZOS))
    else:
        res = img.scaled(nw, nh, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    return avec_image_entiere(c, res, round(x * kx), round(y * ky), W, H)


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


MARGE_IA = 3.0      # px : le résultat de l'IA déborde à peine de la sélection (fondu doux, pas de « halo »)


def poids_zone(zone: np.ndarray | None, w: int, h: int) -> np.ndarray:
    """(h, w) float32 0..1 : où le résultat de l'IA est gardé. zone : sélection 0..255 au lancement (None : partout).
    La sélection est gardée telle quelle, plus un fondu de quelques pixels autour pour un raccord invisible."""
    if zone is None:
        return np.ones((h, w), np.float32)
    s = zone.astype(np.float32) / 255
    dure = Image.fromarray(((s > 0.5) * 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(MARGE_IA))
    autour = np.clip(np.asarray(dure, np.float32) / 255 * 2, 0, 1)
    return np.maximum(s, autour)


def fond_ia(rgba: np.ndarray) -> int:
    """Fond uni sur lequel l'IA voit les zones transparentes : il doit contraster avec ce qui est dessus (un texte
    blanc sur fond transparent est montré sur du noir, un logo sombre sur du blanc), sinon l'IA ne le voit pas."""
    a = rgba[:, :, 3]
    plein = a > 128
    if a.min() == 255 or not plein.any():
        return 255
    rgb = rgba[:, :, :3][plein].astype(np.float32)
    return 0 if float((rgb @ np.array([0.299, 0.587, 0.114], np.float32)).mean()) > 140 else 255


def a_plat(rgba: np.ndarray, fond: int | None = None) -> np.ndarray:
    """(h, w, 4) RGBA non prémultiplié -> (h, w, 3) RGB posé sur un fond uni (fond_ia par défaut). Sans cela, une
    zone transparente (fond transparent, calque vide) partait en noir sans qu'on le choisisse, et restait noire."""
    fond = fond_ia(rgba) if fond is None else fond
    a = rgba[:, :, 3:4].astype(np.float32) / 255
    return np.clip(rgba[:, :, :3].astype(np.float32) * a + fond * (1 - a) + 0.5, 0, 255).astype(np.uint8)


def _sans_fond(rgb: np.ndarray, alpha: np.ndarray, fond: int, orig: np.ndarray) -> np.ndarray:
    """Retire le fond uni des pixels à moitié transparents (bords) : sinon un bord garderait un peu de ce fond.
    Plus le pixel est transparent, plus on garde sa couleur d'origine (orig) : aucun liseré sombre ou clair."""
    a = alpha.astype(np.float32)[..., None] / 255
    partiel = a < 1
    vrai = np.clip((rgb.astype(np.float32) - fond * (1 - a)) / np.maximum(a, 0.03), 0, 255)
    melange = vrai * a * a + orig.astype(np.float32) * (1 - a * a)
    return np.where(partiel, np.clip(melange + 0.5, 0, 255), rgb).astype(np.uint8)


def vue_ia(resultat: QImage, base: QImage) -> QImage:
    """Résultat de l'IA tel qu'il sera posé : avec la transparence de l'image (pour la fenêtre de choix)."""
    b = tableau(base.convertToFormat(FORMAT_IMAGE))
    if b[:, :, 3].min() == 255:
        return resultat
    W, H = resultat.width(), resultat.height()
    alpha = b[:, :, 3]
    if (W, H) != (base.width(), base.height()):        # Upscale : transparence agrandie comme le résultat
        alpha = np.asarray(Image.fromarray(alpha, "L").resize((W, H), Image.BICUBIC))
    r = tableau(resultat.convertToFormat(FORMAT_IMAGE)).copy()
    orig = b[:, :, :3]
    if (W, H) != (base.width(), base.height()):
        orig = np.asarray(Image.fromarray(np.ascontiguousarray(orig), "RGB").resize((W, H), Image.BICUBIC))
    r[:, :, :3] = _sans_fond(r[:, :, :3], alpha, fond_ia(b), orig)
    r[:, :, 3] = alpha
    return qimage_rgba(r)


def _image_ia(resultat: QImage, base: QImage, poids: np.ndarray, opacite: np.ndarray | None = None) -> QImage:
    """Résultat de l'IA, transparent là où il ne change rien ou hors de la zone (alpha = poids). opacite (0..1) :
    là où l'image était transparente, le résultat l'est aussi (par défaut : l'opacité de base)."""
    r = tableau(resultat.convertToFormat(FORMAT_IMAGE)).copy()
    b = tableau(base.convertToFormat(FORMAT_IMAGE))
    if opacite is None:
        opacite = b[:, :, 3].astype(np.float32) / 255
    fond = fond_ia(b)
    # changé : autre couleur, ou plus opaque qu'avant (ex. l'ajout d'Agrandir, même tout blanc)
    change = np.any(r[:, :, :3] != a_plat(b, fond), axis=2) | (opacite * 255 > b[:, :, 3] + 0.5)
    r[:, :, :3] = _sans_fond(r[:, :, :3], np.where(opacite * 255 > b[:, :, 3] + 0.5, 255, b[:, :, 3]), fond,
                             b[:, :, :3])
    r[:, :, 3] = np.where(change, np.clip(poids * opacite * 255 + 0.5, 0, 255), 0).astype(np.uint8)
    return qimage_rgba(r)


def peut_recevoir_ia(c) -> bool:
    """Calque où l'on peut poser directement le résultat de l'IA (calque d'image visible, modifiable)."""
    return c.visible and not c.verrou and not c.special and c.texte is None


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
        self.suffixe_nom: str | None = None   # ajouté au nom proposé à l'enregistrement (ex. « _restauree »)
        self.exif = exif
        self.icc = icc
        self.modifie = False
        self.remarques: list[str] = []      # à montrer après l'ouverture (ex. effets d'un PSD non repris)
        self._fusion: QImage | None = None
        self.cible_masque = False           # outils de peinture sur le masque du calque choisi (panneau)
        self.reperes: list = []              # repères : (« h » ou « v », position en pixels) ; hors Annuler
        self.dpi: float = 72.0               # résolution (points par pouce), gardée dans les fichiers
        self.mode: str = "rvb"               # « rvb » ou « gris » (niveaux de gris : l'image vue et enregistrée)
        self.nom: str | None = None          # nom d'une image nouvelle, pas encore enregistrée
        self.epreuve: tuple | None = None    # (profil CMJN, intention) : aperçu « comme à l'impression » à l'écran
        self._apercu: tuple | None = None    # (clé, image) de l'aperçu d'impression

    # ---------------------------------------------------------- image fusionnée
    def taille(self) -> tuple[int, int]:
        img = self.calques[0].image
        return img.width(), img.height()

    @property
    def image(self) -> QImage:
        if self._fusion is None:
            w, h = self.taille()
            self._fusion = fusionner(self.calques, w, h).convertToFormat(FORMAT_IMAGE)
            if self.mode == "gris":
                self._fusion = en_gris(self._fusion)
        return self._fusion

    def image_affichee(self) -> QImage:
        """Image montrée à l'écran : avec l'aperçu d'impression (CMJN) s'il est allumé."""
        img = self.image
        if not self.epreuve:
            return img
        cle = (img.cacheKey(), self.epreuve)
        if self._apercu is None or self._apercu[0] != cle:
            from .impression import apercu_impression
            self._apercu = (cle, apercu_impression(img, *self.epreuve))
        return self._apercu[1]

    def nom_affiche(self) -> str:
        return self.chemin.name if self.chemin else (self.nom or tr("sans titre"))

    def changer_mode(self, mode: str) -> None:
        """RVB ou niveaux de gris (les calques ne sont pas touchés : seule l'image fusionnée passe en gris)."""
        if mode != self.mode:
            self.mode = mode
            self._fusion = None
            self.modifie = True
            self.change.emit()

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
            from .psd import lire_resolution_psd
            doc.dpi = lire_resolution_psd(chemin) or 72.0
            return doc
        if chemin.suffix.lower() in EXTENSIONS_CALQUES:
            doc = cls(chemin=chemin, calques=lire_ora(chemin))
            infos = lire_infos_ora(chemin)
            doc.reperes, doc.dpi, doc.mode = infos["reperes"], infos["dpi"], infos["mode"]
            return doc
        with Image.open(chemin) as im:
            exif = im.info.get("exif")
            icc = im.info.get("icc_profile")
            gris = im.mode in ("L", "LA", "I;16", "I;16B", "I", "F", "1")
            dpi = _dpi_pil(im.info.get("dpi"))
            im = ImageOps.exif_transpose(im)  # remet la photo dans le bon sens
            if im.mode in ("I;16", "I;16B", "I", "F"):
                im = im.point(lambda v: v / 256).convert("L")
            qimg = pil_vers_qimage(im)
        doc = cls(qimg, chemin, exif, icc)
        doc.dpi = dpi
        doc.mode = "gris" if gris else "rvb"
        return doc

    def enregistrer(self, chemin: str | Path) -> None:
        chemin = Path(chemin)
        ext = chemin.suffix.lower()
        if ext == ".psd":
            from .psd import ecrire_psd
            ecrire_psd(chemin, calques_figes(self.calques, garder_groupes=True, garder_masques=True),
                       self.image, self.icc, dpi=self.dpi)
            self.chemin = chemin
            self.modifie = False
            return
        if ext in EXTENSIONS_CALQUES:
            natif = ext == ".pixane"            # .pixane : styles modifiables ; .ora (Krita, GIMP) : effets figés
            ecrire_ora(chemin, self.calques if natif else calques_figes(self.calques, garder_groupes=True),
                       self.image, natif=natif, reperes=self.reperes, dpi=self.dpi, mode=self.mode)
            self.chemin = chemin
            self.modifie = False
            return
        self.exporter(chemin)
        self.chemin = chemin
        self.modifie = False

    def exporter(self, chemin: str | Path, qualite: int = 95) -> None:
        """Image à plat (JPEG, PNG, TIFF, WebP, BMP), pleine taille, avec résolution, profil de couleur et EXIF.
        Le document ne change pas (ni son fichier, ni « modifié ») : c'est une copie (Fichier > Exporter sous)."""
        chemin = Path(chemin)
        ext = chemin.suffix.lower()
        im = qimage_vers_pil(self.image)
        opaque = bool(np.all(np.asarray(im)[:, :, 3] == 255))
        options = {}
        if self.icc and self.mode != "gris":
            options["icc_profile"] = self.icc
        if ext != ".webp":
            options["dpi"] = (self.dpi, self.dpi)
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
            options.update(quality=qualite, subsampling=0 if qualite >= 90 else 2)
        elif ext == ".webp":
            options.update(quality=qualite)
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
        if self.mode == "gris":                       # niveaux de gris : enregistré en gris (avec la transparence)
            im = im.convert("LA" if im.mode == "RGBA" and ext in (".png", ".webp") else "L")
            if ext == ".webp":
                im = im.convert("RGBA" if im.mode == "LA" else "RGB")   # WebP n'a pas de gris
        im.save(chemin, **options)

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
    def cible_ia(self, zone: np.ndarray | None) -> int | None:
        """Calque qui reçoit le résultat de l'IA : le calque choisi s'il peut le recevoir. Sans sélection (toute
        l'image), seulement s'il est le seul calque visible avec des pixels (sinon les autres y seraient copiés)."""
        c = self.calque_actif
        if not peut_recevoir_ia(c):
            return None
        if zone is None and any(i != self.actif and k.visible and not k.special and tableau(k.image)[:, :, 3].any()
                                for i, k in enumerate(self.calques)):
            return None
        return self.actif

    def etat_resultat_ia(self, titre: str, resultat: QImage, zone: np.ndarray | None = None,
                         nouveau_calque: bool = True):
        """Résultat de l'IA de même taille, gardé seulement dans la zone (sélection au lancement, plus un fondu de
        quelques px) et là où il change quelque chose. Posé dans le calque choisi, ou dans un nouveau calque en
        haut (nouveau_calque, ou si le calque choisi ne peut pas le recevoir)."""
        w, h = self.taille()
        pose = _image_ia(resultat, self.image, poids_zone(zone, w, h))
        cible = None if nouveau_calque else self.cible_ia(zone)
        if cible is None:
            calque = Calque.depuis(self.nom_libre(titre), pose)
            return self.etat_avec(self.calques + (calque,), len(self.calques))
        img = self.calques[cible].image.convertToFormat(FORMAT_CALQUE)
        p = QPainter(img)
        p.drawImage(0, 0, pose)
        p.end()
        return self.etat_calque_modifie(cible, image=img)


    def contenu(self) -> tuple[int, int, int, int] | None:
        """(x0, y0, x1, y1) de la partie visible de l'image, quand du vide transparent l'entoure (ex. une photo
        carrée collée dans une image plus large) ; None si l'image touche tous les bords (ou est vide)."""
        a = tableau(self.image.convertToFormat(FORMAT_IMAGE))[:, :, 3] > 8
        lignes, colonnes = np.nonzero(a.any(axis=1))[0], np.nonzero(a.any(axis=0))[0]
        if not len(lignes):
            return None
        x0, x1, y0, y1 = int(colonnes[0]), int(colonnes[-1]) + 1, int(lignes[0]), int(lignes[-1]) + 1
        w, h = self.taille()
        if (x0, y0, x1, y1) == (0, 0, w, h) or x1 - x0 < 16 or y1 - y0 < 16:
            return None
        return x0, y0, x1, y1

    def etat_agrandi(self, titre: str, resultat: QImage, decalage: tuple[int, int], nouveau_calque: bool = True,
                     contenu: tuple[int, int, int, int] | None = None):
        """Agrandir : chaque calque est posé, décalé, sur la nouvelle toile ; l'ajout de l'IA (seulement les pixels
        qui diffèrent de la photo d'origine) va dans le calque choisi, ou dans un nouveau calque en haut.
        contenu : partie visible de départ (le vide autour, dans l'ancienne toile, est rempli lui aussi)."""
        W, H = resultat.width(), resultat.height()
        dx, dy = decalage
        nouveaux = []
        for c in self.calques:
            if c.texte is not None:                    # texte : redessiné à sa nouvelle place
                t = c.texte.deplace(dx, dy)
                nouveaux.append(replace(c, image=rendre(t, W, H), texte=t))
                continue
            nouveaux.append(_decale(c, dx, dy, W, H))
        def poser(img):
            res = image_vide(W, H)
            p = QPainter(res)
            p.drawImage(QPoint(dx, dy), img)
            p.end()
            return res
        nouveaux = [_avec_masque_transforme(c, poser) for c in nouveaux]
        base = fusionner(nouveaux, W, H)
        # l'ajout (hors de la photo d'origine) est gardé en entier ; dans la photo, sa transparence est respectée
        x0, y0, x1, y1 = contenu or (0, 0, *self.taille())
        opacite = np.ones((H, W), np.float32)
        b = tableau(base.convertToFormat(FORMAT_IMAGE))[:, :, 3].astype(np.float32) / 255
        opacite[dy + y0:dy + y1, dx + x0:dx + x1] = b[dy + y0:dy + y1, dx + x0:dx + x1]
        pose = _image_ia(resultat, base, np.ones((H, W), np.float32), opacite)
        if not nouveau_calque and peut_recevoir_ia(nouveaux[self.actif]):
            img = nouveaux[self.actif].image.convertToFormat(FORMAT_CALQUE)
            p = QPainter(img)
            p.drawImage(0, 0, pose)
            p.end()
            nouveaux[self.actif] = replace(nouveaux[self.actif], image=img)
            return self.etat_avec(tuple(nouveaux), self.actif)
        calque = Calque.depuis(self.nom_libre(titre), pose)
        return self.etat_avec(tuple(nouveaux) + (calque,), len(nouveaux))

    def etat_redimensionne(self, titre: str, resultat: QImage, nouveau_calque: bool = True):
        """Upscale : tous les calques sont agrandis (lissage) ; le résultat de l'IA, complet, va en haut. Une photo
        d'un seul calque (sans nouveau_calque) : le résultat remplace simplement ce calque."""
        W, H = resultat.width(), resultat.height()
        # transparence de l'image d'origine remise sur le résultat (l'IA ne rend que du RGB)
        if tableau(self.image.convertToFormat(FORMAT_IMAGE))[:, :, 3].min() < 255:
            resultat = vue_ia(resultat, self.image)       # fond montré à l'IA retiré, bords compris
        if not nouveau_calque and len(self.calques) == 1 and peut_recevoir_ia(self.calques[0]) \
                and self.calques[0].masque is None and self.calques[0].style is None and self.calques[0].hors is None:
            c = replace(self.calques[0], image=resultat.convertToFormat(FORMAT_CALQUE))
            return self.etat_avec((c,), 0, nouvelle_selection(W, H))
        w, h = self.taille()
        nouveaux = []
        for c in self.calques:
            if c.texte is not None:                    # texte : redessiné net à la nouvelle taille
                t = c.texte.mis_a_l_echelle(W / w, H / h)
                nouveaux.append(replace(c, image=rendre(t, W, H), texte=t))
            else:
                nouveaux.append(_mis_a_l_echelle(c, w, h, W, H, lanczos=False))
        nouveaux = _styles_a_l_echelle(nouveaux, ((W / w) * (H / h)) ** 0.5)
        nouveaux = [_avec_masque_transforme(c, lambda im: im.scaled(W, H, Qt.IgnoreAspectRatio,
                                                                     Qt.SmoothTransformation)) for c in nouveaux]
        calque = Calque.depuis(self.nom_libre(titre), resultat)
        return self.etat_avec(tuple(nouveaux) + (calque,), len(nouveaux))

    def etat_recadre(self, r: QRect):
        """Recadrer : chaque calque (et la sélection) ne garde que le rectangle r (ce qui dépassait de la feuille est
        supprimé aussi, comme dans Photoshop) ; les textes restent des textes."""
        r = r.intersected(QRect(0, 0, *self.taille()))
        W, H = r.width(), r.height()
        nouveaux = []
        for c in self.calques:
            if c.texte is not None:
                t = c.texte.deplace(-r.x(), -r.y())
                nouveaux.append(replace(c, image=rendre(t, W, H), texte=t))
            else:
                nouveaux.append(replace(c, image=c.image.copy(r), hors=None))
        nouveaux = [_avec_masque_transforme(c, lambda im: im.copy(r)) for c in nouveaux]
        return self.etat_avec(tuple(nouveaux), self.actif, self.selection.copy(r))

    def etat_zone_travail(self, W: int, H: int, dx: int, dy: int, couleur: QColor | None):
        """Taille de la zone de travail : toile W × H, contenu décalé de (dx, dy) (négatif = rogné). La bande ajoutée
        est remplie de `couleur` sur le calque du bas (s'il n'est ni un texte ni un groupe), transparente ailleurs.
        Les pixels qui dépassaient de la feuille réapparaissent s'ils y entrent ; ceux qui en sortent sont gardés."""
        w, h = self.taille()
        nouveaux = []
        for i, c in enumerate(self.calques):
            if c.texte is not None:
                t = c.texte.deplace(dx, dy)
                nouveaux.append(replace(c, image=rendre(t, W, H), texte=t))
                continue
            n = _decale(c, dx, dy, W, H)
            if i == 0 and couleur is not None and couleur.alpha() and not c.groupe and c.reglage is None:
                img = image_vide(W, H)
                img.fill(couleur)
                p = QPainter(img)
                p.drawImage(0, 0, n.image)
                p.setCompositionMode(QPainter.CompositionMode_Source)   # l'ancienne feuille : telle quelle
                ancienne = QRect(dx, dy, w, h).intersected(QRect(0, 0, W, H))
                p.drawImage(ancienne, n.image, ancienne)
                p.end()
                n = replace(n, image=img)
            nouveaux.append(n)
        def poser(im):
            res = QImage(W, H, im.format())
            res.fill(0)
            p = QPainter(res)
            p.drawImage(QPoint(dx, dy), im)
            p.end()
            return res
        nouveaux = [_avec_masque_transforme(c, poser) for c in nouveaux]
        sel = poser(self.selection)
        return self.etat_avec(tuple(nouveaux), self.actif, sel)

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
                nouveaux.append(_transforme_entier(c, transfo, W, H, lisse))
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
        etat = self.etat_geometrie(t, W, H, angle)
        if recadrer:                                   # coins coupés : supprimés (comme Recadrer)
            etat = (tuple(replace(c, hors=None) for c in etat[0]),) + tuple(etat[1:])
        return etat

    def etat_taille(self, W: int, H: int):
        """Change la taille de l'image (sans IA) : calques rééchantillonnés (Lanczos), textes redessinés nets."""
        w, h = self.taille()
        nouveaux = []
        for c in self.calques:
            if c.texte is not None:
                t = c.texte.mis_a_l_echelle(W / w, H / h)
                nouveaux.append(replace(c, image=rendre(t, W, H), texte=t))
            else:
                nouveaux.append(_mis_a_l_echelle(c, w, h, W, H, lanczos=True))
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
        """Coller : nouveau calque au-dessus du calque choisi, l'image à sa place d'origine (copiée dans Pixane)
        ou au centre (venue d'ailleurs). La sélection est vidée."""
        w, h = self.taille()
        if place is None:
            place = QPoint((w - img.width()) // 2, (h - img.height()) // 2)
        c = avec_image_entiere(Calque(self.nom_libre(tr("Collage")), image_vide(w, h)), img, place.x(), place.y(),
                               w, h)
        return self.inserer(c, selection=nouvelle_selection(w, h))

    def etat_calque_entier(self, index: int, img: QImage, x: int, y: int, **changements):
        """Le calque `index` devient `img` posée en (x, y) (ce qui dépasse de la feuille est gardé)."""
        w, h = self.taille()
        calques = list(self.calques)
        calques[index] = avec_image_entiere(calques[index], img, x, y, w, h, **changements)
        return self.etat_avec(calques)

    def apercu_calque_entier(self, index: int, img: QImage, x: int, y: int) -> None:
        """Comme apercu_calque, en gardant ce qui dépasse de la feuille (fin d'un déplacement)."""
        w, h = self.taille()
        calques = list(self.calques)
        calques[index] = avec_image_entiere(calques[index], img, x, y, w, h, texte=None)
        self.calques = tuple(calques)
        self._fusion = None
        self.change.emit()

    def rect_tout(self) -> QRect:
        """Rectangle qui contient la feuille et tous les pixels qui en dépassent."""
        r = QRect(0, 0, *self.taille())
        for c in self.calques:
            r = r.united(rect_entier(c))
        return r

    def etat_tout_faire_apparaitre(self):
        """Image > Tout faire apparaître : la feuille s'agrandit pour montrer tous les pixels qui dépassent.
        None s'il n'y a rien hors de la feuille."""
        r = self.rect_tout()
        if r == QRect(0, 0, *self.taille()):
            return None
        return self.etat_zone_travail(r.width(), r.height(), -r.x(), -r.y(), None)

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

    def etat_fusionner_choisis(self, indexes):
        """Fusionner les calques choisis (Ctrl+clic dans le panneau) en un seul, à la place du plus haut et avec son
        nom. None si moins de deux, ou si l'un est verrouillé, un groupe ou un calque de réglage."""
        idx = sorted(set(i for i in indexes if 0 <= i < len(self.calques)))
        if len(idx) < 2:
            return None
        choisis = [self.calques[i] for i in idx]
        if any(c.verrou or c.special for c in choisis):
            return None
        w, h = self.taille()
        img = fusionner([replace(c, dans=None) for c in choisis], w, h)
        haut = choisis[-1]
        fusion = Calque(haut.nom, img, dans=haut.dans)
        calques = []
        for i, c in enumerate(self.calques):
            if i == idx[-1]:
                calques.append(fusion)
            elif i not in idx:
                calques.append(c)
        return self.etat_avec(calques, idx[-1] - (len(idx) - 1))

    def etat_supprimer_choisis(self, indexes):
        """Supprimer les calques choisis (et le contenu des groupes choisis). None s'il ne resterait aucun calque
        ou si l'un est verrouillé."""
        enlever = set()
        for i in indexes:
            if 0 <= i < len(self.calques):
                enlever |= set(composition.descendants(self.calques, i)) | {i}
        if not enlever or len(self.calques) - len(enlever) < 1 or any(self.calques[i].verrou for i in enlever):
            return None
        calques = [c for i, c in enumerate(self.calques) if i not in enlever]
        reste = [i for i in range(len(self.calques)) if i not in enlever and i < min(enlever)]
        return self.etat_avec(calques, len(reste) - 1 if reste else 0)

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
    def rgb_pour_ia(self) -> np.ndarray:
        """(h, w, 3) : l'image visible telle que l'IA doit la voir (zones transparentes sur du blanc)."""
        return a_plat(tableau(self.image.convertToFormat(FORMAT_IMAGE)))

    def png_pour_ia(self, avec_selection: bool) -> bytes:
        """PNG de l'image visible ; la zone sélectionnée devient transparente (= zone à traiter pour ComfyUI)."""
        rgb = self.rgb_pour_ia()
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
# Le format de Pixane (.pixane) est le même, avec en plus les réglages des textes (attribut pixane-texte) :
# un .pixane renommé en .ora s'ouvre donc aussi dans Krita ou GIMP (les textes y sont des images).
def taille_redressee(w: int, h: int, angle: float, recadrer: bool) -> tuple[int, int]:
    import math
    a = math.radians(abs(angle))
    c, s = abs(math.cos(a)), abs(math.sin(a))      # au-delà de 90° aussi
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


def ecrire_ora(chemin: Path, calques, fusion: QImage, natif: bool = False, reperes=None, dpi: float = 72.0,
               mode: str = "rvb") -> None:
    """Groupes = piles imbriquées, modes de fusion = composite-op (lus par Krita et GIMP). En .pixane (natif) :
    masques, calques de réglage, styles et textes gardés en attributs « pixane-… »."""
    w, h = calques[0].image.width(), calques[0].image.height()
    pile = ET.Element("image", w=str(w), h=str(h), version="0.0.5", xres=f"{dpi:g}", yres=f"{dpi:g}")
    if natif and mode == "gris":
        pile.set("pixane-mode", "gris")
    if natif and reperes:
        pile.set("pixane-reperes", json.dumps([list(r) for r in reperes]))
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
                    a["pixane-texte"] = json.dumps(c.texte.vers_dict(), ensure_ascii=False)
                if c.style is not None and (c.style.effets or c.style.remplissage < 1):
                    a["pixane-style"] = c.style.vers_json()
                if c.reglage is not None:
                    a["pixane-reglage"] = json.dumps(c.reglage, ensure_ascii=False)
                if c.masque is not None:
                    compte[0] += 1
                    src = f"data/masque{compte[0]}.png"
                    tampon = io.BytesIO()
                    Image.fromarray(masque_tableau(c.masque), "L").save(tampon, "PNG", compress_level=6)
                    z.writestr(src, tampon.getvalue(), compress_type=zipfile.ZIP_STORED)
                    a["pixane-masque"] = src
                    if not c.masque_actif:
                        a["pixane-masque-inactif"] = "true"
                if c.groupe and not c.ouvert:
                    a["pixane-ferme"] = "true"
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
                img, x, y = image_entiere(c)                    # ce qui dépasse de la feuille est gardé
                z.writestr(nom_png, _png(img), compress_type=zipfile.ZIP_STORED)
                ET.SubElement(parent, "layer", src=nom_png, x=str(x), y=str(y), **attributs(c))
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
            src = _attr(e, "masque")
            if src:
                try:
                    with Image.open(io.BytesIO(z.read(src))) as im:
                        a = np.asarray(im.convert("L"))
                    if a.shape == (h, w):
                        kw["masque"] = masque_depuis(a)
                        kw["masque_actif"] = _attr(e, "masque-inactif") != "true"
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
                               ouvert=_attr(e, "ferme") != "true", **commun(e))
                    res.append(g)
                    res.extend(enfants)
                elif e.tag == "layer":
                    with Image.open(io.BytesIO(z.read(e.get("src")))) as im:
                        morceau = pil_vers_qimage(im)
                    place = Calque("", image_vide(w, h))      # pixels hors de la feuille : gardés dans `hors`
                    place = avec_image_entiere(place, morceau, int(float(e.get("x", 0))), int(float(e.get("y", 0))),
                                               w, h)
                    img = place.image
                    texte = json_ou_rien(_attr(e, "texte"), lambda t: Texte.depuis_dict(json.loads(t)))
                    style = json_ou_rien(_attr(e, "style"), Style.depuis_json)
                    reglage = json_ou_rien(_attr(e, "reglage"), json.loads)
                    if reglage is not None and not (isinstance(reglage, dict) and "type" in reglage
                                                    and "params" in reglage):
                        reglage = None
                    res.append(Calque(e.get("name") or tr("Calque"), img, texte=texte, style=style, reglage=reglage,
                                      dans=dans, hors=None if texte is not None else place.hors,
                                      hors_x=place.hors_x, hors_y=place.hors_y, **commun(e)))
            return res
        pile = racine.find("stack")
        calques = lire(pile if pile is not None else racine, None)
    if not calques:
        raise ValueError(tr("Ce fichier ne contient aucun calque."))
    return list(reversed(calques))


def _attr(e, nom: str):
    """Attribut « pixane-<nom> » d'un élément de stack.xml."""
    return e.get("pixane-" + nom)


def lire_infos_ora(chemin: Path) -> dict:
    """Repères, résolution (xres de la norme OpenRaster) et mode (gris / rvb) d'un .pixane ou d'un .ora."""
    infos = {"reperes": [], "dpi": 72.0, "mode": "rvb"}
    try:
        with zipfile.ZipFile(chemin) as z:
            e = ET.fromstring(z.read("stack.xml"))
    except (KeyError, ValueError, OSError, zipfile.BadZipFile, ET.ParseError):
        return infos
    try:
        r = _attr(e, "reperes")
        infos["reperes"] = [(str(a), float(b)) for a, b in json.loads(r)] if r else []
    except (ValueError, TypeError):
        pass
    try:
        infos["dpi"] = float(e.get("xres") or 72) or 72.0
    except ValueError:
        pass
    if _attr(e, "mode") == "gris":
        infos["mode"] = "gris"
    return infos


def lire_reperes_ora(chemin: Path) -> list:
    return lire_infos_ora(chemin)["reperes"]


def _dpi_pil(dpi) -> float:
    """Résolution lue par Pillow ((x, y) ou rien) ; 72 si absente ou absurde."""
    try:
        v = float(dpi[0])
        return round(v, 3) if 1 <= v <= 10000 else 72.0
    except (TypeError, ValueError, IndexError):
        return 72.0


def en_gris(img: QImage) -> QImage:
    """Niveaux de gris (luminance, comme Photoshop), transparence gardée. img au FORMAT_IMAGE (RVBA non prémultiplié)."""
    t = tableau(img).astype(np.float32)
    y = (t[:, :, 0] * 0.299 + t[:, :, 1] * 0.587 + t[:, :, 2] * 0.114 + 0.5).clip(0, 255).astype(np.uint8)
    res = np.dstack([y, y, y, t[:, :, 3].astype(np.uint8)])
    return qimage_rgba(res)
