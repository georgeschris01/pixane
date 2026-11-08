"""Fenêtres : choix du résultat, réglages Agrandir et Upscale."""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon, QImage, QPixmap
from PySide6.QtWidgets import (QButtonGroup, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QHBoxLayout,
                               QLabel, QListWidget, QListWidgetItem, QProgressBar, QPushButton, QRadioButton, QSpinBox,
                               QVBoxLayout, QWidget)


class Apercu(QLabel):
    """Affiche une image en entier, à la taille de la zone."""

    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(500, 350)
        self.setStyleSheet("background:#282828;")
        self._image: QImage | None = None

    def montrer(self, image: QImage):
        self._image = image
        self._maj()

    def resizeEvent(self, e):
        self._maj()
        super().resizeEvent(e)

    def _maj(self):
        if self._image is not None:
            self.setPixmap(QPixmap.fromImage(self._image.scaled(self.size(), Qt.KeepAspectRatio,
                                                                Qt.SmoothTransformation)))


class BoutonComparer(QPushButton):
    appuye = Signal(bool)

    def __init__(self):
        super().__init__("Maintenir pour voir l'original")

    def mousePressEvent(self, e):
        self.appuye.emit(True)
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        self.appuye.emit(False)
        super().mouseReleaseEvent(e)


class ChoixResultat(QDialog):
    """Montre les propositions en vignettes ; on en garde une (comme Photoshop)."""
    autres_demandees = Signal()

    def __init__(self, titre: str, original: QImage, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{titre} — choisis un résultat")
        self.resize(1100, 800)
        self.original = original
        self.images: list[QImage] = []
        self.apercu = Apercu()
        self.vignettes = QListWidget()
        self.vignettes.setViewMode(QListWidget.IconMode)
        self.vignettes.setIconSize(QSize(160, 120))
        self.vignettes.setFixedHeight(175)
        self.vignettes.setFlow(QListWidget.LeftToRight)
        self.vignettes.setWrapping(False)
        self.vignettes.currentRowChanged.connect(self._choisi)
        comparer = BoutonComparer()
        comparer.appuye.connect(self._comparer)
        self.bouton_autres = QPushButton("Autres propositions")
        self.bouton_autres.clicked.connect(self._autres)
        garder = QPushButton("Garder ce résultat")
        garder.setDefault(True)
        garder.clicked.connect(self.accept)
        annuler = QPushButton("Annuler")
        annuler.clicked.connect(self.reject)
        self.etat = QLabel("")
        self.barre = QProgressBar()
        self.barre.setFixedWidth(220)
        self.barre.setFormat("%p %")
        self.barre.hide()
        bas = QHBoxLayout()
        bas.addWidget(comparer)
        bas.addWidget(self.bouton_autres)
        bas.addWidget(self.barre)
        bas.addWidget(self.etat, 1)
        bas.addWidget(annuler)
        bas.addWidget(garder)
        lay = QVBoxLayout(self)
        lay.addWidget(self.apercu, 1)
        lay.addWidget(self.vignettes)
        lay.addLayout(bas)

    def ajouter(self, resultats: list[tuple[str, QImage]]):
        premier = len(self.images)
        for libelle, img in resultats:
            self.images.append(img)
            item = QListWidgetItem(QIcon(QPixmap.fromImage(img.scaled(160, 120, Qt.KeepAspectRatio,
                                                                      Qt.SmoothTransformation))), libelle)
            self.vignettes.addItem(item)
        if self.images:
            self.vignettes.setCurrentRow(premier if premier < len(self.images) else 0)
        self.occupe(False)

    def occupe(self, oui: bool, texte: str = ""):
        self.bouton_autres.setEnabled(not oui)
        self.etat.setText(texte)
        if not oui:
            self.barre.hide()

    def progression(self, info: dict):
        self.barre.show()
        regler_barre(self.barre, info)
        self.etat.setText(f"{info['etape']}  ·  {texte_progression(info)}")

    def _autres(self):
        self.occupe(True, "Calcul de nouvelles propositions…")
        self.autres_demandees.emit()

    def _choisi(self, ligne: int):
        if 0 <= ligne < len(self.images):
            self.apercu.montrer(self.images[ligne])

    def _comparer(self, oui: bool):
        if oui:
            self.apercu.montrer(self.original)
        else:
            self._choisi(self.vignettes.currentRow())

    def choix(self) -> QImage | None:
        ligne = self.vignettes.currentRow()
        return self.images[ligne] if 0 <= ligne < len(self.images) else None


class ReglagesAgrandir(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Agrandir l'image")
        self.cotes = {}
        form = QFormLayout()
        for cle, nom, defaut in (("haut", "En haut", 0), ("bas", "En bas", 0), ("gauche", "À gauche", 25),
                                 ("droite", "À droite", 25)):
            s = QSpinBox()
            s.setRange(0, 200)
            s.setSuffix(" %")
            s.setValue(defaut)
            self.cotes[cle] = s
            form.addRow(nom, s)
        aide = QLabel("Pourcentage de la photo à ajouter de chaque côté.")
        aide.setWordWrap(True)
        boutons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        boutons.button(QDialogButtonBox.Ok).setText("Agrandir")
        boutons.button(QDialogButtonBox.Cancel).setText("Annuler")
        boutons.accepted.connect(self._valider)
        boutons.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.addWidget(aide)
        lay.addLayout(form)
        lay.addWidget(boutons)

    def _valider(self):
        if any(s.value() for s in self.cotes.values()):
            self.accept()

    def valeurs(self) -> dict:
        return {k: float(s.value()) for k, s in self.cotes.items()}


class ReglagesUpscale(QDialog):
    def __init__(self, largeur: int, hauteur: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Upscale")
        self.taille = (largeur, hauteur)
        self.net = QRadioButton("Net (Flux redessine les détails, plus lent)")
        self.rapide = QRadioButton("Rapide (RealESRGAN seul, peut lisser)")
        self.net.setChecked(True)
        groupe = QButtonGroup(self)
        groupe.addButton(self.net)
        groupe.addButton(self.rapide)
        self.facteur = QDoubleSpinBox()
        self.facteur.setRange(1.5, 4.0)
        self.facteur.setSingleStep(0.5)
        self.facteur.setValue(2.0)
        self.facteur.setPrefix("× ")
        self.force = QDoubleSpinBox()
        self.force.setRange(0.10, 0.60)
        self.force.setSingleStep(0.05)
        self.force.setValue(0.35)
        self.resultat = QLabel()
        self.facteur.valueChanged.connect(self._maj)
        self.net.toggled.connect(self._maj)
        form = QFormLayout()
        form.addRow("Agrandir", self.facteur)
        form.addRow("Force (0,25 léger – 0,45 fort)", self.force)
        boutons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        boutons.button(QDialogButtonBox.Ok).setText("Lancer")
        boutons.button(QDialogButtonBox.Cancel).setText("Annuler")
        boutons.accepted.connect(self.accept)
        boutons.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.addWidget(self.net)
        lay.addWidget(self.rapide)
        lay.addLayout(form)
        lay.addWidget(self.resultat)
        lay.addWidget(boutons)
        self._maj()

    def _maj(self):
        self.force.setEnabled(self.net.isChecked())
        w, h = (round(v * self.facteur.value()) for v in self.taille)
        self.resultat.setText(f"Taille finale : {w} × {h} px")

    def valeurs(self) -> dict:
        return {"net": self.net.isChecked(), "facteur": self.facteur.value(), "force": self.force.value()}


def duree(s: int) -> str:
    return f"{s // 60} min {s % 60:02d} s" if s >= 60 else f"{s} s"


def texte_progression(info: dict) -> str:
    texte = f"{duree(info['secondes'])} écoulées"
    if info.get("restant") is not None:
        texte += f"  —  encore environ {duree(info['restant'])}"
    return texte


def regler_barre(barre: QProgressBar, info: dict):
    if info.get("fraction") is None:
        barre.setRange(0, 0)  # barre animée sans pourcentage
    else:
        barre.setRange(0, 1000)
        barre.setValue(int(info["fraction"] * 1000))


class Attente(QDialog):
    """Fenêtre « calcul en cours » : étape, barre de progression, temps, bouton Annuler."""
    annuler = Signal()

    def __init__(self, titre: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(titre)
        self.setModal(True)
        self.titre = QLabel(f"<b>{titre}</b>")
        self.etape = QLabel("Envoi de l'image au moteur…")
        self.barre = QProgressBar()
        self.barre.setTextVisible(True)
        self.barre.setFormat("%p %")
        self.barre.setRange(0, 0)
        self.temps = QLabel("")
        self.bouton = QPushButton("Annuler")
        self.bouton.clicked.connect(self._annuler)
        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        lay.addWidget(self.titre)
        lay.addWidget(self.etape)
        lay.addWidget(self.barre)
        lay.addWidget(self.temps)
        lay.addWidget(self.bouton, alignment=Qt.AlignRight)
        self.setFixedWidth(440)

    def maj(self, info: dict):
        self.etape.setText(info["etape"])
        regler_barre(self.barre, info)
        self.temps.setText(texte_progression(info))

    def _annuler(self):
        self.etape.setText("Annulation…")
        self.bouton.setEnabled(False)
        self.annuler.emit()

    def closeEvent(self, e):
        self._annuler()
        e.ignore()
