"""Petites fenêtres du menu Image et de l'aide : taille de l'image, redresser, à propos."""
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
DEPOT = "https://github.com/georgeschris01/pixane"


def _boutons(d: QDialog, texte_ok: str) -> QDialogButtonBox:
    b = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    b.button(QDialogButtonBox.Ok).setText(texte_ok)
    b.button(QDialogButtonBox.Cancel).setText(tr("Annuler"))
    b.accepted.connect(d.accept)
    b.rejected.connect(d.reject)
    return b


class TailleImage(QDialog):
    """Taille de l'image en pixels ou en %, proportions gardées par défaut."""

    def __init__(self, largeur: int, hauteur: int, parent=None, image: QImage | None = None):
        super().__init__(parent)
        self.setWindowTitle(tr("Taille de l'image"))
        self.w0, self.h0 = largeur, hauteur
        self._image = image
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
        # aperçu : le centre de l'image à 100 % de la nouvelle taille (netteté, détails), à gauche la taille
        # actuelle, à droite la nouvelle
        self.apercu = QLabel()
        self.apercu.setAlignment(Qt.AlignCenter)
        self.apercu.setMinimumSize(2 * self.COTE + 12, self.COTE)
        self.apercu.setVisible(image is not None)
        lay.addWidget(self.apercu)
        self.legende = QLabel(tr("Centre de l'image à 100 % : avant (à gauche), après (à droite)"))
        self.legende.setObjectName("discret")
        self.legende.setVisible(image is not None)
        lay.addWidget(self.legende)
        self._minuteur = QTimer(self)
        self._minuteur.setSingleShot(True)
        self._minuteur.setInterval(80)
        self._minuteur.timeout.connect(self._apercu)
        lay.addWidget(_boutons(self, tr("Appliquer")))
        self._occupe = False
        self.largeur.setValue(largeur)
        self.hauteur.setValue(hauteur)
        self.pct.setValue(100)
        self.largeur.valueChanged.connect(lambda v: self._change("l"))
        self.hauteur.valueChanged.connect(lambda v: self._change("h"))
        self.pct.valueChanged.connect(lambda v: self._change("p"))
        for sp in (self.largeur, self.hauteur):
            sp.valueChanged.connect(lambda _v: self._minuteur.start())
        self._apercu()

    COTE = 220

    def _apercu(self):
        """Morceau du centre, à 100 % : avant / après (même lissage que l'application de la taille)."""
        if self._image is None:
            return
        W, H = self.valeurs()
        kx, ky = W / self.w0, H / self.h0
        c = self.COTE
        # morceau de l'original qui donnera c × c pixels après
        sw, sh = max(1, min(self.w0, round(c / kx))), max(1, min(self.h0, round(c / ky)))
        sx, sy = (self.w0 - sw) // 2, (self.h0 - sh) // 2
        morceau = self._image.copy(sx, sy, sw, sh)
        apres = morceau.scaled(max(1, round(sw * kx)), max(1, round(sh * ky)), Qt.IgnoreAspectRatio,
                               Qt.SmoothTransformation)
        avant = self._image.copy((self.w0 - c) // 2, (self.h0 - c) // 2, min(c, self.w0), min(c, self.h0))
        toile = QImage(2 * c + 12, c, QImage.Format_ARGB32_Premultiplied)
        toile.fill(Qt.transparent)
        p = QPainter(toile)
        p.drawImage(0, 0, avant)
        p.drawImage(c + 12, 0, apres)
        p.setPen(QPen(QColor(128, 128, 128)))
        p.drawRect(0, 0, min(c, avant.width()) - 1, min(c, avant.height()) - 1)
        p.drawRect(c + 12, 0, min(c, apres.width()) - 1, min(c, apres.height()) - 1)
        p.end()
        self.apercu.setPixmap(QPixmap.fromImage(toile))

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


class APropos(QDialog):
    def __init__(self, icone: QPixmap | None, parent=None, couleurs=None):
        super().__init__(parent)
        self.couleurs = couleurs
        self.setWindowTitle(tr("À propos de Pixane"))
        lay = QVBoxLayout(self)
        haut = QHBoxLayout()
        if icone is not None:
            logo = QLabel()
            logo.setPixmap(icone)
            haut.addWidget(logo, 0, Qt.AlignTop)
        texte = QLabel(
            f"<h2 style='margin:0'>Pixane {__version__}</h2>"
            + tr("<p>Éditeur photo avec retouche par IA sur votre PC.</p>"
                 "<p>Pixane est pensé pour celles et ceux qui débutent en retouche photo, ou qui en ont peu "
                 "l'expérience : les outils vont à l'essentiel, l'IA se charge du travail difficile et l'aide "
                 "explique chaque réglage pas à pas. Pixane n'a pas la prétention de remplacer des programmes "
                 "comme Photoshop, GIMP ou Krita, qui restent la référence pour un travail poussé : il veut "
                 "rendre la retouche accessible à tous.</p>"
                 "<p>© 2026 Georges Christophe (chrypox)<br>Licence Pixane 1.2 : gratuit, code source disponible, "
                 "non commercial. Modifications permises en gardant le nom de l'auteur et la même licence.</p>"
                 "<p>Moteur IA : ComfyUI (GPL-3.0). Modèle Flux Fill : licence FLUX.1 [dev], non commerciale.</p>"))
        texte.setWordWrap(True)
        texte.setTextFormat(Qt.RichText)
        texte.setMinimumWidth(420)
        haut.addWidget(texte, 1)
        lay.addLayout(haut)
        liens = QHBoxLayout()
        from .aide import FenetreLicence, FenetreTiers
        for nom, action in ((tr("Licence"), lambda: FenetreLicence(self).exec()),
                            (tr("Éléments tiers"), lambda: FenetreTiers(self.couleurs, self).exec()),
                            (tr("Guide"), self._guide),
                            (tr("Page GitHub"), lambda: QDesktopServices.openUrl(QUrl(DEPOT)))):
            b = QPushButton(nom)
            b.clicked.connect(lambda _=False, a=action: a())
            liens.addWidget(b)
        lay.addLayout(liens)
        b = QDialogButtonBox(QDialogButtonBox.Close)
        b.button(QDialogButtonBox.Close).setText(tr("Fermer"))
        b.rejected.connect(self.reject)
        lay.addWidget(b)

    def _guide(self):
        f = self.parent()
        if f is not None and hasattr(f, "guide"):
            self.accept()
            f.guide()
