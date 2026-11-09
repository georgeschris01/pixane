"""Panneau Texte : réglages du calque de texte choisi (ou du prochain texte si aucun n'est choisi).

Chaque changement est envoyé par `modifie(texte, champ)` ; la fenêtre en fait une entrée d'Annuler
(les changements successifs d'un même réglage sont regroupés).
"""
from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QColorDialog, QDoubleSpinBox, QFontComboBox, QFormLayout,
                               QFrame, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QScrollArea, QSpinBox,
                               QToolButton, QVBoxLayout, QWidget)

from .calques import damier
from .langue import tr
from .texte import CENTRE, DROITE, GAUCHE, Texte


class BoutonCouleur(QToolButton):
    """Pastille de couleur ; un clic ouvre le choix de couleur (avec la transparence)."""
    change = Signal(str)

    def __init__(self, titre: str):
        super().__init__()
        self.titre = titre
        self.couleur = "#ffffffff"
        self.setIconSize(QSize(34, 16))
        self.setToolTip(titre)
        self.setCursor(Qt.PointingHandCursor)
        self.clicked.connect(self._choisir)
        self.definir(self.couleur)

    def definir(self, couleur: str):
        self.couleur = couleur
        pm = damier(QSize(34, 16), 4)
        p = QPainter(pm)
        p.fillRect(pm.rect(), QColor(couleur))
        p.setPen(QColor(0, 0, 0, 90))
        p.drawRect(pm.rect().adjusted(0, 0, -1, -1))
        p.end()
        self.setIcon(pm)

    def _choisir(self):
        c = QColorDialog.getColor(QColor(self.couleur), self, self.titre, QColorDialog.ShowAlphaChannel)
        if c.isValid():
            self.definir(c.name(QColor.HexArgb))
            self.change.emit(self.couleur)


def _titre(texte: str) -> QLabel:
    l = QLabel(f"<b>{texte}</b>")
    l.setContentsMargins(0, 8, 0, 0)
    return l


class PanneauTexte(QScrollArea):
    modifie = Signal(object, str)        # (nouveau Texte, nom du réglage changé)

    def __init__(self, icones):
        super().__init__()
        self.icones = icones
        self.defaut = Texte(texte="")    # réglages du prochain texte
        self.t = self.defaut
        self.lie = False                 # vrai si les réglages affichés sont ceux d'un calque de texte
        self._remplissage = False
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(10, 4, 10, 10)
        lay.setSpacing(6)
        self.aide = QLabel()
        self.aide.setObjectName("discret")
        self.aide.setWordWrap(True)
        lay.addWidget(self.aide)

        self.saisie = QPlainTextEdit()
        self.saisie.setFixedHeight(76)
        self.saisie.setPlaceholderText(tr("Écris ton texte ici"))
        self.saisie.textChanged.connect(lambda: self._changer("texte", self.saisie.toPlainText()))
        lay.addWidget(self.saisie)

        # ---- caractères
        lay.addWidget(_titre(tr("Caractères")))
        self.police = QFontComboBox()
        self.police.currentFontChanged.connect(lambda f: self._changer("police", f.family()))
        lay.addWidget(self.police)
        ligne = QHBoxLayout()
        self.taille = self._entier(4, 5000, " px", "taille")
        self.taille.setToolTip(tr("Taille des lettres, en pixels de la photo"))
        self.couleur = BoutonCouleur(tr("Couleur du texte"))
        self.couleur.change.connect(lambda c: self._changer("couleur", c))
        ligne.addWidget(self.taille, 1)
        ligne.addWidget(self.couleur)
        lay.addLayout(ligne)

        ligne = QHBoxLayout()
        ligne.setSpacing(2)
        self.styles = {}
        for champ, lettre, aide, style in (("gras", tr("G|gras"), tr("Gras"), "bold"),
                                           ("italique", tr("I|italique"), tr("Italique"), "italic"),
                                           ("souligne", tr("S|souligné"), tr("Souligné"), "underline"),
                                           ("barre", tr("B|barré"), tr("Barré"), "strike")):
            b = QToolButton()
            b.setText(lettre)
            b.setCheckable(True)
            b.setToolTip(aide)
            b.setFixedSize(30, 28)
            f = QFont(b.font())
            f.setBold(style == "bold")
            f.setItalic(style == "italic")
            f.setUnderline(style == "underline")
            f.setStrikeOut(style == "strike")
            b.setFont(f)
            b.toggled.connect(lambda oui, c=champ: self._changer(c, oui))
            self.styles[champ] = b
            ligne.addWidget(b)
        ligne.addSpacing(10)
        self.alignements = {}
        groupe = QButtonGroup(self)
        for valeur, nom, aide in ((GAUCHE, "aligner_gauche", tr("Aligner à gauche")),
                                  (CENTRE, "aligner_centre", tr("Centrer")),
                                  (DROITE, "aligner_droite", tr("Aligner à droite"))):
            b = QToolButton()
            b.setCheckable(True)
            b.setToolTip(aide)
            b.setFixedSize(30, 28)
            b.clicked.connect(lambda _=False, v=valeur: self._changer("alignement", v))
            groupe.addButton(b)
            self.alignements[valeur] = (b, nom)
            ligne.addWidget(b)
        ligne.addStretch(1)
        lay.addLayout(ligne)

        form = self._formulaire(lay)
        self.lettres = self._entier(-50, 300, " %", "lettres")
        self.lettres.setToolTip(tr("Espace ajouté entre les lettres, en % de la taille"))
        form.addRow(tr("Lettres"), self.lettres)
        self.interligne = QDoubleSpinBox()
        self.interligne.setRange(0.5, 5.0)
        self.interligne.setSingleStep(0.1)
        self.interligne.setDecimals(2)
        self.interligne.setSuffix(" ×")
        self.interligne.setToolTip(tr("Écart entre les lignes, × la taille des lettres"))
        self.interligne.valueChanged.connect(lambda v: self._changer("interligne", v))
        form.addRow(tr("Lignes"), self.interligne)

        # ---- disposition
        lay.addWidget(_titre(tr("Disposition")))
        form = self._formulaire(lay)
        self.angle = self._entier(-180, 180, "°", "angle")
        self.angle.setToolTip(tr("Rotation (aussi avec la poignée ronde au-dessus du texte)"))
        form.addRow(tr("Rotation"), self.angle)
        self.courbe = self._entier(-360, 360, "°", "courbe")
        self.courbe.setToolTip(tr("Texte en arc : positif = en voûte, négatif = en creux, 360 = cercle complet"))
        form.addRow(tr("Courbe"), self.courbe)

        # ---- effets
        self.effets = {}
        for cle, titre, reglages in (
                ("contour", tr("Contour"), (("contour_epaisseur", tr("Épaisseur"), 1, 100, " %"),)),
                ("ombre", tr("Ombre portée"), (("ombre_distance", tr("Distance"), 0, 300, " %"),
                                               ("ombre_direction", tr("Direction"), 0, 359, "°"),
                                               ("ombre_flou", tr("Flou"), 0, 300, " %"))),
                ("fond", tr("Fond"), (("fond_marge", tr("Marge"), 0, 300, " %"),
                                      ("fond_arrondi", tr("Arrondi"), 0, 200, " %")))):
            ligne = QHBoxLayout()
            case = QCheckBox(titre)
            case.setStyleSheet("font-weight: bold")
            case.toggled.connect(lambda oui, c=cle: self._changer(c, oui))
            couleur = BoutonCouleur(tr("Couleur : {effet}", effet=titre))
            couleur.change.connect(lambda c, ch=cle + "_couleur": self._changer(ch, c))
            ligne.addWidget(case, 1)
            ligne.addWidget(couleur)
            lay.addSpacing(6)
            lay.addLayout(ligne)
            form = self._formulaire(lay)
            cases = {}
            for champ, nom, mini, maxi, suffixe in reglages:
                s = self._entier(mini, maxi, suffixe, champ)
                if suffixe == " %":
                    s.setToolTip(tr("En % de la taille des lettres"))
                form.addRow(nom, s)
                cases[champ] = s
            self.effets[cle] = (case, couleur, cases)
        note = QLabel(tr("Transparence : curseur Opacité du panneau Calques, ou la couleur (canal alpha)."))
        note.setObjectName("discret")
        note.setWordWrap(True)
        lay.addSpacing(6)
        lay.addWidget(note)
        lay.addStretch(1)
        self.setWidget(w)
        self.appliquer_icones()
        self.afficher(None)

    # ---------------------------------------------------------- construction
    @staticmethod
    def _formulaire(lay) -> QFormLayout:
        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(4)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        lay.addLayout(form)
        return form

    def _entier(self, mini: int, maxi: int, suffixe: str, champ: str) -> QSpinBox:
        s = QSpinBox()
        s.setRange(mini, maxi)
        s.setSuffix(suffixe)
        s.setKeyboardTracking(False)
        s.valueChanged.connect(lambda v: self._changer(champ, float(v)))
        return s

    def appliquer_icones(self):
        for b, nom in self.alignements.values():
            b.setIcon(self.icones(nom))

    # ---------------------------------------------------------- affichage
    def afficher(self, t: Texte | None, verrou: bool = False):
        """Montre les réglages du calque de texte `t`, ou ceux du prochain texte (t = None)."""
        self.lie = t is not None
        self.t = t if t is not None else self.defaut
        t = self.t
        self._remplissage = True
        try:
            if self.saisie.toPlainText() != (t.texte if self.lie else ""):
                self.saisie.setPlainText(t.texte if self.lie else "")
            self.saisie.setEnabled(self.lie and not verrou)
            self.police.setCurrentFont(QFont(t.police))
            self.taille.setValue(round(t.taille))
            self.couleur.definir(t.couleur)
            for champ, b in self.styles.items():
                b.setChecked(getattr(t, champ))
            for valeur, (b, _) in self.alignements.items():
                b.setChecked(valeur == t.alignement)
            self.lettres.setValue(round(t.lettres))
            self.interligne.setValue(t.interligne)
            self.angle.setValue(round(t.angle))
            self.courbe.setValue(round(t.courbe))
            for cle, (case, couleur, cases) in self.effets.items():
                case.setChecked(getattr(t, cle))
                couleur.definir(getattr(t, cle + "_couleur"))
                for champ, s in cases.items():
                    s.setValue(round(getattr(t, champ)))
        finally:
            self._remplissage = False
        self.taille.setEnabled(self.lie)       # sans texte choisi, la taille est calculée d'après la photo
        self.angle.setEnabled(self.lie)
        if verrou:
            self.aide.setText(tr("Ce calque de texte est verrouillé : clique sur son cadenas pour le modifier."))
        elif self.lie:
            self.aide.setText(tr("Le texte s'applique au fur et à mesure, rien à valider. Glisse-le pour le "
                                 "déplacer, la poignée ronde le tourne. Clique ailleurs pour un autre texte."))
        else:
            self.aide.setText(tr("Clique sur la photo pour écrire un texte, ou sur un texte existant pour le "
                                 "modifier. Les réglages ci-dessous serviront pour le prochain texte."))

    def commencer_saisie(self):
        """Nouveau texte : on peut taper tout de suite (le texte proposé est sélectionné)."""
        self.saisie.setFocus()
        self.saisie.selectAll()

    # ---------------------------------------------------------- changements
    def _changer(self, champ: str, valeur):
        if self._remplissage or getattr(self.t, champ) == valeur:
            return
        self.t = replace(self.t, **{champ: valeur})
        if champ not in ("texte", "x", "y", "angle", "taille", "courbe"):
            self.defaut = replace(self.defaut, **{champ: valeur})      # le prochain texte reprend ce style
        if self.lie:
            self.modifie.emit(self.t, champ)
