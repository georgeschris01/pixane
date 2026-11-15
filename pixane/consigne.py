"""Fenêtre « Modifier avec une consigne » : ce que l'IA doit faire, en français (traduit en anglais si le traducteur
est installé) ou directement en anglais ; exemples à cliquer ; nombre de propositions."""
from __future__ import annotations

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QMessageBox,
                               QPlainTextEdit, QPushButton, QSpinBox, QVBoxLayout)

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
# « Créer une image d'après un texte »
EXEMPLES_CREER = [
    ("Fond abstrait", "Fond abstrait aux couleurs …, formes douces et lumineuses, sans texte"),
    ("Paysage", "Photo d'un paysage de …, lumière de fin de journée, très détaillée"),
    ("Texture", "Texture de … vue de près, uniforme, sans objet au centre"),
    ("Illustration", "Illustration de … dans le style …, couleurs vives"),
    ("Portrait", "Portrait photo d'une personne …, fond flou, lumière douce"),
]
# formats d'une nouvelle image : (nom, largeur, hauteur) ; environ 1 mégapixel (taille où Flux Schnell est à l'aise)
FORMATS_CREER = [
    ("Carré (pochette, réseaux sociaux)", 1024, 1024),
    ("Paysage 4:3", 1152, 864),
    ("Portrait 3:4", 864, 1152),
    ("Large 16:9", 1344, 768),
    ("Haut 9:16", 768, 1344),
]


def _reglages() -> QSettings:
    import os
    return QSettings("Pixane", os.environ.get("PIXANE_REGLAGES", "Pixane"))


class DialogueConsigne(QDialog):
    def __init__(self, parent=None, transparent: bool = False, avec_selection: bool = True, nb: int = 2,
                 creer: bool = False, image_ouverte: bool = False):
        """creer : « Créer une image d'après un texte » (Flux Schnell) au lieu de « Modifier » ; image_ouverte :
        le résultat peut aller dans un nouveau calque de l'image ouverte."""
        super().__init__(parent)
        self.creer = creer
        self._cle = "creer_derniere" if creer else "consigne_derniere"
        self.setWindowTitle(tr("Créer une image d'après un texte") if creer else tr("Modifier avec une consigne"))
        self.resize(560, 460 if creer else 420)
        lay = QVBoxLayout(self)
        if creer:
            intro = QLabel(tr("Décris l'image que l'IA doit créer : le sujet, les couleurs, la lumière, le style. "
                              "Plus c'est précis, mieux c'est. L'IA écrit mal les textes : ajoute-les plutôt "
                              "ensuite avec l'outil Texte."))
        else:
            quoi = tr("la zone sélectionnée") if avec_selection else tr("toute l'image (rien n'est sélectionné)")
            intro = QLabel(tr("Dis à l'IA ce qu'elle doit changer dans {quoi}. Elle garde le style de l'image ; ce "
                              "qui est hors de la sélection ne bouge pas. Mets entre guillemets un texte à écrire "
                              "tel quel : il n'est pas traduit.", quoi=quoi))
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
        for nom, modele in (EXEMPLES_CREER if creer else EXEMPLES):
            self.exemples.addItem(tr(nom), tr(modele))
        self.exemples.activated.connect(self._exemple)
        ligne.addWidget(self.exemples, 1)
        lay.addLayout(ligne)
        self.texte = QPlainTextEdit()
        self.texte.setPlaceholderText(
            tr("Ex. : Fond abstrait bleu nuit et or, fumée lumineuse, pour une pochette de disque") if creer else
            tr("Ex. : Remplace le texte « brûler le feu » par « Flamme », dans le même style"))
        self.texte.setPlainText(_reglages().value(self._cle, "") or "")
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
        self.ou = QComboBox()
        self.format = QComboBox()
        if creer:
            ligne = QHBoxLayout()
            ligne.addWidget(QLabel(tr("Résultat :")))
            if image_ouverte:
                self.ou.addItem(tr("Nouveau calque dans l'image ouverte (à sa taille)"), "calque")
            self.ou.addItem(tr("Nouvelle image"), "image")
            ligne.addWidget(self.ou, 1)
            lay.addLayout(ligne)
            ligne = QHBoxLayout()
            ligne.addWidget(QLabel(tr("Format :")))
            for nom, w, h in FORMATS_CREER:
                self.format.addItem(f"{tr(nom)} : {w} × {h} px", (w, h))
            self.format.setCurrentIndex(max(0, int(_reglages().value("creer_format", 0) or 0)))
            ligne.addWidget(self.format, 1)
            lay.addLayout(ligne)
            self.ou.currentIndexChanged.connect(lambda _i: self.format.setEnabled(self.ou.currentData() == "image"))
            self.format.setEnabled(self.ou.currentData() == "image")
        ligne = QHBoxLayout()
        ligne.addWidget(QLabel(tr("Propositions")))
        self.nb = QSpinBox()
        self.nb.setRange(1, 4)
        self.nb.setValue(nb)
        ligne.addWidget(self.nb)
        ligne.addWidget(QLabel(tr("(environ 30 secondes chacune)") if creer else
                               tr("(environ 2 à 3 minutes chacune)")))
        ligne.addStretch(1)
        lay.addLayout(ligne)
        boutons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        boutons.button(QDialogButtonBox.Ok).setText(tr("Créer") if creer else tr("Modifier"))
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
            self.etat.setText(tr("Traducteur non installé : l'IA ne comprend bien que l'anglais. Écris la consigne "
                                 "en anglais, ou installe le traducteur (français) : sinon le résultat sera au hasard."))
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
            self.etat.setText(tr("Décris d'abord l'image à créer.") if self.creer else
                              tr("Écris d'abord ce que l'IA doit faire."))
            return
        if not self.anglais.toPlainText().strip() and traduction.installe():
            self.traduire()
        if not self.anglais.toPlainText().strip() and not traduction.semble_anglais(self.texte.toPlainText()) \
                and not self._prevenir():
            return
        _reglages().setValue(self._cle, self.texte.toPlainText())
        if self.creer:
            _reglages().setValue("creer_format", self.format.currentIndex())
        super().accept()

    def _prevenir(self) -> bool:
        """Consigne pas en anglais, sans traduction : on prévient, mais on laisse le choix. -> True : envoyer."""
        m = QMessageBox(QMessageBox.Warning, tr("Consigne pas en anglais"), tr(
            "Ta consigne ne semble pas écrite en anglais, et elle n'est pas traduite.\n\n"
            "L'IA ne comprend bien que l'anglais : dans une autre langue (français, polonais…), elle devine, et le "
            "résultat est souvent au hasard (rien ne change, ou autre chose que ce que tu voulais).\n\n"
            "• Installer le traducteur (français → anglais, sur ton PC) ;\n"
            "• ou corriger : écrire la consigne en anglais ;\n"
            "• ou l'envoyer quand même, telle quelle."), parent=self)
        b_installer = m.addButton(tr("Installer le traducteur…"), QMessageBox.ActionRole) \
            if not traduction.installe() else None
        b_envoyer = m.addButton(tr("Envoyer quand même"), QMessageBox.AcceptRole)
        b_corriger = m.addButton(tr("Corriger"), QMessageBox.RejectRole)
        m.setDefaultButton(b_corriger)
        m.exec()
        if b_installer is not None and m.clickedButton() is b_installer:
            self._installer()
            if traduction.installe():
                self.traduire()          # traduit : la phrase anglaise est montrée, on vérifie puis on valide
            return False
        return m.clickedButton() is b_envoyer

    def consigne(self) -> str:
        """Ce qui part à l'IA : l'anglais s'il est rempli, sinon la consigne telle quelle (guillemets « » -> " ")."""
        t = self.anglais.toPlainText().strip() or self.texte.toPlainText().strip()
        return traduction.guillemets_droits(t)

    def nombre(self) -> int:
        return self.nb.value()

    def nouvelle_image(self) -> bool:
        """Créer : le résultat est une nouvelle image (sinon : un nouveau calque de l'image ouverte)."""
        return self.ou.currentData() != "calque"

    def taille(self) -> tuple[int, int]:
        """Créer, nouvelle image : largeur et hauteur choisies."""
        return self.format.currentData() or (1024, 1024)
