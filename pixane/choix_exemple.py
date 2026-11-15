"""Choisir un style (ciel, lumière) sur des vignettes d'exemple, au lieu d'une liste de mots.

Les vignettes sont dans ressources/exemples : une photo inventée par Flux Schnell (origine.webp), puis redessinée
par Flux Kontext avec chaque consigne de Pixane (ciel_<clé>.webp, lumiere_<clé>.webp).
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, QSize, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QGridLayout, QLabel, QToolButton, QVBoxLayout

from .langue import tr

DOSSIER = Path(__file__).resolve().parent / "ressources" / "exemples"
VIGNETTE = QSize(240, 180)


def vignette(nom: str) -> Path | None:
    f = DOSSIER / f"{nom}.webp"
    return f if f.is_file() else None


class ChoixExemple(QDialog):
    """Grille de vignettes ; un clic choisit, un double-clic choisit et valide."""

    def __init__(self, parent, titre: str, consigne: str, noms: dict, prefixe: str, dernier: str | None = None):
        super().__init__(parent)
        self.setWindowTitle(titre)
        self.cle = None
        lay = QVBoxLayout(self)
        info = QLabel(consigne)
        info.setWordWrap(True)
        lay.addWidget(info)
        grille = QGridLayout()
        grille.setSpacing(6)
        self.boutons = {}
        cases = [("", tr("Photo de départ"), vignette("origine"))] + [(k, n, vignette(f"{prefixe}_{k}"))
                                                                      for k, n in noms.items()]
        for i, (cle, nom, fichier) in enumerate(cases):
            b = QToolButton()
            b.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            b.setText(nom)
            b.setIconSize(VIGNETTE)
            b.setFixedWidth(VIGNETTE.width() + 16)
            if fichier is not None:
                b.setIcon(QIcon(QPixmap(str(fichier))))
            if cle:
                b.setCheckable(True)
                b.setAutoRaise(True)
                b.clicked.connect(lambda _=False, c=cle: self._choisir(c))
                b.installEventFilter(self)
                self.boutons[cle] = b
            else:
                b.setAutoRaise(True)                      # la photo de départ, pour comparer (pas un choix)
                b.setFocusPolicy(Qt.NoFocus)
                b.setToolTip(tr("La photo d'exemple avant le changement"))
            grille.addWidget(b, i // 4, i % 4)
        lay.addLayout(grille)
        note = QLabel(tr("Exemples faits par Pixane sur une photo inventée ; le résultat sur votre photo variera."))
        note.setWordWrap(True)
        note.setEnabled(False)
        lay.addWidget(note)
        self.ok_annuler = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.ok_annuler.accepted.connect(self.accept)
        self.ok_annuler.rejected.connect(self.reject)
        lay.addWidget(self.ok_annuler)
        self._choisir(dernier if dernier in self.boutons else next(iter(self.boutons)))

    def _choisir(self, cle: str):
        self.cle = cle
        for c, b in self.boutons.items():
            b.setChecked(c == cle)

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.MouseButtonDblClick and obj in self.boutons.values():
            self._choisir(next(c for c, b in self.boutons.items() if b is obj))
            self.accept()
            return True
        return super().eventFilter(obj, ev)


def choisir(parent, titre: str, consigne: str, noms: dict, prefixe: str, dernier: str | None = None) -> str | None:
    """Clé choisie, ou None si annulé."""
    d = ChoixExemple(parent, titre, consigne, noms, prefixe, dernier)
    return d.cle if d.exec() == QDialog.Accepted else None
