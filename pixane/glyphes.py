"""Fenêtre Glyphes (comme le panneau Glyphes de Photoshop) : tous les caractères de la police du texte ; un clic en
insère un dans le texte, à la place du curseur. Les derniers utilisés sont gardés en haut."""
from __future__ import annotations

import unicodedata

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QFont, QRawFont
from PySide6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout)

from .langue import tr

RECENTS_MAX = 24
# blocs parcourus : latin, grec, cyrillique, ponctuation, symboles, flèches, maths, formes, dingbats ; zone privée
# (polices de symboles comme Wingdings) ; émojis
PLAGES = [(0x21, 0x7E), (0xA1, 0x24F), (0x250, 0x2FF), (0x370, 0x3FF), (0x400, 0x4FF), (0x1E00, 0x1EFF),
          (0x2000, 0x2BFF), (0x2C60, 0x2C7F), (0xA720, 0xA7FF), (0xE000, 0xF8FF), (0xFB00, 0xFB4F),
          (0x1F300, 0x1FAFF)]


def caracteres(famille: str, gras: bool = False, italique: bool = False) -> list[str]:
    """Caractères que la police sait dessiner."""
    f = QFont(famille)
    f.setPixelSize(32)
    f.setBold(gras)
    f.setItalic(italique)
    f.setStyleStrategy(QFont.NoFontMerging)          # seulement la police elle-même (pas une police de secours)
    raw = QRawFont.fromFont(f)
    res = []
    for a, b in PLAGES:
        for code in range(a, b + 1):
            ch = chr(code)
            if unicodedata.category(ch) in ("Cc", "Cf", "Zs", "Zl", "Zp", "Mn", "Me", "Cs"):
                continue
            if raw.supportsCharacter(code):
                res.append(ch)
    return res


def nom_caractere(ch: str) -> str:
    try:
        nom = unicodedata.name(ch).lower()
    except ValueError:
        nom = ""
    return f"U+{ord(ch):04X}" + (f" — {nom}" if nom else "")


class FenetreGlyphes(QDialog):
    choisi = Signal(str)          # caractère à insérer

    def __init__(self, parent=None, recents: list[str] | None = None):
        super().__init__(parent)
        self.setWindowTitle(tr("Glyphes"))
        self.resize(560, 520)
        self.recents = list(recents or [])
        self.famille = ""
        self._tous: list[str] = []
        lay = QVBoxLayout(self)
        self.titre = QLabel()
        lay.addWidget(self.titre)
        ligne = QHBoxLayout()
        self.cherche = QLineEdit()
        self.cherche.setPlaceholderText(tr("Chercher (nom anglais : arrow, heart, euro… ou U+2192)"))
        self.cherche.setClearButtonEnabled(True)
        self.cherche.textChanged.connect(self._filtrer)
        ligne.addWidget(self.cherche)
        lay.addLayout(ligne)
        lay.addWidget(QLabel(tr("Derniers utilisés")))
        self.liste_recents = self._grille(1)
        lay.addWidget(self.liste_recents)
        self.liste = self._grille(0)
        lay.addWidget(self.liste, 1)
        self.info = QLabel(tr("Clique sur un caractère pour l'insérer dans le texte."))
        self.info.setObjectName("discret")
        lay.addWidget(self.info)

    def _grille(self, lignes: int) -> QListWidget:
        l = QListWidget()
        l.setViewMode(QListWidget.IconMode)
        l.setResizeMode(QListWidget.Adjust)
        l.setUniformItemSizes(True)
        l.setGridSize(QSize(40, 40))
        l.setMovement(QListWidget.Static)
        l.setMouseTracking(True)
        if lignes:
            l.setFixedHeight(48)
            l.setFlow(QListWidget.LeftToRight)
            l.setWrapping(False)
        l.itemClicked.connect(lambda it: self._choisir(it.data(Qt.UserRole)))
        l.itemEntered.connect(lambda it: self.info.setText(nom_caractere(it.data(Qt.UserRole))))
        return l

    def montrer_police(self, famille: str, gras: bool = False, italique: bool = False):
        self.famille = famille
        self.titre.setText(tr("Police : <b>{nom}</b>", nom=famille))
        self._police = QFont(famille)
        self._police.setPixelSize(22)
        self._police.setBold(gras)
        self._police.setItalic(italique)
        self._tous = caracteres(famille, gras, italique)
        self._filtrer()
        self._remplir(self.liste_recents, self.recents)

    def _remplir(self, liste: QListWidget, chars: list[str]):
        liste.clear()
        for ch in chars:
            it = QListWidgetItem(ch)
            it.setData(Qt.UserRole, ch)
            it.setFont(self._police)
            it.setTextAlignment(Qt.AlignCenter)
            it.setToolTip(nom_caractere(ch))
            it.setSizeHint(QSize(38, 38))
            liste.addItem(it)

    def _filtrer(self):
        q = self.cherche.text().strip().lower()
        chars = self._tous
        if q:
            if q.startswith("u+"):
                chars = [c for c in chars if f"u+{ord(c):04x}".startswith(q)]
            else:
                chars = [c for c in chars if q in nom_caractere(c).lower() or q == c]
        self._remplir(self.liste, chars)

    def _choisir(self, ch: str):
        if ch in self.recents:
            self.recents.remove(ch)
        self.recents.insert(0, ch)
        del self.recents[RECENTS_MAX:]
        self._remplir(self.liste_recents, self.recents)
        self.choisi.emit(ch)
