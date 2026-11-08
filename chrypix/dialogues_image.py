"""Petites fenêtres du menu Image et de l'aide : taille de l'image, redresser, nouvelle image, à propos."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QImage, QPainter, QPen, QPixmap, QTransform
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QGridLayout,
                               QHBoxLayout, QLabel, QPushButton, QSlider, QSpinBox, QVBoxLayout)

from . import __version__
from .document import taille_redressee
from .langue import tr

RACINE = Path(__file__).resolve().parents[1]
DEPOT = "https://github.com/georgeschris01/chrypix"


def _boutons(d: QDialog, texte_ok: str) -> QDialogButtonBox:
    b = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    b.button(QDialogButtonBox.Ok).setText(texte_ok)
    b.button(QDialogButtonBox.Cancel).setText(tr("Annuler"))
    b.accepted.connect(d.accept)
    b.rejected.connect(d.reject)
    return b


class TailleImage(QDialog):
    """Taille de l'image en pixels ou en %, proportions gardées par défaut."""

    def __init__(self, largeur: int, hauteur: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Taille de l'image"))
        self.w0, self.h0 = largeur, hauteur
        lay = QVBoxLayout(self)
        info = QLabel(tr("Taille actuelle : {l} × {h} px. Sans IA : pour agrandir avec plus de détails, utilisez "
                         "plutôt Upscale.", l=largeur, h=hauteur))
        info.setObjectName("discret")
        info.setWordWrap(True)
        lay.addWidget(info)
        g = QGridLayout()
        self.largeur = QSpinBox()
        self.hauteur = QSpinBox()
        for s in (self.largeur, self.hauteur):
            s.setRange(1, 30000)
            s.setSuffix(" px")
        self.pct = QDoubleSpinBox()
        self.pct.setRange(1, 1000)
        self.pct.setDecimals(1)
        self.pct.setSuffix(" %")
        self.c_prop = QCheckBox(tr("Garder les proportions"))
        self.c_prop.setChecked(True)
        g.addWidget(QLabel(tr("Largeur")), 0, 0)
        g.addWidget(self.largeur, 0, 1)
        g.addWidget(QLabel(tr("Hauteur")), 1, 0)
        g.addWidget(self.hauteur, 1, 1)
        g.addWidget(QLabel(tr("Échelle")), 2, 0)
        g.addWidget(self.pct, 2, 1)
        lay.addLayout(g)
        lay.addWidget(self.c_prop)
        rapides = QHBoxLayout()
        for p in (25, 50, 75):
            b = QPushButton(f"{p} %")
            b.clicked.connect(lambda _=False, v=p: self.pct.setValue(v))
            rapides.addWidget(b)
        b = QPushButton(tr("1920 px (écran, Internet)"))
        b.clicked.connect(lambda: self._cote_long(1920))
        rapides.addWidget(b)
        lay.addLayout(rapides)
        lay.addWidget(_boutons(self, tr("Appliquer")))
        self._occupe = False
        self.largeur.setValue(largeur)
        self.hauteur.setValue(hauteur)
        self.pct.setValue(100)
        self.largeur.valueChanged.connect(lambda v: self._change("l"))
        self.hauteur.valueChanged.connect(lambda v: self._change("h"))
        self.pct.valueChanged.connect(lambda v: self._change("p"))

    def _cote_long(self, px: int):
        self.c_prop.setChecked(True)
        self.pct.setValue(min(1000.0, px * 100 / max(self.w0, self.h0)))

    def _change(self, quoi: str):
        if self._occupe:
            return
        self._occupe = True
        if quoi == "p":
            self.largeur.setValue(max(1, round(self.w0 * self.pct.value() / 100)))
            self.hauteur.setValue(max(1, round(self.h0 * self.pct.value() / 100)))
        elif self.c_prop.isChecked():
            k = self.largeur.value() / self.w0 if quoi == "l" else self.hauteur.value() / self.h0
            if quoi == "l":
                self.hauteur.setValue(max(1, round(self.h0 * k)))
            else:
                self.largeur.setValue(max(1, round(self.w0 * k)))
            self.pct.setValue(k * 100)
        self._occupe = False

    def valeurs(self) -> tuple[int, int]:
        return self.largeur.value(), self.hauteur.value()


class Redresser(QDialog):
    """Tourner d'un petit angle (horizon penché), avec aperçu et grille."""

    def __init__(self, image: QImage, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Redresser"))
        self.w0, self.h0 = image.width(), image.height()
        self.vignette = image.scaled(560, 380, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        lay = QVBoxLayout(self)
        info = QLabel(tr("Tournez jusqu'à ce que l'horizon (ou un mur) suive la grille."))
        info.setObjectName("discret")
        lay.addWidget(info)
        self.apercu = QLabel()
        self.apercu.setAlignment(Qt.AlignCenter)
        self.apercu.setMinimumSize(580, 400)
        lay.addWidget(self.apercu)
        ligne = QHBoxLayout()
        ligne.addWidget(QLabel(tr("Angle")))
        self.curseur = QSlider(Qt.Horizontal)
        self.curseur.setRange(-450, 450)
        self.angle = QDoubleSpinBox()
        self.angle.setRange(-45, 45)
        self.angle.setDecimals(1)
        self.angle.setSingleStep(0.1)
        self.angle.setSuffix(" °")
        self.curseur.valueChanged.connect(lambda v: self.angle.setValue(v / 10))
        self.angle.valueChanged.connect(lambda v: self.curseur.setValue(round(v * 10)))
        self.angle.valueChanged.connect(self._dessiner)
        ligne.addWidget(self.curseur, 1)
        ligne.addWidget(self.angle)
        lay.addLayout(ligne)
        self.c_recadrer = QCheckBox(tr("Recadrer pour enlever les coins vides"))
        self.c_recadrer.setChecked(True)
        self.c_recadrer.toggled.connect(self._dessiner)
        lay.addWidget(self.c_recadrer)
        self.taille = QLabel()
        self.taille.setObjectName("discret")
        lay.addWidget(self.taille)
        lay.addWidget(_boutons(self, tr("Appliquer")))
        self._dessiner()

    def _dessiner(self, *_):
        a = self.angle.value()
        vw, vh = self.vignette.width(), self.vignette.height()
        W, H = taille_redressee(vw, vh, a, self.c_recadrer.isChecked())
        pm = QPixmap(W, H)
        pm.fill(QColor(0, 0, 0, 0))
        p = QPainter(pm)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.setTransform(QTransform().translate(W / 2, H / 2).rotate(a).translate(-vw / 2, -vh / 2))
        p.drawImage(QPointF(0, 0), self.vignette)
        p.resetTransform()
        p.setPen(QPen(QColor(255, 255, 255, 150), 1))
        for i in range(1, 6):
            p.drawLine(QPointF(W * i / 6, 0), QPointF(W * i / 6, H))
            p.drawLine(QPointF(0, H * i / 6), QPointF(W, H * i / 6))
        p.end()
        self.apercu.setPixmap(pm)
        Wr, Hr = taille_redressee(self.w0, self.h0, a, self.c_recadrer.isChecked())
        self.taille.setText(tr("Résultat : {l} × {h} px", l=Wr, h=Hr))

    def valeurs(self) -> tuple[float, bool]:
        return self.angle.value(), self.c_recadrer.isChecked()


class NouvelleImage(QDialog):
    def __init__(self, largeur: int = 1920, hauteur: int = 1080, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Nouvelle image"))
        lay = QVBoxLayout(self)
        g = QGridLayout()
        self.largeur, self.hauteur = QSpinBox(), QSpinBox()
        for s, v in ((self.largeur, largeur), (self.hauteur, hauteur)):
            s.setRange(1, 30000)
            s.setSuffix(" px")
            s.setValue(v)
        self.fond = QComboBox()
        self.fond.addItem(tr("Blanc"), "#ffffffff")
        self.fond.addItem(tr("Transparent"), "#00000000")
        self.fond.addItem(tr("Noir"), "#ff000000")
        g.addWidget(QLabel(tr("Largeur")), 0, 0)
        g.addWidget(self.largeur, 0, 1)
        g.addWidget(QLabel(tr("Hauteur")), 1, 0)
        g.addWidget(self.hauteur, 1, 1)
        g.addWidget(QLabel(tr("Fond")), 2, 0)
        g.addWidget(self.fond, 2, 1)
        lay.addLayout(g)
        lay.addWidget(_boutons(self, tr("Créer")))

    def image(self) -> QImage:
        img = QImage(self.largeur.value(), self.hauteur.value(), QImage.Format_ARGB32_Premultiplied)
        img.fill(QColor(self.fond.currentData()))
        return img


class APropos(QDialog):
    def __init__(self, icone: QPixmap | None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("À propos de Chrypix"))
        lay = QVBoxLayout(self)
        haut = QHBoxLayout()
        if icone is not None:
            logo = QLabel()
            logo.setPixmap(icone)
            haut.addWidget(logo, 0, Qt.AlignTop)
        texte = QLabel(
            f"<h2 style='margin:0'>Chrypix {__version__}</h2>"
            + tr("<p>Éditeur photo avec retouche par IA sur votre PC.</p>"
                 "<p>© 2026 Georges Christophe (chrypox)<br>Licence Chrypix 1.1 : gratuit, code source ouvert, "
                 "non commercial. Modifications permises en gardant le nom de l'auteur et la même licence.</p>"
                 "<p>Moteur IA : ComfyUI (GPL-3.0). Modèle Flux Fill : licence FLUX.1 [dev], non commerciale.</p>"
                 "<p>Écrit avec l'aide de l'IA Claude Code.</p>"))
        texte.setWordWrap(True)
        texte.setTextFormat(Qt.RichText)
        texte.setMinimumWidth(420)
        haut.addWidget(texte, 1)
        lay.addLayout(haut)
        liens = QHBoxLayout()
        for nom, cible in ((tr("Licence"), RACINE / "LICENSE"),
                           (tr("Éléments tiers"), RACINE / "docs" / "LICENCES_TIERS.md"),
                           (tr("Guide"), RACINE / "docs" / tr("GUIDE.md")),
                           (tr("Page GitHub"), DEPOT)):
            b = QPushButton(nom)
            b.clicked.connect(lambda _=False, c=cible: QDesktopServices.openUrl(
                QUrl(c) if isinstance(c, str) else QUrl.fromLocalFile(str(c))))
            if isinstance(cible, Path) and not cible.exists():
                b.setEnabled(False)
            liens.addWidget(b)
        lay.addLayout(liens)
        b = QDialogButtonBox(QDialogButtonBox.Close)
        b.button(QDialogButtonBox.Close).setText(tr("Fermer"))
        b.rejected.connect(self.reject)
        lay.addWidget(b)
