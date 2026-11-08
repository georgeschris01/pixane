"""Panneau Calques : liste (vignette, œil, nom), opacité, boutons nouveau / dupliquer / supprimer / monter /
descendre / fusionner / aplatir. Chaque action passe par `demande(etat, texte)` pour être annulable."""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (QGraphicsOpacityEffect, QHBoxLayout, QInputDialog, QLabel, QListWidget, QListWidgetItem, QSlider, QToolButton,
                               QVBoxLayout, QWidget)

from .document import Document
from .langue import tr

VIGNETTE = QSize(44, 34)


def damier(taille: QSize, case: int = 5) -> QPixmap:
    pm = QPixmap(taille)
    pm.fill(QColor(235, 235, 235))
    p = QPainter(pm)
    for y in range(0, taille.height(), case):
        for x in range(0, taille.width(), case):
            if (x // case + y // case) % 2:
                p.fillRect(x, y, case, case, QColor(200, 200, 200))
    p.end()
    return pm


class LigneCalque(QWidget):
    """Une ligne de la liste : œil, vignette, nom, cadenas."""
    oeil_clique = Signal()
    cadenas_clique = Signal()

    def __init__(self, icones):
        super().__init__()
        self.icones = icones            # fonction nom -> QIcon (couleurs du thème)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 3, 6, 3)
        lay.setSpacing(8)
        self.oeil = QToolButton()
        self.oeil.setAutoRaise(True)
        self.oeil.setToolTip(tr("Afficher / masquer le calque"))
        self.oeil.clicked.connect(self.oeil_clique)
        self.vignette = QLabel()
        self.vignette.setFixedSize(VIGNETTE)
        self.nom = QLabel()
        self.details = QLabel()
        self.details.setObjectName("discret")
        textes = QVBoxLayout()
        textes.setSpacing(0)
        textes.addWidget(self.nom)
        textes.addWidget(self.details)
        self.cadenas = QToolButton()
        self.cadenas.setAutoRaise(True)
        self.cadenas.clicked.connect(self.cadenas_clique)
        lay.addWidget(self.oeil)
        lay.addWidget(self.vignette)
        lay.addLayout(textes, 1)
        lay.addWidget(self.cadenas)

    def remplir(self, nom: str, visible: bool, opacite: float, vignette: QPixmap, verrou: bool = False,
                texte: bool = False, style: bool = False):
        self.oeil.setIcon(self.icones("oeil" if visible else "oeil_ferme"))
        self.cadenas.setIcon(self.icones("cadenas" if verrou else "cadenas_ouvert"))
        self.cadenas.setToolTip(tr("Calque verrouillé : cliquer pour le déverrouiller") if verrou else
                                tr("Verrouiller le calque (protège contre les modifications)"))
        effet = self.cadenas.graphicsEffect()
        if effet is None:
            effet = QGraphicsOpacityEffect(self.cadenas)
            self.cadenas.setGraphicsEffect(effet)
        effet.setOpacity(1.0 if verrou else 0.35)        # cadenas ouvert discret
        self.nom.setText(nom)
        self.nom.setEnabled(visible)
        details = [tr("texte")] if texte else []
        if style:
            details.append(tr("fx · style"))
        if opacite < 0.999:
            details.append(tr("opacité {n} %", n=round(opacite * 100)))
        self.details.setText(" · ".join(details))
        self.details.setVisible(bool(details))
        self.vignette.setPixmap(vignette)


class PanneauCalques(QWidget):
    demande = Signal(object, str)      # (nouvel état, texte pour Annuler)
    style_demande = Signal()           # double-clic sur un calque (hors du nom) ou bouton fx

    def __init__(self, icones):
        super().__init__()
        self.icones = icones
        self.doc: Document | None = None
        self._vignettes: dict[int, QPixmap] = {}
        self._avant_opacite = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 4, 10, 10)
        lay.setSpacing(6)

        self.liste = QListWidget()
        self.liste.setObjectName("calques")
        self.liste.setIconSize(VIGNETTE)
        self.liste.currentRowChanged.connect(self._ligne_choisie)
        self.liste.itemDoubleClicked.connect(self._double_clic)
        lay.addWidget(self.liste, 1)

        opacite = QHBoxLayout()
        opacite.addWidget(QLabel(tr("Opacité")))
        self.curseur = QSlider(Qt.Horizontal)
        self.curseur.setRange(0, 100)
        self.curseur.sliderPressed.connect(self._opacite_debut)
        self.curseur.valueChanged.connect(self._opacite_change)
        self.curseur.sliderReleased.connect(self._opacite_fin)
        self.valeur = QLabel("100 %")
        self.valeur.setMinimumWidth(42)
        opacite.addWidget(self.curseur, 1)
        opacite.addWidget(self.valeur)
        lay.addLayout(opacite)

        boutons = QHBoxLayout()
        boutons.setSpacing(2)
        self.boutons = {}
        # bulles d'aide : tr("Nouveau calque vide"), tr("Fusionner avec le calque du dessous"),
        # tr("Aplatir l'image (un seul calque)") ; les autres sont déjà traduites ailleurs
        for nom, aide, action in (("calque_nouveau", "Nouveau calque vide", self.nouveau),
                                  ("dupliquer", tr("Dupliquer le calque"), self.dupliquer),
                                  ("style", tr("Style du calque (ombre, contour, lueur…)"), self.style_demande.emit),
                                  ("monter", tr("Monter le calque"), lambda: self.deplacer(+1)),
                                  ("descendre", tr("Descendre le calque"), lambda: self.deplacer(-1)),
                                  ("fusionner", "Fusionner avec le calque du dessous", self.fusionner),
                                  ("aplatir", "Aplatir l'image (un seul calque)", self.aplatir),
                                  ("supprimer", tr("Supprimer le calque"), self.supprimer)):
            b = QToolButton()
            b.setAutoRaise(True)
            b.setToolTip(tr(aide))
            b.setIconSize(QSize(18, 18))
            b.clicked.connect(action)
            self.boutons[nom] = b
            boutons.addWidget(b)
        boutons.addStretch(1)
        lay.addLayout(boutons)
        self.appliquer_icones()
        self.rafraichir()

    # ---------------------------------------------------------- document
    def definir_document(self, doc: Document | None):
        if self.doc is not None:
            try:
                self.doc.calques_changes.disconnect(self.rafraichir)
            except (RuntimeError, TypeError):
                pass
        self.doc = doc
        self._vignettes.clear()
        if doc is not None:
            doc.calques_changes.connect(self.rafraichir)
        self.rafraichir()

    def appliquer_icones(self):
        for nom, b in self.boutons.items():
            b.setIcon(self.icones(nom))
        self.rafraichir()

    def _vignette(self, img: QImage) -> QPixmap:
        cle = img.cacheKey()
        if cle not in self._vignettes:
            pm = damier(VIGNETTE)
            petit = img.scaled(VIGNETTE, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            p = QPainter(pm)
            p.drawImage((VIGNETTE.width() - petit.width()) // 2, (VIGNETTE.height() - petit.height()) // 2, petit)
            p.end()
            if len(self._vignettes) > 200:
                self._vignettes.clear()
            self._vignettes[cle] = pm
        return self._vignettes[cle]

    def rafraichir(self):
        doc = self.doc
        n = len(doc.calques) if doc else 0
        self.liste.blockSignals(True)
        while self.liste.count() > n:
            self.liste.takeItem(self.liste.count() - 1)
        while self.liste.count() < n:
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, VIGNETTE.height() + 8))
            self.liste.addItem(item)
            ligne = LigneCalque(self.icones)
            ligne.oeil_clique.connect(lambda l=ligne: self._oeil(l))
            ligne.cadenas_clique.connect(lambda l=ligne: self._cadenas(l))
            self.liste.setItemWidget(item, ligne)
        for rang in range(n):                       # rang 0 = calque du haut
            index = n - 1 - rang
            c = doc.calques[index]
            ligne = self.liste.itemWidget(self.liste.item(rang))
            ligne.index = index
            ligne.remplir(c.nom, c.visible, c.opacite, self._vignette(c.image), c.verrou, c.texte is not None,
                          c.style is not None and not c.style.vide())
        if doc:
            self.liste.setCurrentRow(n - 1 - doc.actif)
            if not self.curseur.isSliderDown():
                self.curseur.blockSignals(True)
                self.curseur.setValue(round(doc.calque_actif.opacite * 100))
                self.curseur.blockSignals(False)
            self.valeur.setText(f"{self.curseur.value()} %")
        self.liste.blockSignals(False)
        for nom, b in self.boutons.items():
            b.setEnabled(bool(doc))
        verrou = bool(doc) and doc.calque_actif.verrou
        if doc:
            self.boutons["supprimer"].setEnabled(doc.etat_supprimer() is not None)
            self.boutons["aplatir"].setEnabled(n > 1 and not any(c.verrou for c in doc.calques))
            self.boutons["fusionner"].setEnabled(doc.actif > 0 and not verrou and not doc.calques[doc.actif - 1].verrou)
            self.boutons["monter"].setEnabled(doc.actif < n - 1)
            self.boutons["descendre"].setEnabled(doc.actif > 0)
        self.curseur.setEnabled(bool(doc) and not verrou)
        self.curseur.setToolTip(tr("Calque verrouillé") if verrou else "")

    # ---------------------------------------------------------- actions
    def _ligne_choisie(self, rang: int):
        """Changer de calque actif n'est pas une retouche : pas d'entrée dans Annuler."""
        if self.doc and rang >= 0:
            self.doc.actif = len(self.doc.calques) - 1 - rang
            self.doc.calques_changes.emit()        # panneau, canevas et panneau Texte suivent

    def _oeil(self, ligne: LigneCalque):
        c = self.doc.calques[ligne.index]
        texte = tr("Masquer le calque") if c.visible else tr("Afficher le calque")
        self.demande.emit(self.doc.etat_calque_modifie(ligne.index, visible=not c.visible), texte)

    def _cadenas(self, ligne: LigneCalque):
        c = self.doc.calques[ligne.index]
        texte = tr("Déverrouiller le calque") if c.verrou else tr("Verrouiller le calque")
        self.demande.emit(self.doc.etat_calque_modifie(ligne.index, verrou=not c.verrou), texte)

    def _opacite_debut(self):
        self._avant_opacite = self.doc.etat()

    def _opacite_change(self, v: int):
        self.valeur.setText(f"{v} %")
        if not self.doc:
            return
        etat = self.doc.etat_calque_modifie(self.doc.actif, opacite=v / 100)
        if self.curseur.isSliderDown():
            self.doc.appliquer_etat(etat)              # aperçu en direct ; l'entrée Annuler est créée au lâcher
        else:
            self.demande.emit(etat, tr("Opacité du calque"))

    def _opacite_fin(self):
        if self._avant_opacite is not None:
            apres = self.doc.etat()
            avant, self._avant_opacite = self._avant_opacite, None
            self.doc.appliquer_etat(avant)
            self.demande.emit(apres, tr("Opacité du calque"))

    def nouveau(self):
        self.demande.emit(self.doc.etat_nouveau_calque(), tr("Nouveau calque"))

    def dupliquer(self):
        self.demande.emit(self.doc.etat_dupliquer(), tr("Dupliquer le calque"))

    def deplacer(self, sens: int):
        etat = self.doc.etat_deplacer(self.doc.actif, self.doc.actif + sens)
        if etat:
            self.demande.emit(etat, tr("Monter le calque") if sens > 0 else tr("Descendre le calque"))

    def fusionner(self):
        etat = self.doc.etat_fusionner_bas()
        if etat:
            self.demande.emit(etat, tr("Fusionner les calques"))

    def aplatir(self):
        etat = self.doc.etat_aplatir()
        if etat:
            self.demande.emit(etat, tr("Aplatir l'image"))

    def supprimer(self):
        etat = self.doc.etat_supprimer()
        if etat:
            self.demande.emit(etat, tr("Supprimer le calque"))

    def _double_clic(self, item):
        """Comme Photoshop : double-clic sur le nom = renommer ; ailleurs sur la ligne = style du calque."""
        ligne = self.liste.itemWidget(item)
        p = ligne.nom.mapFromGlobal(QCursor.pos()) if ligne is not None else None
        largeur = ligne.nom.fontMetrics().horizontalAdvance(ligne.nom.text()) + 10 if ligne is not None else 0
        if p is not None and 0 <= p.y() < ligne.nom.height() and p.x() < largeur:
            self.renommer()
        else:
            self.style_demande.emit()

    def renommer(self):
        if not self.doc:
            return
        c = self.doc.calque_actif
        nom, ok = QInputDialog.getText(self, tr("Renommer le calque"), tr("Nom :"), text=c.nom)
        if ok and nom.strip() and nom.strip() != c.nom:
            self.demande.emit(self.doc.etat_calque_modifie(self.doc.actif, nom=nom.strip()), tr("Renommer le calque"))
