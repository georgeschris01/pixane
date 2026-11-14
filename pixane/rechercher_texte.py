"""Édition > Rechercher et remplacer (Ctrl+H) : dans tous les calques de texte de l'image (comme Photoshop).
Les styles propres à certaines lettres suivent les mots remplacés ; « Tout remplacer » = une seule étape d'Annuler."""
from __future__ import annotations

import re

from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (QCheckBox, QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                               QVBoxLayout)

from .langue import tr


def motif(cherche: str, casse: bool, mot_entier: bool) -> re.Pattern | None:
    if not cherche:
        return None
    m = re.escape(cherche)
    if mot_entier:
        m = r"(?<!\w)" + m + r"(?!\w)"
    return re.compile(m, 0 if casse else re.IGNORECASE)


def remplacer_tout(t, rx: re.Pattern, par: str):
    """(texte modifié, nombre de remplacements) ; remplacés de la fin vers le début, un à un, pour que les styles
    par lettre restent sur les bonnes lettres."""
    trouves = list(rx.finditer(t.texte))
    for m in reversed(trouves):
        t = t.avec_texte(t.texte[:m.start()] + par + t.texte[m.end():])
    return t, len(trouves)


class FenetreRechercher(QDialog):
    def __init__(self, fenetre):
        super().__init__(fenetre)
        self.fenetre = fenetre
        self.setWindowTitle(tr("Rechercher et remplacer dans les textes"))
        self.resize(460, 0)
        self.position = None              # (index du calque, fin de la dernière trouvaille)
        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.cherche = QLineEdit()
        self.cherche.textChanged.connect(lambda: self._effacer_info())
        self.par = QLineEdit()
        form.addRow(tr("Rechercher"), self.cherche)
        form.addRow(tr("Remplacer par"), self.par)
        lay.addLayout(form)
        ligne = QHBoxLayout()
        self.casse = QCheckBox(tr("Respecter les majuscules"))
        self.mot = QCheckBox(tr("Mot entier"))
        ligne.addWidget(self.casse)
        ligne.addWidget(self.mot)
        ligne.addStretch(1)
        lay.addLayout(ligne)
        self.info = QLabel(tr("Cherche dans tous les calques de texte de l'image (même cachés ou verrouillés : "
                              "ceux-là ne sont pas modifiés)."))
        self.info.setObjectName("discret")
        self.info.setWordWrap(True)
        lay.addWidget(self.info)
        ligne = QHBoxLayout()
        ligne.addStretch(1)
        for texte, fonction in ((tr("Suivant"), self.suivant), (tr("Remplacer"), self.remplacer),
                                (tr("Tout remplacer"), self.tout_remplacer), (tr("Fermer"), self.close)):
            b = QPushButton(texte)
            b.clicked.connect(fonction)
            ligne.addWidget(b)
            if fonction == self.suivant:
                b.setDefault(True)
        lay.addLayout(ligne)

    def _effacer_info(self):
        self.position = None

    def _motif(self):
        return motif(self.cherche.text(), self.casse.isChecked(), self.mot.isChecked())

    def _textes(self):
        doc = self.fenetre.doc
        return [] if doc is None else [i for i, c in enumerate(doc.calques) if c.texte is not None]

    def suivant(self) -> bool:
        """Montre la prochaine trouvaille : le calque de texte est choisi, le mot sélectionné dans le panneau."""
        rx = self._motif()
        doc = self.fenetre.doc
        indices = self._textes()
        if rx is None or not indices:
            self.info.setText(tr("Aucun texte dans l'image.") if not indices else tr("Tape le texte à chercher."))
            return False
        trouves = [(i, m.start(), m.end()) for i in indices for m in rx.finditer(doc.calques[i].texte.texte)]
        if trouves:
            i0, p0 = self.position if self.position else (-1, 0)
            suite = [x for x in trouves if x[0] > i0 or (x[0] == i0 and x[1] >= p0)]
            i, a, b = (suite or trouves)[0]                    # après la dernière ; au bout : on repart du début
            self._montrer(i, a, b)
            return True
        self.position = None
        self.info.setText(tr("« {mot} » est introuvable.", mot=self.cherche.text()))
        return False

    def _montrer(self, i: int, a: int, b: int):
        f = self.fenetre
        from .canevas import TEXTE
        if f.canevas.outil != TEXTE:
            f._choisir_outil(TEXTE)
        if f.doc.actif != i:
            f._texte_choisi(i)
        f._sync_texte()
        saisie = f.panneau_texte.saisie
        c = saisie.textCursor()
        c.setPosition(a)
        c.setPosition(b, QTextCursor.KeepAnchor)
        saisie.setTextCursor(c)
        self.position = (i, b)
        self.info.setText(tr("Trouvé dans « {nom} ».", nom=f.doc.calques[i].nom))

    def remplacer(self):
        """Remplace la trouvaille sélectionnée, puis montre la suivante."""
        rx = self._motif()
        f = self.fenetre
        if rx is None or f.doc is None:
            return
        saisie = f.panneau_texte.saisie
        c = saisie.textCursor()
        choisi = c.selectedText()
        if self.position and f.doc.actif == self.position[0] and choisi and rx.fullmatch(choisi):
            if f.doc.calque_actif.verrou:
                self.info.setText(tr("Ce calque de texte est verrouillé."))
            else:
                c.insertText(self.par.text())
                self.position = (f.doc.actif, c.position())
        self.suivant()

    def tout_remplacer(self):
        from .fenetre import CommandeEtat
        rx = self._motif()
        f = self.fenetre
        doc = f.doc
        if rx is None or doc is None:
            return
        nouveaux = {}
        total = 0
        for i in self._textes():
            c = doc.calques[i]
            if c.verrou:
                continue
            t, n = remplacer_tout(c.texte, rx, self.par.text())
            if n:
                nouveaux[i] = t
                total += n
        if not total:
            self.info.setText(tr("« {mot} » est introuvable.", mot=self.cherche.text()))
            return
        f.historique.push(CommandeEtat(doc, doc.etat(), doc.etat_textes_modifies(nouveaux),
                                       tr("Remplacer dans les textes")))
        f._sync_texte()
        self.position = None
        self.info.setText(tr("{n} remplacement(s) dans {c} texte(s).", n=total, c=len(nouveaux)))
