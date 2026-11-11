"""Fenêtre « Modifier avec une consigne » : ce que l'IA doit faire, en français (traduit en anglais si le traducteur
est installé) ou directement en anglais ; exemples à cliquer ; nombre de propositions."""
from __future__ import annotations

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QPlainTextEdit,
                               QPushButton, QSpinBox, QVBoxLayout)

from . import traduction
from .langue import tr

# (texte montré, modèle inséré : « … » à remplacer par l'utilisateur)
EXEMPLES = [
    ("Remplacer un texte", "Remplace le texte « … » par « … », dans le même style"),
    ("Changer une couleur", "Change la couleur de … en …"),
    ("Remplacer un objet", "Remplace … par …"),
    ("Enlever quelque chose", "Enlève …"),
    ("Ajouter quelque chose", "Ajoute …"),
    ("Changer de style", "Transforme en style …"),
]


def _reglages() -> QSettings:
    import os
    return QSettings("Pixane", os.environ.get("PIXANE_REGLAGES", "Pixane"))


class DialogueConsigne(QDialog):
    def __init__(self, parent=None, transparent: bool = False, avec_selection: bool = True, nb: int = 2):
        super().__init__(parent)
        self.setWindowTitle(tr("Modifier avec une consigne"))
        self.resize(560, 420)
        lay = QVBoxLayout(self)
        quoi = tr("la zone sélectionnée") if avec_selection else tr("toute l'image (rien n'est sélectionné)")
        intro = QLabel(tr("Dis à l'IA ce qu'elle doit changer dans {quoi}. Elle garde le style de l'image ; ce qui "
                          "est hors de la sélection ne bouge pas. Mets entre guillemets un texte à écrire tel "
                          "quel : il n'est pas traduit.", quoi=quoi))
        intro.setWordWrap(True)
        lay.addWidget(intro)
        if transparent:
            t = QLabel(tr("Calque avec de la transparence (texte, logo) : l'IA le voit seul et le résultat garde "
                          "un fond transparent."))
            t.setWordWrap(True)
            t.setObjectName("discret")
            lay.addWidget(t)
        ligne = QHBoxLayout()
        ligne.addWidget(QLabel(tr("Exemples :")))
        self.exemples = QComboBox()
        self.exemples.addItem(tr("(choisir pour l'insérer)"), "")
        for nom, modele in EXEMPLES:
            self.exemples.addItem(tr(nom), tr(modele))
        self.exemples.activated.connect(self._exemple)
        ligne.addWidget(self.exemples, 1)
        lay.addLayout(ligne)
        self.texte = QPlainTextEdit()
        self.texte.setPlaceholderText(tr("Ex. : Remplace le texte « brûler le feu » par « Flamme », dans le même "
                                         "style"))
        self.texte.setPlainText(_reglages().value("consigne_derniere", "") or "")
        self.texte.textChanged.connect(self._texte_change)
        lay.addWidget(self.texte, 2)
        ligne = QHBoxLayout()
        ligne.addWidget(QLabel(tr("Envoyé à l'IA (anglais) :")))
        ligne.addStretch(1)
        self.bouton_installer = QPushButton(tr("Installer le traducteur…"))
        self.bouton_installer.clicked.connect(self._installer)
        ligne.addWidget(self.bouton_installer)
        self.bouton_traduire = QPushButton(tr("Traduire"))
        self.bouton_traduire.clicked.connect(self.traduire)
        ligne.addWidget(self.bouton_traduire)
        lay.addLayout(ligne)
        self.anglais = QPlainTextEdit()
        self.anglais.setPlaceholderText(tr("Rempli par « Traduire » ; tu peux le corriger. Vide : la consigne est "
                                           "envoyée telle quelle."))
        lay.addWidget(self.anglais, 1)
        self.etat = QLabel()
        self.etat.setWordWrap(True)
        self.etat.setObjectName("discret")
        lay.addWidget(self.etat)
        ligne = QHBoxLayout()
        ligne.addWidget(QLabel(tr("Propositions")))
        self.nb = QSpinBox()
        self.nb.setRange(1, 4)
        self.nb.setValue(nb)
        ligne.addWidget(self.nb)
        ligne.addWidget(QLabel(tr("(environ 2 à 3 minutes chacune)")))
        ligne.addStretch(1)
        lay.addLayout(ligne)
        boutons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        boutons.button(QDialogButtonBox.Ok).setText(tr("Modifier"))
        boutons.accepted.connect(self.accept)
        boutons.rejected.connect(self.reject)
        lay.addWidget(boutons)
        self._traduit_de = None
        self._maj_etat()

    def _maj_etat(self):
        if traduction.installe():
            self.etat.setText(tr("Traducteur installé : écris en français, Pixane traduit (sur ton PC, rien n'est "
                                 "envoyé sur Internet)."))
            self.bouton_traduire.setEnabled(True)
            self.bouton_installer.hide()
        else:
            self.bouton_installer.show()
            self.etat.setText(tr("Traducteur non installé : l'IA comprend mal le français, écris la consigne en "
                                 "anglais (ou installe-le : menu IA > Installer le moteur IA, case « Traducteur »)."))
            self.bouton_traduire.setEnabled(False)

    def _installer(self):
        from .installation_traducteur import FenetreTraducteur
        FenetreTraducteur(self).exec()
        self._maj_etat()

    def _exemple(self, i: int):
        modele = self.exemples.itemData(i)
        if modele:
            self.texte.setPlainText(modele)
            self.texte.setFocus()
        self.exemples.setCurrentIndex(0)

    def _texte_change(self):
        if self._traduit_de is not None and self.texte.toPlainText() != self._traduit_de:
            self.anglais.clear()                  # traduction périmée
            self._traduit_de = None

    def traduire(self) -> bool:
        texte = self.texte.toPlainText().strip()
        if not texte or not traduction.installe():
            return False
        from PySide6.QtWidgets import QApplication
        self.etat.setText(tr("Traduction…"))
        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.processEvents()
        try:
            self.anglais.setPlainText(traduction.traduire(texte))
            self._traduit_de = self.texte.toPlainText()
            self._maj_etat()
            return True
        except Exception as e:                     # traducteur abîmé : on peut encore écrire en anglais
            self.etat.setText(tr("Traduction impossible : {raison}", raison=e))
            return False
        finally:
            QApplication.restoreOverrideCursor()

    def accept(self):
        if not self.texte.toPlainText().strip() and not self.anglais.toPlainText().strip():
            self.etat.setText(tr("Écris d'abord ce que l'IA doit faire."))
            return
        if not self.anglais.toPlainText().strip() and traduction.installe():
            self.traduire()
        _reglages().setValue("consigne_derniere", self.texte.toPlainText())
        super().accept()

    def consigne(self) -> str:
        """Ce qui part à l'IA : l'anglais s'il est rempli, sinon la consigne telle quelle (guillemets « » -> " ")."""
        t = self.anglais.toPlainText().strip() or self.texte.toPlainText().strip()
        return traduction.guillemets_droits(t)

    def nombre(self) -> int:
        return self.nb.value()
