"""Fenêtre « Trouver une police semblable » : les lettres sélectionnées dans l'image, les lettres tapées par
l'utilisateur, puis les polices installées les plus proches (écrites avec ces lettres, pour comparer d'un coup
d'œil). Un clic applique la police au texte choisi, ou crée un texte avec elle."""
from __future__ import annotations

import numpy as np
from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (QApplication, QDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                               QProgressBar, QPushButton, QVBoxLayout)

from . import polices_semblables as ps
from .langue import tr

ECHANTILLON = QSize(460, 64)


def echantillon(texte: str, r: ps.Resultat, taille: QSize = ECHANTILLON) -> QPixmap:
    """Le texte écrit avec cette police, noir sur blanc, ajusté à la case."""
    img = QImage(taille, QImage.Format_ARGB32_Premultiplied)
    img.fill(QColor(255, 255, 255))
    p = QPainter(img)
    p.setRenderHint(QPainter.TextAntialiasing)
    f = r.police(48)
    p.setFont(f)
    rect = p.boundingRect(QRect(0, 0, 10000, 1000), Qt.AlignLeft | Qt.AlignTop, texte)
    k = min((taille.width() - 16) / max(1, rect.width()), (taille.height() - 8) / max(1, rect.height()), 1.5)
    f.setPixelSize(max(6, int(48 * k)))
    p.setFont(f)
    p.setPen(QColor(20, 20, 20))
    p.drawText(QRect(8, 0, taille.width() - 16, taille.height()), Qt.AlignVCenter | Qt.AlignLeft, texte)
    p.end()
    return QPixmap.fromImage(img)


class FenetrePolices(QDialog):
    def __init__(self, lettres_image: QImage, masque: np.ndarray, texte_depart: str, peut_appliquer: bool,
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Trouver une police semblable"))
        self.masque = masque
        self.resultats: list[ps.Resultat] = []
        self.choisi: ps.Resultat | None = None
        self.action = None                     # "appliquer" ou "creer"
        self._arret = False
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(tr("Les lettres de l'image :")))
        vue = QLabel()
        pm = QPixmap.fromImage(lettres_image)
        if pm.height() > 90 or pm.width() > 560:
            pm = pm.scaled(560, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        vue.setPixmap(pm)
        vue.setStyleSheet("background: white; padding: 6px;")
        vue.setAlignment(Qt.AlignCenter)
        lay.addWidget(vue)
        ligne = QHBoxLayout()
        ligne.addWidget(QLabel(tr("Tape les mêmes lettres :")))
        self.texte = QLineEdit(texte_depart)
        self.texte.setPlaceholderText(tr("ex. DISCO"))
        self.texte.returnPressed.connect(self.chercher)
        ligne.addWidget(self.texte, 1)
        self.b_chercher = QPushButton(tr("Chercher"))
        self.b_chercher.setDefault(True)
        self.b_chercher.clicked.connect(self.chercher)
        ligne.addWidget(self.b_chercher)
        lay.addLayout(ligne)
        aide = QLabel(tr("Respecte les majuscules et les minuscules, et les retours à la ligne s'il y en a "
                         "(Maj+Entrée n'existe pas ici : sépare les lignes par « / »)."))
        aide.setObjectName("discret")
        aide.setWordWrap(True)
        lay.addWidget(aide)
        self.progres = QProgressBar()
        self.progres.setVisible(False)
        lay.addWidget(self.progres)
        self.etat = QLabel()
        self.etat.setObjectName("discret")
        lay.addWidget(self.etat)
        self.liste = QListWidget()
        self.liste.setIconSize(ECHANTILLON)
        self.liste.setMinimumSize(ECHANTILLON.width() + 220, 380)
        self.liste.currentRowChanged.connect(self._maj_boutons)
        self.liste.itemDoubleClicked.connect(lambda _it: self._finir("appliquer" if peut_appliquer else "creer"))
        lay.addWidget(self.liste, 1)
        bas = QHBoxLayout()
        self.b_appliquer = QPushButton(tr("Appliquer au texte choisi"))
        self.b_appliquer.setVisible(peut_appliquer)
        self.b_appliquer.clicked.connect(lambda: self._finir("appliquer"))
        self.b_creer = QPushButton(tr("Créer un texte avec cette police"))
        self.b_creer.setToolTip(tr("Nouveau calque de texte, à la place des lettres sélectionnées, avec les lettres "
                                   "tapées. Les lettres de l'image restent : efface-les ensuite si besoin."))
        self.b_creer.clicked.connect(lambda: self._finir("creer"))
        self.b_copier = QPushButton(tr("Copier le nom"))
        self.b_copier.clicked.connect(self._copier)
        fermer = QPushButton(tr("Fermer"))
        fermer.clicked.connect(self.reject)
        for b in (self.b_appliquer, self.b_creer, self.b_copier):
            bas.addWidget(b)
        bas.addStretch(1)
        bas.addWidget(fermer)
        lay.addLayout(bas)
        self._maj_boutons()
        self.resize(760, 640)

    def lettres(self) -> str:
        return "\n".join(l.strip() for l in self.texte.text().split("/") if l.strip())

    def chercher(self) -> None:
        texte = self.lettres()
        if not texte:
            self.etat.setText(tr("Tape d'abord les lettres que tu vois dans l'image."))
            return
        if self.b_chercher.text() == tr("Arrêter"):
            self._arret = True
            return
        self._arret = False
        self.b_chercher.setText(tr("Arrêter"))
        self.texte.setEnabled(False)
        self.liste.clear()
        self.progres.setVisible(True)
        self.progres.setValue(0)
        manquantes = sum(1 for f in ps.familles() if f not in ps.memoire())
        self.etat.setText(tr("Première fois : Pixane prépare tes {n} polices, une seule fois. La durée dépend de leur "
                             "nombre (environ 1 min 20 pour 1 200 polices)…",
                             n=manquantes) if manquantes > 50 else tr("Recherche…"))

        def progres(fait, total):
            self.progres.setMaximum(total)
            self.progres.setValue(fait)
            QApplication.processEvents()
            return not self._arret
        try:
            self.resultats = ps.chercher(self.masque, texte, 12, progres)
        finally:
            self.b_chercher.setText(tr("Chercher"))
            self.texte.setEnabled(True)
            self.progres.setVisible(False)
        if self._arret:
            self.etat.setText(tr("Recherche arrêtée."))
            return
        for r in self.resultats:
            style = " ".join(x for x in (tr("gras") if r.gras else "", tr("italique") if r.italique else "") if x)
            it = QListWidgetItem(QIcon(echantillon(texte, r)), f"{r.famille}{'  ·  ' + style if style else ''}\n"
                                 + tr("ressemblance : {n} %", n=round(r.score)))
            it.setData(Qt.UserRole, r)
            self.liste.addItem(it)
        if self.resultats:
            self.liste.setCurrentRow(0)
            self.etat.setText(tr("Les plus proches d'abord. Double-clic pour l'utiliser."))
        else:
            self.etat.setText(tr("Rien trouvé : vérifie les lettres tapées et la sélection (les lettres seules)."))

    def _maj_boutons(self, *_a) -> None:
        it = self.liste.currentItem()
        self.choisi = it.data(Qt.UserRole) if it is not None else None
        for b in (self.b_appliquer, self.b_creer, self.b_copier):
            b.setEnabled(self.choisi is not None)

    def _copier(self) -> None:
        if self.choisi is not None:
            QApplication.clipboard().setText(self.choisi.famille)
            self.etat.setText(tr("Nom copié : {nom}", nom=self.choisi.famille))

    def _finir(self, action: str) -> None:
        if self.choisi is not None:
            self.action = action
            self.accept()
