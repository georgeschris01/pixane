"""Fenêtre « Installer le traducteur » : explique à quoi il sert, puis le télécharge (reprise après coupure,
fichiers vérifiés) dans le dossier de Pixane. Ouverte depuis « Modifier avec une consigne » et proposée (case) dans
« Installer le moteur IA »."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QDialog, QFileDialog, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout,
                               QWidget)

from . import traduction
from .installation_moteur import DOSSIER_APP, Installation
from .langue import tr


def explication() -> str:
    return tr("L'IA qui modifie les images (Flux Kontext) ne comprend bien que l'anglais. Avec le traducteur, tu "
              "écris tes consignes en français (« remplace le texte « brûler le feu » par « Flamme » ») et Pixane "
              "les traduit avant de les envoyer. La traduction se fait sur ton PC : rien n'est envoyé sur Internet. "
              "Sans lui, il faut écrire les consignes en anglais.")


class ChoixDossier(QWidget):
    """« Dossier du traducteur : … [Changer…] ». Grisé quand le traducteur est déjà installé."""
    change = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(24, 0, 0, 0)
        self.texte = QLabel()
        self.texte.setObjectName("discret")
        self.texte.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.b_changer = QPushButton(tr("Changer…"))
        self.b_changer.clicked.connect(self.changer)
        lay.addWidget(self.texte, 1)
        lay.addWidget(self.b_changer)
        self.maj()

    def maj(self):
        self.texte.setText(tr("Dossier du traducteur : {dossier}", dossier=traduction.dossier()))
        self.b_changer.setEnabled(not traduction.installe())

    def setEnabled(self, oui: bool):
        self.b_changer.setEnabled(oui and not traduction.installe())

    def changer(self):
        d = QFileDialog.getExistingDirectory(self, tr("Dossier du traducteur"), str(traduction.dossier_choisi()))
        if d:
            traduction.choisir_dossier(d)
            self.maj()
            self.change.emit()


class FenetreTraducteur(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Installer le traducteur"))
        self.setMinimumWidth(520)
        lay = QVBoxLayout(self)
        t = QLabel(explication())
        t.setWordWrap(True)
        lay.addWidget(t)
        d = QLabel(tr("Modèle Opus-MT français → anglais (université d'Helsinki), {taille}, licence {licence}, "
                      "téléchargé depuis Hugging Face.",
                      taille=tr("{n} Mo", n=round(traduction.TAILLE / 1024 ** 2)), licence=traduction.LICENCE))
        d.setWordWrap(True)
        d.setObjectName("discret")
        lay.addWidget(d)
        self.choix_dossier = ChoixDossier()
        lay.addWidget(self.choix_dossier)
        self.barre = QProgressBar()
        self.barre.setRange(0, 1000)
        self.barre.hide()
        lay.addWidget(self.barre)
        self.etat = QLabel()
        self.etat.setWordWrap(True)
        lay.addWidget(self.etat)
        bas = QHBoxLayout()
        bas.addStretch(1)
        self.b_installer = QPushButton(tr("Installer ({taille})", taille=tr("{n} Mo", n=round(traduction.TAILLE / 1024 ** 2))))
        self.b_installer.setDefault(True)
        self.b_installer.clicked.connect(self.installer)
        self.b_fermer = QPushButton(tr("Plus tard"))
        self.b_fermer.clicked.connect(self.reject)
        bas.addWidget(self.b_installer)
        bas.addWidget(self.b_fermer)
        lay.addLayout(bas)
        self.travail: Installation | None = None

    def installer(self):
        self.b_installer.setEnabled(False)
        self.choix_dossier.setEnabled(False)
        self.barre.show()
        self.etat.setText(tr("Téléchargement…"))
        self.travail = Installation(DOSSIER_APP / "complement", traduction.elements(), complement=True)
        self.travail.progres.connect(lambda fait, total, _v: self.barre.setValue(int(1000 * fait / max(1, total))))
        self.travail.fini.connect(self._fini)
        self.travail.lancer()

    def _fini(self, reussi: bool, message: str):
        self.travail = None
        if reussi and traduction.installe():
            self.etat.setText(tr("Le traducteur est installé."))
            self.barre.setValue(1000)
            self.b_fermer.setText(tr("Fermer"))
            self.b_fermer.clicked.disconnect()
            self.b_fermer.clicked.connect(self.accept)
        else:
            self.etat.setText(message)
            self.b_installer.setEnabled(True)
            self.choix_dossier.setEnabled(True)
            self.b_installer.setText(tr("Réessayer"))

    def reject(self):
        if self.travail is not None:
            self.travail.arret.set()
        super().reject()
