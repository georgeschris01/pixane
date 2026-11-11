"""Fenêtre « Réglages du pinceau » (comme le panneau Pinceaux de Photoshop) : forme, dispersion, texture, double
pinceau, couleur, transfert et tablette, avec un aperçu du trait qui suit chaque changement."""
from __future__ import annotations

import math
from dataclasses import replace

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLabel, QPushButton,
                               QSpinBox, QTabWidget, QVBoxLayout, QWidget)

from .bibliotheque import MOTIFS, PINCEAUX, bibliotheque
from .langue import tr
from .pointe import Pointe, Reglages
from .retouche import GOMME, Trait

# (attribut, libellé, genre, minimum, maximum, onglet, aide) ; genre : « % » (0..1 affiché en %), « ° », « n », « oui »
CHAMPS = [
    ("espacement", "Espacement", "%", 1, 1000, "Forme", "Écart entre deux touches, en part de la taille du pinceau "
                                                        "(25 % : trait continu ; 150 % : touches séparées)"),
    ("angle", "Angle", "°", -180, 180, "Forme", "Rotation de la forme"),
    ("suivre", "L'angle suit le trait", "oui", 0, 0, "Forme", "La forme tourne avec la direction du trait (comme "
                                                             "une plume ou un pinceau plat)"),
    ("rondeur", "Rondeur", "%", 2, 100, "Forme", "100 % : forme d'origine ; moins : écrasée"),
    ("dispersion", "Dispersion", "%", 0, 1000, "Dispersion", "Les touches s'écartent du trait au hasard (en part "
                                                             "de la taille)"),
    ("deux_axes", "Sur les deux axes", "oui", 0, 0, "Dispersion", "Aussi le long du trait (sinon : de part et "
                                                                  "d'autre seulement)"),
    ("nombre", "Nombre", "n", 1, 16, "Dispersion", "Touches posées à chaque pas"),
    ("var_taille", "Variation de taille", "%", 0, 100, "Dispersion", "Taille différente à chaque touche"),
    ("taille_min", "Taille minimale", "%", 0, 100, "Dispersion", "Plancher de la variation et de la pression"),
    ("var_angle", "Variation d'angle", "%", 0, 100, "Dispersion", "100 % : un tour complet au hasard"),
    ("var_rondeur", "Variation de rondeur", "%", 0, 100, "Dispersion", ""),
    ("texture_echelle", "Échelle", "%", 10, 1000, "Texture", "Taille du motif"),
    ("texture_force", "Force", "%", 0, 100, "Texture", "100 % : le motif creuse le trait à fond"),
    ("texture_inverser", "Inverser", "oui", 0, 0, "Texture", "Les parties claires du motif creusent au lieu des "
                                                             "foncées"),
    ("double_taille", "Taille", "%", 5, 300, "Double pinceau", "Taille de la deuxième forme, en part du pinceau"),
    ("double_espacement", "Espacement", "%", 1, 1000, "Double pinceau", ""),
    ("double_dispersion", "Dispersion", "%", 0, 1000, "Double pinceau", ""),
    ("var_teinte", "Variation de teinte", "%", 0, 100, "Couleur", "À chaque touche, la couleur change un peu"),
    ("var_saturation", "Variation de saturation", "%", 0, 100, "Couleur", ""),
    ("var_luminosite", "Variation de luminosité", "%", 0, 100, "Couleur", ""),
    ("melange_fond", "Mélange avec le blanc", "%", 0, 100, "Couleur", "Chaque touche va plus ou moins vers le blanc"),
    ("flux", "Flux", "%", 1, 100, "Transfert", "Force de chaque touche : à moins de 100 %, les touches s'ajoutent "
                                               "(comme l'aérographe)"),
    ("var_opacite", "Variation d'opacité", "%", 0, 100, "Transfert", ""),
    ("var_flux", "Variation de flux", "%", 0, 100, "Transfert", ""),
    ("pression_taille", "La pression change la taille", "oui", 0, 0, "Tablette", "Stylet : appuyer plus fort = "
                                                                                 "trait plus large"),
    ("pression_opacite", "La pression change l'opacité", "oui", 0, 0, "Tablette", ""),
    ("pression_flux", "La pression change le flux", "oui", 0, 0, "Tablette", ""),
]
ONGLETS = ["Forme", "Dispersion", "Texture", "Double pinceau", "Couleur", "Transfert", "Tablette"]


def apercu_trait(pointe: Pointe | None, r: Reglages, taille: float, durete: float, couleur: QColor,
                 largeur: int = 420, hauteur: int = 110, gomme: bool = False, texture=None,
                 double: Pointe | None = None) -> QImage:
    """Un trait en S, qui s'affine (pression simulée de 0,3 à 1 puis 0,3) : montre l'effet des réglages."""
    fond = QImage(largeur, hauteur, QImage.Format_ARGB32_Premultiplied)
    fond.fill(QColor(70, 120, 200) if gomme else QColor(250, 248, 242))
    base = QImage(fond) if gomme else QImage(largeur, hauteur, QImage.Format_ARGB32_Premultiplied)
    if not gomme:
        base.fill(Qt.transparent)
    t = min(taille, hauteur * 0.45)
    if pointe is not None:
        pointe.indice = 0
    tr_ = Trait(GOMME if gomme else "peinture", base, t, durete, 1.0, couleur=couleur, pointe=pointe,
                reglages=r, texture=texture, double=double, graine=7)
    n = 80
    for i in range(n + 1):
        f = i / n
        x = 20 + f * (largeur - 40)
        y = hauteur / 2 + hauteur * 0.22 * math.sin(f * 2 * math.pi)
        tr_.ajouter(QPointF(x, y), 0.3 + 0.7 * math.sin(f * math.pi))
    if gomme:
        return tr_.image
    p = QPainter(fond)
    p.drawImage(0, 0, tr_.image)
    p.end()
    return fond


class ReglagesPinceau(QDialog):
    """Après exec() accepté : self.reglages (Reglages)."""

    def __init__(self, reglages: Reglages, pointe: Pointe | None, taille: float, durete: float, couleur: QColor,
                 parent=None, gomme: bool = False, nom_pinceau: str = ""):
        super().__init__(parent)
        self.setWindowTitle(tr("Réglages du pinceau") + (f" — {nom_pinceau}" if nom_pinceau else ""))
        self.reglages = replace(reglages)
        self.pointe, self.taille, self.durete, self.couleur, self.gomme = pointe, taille, durete, couleur, gomme
        self._espacement_pinceau = pointe.espacement if pointe is not None else 0.08
        self.cases: dict = {}
        onglets = QTabWidget()
        formulaires = {}
        for nom in ONGLETS:
            w = QWidget()
            formulaires[nom] = QFormLayout(w)
            onglets.addTab(w, tr(nom))
        # texture et double pinceau : choix du motif / de la forme
        self.bouton_texture = QPushButton()
        self.bouton_texture.clicked.connect(lambda: self._choisir(MOTIFS))
        self.sans_texture = QPushButton(tr("Aucune"))
        self.sans_texture.clicked.connect(lambda: self._definir("texture", None))
        ligne = QHBoxLayout()
        ligne.addWidget(self.bouton_texture, 1)
        ligne.addWidget(self.sans_texture)
        formulaires["Texture"].addRow(tr("Motif"), ligne)
        self.bouton_double = QPushButton()
        self.bouton_double.clicked.connect(lambda: self._choisir(PINCEAUX))
        self.sans_double = QPushButton(tr("Aucun"))
        self.sans_double.clicked.connect(lambda: self._definir("double", None))
        ligne = QHBoxLayout()
        ligne.addWidget(self.bouton_double, 1)
        ligne.addWidget(self.sans_double)
        formulaires["Double pinceau"].addRow(tr("Deuxième forme"), ligne)
        for attr, libelle, genre, mini, maxi, onglet, aide in CHAMPS:
            if genre == "oui":
                c = QCheckBox(tr(libelle))
                c.toggled.connect(self._lire)
                formulaires[onglet].addRow(c)
            else:
                c = QSpinBox()
                c.setRange(mini, maxi)
                c.setSuffix({"%": " %", "°": " °", "n": ""}[genre])
                c.valueChanged.connect(self._lire)
                formulaires[onglet].addRow(tr(libelle), c)
            if aide:
                c.setToolTip(tr(aide))
            self.cases[attr] = (c, genre)
        explication = {
            "Texture": "Le motif « troue » le trait, comme une craie sur un papier à grain.",
            "Double pinceau": "Une deuxième forme découpe la première : le trait n'apparaît que là où les deux se "
                              "croisent.",
            "Tablette": "Avec un stylet de tablette graphique. À la souris, la pression vaut toujours 100 %.",
        }
        for onglet, texte in explication.items():
            l_ = QLabel(tr(texte))
            l_.setWordWrap(True)
            formulaires[onglet].insertRow(0, l_)
        self.apercu = QLabel()
        self.apercu.setMinimumHeight(110)
        self.apercu.setAlignment(Qt.AlignCenter)
        self.bouton_defaut = QPushButton(tr("Valeurs par défaut"))
        self.bouton_defaut.clicked.connect(self._defaut)
        boutons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        boutons.accepted.connect(self.accept)
        boutons.rejected.connect(self.reject)
        bas = QHBoxLayout()
        bas.addWidget(self.bouton_defaut)
        bas.addStretch(1)
        bas.addWidget(boutons)
        lay = QVBoxLayout(self)
        lay.addWidget(onglets, 1)
        lay.addWidget(QLabel(tr("Aperçu (la pression simulée va de faible à forte puis faible) :")))
        lay.addWidget(self.apercu)
        lay.addLayout(bas)
        self._remplir()

    # ------------------------------------------------------------------
    def _remplir(self):
        r = self.reglages
        for attr, (c, genre) in self.cases.items():
            c.blockSignals(True)
            v = getattr(r, attr)
            if attr == "espacement" and v is None:
                v = self._espacement_pinceau
            if genre == "oui":
                c.setChecked(bool(v))
            elif genre == "%":
                c.setValue(round(v * 100))
            else:
                c.setValue(int(round(v)))
            c.blockSignals(False)
        self._maj_noms()
        self._maj_apercu()

    def _maj_noms(self):
        b = bibliotheque()
        m = b.trouver(MOTIFS, self.reglages.texture) if self.reglages.texture else None
        self.bouton_texture.setText(m.nom if m is not None else tr("Choisir un motif…"))
        d = b.trouver(PINCEAUX, self.reglages.double) if self.reglages.double else None
        self.bouton_double.setText(d.nom if d is not None else tr("Choisir une forme…"))

    def _lire(self, *_):
        valeurs = {}
        for attr, (c, genre) in self.cases.items():
            if genre == "oui":
                valeurs[attr] = c.isChecked()
            elif genre == "%":
                valeurs[attr] = c.value() / 100
            else:
                valeurs[attr] = c.value()
        if abs(valeurs["espacement"] - self._espacement_pinceau) < 0.005:
            valeurs["espacement"] = None             # celui du pinceau
        self.reglages = replace(self.reglages, **valeurs)
        self._maj_apercu()

    def _definir(self, attr: str, valeur):
        self.reglages = replace(self.reglages, **{attr: valeur})
        self._maj_noms()
        self._maj_apercu()

    def _choisir(self, genre: str):
        from .choix_bibliotheque import ChoixBibliotheque
        cle = self.reglages.texture if genre == MOTIFS else self.reglages.double
        d = ChoixBibliotheque(genre, self, cle=cle)
        if d.exec() and d.choisi is not None:
            self._definir("texture" if genre == MOTIFS else "double", d.choisi.cle)

    def _defaut(self):
        self.reglages = Reglages()
        self._remplir()

    def _maj_apercu(self):
        b = bibliotheque()
        r = self.reglages
        m = b.trouver(MOTIFS, r.texture) if r.texture else None
        d = b.trouver(PINCEAUX, r.double) if r.double else None
        img = apercu_trait(self.pointe, r, self.taille, self.durete, self.couleur, gomme=self.gomme,
                           texture=m.image if m is not None else None,
                           double=Pointe(d.formes, d.espacement) if d is not None else None)
        self.apercu.setPixmap(QPixmap.fromImage(img))
