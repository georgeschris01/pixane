"""Réglages de l'image : luminosité, contraste, saturation, teinte, température, netteté.

S'appliquent au calque choisi, seulement dans la sélection s'il y en a une (avec ses bords doux). Calcul rapide :
luminosité, contraste et température sont des courbes par couleur (tables de 256 valeurs) ; saturation et teinte,
une matrice 3 × 3 ; netteté, le masque flou de Pillow. La transparence du calque est gardée.
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageFilter
from PySide6.QtCore import QRect, Qt, QTimer, Signal
from PySide6.QtGui import QImage
from PySide6.QtWidgets import (QCheckBox, QDialog, QGridLayout, QHBoxLayout, QLabel, QPushButton, QSlider, QSpinBox,
                               QVBoxLayout)

from .document import FORMAT_CALQUE, FORMAT_IMAGE, masque, qimage_rgba, tableau
from .langue import tr

# (clé, nom, minimum, maximum, unité)
REGLAGES = (("luminosite", "Luminosité", -100, 100, ""),
            ("contraste", "Contraste", -100, 100, ""),
            ("saturation", "Saturation", -100, 100, ""),
            ("teinte", "Teinte", -180, 180, "°"),
            ("temperature", "Température", -100, 100, ""),
            ("nettete", "Netteté", 0, 200, " %"))
GROUPES = (("Lumière", ("luminosite", "contraste")),
           ("Couleurs", ("saturation", "teinte", "temperature")),
           ("Détails", ("nettete",)))


def _noms() -> dict:
    """Noms affichés (écrits ici en entier pour que la traduction les trouve)."""
    return {"luminosite": tr("Luminosité"), "contraste": tr("Contraste"), "saturation": tr("Saturation"),
            "teinte": tr("Teinte"), "temperature": tr("Température"), "nettete": tr("Netteté"),
            "Lumière": tr("Lumière"), "Couleurs": tr("Couleurs"), "Détails": tr("Détails")}


def neutre(r: dict) -> bool:
    return all(v == 0 for v in r.values())


def _courbes(r: dict) -> list[np.ndarray]:
    """Une table de 256 valeurs par couleur (rouge, vert, bleu) : température, luminosité, contraste."""
    x = np.arange(256, dtype=np.float64) / 255
    t = r.get("temperature", 0) / 100                    # + = plus chaud (rouge), - = plus froid (bleu)
    b = r.get("luminosite", 0) / 100
    c = r.get("contraste", 0) / 100
    tables = []
    for mult in (1 + 0.2 * t, 1 + 0.03 * t, 1 - 0.2 * t):
        v = np.clip(x * mult, 0, 1)
        v = v ** (2 ** (-b))                             # garde le noir et le blanc
        v = (v - 0.5) * 2 ** (1.5 * c) + 0.5
        tables.append(np.clip(np.round(v * 255), 0, 255).astype(np.uint8))
    return tables


def _matrice(r: dict) -> np.ndarray:
    """Saturation puis rotation de la teinte (formules des filtres CSS)."""
    s = 1 + r.get("saturation", 0) / 100
    L = np.array([0.2126, 0.7152, 0.0722])
    sat = (1 - s) * np.tile(L, (3, 1)) + s * np.eye(3)
    a = math.radians(r.get("teinte", 0))
    co, si = math.cos(a), math.sin(a)
    teinte = np.array([
        [0.213 + co * 0.787 - si * 0.213, 0.715 - co * 0.715 - si * 0.715, 0.072 - co * 0.072 + si * 0.928],
        [0.213 - co * 0.213 + si * 0.143, 0.715 + co * 0.285 + si * 0.140, 0.072 - co * 0.072 - si * 0.283],
        [0.213 - co * 0.213 - si * 0.787, 0.715 - co * 0.715 + si * 0.715, 0.072 + co * 0.928 + si * 0.072]])
    return teinte @ sat


def ajuster(img: QImage, r: dict, selection: QImage | None = None) -> QImage:
    """Nouvelle image (FORMAT_CALQUE) du calque `img` avec les réglages `r`, seulement dans `selection` si donnée."""
    tab = tableau(img.convertToFormat(FORMAT_IMAGE))     # RGBA, couleurs non prémultipliées
    h, w = tab.shape[:2]
    zone = QRect(0, 0, w, h)
    poids = None
    if selection is not None:
        m = masque(selection)
        if not m.any():
            return QImage(img)
        ys, xs = np.nonzero(m)
        zone = QRect(int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1))
        poids = m[zone.top():zone.bottom() + 1, zone.left():zone.right() + 1].astype(np.float32)[..., None] / 255
    morceau = tab[zone.top():zone.bottom() + 1, zone.left():zone.right() + 1]
    rgb = morceau[..., :3]
    tables = _courbes(r)
    res = np.stack([tables[k][rgb[..., k]] for k in range(3)], axis=-1)
    if r.get("saturation", 0) or r.get("teinte", 0):
        f = res.reshape(-1, 3).astype(np.float32) @ _matrice(r).T.astype(np.float32)
        res = np.clip(np.round(f), 0, 255).astype(np.uint8).reshape(res.shape)
    if r.get("nettete", 0):
        net = Image.fromarray(np.ascontiguousarray(res), "RGB").filter(
            ImageFilter.UnsharpMask(radius=2, percent=int(r["nettete"]), threshold=2))
        res = np.asarray(net)
    if poids is not None:
        res = np.round(rgb + (res.astype(np.float32) - rgb) * poids).astype(np.uint8)
    morceau[..., :3] = res
    return qimage_rgba(tab).convertToFormat(FORMAT_CALQUE)


class FenetreReglages(QDialog):
    """Curseurs des réglages, aperçu en direct sur la photo (signal `change`, envoyé après une courte pause)."""
    change = Signal(dict)

    def __init__(self, nom_calque: str, dans_selection: bool, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Réglages de l'image"))
        lay = QVBoxLayout(self)
        ou = tr("dans la sélection") if dans_selection else tr("sur tout le calque")
        info = QLabel(tr("S'applique au calque « {nom} », {ou}.", nom=nom_calque, ou=ou))
        info.setObjectName("discret")
        info.setWordWrap(True)
        lay.addWidget(info)
        self.curseurs: dict[str, QSlider] = {}
        self.cases: dict[str, QSpinBox] = {}
        reglages = {cle: (nom, mini, maxi, unite) for cle, nom, mini, maxi, unite in REGLAGES}
        noms = _noms()
        grille = QGridLayout()                       # une seule grille : curseurs alignés d'un groupe à l'autre
        grille.setColumnStretch(1, 1)
        grille.setHorizontalSpacing(12)
        ligne = 0
        for titre, cles in GROUPES:
            t = QLabel(f"<b>{noms[titre]}</b>")
            if ligne:
                t.setContentsMargins(0, 8, 0, 0)
            grille.addWidget(t, ligne, 0, 1, 3)
            ligne += 1
            for cle in cles:
                i = ligne
                ligne += 1
                nom, mini, maxi, unite = reglages[cle]
                grille.addWidget(QLabel(noms[cle]), i, 0)
                c = QSlider(Qt.Horizontal)
                c.setRange(mini, maxi)
                c.setMinimumWidth(260)
                s = QSpinBox()
                s.setRange(mini, maxi)
                s.setSuffix(unite)
                c.valueChanged.connect(s.setValue)
                s.valueChanged.connect(c.setValue)
                c.valueChanged.connect(self._plus_tard)
                grille.addWidget(c, i, 1)
                grille.addWidget(s, i, 2)
                self.curseurs[cle], self.cases[cle] = c, s
        lay.addLayout(grille)
        self.c_apercu = QCheckBox(tr("Aperçu sur la photo"))
        self.c_apercu.setChecked(True)
        self.c_apercu.toggled.connect(self._plus_tard)
        lay.addWidget(self.c_apercu)
        boutons = QHBoxLayout()
        b = QPushButton(tr("Réinitialiser"))
        b.clicked.connect(self.reinitialiser)
        boutons.addWidget(b)
        boutons.addStretch(1)
        self.b_ok = QPushButton(tr("Appliquer"))
        self.b_ok.setDefault(True)
        self.b_ok.setMinimumWidth(self.b_ok.fontMetrics().horizontalAdvance(self.b_ok.text()) + 40)
        self.b_ok.clicked.connect(self.accept)
        annuler = QPushButton(tr("Annuler"))
        annuler.clicked.connect(self.reject)
        boutons.addWidget(self.b_ok)
        boutons.addWidget(annuler)
        lay.addLayout(boutons)
        self._minuterie = QTimer(self)
        self._minuterie.setSingleShot(True)
        self._minuterie.setInterval(120)
        self._minuterie.timeout.connect(lambda: self.change.emit(self.valeurs_apercu()))

    def _plus_tard(self, *_):
        self._minuterie.start()

    def valeurs(self) -> dict:
        return {cle: c.value() for cle, c in self.curseurs.items()}

    def valeurs_apercu(self) -> dict:
        r = self.valeurs()
        return r if self.c_apercu.isChecked() else {cle: 0 for cle in r}

    def reinitialiser(self):
        for c in self.curseurs.values():
            c.setValue(0)
