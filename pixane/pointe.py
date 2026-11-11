"""Pinceaux à forme (comme Photoshop, Krita) : la forme est « tamponnée » le long du trait.

Réglages (comme le panneau « Forme de pinceau » de Photoshop) :
- forme : espacement (part de la taille), angle fixe ou qui suit le trait, rondeur ;
- dispersion : écart au trait, sur un axe ou deux, nombre de touches, variations de taille, d'angle, de rondeur ;
- texture : un motif qui « troue » le trait (comme du papier), échelle, force, inversé ;
- double pinceau : une deuxième forme qui découpe la première ;
- couleur : variation de teinte, saturation, luminosité, mélange couleur / arrière-plan, à chaque touche ;
- transfert : variation d'opacité et de flux ;
- tablette : la pression change la taille, l'opacité et/ou le flux.

Ce module calcule les touches (position, taille, angle, couleur…) et les dessine dans une « couche » de trait
(QImage ARGB prémultipliée). retouche.Trait pose ensuite la couche sur le calque.
"""
from __future__ import annotations

import colorsys
import math
import random
from dataclasses import asdict, dataclass, field, fields

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QTransform


@dataclass
class Reglages:
    espacement: float | None = None      # part de la taille (0.25 = 25 %) ; None : celui du pinceau
    angle: float = 0.0                    # degrés
    suivre: bool = False                  # l'angle suit la direction du trait
    rondeur: float = 1.0                  # 1 = forme d'origine ; 0.2 = écrasée
    retourner: bool = False               # miroir horizontal
    dispersion: float = 0.0               # écart au trait, en part de la taille (0 à 10)
    deux_axes: bool = False               # aussi le long du trait
    nombre: int = 1                       # touches par pas
    var_taille: float = 0.0               # 0..1
    taille_min: float = 0.0               # 0..1 (plancher de la variation et de la pression)
    var_angle: float = 0.0                # 0..1 (1 = un tour complet)
    var_rondeur: float = 0.0              # 0..1
    texture: str | None = None            # clé du motif dans la bibliothèque
    texture_echelle: float = 1.0
    texture_force: float = 1.0            # 0..1
    texture_inverser: bool = False
    double: str | None = None             # clé du deuxième pinceau
    double_taille: float = 1.0            # part de la taille du pinceau
    double_espacement: float = 0.25
    double_dispersion: float = 0.0
    var_teinte: float = 0.0               # 0..1
    var_saturation: float = 0.0
    var_luminosite: float = 0.0
    melange_fond: float = 0.0             # 0..1 : vers la couleur d'arrière-plan
    flux: float = 1.0                     # 0..1 : force de chaque touche (s'additionnent)
    var_opacite: float = 0.0
    var_flux: float = 0.0
    pression_taille: bool = True          # tablette
    pression_opacite: bool = False
    pression_flux: bool = False

    def vers_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def depuis_dict(cls, d: dict | None) -> "Reglages":
        noms = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in (d or {}).items() if k in noms})

    def simples(self) -> bool:
        """Aucun réglage qui demande le moteur à formes (le rond simple suffit)."""
        return self == Reglages(espacement=self.espacement)


def _image_alpha(a: np.ndarray) -> QImage:
    """Forme grise -> image blanche dont l'alpha est la forme (prémultipliée) ; RGBA -> telle quelle."""
    a = np.ascontiguousarray(a)
    h, w = a.shape[:2]
    if a.ndim == 2:
        rgba = np.empty((h, w, 4), np.uint8)
        rgba[..., 0] = rgba[..., 1] = rgba[..., 2] = rgba[..., 3] = a
        return QImage(rgba.data, w, h, 4 * w, QImage.Format_RGBA8888_Premultiplied).convertToFormat(
            QImage.Format_ARGB32_Premultiplied)
    return QImage(a.data, w, h, 4 * w, QImage.Format_RGBA8888).convertToFormat(QImage.Format_ARGB32_Premultiplied)


def forme_ronde(durete: float, taille: int = 256) -> np.ndarray:
    yy, xx = np.mgrid[0:taille, 0:taille].astype(np.float32)
    c = (taille - 1) / 2
    r = np.hypot(xx - c, yy - c) / (taille / 2)
    h = min(0.99, max(0.0, durete))
    return (np.clip((1 - r) / (1 - h), 0, 1) * 255 + 0.5).astype(np.uint8)


class Pointe:
    """Les formes d'un pinceau, prêtes à tamponner. formes : liste de tableaux (gris ou RGBA)."""

    def __init__(self, formes: list, espacement: float = 0.25):
        self.formes = formes
        self.espacement = espacement
        self.en_couleur = formes[0].ndim == 3
        self._images = [_image_alpha(f) for f in formes]
        self._teintes: dict = {}
        self.indice = 0

    def suivante(self) -> int:
        """Formes d'un pinceau animé : l'une après l'autre."""
        i = self.indice % len(self._images)
        self.indice += 1
        return i

    def image(self, i: int, couleur: QColor | None) -> QImage:
        """Forme i, de la couleur demandée (forme grise) ou avec ses couleurs (forme en couleur)."""
        if self.en_couleur or couleur is None:
            return self._images[i]
        cle = (i, couleur.rgba())
        img = self._teintes.get(cle)
        if img is None:
            if len(self._teintes) > 64:
                self._teintes.clear()
            img = QImage(self._images[i].size(), QImage.Format_ARGB32_Premultiplied)
            img.fill(couleur)
            p = QPainter(img)
            p.setCompositionMode(QPainter.CompositionMode_DestinationIn)
            p.drawImage(0, 0, self._images[i])
            p.end()
            self._teintes[cle] = img
        return img

    def taille(self, i: int) -> tuple[int, int]:
        im = self._images[i]
        return im.width(), im.height()


@dataclass
class Touche:
    x: float
    y: float
    taille: float
    angle: float
    rondeur: float
    flux: float
    couleur: QColor
    forme: int = 0


@dataclass
class Suivi:
    """Avancement le long du trait (pour placer les touches régulièrement)."""
    dernier: QPointF | None = None
    reste: float = 0.0
    direction: float = 0.0
    pression: float = 1.0
    touches: list = field(default_factory=list)


def _var(r: random.Random, v: float) -> float:
    """Nombre au hasard entre -v et +v."""
    return (r.random() * 2 - 1) * v if v else 0.0


class Placement:
    """Calcule les touches d'un trait, point après point (avec la pression de la tablette)."""

    def __init__(self, pointe: Pointe, reglages: Reglages, taille: float, couleur: QColor,
                 fond: QColor | None = None, graine: int | None = None):
        self.pointe, self.r, self.taille = pointe, reglages, max(1.0, taille)
        self.couleur, self.fond = QColor(couleur), QColor(fond) if fond is not None else QColor(255, 255, 255)
        self.hasard = random.Random(graine)
        self.suivi = Suivi()
        esp = reglages.espacement if reglages.espacement is not None else pointe.espacement
        self.espacement = max(0.01, float(esp or 0.25))

    def _pas(self, pression: float) -> float:
        t = self.taille * (self._facteur_pression(pression) if self.r.pression_taille else 1.0)
        return max(1.0, t * self.espacement)

    def _facteur_pression(self, p: float) -> float:
        m = self.r.taille_min
        return m + (1 - m) * max(0.0, min(1.0, p))

    def ajouter(self, pt: QPointF, pression: float = 1.0) -> list:
        """Prolonge le trait jusqu'à pt ; renvoie les nouvelles touches."""
        s = self.suivi
        nouvelles = []
        if s.dernier is None:
            nouvelles += self._touches(pt, pression)
        else:
            a = s.dernier
            d = math.hypot(pt.x() - a.x(), pt.y() - a.y())
            if d > 0:
                s.direction = math.degrees(math.atan2(pt.y() - a.y(), pt.x() - a.x()))
            p0 = s.pression
            pas = self._pas(pression)
            t = pas - s.reste
            while t <= d:
                f = t / d if d else 1.0
                pr = p0 + (pression - p0) * f
                nouvelles += self._touches(a + (pt - a) * f, pr)
                pas = self._pas(pr)
                t += pas
            s.reste = d - (t - pas)
        s.dernier, s.pression = QPointF(pt), pression
        s.touches += nouvelles
        return nouvelles

    def _touches(self, c: QPointF, pression: float) -> list:
        r, h = self.r, self.hasard
        res = []
        for _ in range(max(1, int(r.nombre))):
            taille = self.taille
            if r.pression_taille:
                taille *= self._facteur_pression(pression)
            if r.var_taille:
                taille *= max(r.taille_min, 1 - h.random() * r.var_taille)
            angle = r.angle + (self.suivi.direction if r.suivre else 0.0) + _var(h, r.var_angle) * 180
            rondeur = max(0.02, min(1.0, r.rondeur * (1 - h.random() * r.var_rondeur)))
            x, y = c.x(), c.y()
            if r.dispersion:
                d = self.taille * r.dispersion
                a = math.radians(self.suivi.direction)
                perp = _var(h, d)
                le_long = _var(h, d) if r.deux_axes else 0.0
                x += -math.sin(a) * perp + math.cos(a) * le_long
                y += math.cos(a) * perp + math.sin(a) * le_long
            flux = r.flux
            if r.pression_flux:
                flux *= max(0.0, min(1.0, pression))
            if r.var_flux:
                flux *= 1 - h.random() * r.var_flux
            res.append(Touche(x, y, max(0.5, taille), angle, rondeur, max(0.0, min(1.0, flux)),
                              self._couleur(), self.pointe.suivante()))
        return res

    def _couleur(self) -> QColor:
        r, h = self.r, self.hasard
        c = self.couleur
        if r.melange_fond:
            k = h.random() * r.melange_fond
            c = QColor.fromRgbF(*(a + (b - a) * k for a, b in zip(c.getRgbF()[:3], self.fond.getRgbF()[:3])))
        if r.var_teinte or r.var_saturation or r.var_luminosite:
            hh, ll, ss = colorsys.rgb_to_hls(*c.getRgbF()[:3])
            hh = (hh + _var(h, r.var_teinte) * 0.5) % 1.0
            ss = max(0.0, min(1.0, ss + _var(h, r.var_saturation)))
            ll = max(0.0, min(1.0, ll + _var(h, r.var_luminosite) * 0.5))
            c = QColor.fromRgbF(*colorsys.hls_to_rgb(hh, ll, ss))
        return c


def dessiner(p: QPainter, pointe: Pointe, t: Touche, couleur: bool = True) -> QRectF:
    """Tamponne une touche ; renvoie la zone couverte. couleur=False : forme blanche (masque)."""
    w, h = pointe.taille(t.forme)
    k = t.taille / max(w, h)
    tr = QTransform()
    tr.translate(t.x, t.y)
    tr.rotate(t.angle)
    tr.scale(k, k * t.rondeur)
    p.save()
    p.setTransform(tr, False)
    p.setOpacity(t.flux)
    p.setRenderHint(QPainter.SmoothPixmapTransform, True)
    p.drawImage(QRectF(-w / 2, -h / 2, w, h), pointe.image(t.forme, t.couleur if couleur else QColor(255, 255, 255)))
    p.restore()
    return tr.mapRect(QRectF(-w / 2, -h / 2, w, h)).adjusted(-2, -2, 2, 2)


def texture_grise(motif: np.ndarray, echelle: float = 1.0) -> np.ndarray:
    """Motif RGBA -> valeurs 0..1 (gris ; transparent = blanc, laisse passer), à l'échelle voulue."""
    if echelle != 1.0:
        from PIL import Image
        mh, mw = motif.shape[:2]
        motif = np.asarray(Image.fromarray(motif).resize((max(1, round(mw * echelle)), max(1, round(mh * echelle))),
                                                         Image.LANCZOS))
    g = motif[..., :3].astype(np.float32).mean(axis=2) / 255
    a = motif[..., 3].astype(np.float32) / 255
    return np.ascontiguousarray(g * a + (1 - a))


def texture_zone(g: np.ndarray, x: int, y: int, w: int, h: int) -> np.ndarray:
    """Valeurs du motif gris (texture_grise) sur la zone, répété (coordonnées de l'image)."""
    mh, mw = g.shape
    ys = (np.arange(y, y + h) % mh)[:, None]
    xs = (np.arange(x, x + w) % mw)[None, :]
    return g[ys, xs]
