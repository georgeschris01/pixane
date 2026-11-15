"""Nuancier (comme le panneau Nuancier de Photoshop) : des couleurs enregistrées (celles d'un artiste, d'un label…),
réutilisables partout. Un clic : couleur de peinture. Importer un nuancier Photoshop (.aco) ou GIMP (.gpl), exporter
en .aco. Les 16 premières couleurs sont aussi dans « Couleurs personnalisées » de chaque fenêtre de choix de couleur.
"""
from __future__ import annotations

import colorsys
import json
import os
import struct
from pathlib import Path

from PySide6.QtCore import QSettings, QSize, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (QColorDialog, QFileDialog, QHBoxLayout, QInputDialog, QListWidget, QListWidgetItem,
                               QMenu, QMessageBox, QToolButton, QVBoxLayout, QWidget)

from .langue import tr

DEPART = ["#000000", "#ffffff", "#808080", "#c0c0c0", "#e53935", "#fb8c00", "#fdd835", "#43a047", "#00897b",
          "#1e88e5", "#3949ab", "#8e24aa", "#d81b60", "#6d4c41", "#f5f5dc", "#1a237e", "#b71c1c", "#ffd700"]


def _reglages() -> QSettings:
    return QSettings("Pixane", os.environ.get("PIXANE_REGLAGES", "Pixane"))


def charger() -> list[tuple[str, str]]:
    """[(nom, "#rrggbb"), …]"""
    try:
        d = json.loads(_reglages().value("nuancier", "") or "null")
        if isinstance(d, list):
            return [(str(n), QColor(c).name()) for n, c in d if QColor(c).isValid()]
    except (ValueError, TypeError):
        pass
    return [("", c) for c in DEPART]


def enregistrer(couleurs: list[tuple[str, str]]):
    _reglages().setValue("nuancier", json.dumps([[n, c] for n, c in couleurs], ensure_ascii=False))
    partager(couleurs)


def partager(couleurs: list[tuple[str, str]]):
    """Les 16 premières couleurs dans « Couleurs personnalisées » des fenêtres de choix de couleur (QColorDialog)."""
    for i in range(QColorDialog.customCount()):
        QColorDialog.setCustomColor(i, QColor(couleurs[i][1]) if i < len(couleurs) else QColor(255, 255, 255))


# ------------------------------------------------------------------ fichiers
def lire_aco(octets: bytes) -> list[tuple[str, str]]:
    """Nuancier Photoshop .aco (version 1, et version 2 avec les noms) : RVB, TSL (HSB), CMJN, gris."""
    def couleurs_v(pos: int, avec_noms: bool):
        version, n = struct.unpack_from(">HH", octets, pos)
        pos += 4
        res = []
        for _ in range(n):
            espace, w, x, y, z = struct.unpack_from(">HHHHH", octets, pos)
            pos += 10
            nom = ""
            if avec_noms:
                _zero, longueur = struct.unpack_from(">HI", octets, pos)
                pos += 6
                nom = octets[pos:pos + 2 * longueur].decode("utf-16-be", "replace").rstrip("\x00")
                pos += 2 * longueur
            if espace == 0:
                c = QColor.fromRgbF(w / 65535, x / 65535, y / 65535)
            elif espace == 1:
                r, v, b = colorsys.hsv_to_rgb(w / 65535, x / 65535, y / 65535)
                c = QColor.fromRgbF(r, v, b)
            elif espace == 2:                              # CMJN, valeurs inversées (65535 = 0 %)
                c = QColor.fromCmykF(1 - w / 65535, 1 - x / 65535, 1 - y / 65535, 1 - z / 65535).toRgb()
            elif espace == 8:
                g = w / 10000
                c = QColor.fromRgbF(g, g, g)
            else:                                          # Lab et autres : pas pris
                continue
            res.append(("" if nom.lower() == c.name() else nom, c.name()))   # nom = code couleur : pas de nom
        return res, pos, version

    v1, fin, version = couleurs_v(0, False)
    if version == 1 and fin + 4 <= len(octets):
        try:
            v2, _f, version2 = couleurs_v(fin, True)
            if version2 == 2:
                return v2
        except (struct.error, UnicodeDecodeError):
            pass
    if version == 2:
        return couleurs_v(0, True)[0]
    return v1


def ecrire_aco(couleurs: list[tuple[str, str]]) -> bytes:
    """Version 1 puis version 2 (avec les noms), comme Photoshop."""
    def rvb(c):
        q = QColor(c)
        return struct.pack(">HHHHH", 0, q.red() * 257, q.green() * 257, q.blue() * 257, 0)
    o = struct.pack(">HH", 1, len(couleurs)) + b"".join(rvb(c) for _n, c in couleurs)
    o += struct.pack(">HH", 2, len(couleurs))
    for n, c in couleurs:
        nom = (n or QColor(c).name()) + "\x00"
        o += rvb(c) + struct.pack(">HI", 0, len(nom)) + nom.encode("utf-16-be")
    return o


def lire_gpl(texte: str) -> list[tuple[str, str]]:
    """Palette GIMP .gpl : « R G B nom » par ligne."""
    res = []
    for ligne in texte.splitlines():
        p = ligne.split(None, 3)
        if len(p) >= 3 and all(x.isdigit() for x in p[:3]):
            r, v, b = (min(255, int(x)) for x in p[:3])
            res.append((p[3].strip() if len(p) > 3 else "", QColor(r, v, b).name()))
    return res


def lire_fichier(chemin: str) -> list[tuple[str, str]]:
    p = Path(chemin)
    if p.suffix.lower() == ".gpl":
        return lire_gpl(p.read_text(encoding="utf-8", errors="replace"))
    return lire_aco(p.read_bytes())


# ------------------------------------------------------------------ panneau
class PanneauNuancier(QWidget):
    choisi = Signal(str)                 # "#rrggbb"

    def __init__(self, couleur_actuelle, parent=None):
        super().__init__(parent)
        self.couleur_actuelle = couleur_actuelle          # fonction : la couleur de peinture (QColor)
        self.couleurs = charger()
        partager(self.couleurs)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        self.liste = QListWidget()
        self.liste.setViewMode(QListWidget.IconMode)
        self.liste.setIconSize(QSize(24, 24))
        self.liste.setGridSize(QSize(30, 30))
        self.liste.setMovement(QListWidget.Static)
        self.liste.setResizeMode(QListWidget.Adjust)
        self.liste.setSpacing(0)
        self.liste.setSelectionMode(QListWidget.SingleSelection)
        self.liste.itemClicked.connect(lambda it: self.choisi.emit(it.data(Qt.UserRole)))
        self.liste.setContextMenuPolicy(Qt.CustomContextMenu)
        self.liste.customContextMenuRequested.connect(self._menu_couleur)
        lay.addWidget(self.liste, 1)
        bas = QHBoxLayout()
        self.b_ajouter = QToolButton()
        self.b_ajouter.setText("+")
        self.b_ajouter.setToolTip(tr("Ajouter la couleur de peinture au nuancier"))
        self.b_ajouter.clicked.connect(self.ajouter)
        self.b_retirer = QToolButton()
        self.b_retirer.setText("−")
        self.b_retirer.setToolTip(tr("Retirer la couleur choisie du nuancier"))
        self.b_retirer.clicked.connect(self.retirer)
        self.b_plus = QToolButton()
        self.b_plus.setText("…")
        self.b_plus.setToolTip(tr("Importer, exporter, remettre les couleurs de départ"))
        self.b_plus.setPopupMode(QToolButton.InstantPopup)
        m = QMenu(self.b_plus)
        m.addAction(tr("Importer un nuancier (Photoshop .aco, GIMP .gpl)…"), self.importer)
        m.addAction(tr("Exporter le nuancier (.aco, pour Photoshop)…"), self.exporter)
        m.addSeparator()
        m.addAction(tr("Remettre les couleurs de départ"), self.remettre)
        self.b_plus.setMenu(m)
        for b in (self.b_ajouter, self.b_retirer, self.b_plus):
            bas.addWidget(b)
        bas.addStretch(1)
        lay.addLayout(bas)
        self._remplir()

    def _remplir(self):
        self.liste.clear()
        for nom, c in self.couleurs:
            pm = QPixmap(24, 24)
            pm.fill(QColor(c))
            p = QPainter(pm)                     # contour gris : le blanc se voit sur un fond blanc
            p.setPen(QColor(128, 128, 128, 160))
            p.drawRect(0, 0, 23, 23)
            p.end()
            it = QListWidgetItem(QIcon(pm), "")
            it.setData(Qt.UserRole, c)
            it.setToolTip(f"{nom} ({c})" if nom else c)
            self.liste.addItem(it)

    def _changer(self, couleurs):
        self.couleurs = couleurs
        enregistrer(couleurs)
        self._remplir()

    def ajouter(self):
        c = QColor(self.couleur_actuelle()).name()
        self._changer(self.couleurs + [("", c)])
        self.liste.setCurrentRow(len(self.couleurs) - 1)

    def retirer(self):
        i = self.liste.currentRow()
        if 0 <= i < len(self.couleurs):
            self._changer(self.couleurs[:i] + self.couleurs[i + 1:])

    def renommer(self, i: int):
        nom, ok = QInputDialog.getText(self, tr("Nuancier"), tr("Nom de la couleur :"), text=self.couleurs[i][0])
        if ok:
            liste = list(self.couleurs)
            liste[i] = (nom.strip(), liste[i][1])
            self._changer(liste)

    def _menu_couleur(self, pos):
        it = self.liste.itemAt(pos)
        if it is None:
            return
        i = self.liste.row(it)
        self.liste.setCurrentRow(i)
        m = QMenu(self)
        m.addAction(tr("Renommer…"), lambda: self.renommer(i))
        m.addAction(tr("Retirer du nuancier"), self.retirer)
        m.exec(self.liste.mapToGlobal(pos))

    def importer(self, chemin: str | None = None):
        if not chemin:
            chemin, _f = QFileDialog.getOpenFileName(self, tr("Importer un nuancier"), "",
                                                     tr("Nuanciers") + " (*.aco *.gpl)")
        if not chemin:
            return
        try:
            nouvelles = lire_fichier(chemin)
        except (OSError, struct.error, ValueError) as e:
            QMessageBox.warning(self, tr("Nuancier"), tr("Fichier illisible : {erreur}", erreur=e))
            return
        if not nouvelles:
            QMessageBox.information(self, tr("Nuancier"), tr("Aucune couleur trouvée dans ce fichier."))
            return
        self._changer(self.couleurs + nouvelles)

    def exporter(self, chemin: str | None = None):
        if not chemin:
            chemin, _f = QFileDialog.getSaveFileName(self, tr("Exporter le nuancier"), "nuancier.aco",
                                                     tr("Nuancier Photoshop") + " (*.aco)")
        if chemin:
            Path(chemin).write_bytes(ecrire_aco(self.couleurs))

    def remettre(self):
        self._changer([("", c) for c in DEPART])
