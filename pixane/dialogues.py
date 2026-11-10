"""Fenêtres : choix du résultat, barre Agrandir, réglages Upscale."""
from __future__ import annotations

from PySide6.QtCore import QEvent, QSize, Qt, Signal
from PySide6.QtGui import QIcon, QImage, QPixmap
from PySide6.QtWidgets import (QButtonGroup, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QFrame, QGridLayout, QHBoxLayout,
                               QLabel, QListWidget, QListWidgetItem, QProgressBar, QPushButton, QRadioButton, QSpinBox,
                               QVBoxLayout, QWidget, QCheckBox)

from .langue import tr


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
        super().__init__(tr("Maintenir pour voir l'original"))

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
        self.setWindowTitle(tr("{titre} — choisis un résultat", titre=titre))
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
        self.bouton_autres = QPushButton(tr("Autres propositions"))
        self.bouton_autres.clicked.connect(self._autres)
        garder = QPushButton(tr("Garder ce résultat"))
        garder.setDefault(True)
        garder.clicked.connect(self.accept)
        annuler = QPushButton(tr("Annuler"))
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

    vue = None          # fonction image -> image montrée (ex. transparence de la photo remise)

    def ajouter(self, resultats: list[tuple[str, QImage]]):
        premier = len(self.images)
        for libelle, img in resultats:
            self.images.append(img)
            if self.vue is not None:
                img = self.vue(img)
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
        self.occupe(True, tr("Calcul de nouvelles propositions…"))
        self.autres_demandees.emit()

    def _choisi(self, ligne: int):
        if 0 <= ligne < len(self.images):
            img = self.images[ligne]
            self.apercu.montrer(self.vue(img) if self.vue is not None else img)

    def _comparer(self, oui: bool):
        if oui:
            self.apercu.montrer(self.original)
        else:
            self._choisi(self.vignettes.currentRow())

    def choix(self) -> QImage | None:
        ligne = self.vignettes.currentRow()
        return self.images[ligne] if 0 <= ligne < len(self.images) else None


class BarreAgrandir(QFrame):
    """Petite barre posée sur la photo pendant Agrandir.
    Ligne « Agrandir » : % ajoutés par côté (cadre extérieur). Ligne « Bord abîmé » : px du bord de la photo
    à jeter et faire redessiner par l'IA (cadre intérieur rouge). Les cases suivent le cadre, et l'inverse."""
    lancer = Signal()
    annuler = Signal()
    valeurs_changees = Signal(object, object)   # (ajout, bord abîmé) en px, (haut, bas, gauche, droite)

    COTES = (("haut", "Haut"), ("bas", "Bas"), ("gauche", "Gauche"), ("droite", "Droite"))   # noms traduits à l'affichage

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setObjectName("panneau")
        self.taille = (1, 1)
        self.ajout = {}
        self.abime = {}
        colonne = QVBoxLayout(self)
        colonne.setContentsMargins(12, 6, 8, 8)
        colonne.setSpacing(4)
        aide = QLabel(tr("Cadre carré : tire vers l'extérieur pour agrandir.  Cadre rond rouge : tire vers "
                         "l'intérieur pour marquer un bord abîmé à refaire.  (Maj : les deux côtés)"))
        aide.setObjectName("discret")
        colonne.addWidget(aide)
        self.vide = None
        self.info_vide = QLabel(tr("Il y a du vide autour de la photo : le cadre part de la photo. Tire-le "
                                   "jusqu'où l'IA doit la prolonger : dans le vide (il s'arrête tout seul au bord "
                                   "de l'image), ou au-delà pour agrandir l'image."))
        self.info_vide.setWordWrap(True)
        self.info_vide.hide()
        colonne.addWidget(self.info_vide)
        bas = QHBoxLayout()
        bas.setSpacing(12)
        colonne.addLayout(bas)
        grille = QGridLayout()
        grille.setHorizontalSpacing(6)
        grille.setVerticalSpacing(4)
        bas.addLayout(grille)
        grille.addWidget(QLabel(tr("Agrandir")), 1, 0)
        grille.addWidget(QLabel(tr("Bord abîmé")), 2, 0)
        for i, (cle, nom) in enumerate(self.COTES):
            titre = QLabel(tr(nom))
            titre.setObjectName("discret")
            titre.setAlignment(Qt.AlignCenter)
            grille.addWidget(titre, 0, 1 + i)
            a = QSpinBox()
            a.setRange(0, 200)
            a.setSuffix(" %")
            a.setToolTip(tr("Ce que l'IA ajoute de ce côté, en % de la photo."))
            a.valueChanged.connect(self._case_changee)
            self.ajout[cle] = a
            grille.addWidget(a, 1, 1 + i)
            m = QSpinBox()
            m.setRange(0, 5000)
            m.setSuffix(" px")
            m.setToolTip(tr("Bande abîmée au bord de la photo : jetée puis redessinée par l'IA."))
            m.valueChanged.connect(self._case_changee)
            self.abime[cle] = m
            grille.addWidget(m, 2, 1 + i)
        droite = QVBoxLayout()
        droite.setSpacing(4)
        self.texte_taille = QLabel()
        self.texte_taille.setMinimumWidth(self.texte_taille.fontMetrics().horizontalAdvance("00000 × 00000 px"))
        self.texte_taille.setAlignment(Qt.AlignCenter)
        droite.addWidget(self.texte_taille)
        boutons = QHBoxLayout()
        b_annuler = QPushButton(tr("Annuler"))
        b_annuler.setAutoDefault(False)
        b_annuler.clicked.connect(self.annuler)
        self.b_lancer = QPushButton(tr("Lancer"))
        self.b_lancer.setObjectName("principal")
        self.b_lancer.setAutoDefault(False)
        self.b_lancer.clicked.connect(self.lancer)
        boutons.addWidget(b_annuler)
        boutons.addWidget(self.b_lancer)
        droite.addLayout(boutons)
        self.pleine = QCheckBox(tr("Pleine définition"))
        self.pleine.setToolTip(tr(
            "Après le choix d'une proposition, l'ajout est redessiné à la vraie taille de la photo, par morceaux : "
            "aussi net et détaillé que le reste, avec le même grain. Plus long (environ 30 s à 1 min par "
            "morceau de 1024 px). Sans effet sur une petite photo."))
        droite.addWidget(self.pleine)
        droite.addStretch()
        bas.addLayout(droite)
        self._px = ((0, 0, 0, 0), (0, 0, 0, 0))
        parent.installEventFilter(self)
        self.hide()

    def ouvrir(self, largeur: int, hauteur: int, abime=(0, 0, 0, 0), vide=None):
        """vide : None, ou ((x0, y0, x1, y1) de la photo, (largeur, hauteur) de l'image) quand du vide transparent
        entoure la photo : le cadre part alors de la photo, les % sont ceux de la photo."""
        self.taille = (largeur, hauteur)
        self.vide = vide
        if vide is not None:
            x0, y0, x1, y1 = vide[0]
            self.taille = (x1 - x0, y1 - y0)
            largeur, hauteur = self.taille
        self.info_vide.setVisible(vide is not None)
        for c in self.abime.values():
            c.setMaximum(max(0, max(largeur, hauteur) - 32))
        self.definir_px((0, 0, 0, 0), abime)
        self.adjustSize()
        self._placer()
        self.show()
        self.raise_()

    def definir_px(self, ajout, abime):
        """Valeurs venant des cadres tirés à la souris."""
        self._px = (tuple(int(v) for v in ajout), tuple(int(v) for v in abime))
        w, h = self.taille
        for c, v, n in zip(self.ajout.values(), self._px[0], (h, h, w, w)):
            c.blockSignals(True)
            c.setValue(round(v * 100 / n))
            c.blockSignals(False)
        for c, v in zip(self.abime.values(), self._px[1]):
            c.blockSignals(True)
            c.setValue(v)
            c.blockSignals(False)
        self._maj_texte()

    def _case_changee(self):
        """Seule la case modifiée change (les autres gardent leur valeur exacte en px)."""
        w, h = self.taille
        ajout, abime = list(self._px[0]), list(self._px[1])
        for i, (c, n) in enumerate(zip(self.ajout.values(), (h, h, w, w))):
            if c is self.sender():
                ajout[i] = round(c.value() * n / 100)
        for i, c in enumerate(self.abime.values()):
            if c is self.sender():
                ajout_n = (h, h, w, w)[i]
                autre = abime[i ^ 1]
                abime[i] = min(c.value(), max(0, ajout_n - autre - 32))
        self._px = (tuple(ajout), tuple(abime))
        self._maj_texte()
        self.valeurs_changees.emit(*self._px)

    def _maj_texte(self):
        w, h = self.taille
        hh, bb, gg, dd = self._px[0]
        if self.vide is not None:                      # l'image ne rétrécit pas : elle grandit si le cadre dépasse
            (x0, y0, x1, y1), (W, H) = self.vide
            self.texte_taille.setText(f"{max(W, x1 + dd) - min(0, x0 - gg)} × {max(H, y1 + bb) - min(0, y0 - hh)} px")
        else:
            self.texte_taille.setText(f"{w + gg + dd} × {h + hh + bb} px")
        self.b_lancer.setEnabled(any(self._px[0]) or any(self._px[1]))

    def valeurs_px(self) -> tuple:
        """((ajout), (bord abîmé)), chacun (haut, bas, gauche, droite) en px."""
        return self._px

    def _placer(self):
        p = self.parentWidget()
        self.move(max(0, (p.width() - self.width()) // 2), 12)

    def eventFilter(self, objet, e):
        if e.type() == QEvent.Resize:
            self._placer()
        return False


class ReglagesUpscale(QDialog):
    def __init__(self, largeur: int, hauteur: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Upscale"))
        self.taille = (largeur, hauteur)
        self.net = QRadioButton(tr("Net (Flux redessine les détails, plus lent)"))
        self.rapide = QRadioButton(tr("Rapide (RealESRGAN seul, peut lisser)"))
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
        form.addRow(tr("Agrandir|facteur"), self.facteur)
        form.addRow(tr("Force (0,25 léger – 0,45 fort)"), self.force)
        boutons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        boutons.button(QDialogButtonBox.Ok).setText(tr("Lancer"))
        boutons.button(QDialogButtonBox.Cancel).setText(tr("Annuler"))
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
        self.resultat.setText(tr("Taille finale : {largeur} × {hauteur} px", largeur=w, hauteur=h))

    def valeurs(self) -> dict:
        return {"net": self.net.isChecked(), "facteur": self.facteur.value(), "force": self.force.value()}


def duree(s: int) -> str:
    return tr("{min} min {s} s", min=s // 60, s=f"{s % 60:02d}") if s >= 60 else tr("{s} s", s=s)


def texte_progression(info: dict) -> str:
    texte = tr("{duree} écoulées", duree=duree(info['secondes']))
    if info.get("restant") is not None:
        texte += tr("  —  encore environ {duree}", duree=duree(info['restant']))
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
        self.etape = QLabel(tr("Envoi de l'image au moteur…"))
        self.barre = QProgressBar()
        self.barre.setTextVisible(True)
        self.barre.setFormat("%p %")
        self.barre.setRange(0, 0)
        self.temps = QLabel("")
        self.bouton = QPushButton(tr("Annuler"))
        self.bouton.setAutoDefault(False)
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
        self.etape.setText(tr("Annulation…"))
        self.bouton.setEnabled(False)
        self.annuler.emit()

    def closeEvent(self, e):
        self._annuler()
        e.ignore()
