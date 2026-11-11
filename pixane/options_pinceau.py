"""Barre d'options : choix du pinceau (forme de la bibliothèque) et ses réglages, pour le pinceau de couleur (et
les masques), la gomme de calque et le pinceau de sélection. Un choix par groupe d'outils, gardé d'une fois sur
l'autre."""
from __future__ import annotations

import json

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QToolButton, QWidget

from .bibliotheque import PINCEAUX, STYLES, bibliotheque
from .canevas import GOMME_CALQUE, GROUPE_OUTIL, GROUPES_PINCEAU
from .langue import tr
from .pointe import Reglages


class OptionsPinceau:
    """Mélangé à Fenetre (self.canevas, self.reglages)."""

    def _options_pinceau(self, tout: QHBoxLayout):
        self.opt_pinceau = QWidget()
        lay = QHBoxLayout(self.opt_pinceau)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        lay.addWidget(QLabel(tr("Pinceau")))
        self.bouton_pinceau = QToolButton()
        self.bouton_pinceau.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.bouton_pinceau.setIconSize(QSize(22, 22))
        self.bouton_pinceau.setToolTip(tr("Forme du pinceau : rond, ou un pinceau de la bibliothèque (Krita, "
                                          "Photoshop .abr, GIMP…)"))
        self.bouton_pinceau.clicked.connect(self.choisir_pinceau)
        lay.addWidget(self.bouton_pinceau)
        self.bouton_reglages_pinceau = QPushButton(tr("Réglages…"))
        self.bouton_reglages_pinceau.setToolTip(tr("Espacement, angle, dispersion, texture, double pinceau, "
                                                   "couleur, tablette"))
        self.bouton_reglages_pinceau.clicked.connect(self.regler_pinceau)
        lay.addWidget(self.bouton_reglages_pinceau)
        tout.addWidget(self.opt_pinceau)
        for g in GROUPES_PINCEAU:                      # choix gardés
            cle = self.reglages.value(f"pinceau_{g}_cle", "") or None
            try:
                r = Reglages.depuis_dict(json.loads(self.reglages.value(f"pinceau_{g}_reglages", "{}") or "{}"))
            except (ValueError, TypeError):
                r = Reglages()
            if cle is not None and bibliotheque().trouver(PINCEAUX, cle) is None:
                cle = None                             # pinceau retiré de la bibliothèque depuis
            self.canevas.pinceaux[g] = {"cle": cle, "reglages": r}

    def _groupe_pinceau(self) -> str | None:
        return GROUPE_OUTIL.get(self.canevas.outil)

    def maj_bouton_pinceau(self):
        g = self._groupe_pinceau()
        self.opt_pinceau.setVisible(g is not None)
        if g is None:
            return
        choix = self.canevas.pinceaux[g]
        e = bibliotheque().trouver(PINCEAUX, choix["cle"]) if choix["cle"] else None
        if e is None:
            self.bouton_pinceau.setText(tr("Rond"))
            self.bouton_pinceau.setIcon(QIcon())
        else:
            from .choix_bibliotheque import vignette
            self.bouton_pinceau.setText(e.nom if len(e.nom) <= 22 else e.nom[:21] + "…")
            self.bouton_pinceau.setIcon(QIcon(QPixmap.fromImage(vignette(e, 22))))
        regle = choix["reglages"] != Reglages()
        self.bouton_reglages_pinceau.setText(tr("Réglages…") + (" •" if regle else ""))

    def _enregistrer_pinceau(self, g: str):
        choix = self.canevas.pinceaux[g]
        self.reglages.setValue(f"pinceau_{g}_cle", choix["cle"] or "")
        self.reglages.setValue(f"pinceau_{g}_reglages", json.dumps(choix["reglages"].vers_dict()))
        self.maj_bouton_pinceau()

    def choisir_pinceau(self):
        from .choix_bibliotheque import ChoixBibliotheque
        g = self._groupe_pinceau()
        if g is None:
            return
        d = ChoixBibliotheque(PINCEAUX, self, cle=self.canevas.pinceaux[g]["cle"], avec_rond=True)
        if not d.exec():
            return
        cle = d.choisi.cle if d.choisi is not None else None
        ancien = self.canevas.pinceaux[g]
        r = ancien["reglages"]
        if d.choisi is not None and d.choisi.reglages is not None:
            r = Reglages.depuis_dict(d.choisi.reglages)          # style prêt : ses réglages
        elif (ancien["cle"] or "").startswith(STYLES + "/") and cle != ancien["cle"]:
            r = Reglages()                             # on quitte un style prêt : réglages de départ
        elif cle != ancien["cle"]:
            from dataclasses import replace
            r = replace(r, espacement=None)            # nouvelle forme : son propre espacement
        self.canevas.pinceaux[g] = {"cle": cle, "reglages": r}
        self._enregistrer_pinceau(g)

    def regler_pinceau(self):
        from .reglages_pinceau import ReglagesPinceau
        g = self._groupe_pinceau()
        if g is None:
            return
        choix = self.canevas.pinceaux[g]
        e = bibliotheque().trouver(PINCEAUX, choix["cle"]) if choix["cle"] else None
        pointe = self.canevas._pointe(choix["cle"]) if e is not None else None
        d = ReglagesPinceau(choix["reglages"], pointe, self.canevas.taille_pinceau,
                            1.0 if g != "peinture" else self.canevas.durete, self.canevas.couleur_peinture, self,
                            gomme=self.canevas.outil == GOMME_CALQUE, nom_pinceau=e.nom if e else tr("Rond"))
        if d.exec():
            self.canevas.pinceaux[g] = {"cle": choix["cle"], "reglages": d.reglages}
            self._enregistrer_pinceau(g)
