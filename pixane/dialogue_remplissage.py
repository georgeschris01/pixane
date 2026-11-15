"""Fenêtre d'un calque de remplissage : couleur unie, dégradé (style, angle, échelle, inverser) ou motif (échelle).
Chaque changement est montré tout de suite sur le calque (signal change)."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLabel,
                               QStackedWidget, QVBoxLayout, QWidget)

from .calque_remplissage import GENRES, NOIR_BLANC, STYLES, Remplissage, noms_genres, noms_styles
from .degrades import BoutonDegrade
from .dialogue_style import ChampCouleur
from .dialogues_reglage import Curseur
from .langue import tr
from .motifs import BoutonMotif


class DialogueRemplissage(QDialog):
    change = Signal(object)                 # Remplissage

    def __init__(self, r: Remplissage, parent=None, explication: str = ""):
        super().__init__(parent)
        self.setWindowTitle(tr("Calque de remplissage"))
        self.r = r
        lay = QVBoxLayout(self)
        if explication:
            info = QLabel(explication)
            info.setWordWrap(True)
            lay.addWidget(info)
        haut = QHBoxLayout()
        haut.addWidget(QLabel(tr("Remplir avec :")))
        self.genre = QComboBox()
        for g in GENRES:
            self.genre.addItem(noms_genres()[g], g)
        self.genre.setCurrentIndex(GENRES.index(r.genre))
        haut.addWidget(self.genre, 1)
        lay.addLayout(haut)

        self.pages = QStackedWidget()
        # couleur unie
        p = QWidget()
        f = QFormLayout(p)
        self.couleur = ChampCouleur(r.couleur)
        f.addRow(tr("Couleur :"), self.couleur)
        self.pages.addWidget(p)
        # dégradé
        p = QWidget()
        f = QFormLayout(p)
        self.degrade = BoutonDegrade(r.degrade if r.degrade is not None else NOIR_BLANC, None, self, largeur=160,
                                     avec_peinture=False, en_direct=True)
        self._degrade = self.degrade.degrade
        f.addRow(tr("Dégradé :"), self.degrade)
        self.style = QComboBox()
        for s in STYLES:
            self.style.addItem(noms_styles()[s], s)
        self.style.setCurrentIndex(STYLES.index(r.style))
        f.addRow(tr("Style :"), self.style)
        self.angle = Curseur(tr("Angle"), -180, 180, round(r.angle), " °")
        self.echelle = Curseur(tr("Échelle"), 10, 300, round(r.echelle), " %")
        f.addRow(self.angle)
        f.addRow(self.echelle)
        self.inverser = QCheckBox(tr("Inverser"))
        self.inverser.setChecked(r.inverser)
        f.addRow(self.inverser)
        self.pages.addWidget(p)
        # motif
        p = QWidget()
        f = QFormLayout(p)
        self.motif = BoutonMotif(r.motif, self)
        f.addRow(tr("Motif :"), self.motif)
        self.motif_echelle = Curseur(tr("Échelle"), 5, 400, round(r.motif_echelle), " %")
        f.addRow(self.motif_echelle)
        self.pages.addWidget(p)
        self.pages.setCurrentIndex(GENRES.index(r.genre))
        lay.addWidget(self.pages)

        boutons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        boutons.accepted.connect(self.accept)
        boutons.rejected.connect(self.reject)
        lay.addWidget(boutons)

        self.genre.currentIndexChanged.connect(self._lire)
        self.couleur.change.connect(self._lire)
        self.degrade.change.connect(self._degrade_change)
        self.style.currentIndexChanged.connect(self._lire)
        for c in (self.angle, self.echelle, self.motif_echelle):
            c.change.connect(self._lire)
        self.inverser.toggled.connect(self._lire)
        self.motif.change.connect(self._lire)

    def _degrade_change(self, d):
        self._degrade = d                    # en direct pendant l'éditeur : le bouton ne l'a pas encore gardé
        self._lire()

    def _lire(self, *_):
        genre = self.genre.currentData()
        self.pages.setCurrentIndex(GENRES.index(genre))
        d = self._degrade
        self.r = self.r.avec(genre=genre, couleur=self.couleur.valeur, degrade=d if isinstance(d, dict) else None,
                             style=self.style.currentData(), angle=float(self.angle.valeur()),
                             echelle=float(self.echelle.valeur()), inverser=self.inverser.isChecked(),
                             motif=self.motif.cle, motif_echelle=float(self.motif_echelle.valeur()))
        self.change.emit(self.r)
