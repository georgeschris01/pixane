"""Barre du haut des outils Formes (U) et Plume (P) : genre de forme, remplissage, contour, épaisseur, côtés ; mode de
la Plume (calque de forme ou sélection). Calque de forme choisi : la barre montre ses réglages et les lui applique
(comme le calque de pinceau)."""
from __future__ import annotations

from PySide6.QtCore import QSize
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QLabel, QSpinBox, QWidget

from . import calque_forme
from .langue import tr

FORMES_OUTIL, PLUME_OUTIL = "formes", "plume"


class OptionsForme:
    def _options_forme(self, tout: QHBoxLayout):
        from .dialogue_style import ChampCouleur
        c = self.canevas
        r = self.reglages
        self._sync_forme = False
        self._forme_montree = None
        self.opt_formes = QWidget()
        lay = QHBoxLayout(self.opt_formes)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        self.opt_genre = QComboBox()
        for k, n in calque_forme.noms_genres().items():
            self.opt_genre.addItem(n, k)
        self.opt_genre.setCurrentIndex(max(0, self.opt_genre.findData(r.value("forme", "rectangle"))))
        lay.addWidget(self.opt_genre)
        self.opt_mode_plume = QComboBox()
        self.opt_mode_plume.addItem(tr("Forme"), "forme")
        self.opt_mode_plume.addItem(tr("Sélection"), "selection")
        self.opt_mode_plume.setToolTip(tr("Le tracé fini devient un calque de forme, ou une sélection (Maj : "
                                          "ajouter, Alt : retirer, au moment de finir)"))
        self.opt_mode_plume.setCurrentIndex(max(0, self.opt_mode_plume.findData(r.value("plume_mode", "forme"))))
        lay.addWidget(self.opt_mode_plume)
        self.opt_cotes_label = QLabel(tr("Côtés"))
        lay.addWidget(self.opt_cotes_label)
        self.opt_cotes = QSpinBox()
        self.opt_cotes.setRange(3, 40)
        self.opt_cotes.setValue(int(r.value("forme_cotes", 5)))
        self.opt_cotes.setToolTip(tr("Nombre de côtés du polygone, ou de branches de l'étoile"))
        lay.addWidget(self.opt_cotes)
        self.opt_remplir = QCheckBox(tr("Remplissage"))
        self.opt_remplir.setChecked(r.value("forme_remplie", "true") == "true")
        lay.addWidget(self.opt_remplir)
        self.opt_couleur_forme = ChampCouleur(r.value("forme_couleur", "#e04030"))
        self.opt_couleur_forme.setFixedSize(40, 24)
        self.opt_couleur_forme.setIconSize(QSize(26, 12))
        lay.addWidget(self.opt_couleur_forme)
        self.opt_contour = QCheckBox(tr("Contour"))
        self.opt_contour.setChecked(r.value("forme_contour", "false") == "true")
        lay.addWidget(self.opt_contour)
        self.opt_couleur_contour = ChampCouleur(r.value("forme_couleur_contour", "#000000"))
        self.opt_couleur_contour.setFixedSize(40, 24)
        self.opt_couleur_contour.setIconSize(QSize(26, 12))
        lay.addWidget(self.opt_couleur_contour)
        self.opt_epaisseur = QSpinBox()
        self.opt_epaisseur.setRange(1, 500)
        self.opt_epaisseur.setSuffix(" px")
        self.opt_epaisseur.setValue(int(r.value("forme_epaisseur", 6)))
        self.opt_epaisseur.setToolTip(tr("Épaisseur du contour (et de la ligne ou de la flèche)"))
        lay.addWidget(self.opt_epaisseur)
        for w in (self.opt_genre, self.opt_mode_plume):
            w.currentIndexChanged.connect(self._forme_barre_change)
        for w in (self.opt_cotes, self.opt_epaisseur):
            w.valueChanged.connect(self._forme_barre_change)
        for w in (self.opt_remplir, self.opt_contour):
            w.toggled.connect(self._forme_barre_change)
        for w in (self.opt_couleur_forme, self.opt_couleur_contour):
            w.change.connect(self._forme_barre_change)
        tout.addWidget(self.opt_formes)
        self.opt_formes.hide()
        self._forme_barre_change()

    def montrer_options_forme(self, outil: str):
        self.opt_formes.setVisible(outil in (FORMES_OUTIL, PLUME_OUTIL))
        plume = outil == PLUME_OUTIL
        self.opt_genre.setVisible(not plume)
        self.opt_mode_plume.setVisible(plume)
        self._maj_visibles_forme()
        if outil in (FORMES_OUTIL, PLUME_OUTIL):
            self._forme_montree = None
            self.sync_calque_forme()

    def _maj_visibles_forme(self):
        plume = self.canevas.outil == PLUME_OUTIL
        genre = self.opt_genre.currentData()
        cotes = not plume and genre in ("etoile", "polygone")
        self.opt_cotes_label.setVisible(cotes)
        self.opt_cotes.setVisible(cotes)
        ouvert = not plume and genre in calque_forme.OUVERTS
        selection = plume and self.opt_mode_plume.currentData() == "selection"
        for w in (self.opt_remplir, self.opt_couleur_forme):
            w.setVisible(not ouvert and not selection)
        self.opt_contour.setVisible(not ouvert and not selection)
        for w in (self.opt_couleur_contour, self.opt_epaisseur):
            w.setVisible(not selection)

    def _forme_barre_change(self, *_):
        c = self.canevas
        r = self.reglages
        c.forme = self.opt_genre.currentData()
        c.forme_cotes = self.opt_cotes.value()
        c.forme_remplie = self.opt_remplir.isChecked()
        c.forme_contour = self.opt_contour.isChecked()
        c.forme_couleur = QColor(self.opt_couleur_forme.valeur)
        c.forme_couleur_contour = QColor(self.opt_couleur_contour.valeur)
        c.forme_epaisseur = self.opt_epaisseur.value()
        c.plume_mode = self.opt_mode_plume.currentData()
        self._maj_visibles_forme()
        if self._sync_forme:
            return
        for cle, v in (("forme", c.forme), ("forme_cotes", c.forme_cotes), ("plume_mode", c.plume_mode),
                       ("forme_remplie", "true" if c.forme_remplie else "false"),
                       ("forme_contour", "true" if c.forme_contour else "false"),
                       ("forme_couleur", self.opt_couleur_forme.valeur),
                       ("forme_couleur_contour", self.opt_couleur_contour.valeur),
                       ("forme_epaisseur", c.forme_epaisseur)):
            r.setValue(cle, v)
        self._barre_vers_calque_forme()

    # ---------------------------------------------------------- calque de forme choisi
    def sync_calque_forme(self):
        """Calque de forme choisi, avec Formes ou Plume : la barre montre ses réglages."""
        if not getattr(self, "doc", None) or self.canevas.outil not in (FORMES_OUTIL, PLUME_OUTIL) \
                or self._sync_forme:
            return
        f = calque_forme.valide(self.doc.calque_actif)
        if f is None or f is self._forme_montree:
            if f is None:
                self._forme_montree = None
            return
        self._forme_montree = f
        self._sync_forme = True
        try:
            ouvert = f.ouverts() and not f.remplissage
            if not ouvert:
                self.opt_remplir.setChecked(bool(f.remplissage))
                self.opt_contour.setChecked(bool(f.contour))
            if f.remplissage:
                self.opt_couleur_forme.valeur = QColor(f.remplissage).name()
                self.opt_couleur_forme._peindre()
            if f.contour:
                self.opt_couleur_contour.valeur = QColor(f.contour).name()
                self.opt_couleur_contour._peindre()
            self.opt_epaisseur.setValue(round(f.epaisseur))
            self._forme_barre_change()
        finally:
            self._sync_forme = False

    def _barre_vers_calque_forme(self):
        """Un réglage de la barre a changé : le calque de forme choisi le prend (une étape d'Annuler)."""
        from .fenetre import CommandeEtat
        doc = getattr(self, "doc", None)
        if not doc or self.canevas.outil not in (FORMES_OUTIL, PLUME_OUTIL):
            return
        c = doc.calque_actif
        f = calque_forme.valide(c)
        if f is None or c.verrou:
            return
        ouvert = f.ouverts() and not f.remplissage
        couleur = QColor(self.opt_couleur_forme.valeur).name(QColor.HexArgb)
        contour = QColor(self.opt_couleur_contour.valeur).name(QColor.HexArgb)
        if ouvert:
            n = f.avec(contour=contour, epaisseur=float(self.opt_epaisseur.value()))
        else:
            remplir, trait = self.opt_remplir.isChecked(), self.opt_contour.isChecked()
            if not remplir and not trait:       # ni l'un ni l'autre : la forme disparaîtrait
                trait = True
            n = f.avec(remplissage=couleur if remplir else "", contour=contour if trait else "",
                       epaisseur=float(self.opt_epaisseur.value()))
        if (n.remplissage, n.contour, n.epaisseur) == (f.remplissage, f.contour, f.epaisseur):
            return
        avant = doc.etat()
        apres = doc.etat_forme(doc.actif, n)
        self.historique.push(CommandeEtat(doc, avant, apres, tr("Modifier la forme")))
        self._forme_montree = calque_forme.valide(doc.calque_actif)
