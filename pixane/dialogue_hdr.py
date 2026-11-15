"""Fenêtres du 32 bits (HDR) :
- Virage HDR : en passant une image 32 bits en 16 ou 8 bits, choisir comment les couleurs plus claires que le blanc
  sont ramenées (exposition, gamma, compression des hautes lumières), avec un aperçu ;
- Exposition 32 bits (Affichage) : régler l'aperçu à l'écran sans toucher à l'image (comme Photoshop).
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel,
                               QPushButton, QSlider, QVBoxLayout)

from . import profondeur as prof
from .langue import tr


def _curseur(mini: float, maxi: float, pas: float, valeur: float, suffixe: str = ""):
    """Curseur + case numérique liés (valeurs à virgule)."""
    s = QSlider(Qt.Horizontal)
    s.setRange(round(mini / pas), round(maxi / pas))
    s.setValue(round(valeur / pas))
    b = QDoubleSpinBox()
    b.setRange(mini, maxi)
    b.setSingleStep(pas)
    b.setDecimals(2)
    b.setValue(valeur)
    if suffixe:
        b.setSuffix(suffixe)
    s.valueChanged.connect(lambda v: b.setValue(v * pas))
    b.valueChanged.connect(lambda v: s.setValue(round(v / pas)))
    ligne = QHBoxLayout()
    ligne.addWidget(s, 1)
    ligne.addWidget(b)
    return ligne, b


class DialogueVirage(QDialog):
    """Image > Mode > 16 / 8 bits depuis 32 bits. valeurs() : dict pour profondeur.virage."""

    def __init__(self, parent, image: QImage, bits: int):
        super().__init__(parent)
        self.setWindowTitle(tr("Virage HDR vers {n} bits", n=bits))
        petite = image.scaled(360, 260, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._petite = prof.en_32(petite)
        lay = QVBoxLayout(self)
        aide = QLabel(tr("L'image a des couleurs plus claires que le blanc. Choisissez comment les ramener : "
                         "baissez l'exposition pour retrouver le ciel ou le soleil, ou cochez « Compresser les "
                         "hautes lumières » pour les garder toutes en douceur."))
        aide.setWordWrap(True)
        lay.addWidget(aide)
        self._apercu = QLabel()
        self._apercu.setAlignment(Qt.AlignCenter)
        self._apercu.setMinimumSize(360, 260)
        lay.addWidget(self._apercu)
        form = QFormLayout()
        l1, self._expo = _curseur(-5, 5, 0.05, 0.0, tr(" diaph"))
        l2, self._gamma = _curseur(0.3, 3.0, 0.01, 1.0)
        form.addRow(tr("Exposition :"), l1)
        form.addRow(tr("Gamma :"), l2)
        self._compr = QCheckBox(tr("Compresser les hautes lumières (rien n'est coupé au blanc)"))
        form.addRow("", self._compr)
        lay.addLayout(form)
        boutons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        defaut = QPushButton(tr("Par défaut"))
        boutons.addButton(defaut, QDialogButtonBox.ResetRole)
        defaut.clicked.connect(self._defaut)
        boutons.accepted.connect(self.accept)
        boutons.rejected.connect(self.reject)
        lay.addWidget(boutons)
        self._minuterie = QTimer(self, singleShot=True, interval=60, timeout=self._montrer)
        for w in (self._expo, self._gamma):
            w.valueChanged.connect(lambda *_: self._minuterie.start())
        self._compr.toggled.connect(lambda *_: self._minuterie.start())
        self._montrer()

    def _defaut(self):
        self._expo.setValue(0.0)
        self._gamma.setValue(1.0)
        self._compr.setChecked(False)

    def valeurs(self) -> dict:
        return {"exposition": self._expo.value(), "gamma": self._gamma.value(), "compression": self._compr.isChecked()}

    def _montrer(self):
        img = prof.vers_8(prof.virage(self._petite, **self.valeurs()))
        self._apercu.setPixmap(QPixmap.fromImage(img))


class DialogueExposition(QDialog):
    """Affichage > Exposition 32 bits : l'aperçu change en direct ; l'image ne change pas."""

    def __init__(self, parent, rafraichir):
        super().__init__(parent)
        self.setWindowTitle(tr("Exposition de l'aperçu 32 bits"))
        self._rafraichir = rafraichir
        lay = QVBoxLayout(self)
        aide = QLabel(tr("Change seulement ce que vous voyez à l'écran, pour regarder les zones plus claires que "
                         "le blanc (ciel, soleil, lampes). L'image et ses exports ne changent pas."))
        aide.setWordWrap(True)
        lay.addWidget(aide)
        ligne, self._expo = _curseur(-8, 8, 0.05, prof.exposition_ecran, tr(" diaph"))
        lay.addLayout(ligne)
        boutons = QDialogButtonBox(QDialogButtonBox.Close)
        zero = QPushButton(tr("Remettre à 0"))
        boutons.addButton(zero, QDialogButtonBox.ResetRole)
        zero.clicked.connect(lambda: self._expo.setValue(0.0))
        boutons.rejected.connect(self.reject)
        lay.addWidget(boutons)
        self._minuterie = QTimer(self, singleShot=True, interval=80, timeout=self._appliquer)
        self._expo.valueChanged.connect(lambda *_: self._minuterie.start())

    def _appliquer(self):
        prof.exposition_ecran = float(self._expo.value())
        self._rafraichir()
