"""Fenêtre « Bibliothèque » : choisir un pinceau (ou un motif), ajouter des fichiers d'autres logiciels
(Photoshop .abr / .pat, GIMP et Krita .gbr / .gih / .pat / .bundle, images), retirer un groupe ajouté."""
from __future__ import annotations

import os

import numpy as np
from PySide6.QtCore import QSettings, QSize, Qt
from PySide6.QtGui import QIcon, QImage, QPixmap
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout, QLabel, QListView, QListWidget,
                               QListWidgetItem, QMessageBox, QPushButton, QSlider, QSplitter, QVBoxLayout, QWidget)

from .bibliotheque import MOTIFS, PINCEAUX, SIMPLES, STYLES, Bibliotheque, Motif, bibliotheque
from .formats_pinceaux import EXT_IMAGES, EXT_MOTIFS, EXT_PAQUETS, EXT_PINCEAUX
from .langue import tr

VIGNETTE = 72
APERCU = 280                       # grand aperçu de l'élément choisi (détails)


def _reglages() -> QSettings:
    return QSettings("Pixane", os.environ.get("PIXANE_REGLAGES", "Pixane"))


def vignette(element, t: int = VIGNETTE, detail: bool = False) -> QImage:
    """Petite image d'un pinceau (forme sombre sur fond clair) ou d'un motif (répété). detail : motif à sa taille
    réelle (pas réduit), pour en voir le grain."""
    if isinstance(element, Motif):
        a = element.image
        k = 1.0 if detail else min(1.0, max(48, t * 2 // 3) / max(a.shape[:2]))
        src = _qimage(a)
        if k < 1:
            src = src.scaled(max(1, round(a.shape[1] * k)), max(1, round(a.shape[0] * k)),
                             Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        img = QImage(t, t, QImage.Format_ARGB32_Premultiplied)
        img.fill(Qt.white)
        from PySide6.QtGui import QPainter
        p = QPainter(img)
        p.drawTiledPixmap(0, 0, t, t, QPixmap.fromImage(src))
        p.end()
        return img
    a = element.formes[0]
    if a.ndim == 2:
        g = (255 - a.astype(np.float32) * 0.9).astype(np.uint8)
        rgba = np.dstack([g, g, g, np.full_like(g, 255)])
    else:
        al = a[..., 3:4].astype(np.float32) / 255
        rgb = (a[..., :3] * al + 255 * (1 - al)).astype(np.uint8)
        rgba = np.dstack([rgb, np.full(a.shape[:2], 255, np.uint8)])
    img = _qimage(rgba)
    return img.scaled(t, t, Qt.KeepAspectRatio, Qt.SmoothTransformation)


def _qimage(rgba: np.ndarray) -> QImage:
    rgba = np.ascontiguousarray(rgba)
    h, w = rgba.shape[:2]
    return QImage(rgba.data, w, h, 4 * w, QImage.Format_RGBA8888).copy()


class ChoixBibliotheque(QDialog):
    """genre : PINCEAUX ou MOTIFS. Après exec(), self.choisi = l'élément choisi (ou None)."""

    def __init__(self, genre: str, parent=None, cle: str | None = None, biblio: Bibliotheque | None = None,
                 avec_rond: bool = False):
        """avec_rond : bouton « Rond simple » (le pinceau rond d'origine : choisi = None)."""
        super().__init__(parent)
        self.genre, self.biblio, self.choisi = genre, biblio or bibliotheque(), None
        self.setWindowTitle(tr("Pinceaux") if genre == PINCEAUX else tr("Motifs"))
        self.resize(1100, 620)
        self.liste_groupes = QListWidget()
        self.liste_groupes.currentRowChanged.connect(self._montrer_groupe)
        self.grille = QListWidget()
        self.grille.setViewMode(QListView.IconMode)
        self.grille.setIconSize(QSize(VIGNETTE, VIGNETTE))
        self.grille.setGridSize(QSize(VIGNETTE + 26, VIGNETTE + 34))
        self.grille.setResizeMode(QListView.Adjust)
        self.grille.setMovement(QListView.Static)
        self.grille.setWordWrap(True)
        self.grille.setUniformItemSizes(True)
        self.grille.itemDoubleClicked.connect(lambda _i: self.accept())
        self.grille.currentItemChanged.connect(self._maj_info)
        self.apercu = QLabel()
        self.apercu.setAlignment(Qt.AlignCenter)
        self.apercu.setMinimumSize(APERCU, APERCU)
        self.apercu.setToolTip(tr("Aperçu en grand de l'élément choisi"))
        separation = QSplitter()
        separation.addWidget(self.liste_groupes)
        separation.addWidget(self.grille)
        separation.addWidget(self.apercu)
        separation.setSizes([180, 560, APERCU + 20])
        self.taille_vignettes = QSlider(Qt.Horizontal)
        self.taille_vignettes.setRange(48, 256)
        self.taille_vignettes.setFixedWidth(160)
        self.taille_vignettes.setToolTip(tr("Taille des vignettes : agrandir pour mieux voir les détails"))
        try:
            t = int(_reglages().value("biblio_vignette", VIGNETTE))
        except (TypeError, ValueError):
            t = VIGNETTE
        self.taille_vignettes.setValue(max(48, min(256, t)))
        self.taille_vignettes.valueChanged.connect(self._taille_vignettes)
        self._appliquer_taille(self.taille_vignettes.value())
        self.info = QLabel()
        self.info.setWordWrap(True)
        self.bouton_ajouter = QPushButton(tr("Ajouter des fichiers…"))
        self.bouton_ajouter.setToolTip(tr("Pinceaux : .abr (Photoshop), .gbr / .gih (GIMP, Krita), images.\n"
                                          "Motifs : .pat (Photoshop, GIMP, Krita), images.\n"
                                          "Paquets Krita (.bundle) : leurs pinceaux et leurs motifs."))
        self.bouton_ajouter.clicked.connect(self._ajouter)
        self.bouton_retirer = QPushButton(tr("Retirer ce groupe"))
        self.bouton_retirer.clicked.connect(self._retirer)
        boutons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        boutons.accepted.connect(self.accept)
        boutons.rejected.connect(self.reject)
        bas = QHBoxLayout()
        if avec_rond:
            self.bouton_rond = QPushButton(tr("Rond simple"))
            self.bouton_rond.setToolTip(tr("Le pinceau rond habituel (réglé par la dureté)"))
            self.bouton_rond.clicked.connect(self._rond)
            bas.addWidget(self.bouton_rond)
        bas.addWidget(self.bouton_ajouter)
        bas.addWidget(self.bouton_retirer)
        bas.addStretch(1)
        bas.addWidget(QLabel(tr("Vignettes")))
        bas.addWidget(self.taille_vignettes)
        bas.addWidget(boutons)
        lay = QVBoxLayout(self)
        lay.addWidget(separation, 1)
        lay.addWidget(self.info)
        lay.addLayout(bas)
        self._remplir_groupes(cle.split("/", 1)[0] if cle else None, cle)

    # ------------------------------------------------------------------
    def _remplir_groupes(self, nom: str | None = None, cle: str | None = None) -> None:
        self._cle_voulue = cle
        self.liste_groupes.blockSignals(True)
        self.liste_groupes.clear()
        rang = 0
        for i, g in enumerate(self.biblio.groupes[self.genre]):
            it = QListWidgetItem(tr(g.nom) if g.de_base and g.genre == PINCEAUX else
                                 g.nom + ("" if not g.de_base else tr(" (de base)")))
            self.liste_groupes.addItem(it)
            if g.nom == nom:
                rang = i
        self.liste_groupes.blockSignals(False)
        if self.liste_groupes.count():
            self.liste_groupes.setCurrentRow(rang)
            self._montrer_groupe(rang)

    def _appliquer_taille(self, t: int) -> None:
        self.t = t
        self.grille.setIconSize(QSize(t, t))
        self.grille.setGridSize(QSize(t + 26, t + 34))

    def _taille_vignettes(self, t: int) -> None:
        self._appliquer_taille(t)
        _reglages().setValue("biblio_vignette", t)
        cle = self.grille.currentItem().data(Qt.UserRole).cle if self.grille.currentItem() else None
        self._cle_voulue = cle
        self._montrer_groupe(self.liste_groupes.currentRow())

    def groupe(self):
        i = self.liste_groupes.currentRow()
        groupes = self.biblio.groupes[self.genre]
        return groupes[i] if 0 <= i < len(groupes) else None

    def _montrer_groupe(self, _i: int) -> None:
        g = self.groupe()
        self.grille.clear()
        self.bouton_retirer.setEnabled(bool(g) and not g.de_base)
        if g is None:
            return
        for e in g.elements:
            it = QListWidgetItem(QIcon(QPixmap.fromImage(vignette(e, self.t))), e.nom)
            it.setData(Qt.UserRole, e)
            it.setToolTip(e.nom)
            self.grille.addItem(it)
            if e.cle == self._cle_voulue:
                self.grille.setCurrentItem(it)
        if self.grille.currentItem() is None and self.grille.count():
            self.grille.setCurrentRow(0)
        self._maj_info()

    def _maj_info(self, *_a) -> None:
        it = self.grille.currentItem()
        g = self.groupe()
        texte = ""
        self.apercu.clear()
        if it is not None:
            e = it.data(Qt.UserRole)
            self.apercu.setPixmap(QPixmap.fromImage(vignette(e, APERCU, detail=True)))
            if isinstance(e, Motif):
                texte = tr("{nom} : {l} × {h} px", nom=e.nom, l=e.image.shape[1], h=e.image.shape[0])
            else:
                h, w = e.formes[0].shape[:2]
                texte = tr("{nom} : {l} × {h} px", nom=e.nom, l=w, h=h)
                if len(e.formes) > 1:
                    texte += tr(" — {n} formes qui alternent pendant le trait", n=len(e.formes))
                if e.en_couleur:
                    texte += tr(" — en couleur (garde ses couleurs)")
        if g is not None and g.nom == STYLES:
            texte += ("\n" if texte else "") + tr("Style prêt : la forme et ses réglages (texture, dispersion, "
                                                   "flux…) d'un coup ; à ajuster ensuite avec Réglages… si besoin.")
        elif g is not None and g.nom == SIMPLES:
            texte += ("\n" if texte else "") + tr("Les pinceaux de tous les jours, pour peindre normalement ; la "
                                                   "taille et l'opacité se règlent dans la barre du haut.")
        elif g is not None and g.de_base:
            texte += ("\n" if texte else "") + tr("Livrés avec Pixane (ressources de Krita, licence CC-0).")
        self.info.setText(texte)

    def _ajouter(self) -> None:
        if self.genre == PINCEAUX:
            exts = EXT_PINCEAUX + EXT_PAQUETS + EXT_IMAGES
            filtre = tr("Pinceaux") + " (" + " ".join("*" + e for e in exts) + ")"
        else:
            exts = EXT_MOTIFS + EXT_PAQUETS + EXT_IMAGES
            filtre = tr("Motifs") + " (" + " ".join("*" + e for e in exts) + ")"
        fichiers, _ = QFileDialog.getOpenFileNames(self, tr("Ajouter des fichiers…"), "", filtre)
        if fichiers:
            self.importer(fichiers)

    def importer(self, fichiers: list) -> list:
        """Ajoute les fichiers ; montre le bilan. Renvoie les messages (pour les essais)."""
        messages, dernier = [], None
        for f in fichiers:
            nom = f.replace("\\", "/").rsplit("/", 1)[-1]
            try:
                b = self.biblio.importer(f, self.genre)
            except Exception as e:
                messages.append(tr("{fichier} : illisible ({raison})", fichier=nom, raison=e))
                continue
            morceaux = []
            if b[PINCEAUX]:
                morceaux.append(tr("{n} pinceau(x)", n=b[PINCEAUX]))
            if b[MOTIFS]:
                morceaux.append(tr("{n} motif(s)", n=b[MOTIFS]))
            texte = tr("{fichier} : {quoi}", fichier=nom, quoi=", ".join(morceaux))
            if b["ignores"]:
                texte += tr(" ({n} illisible(s), ignoré(s))", n=len(b["ignores"]))
            messages.append(texte)
            if b[self.genre]:
                dernier = nom.rsplit(".", 1)[0]
        groupes = self.biblio.groupes[self.genre]
        nom_groupe = next((g.nom for g in groupes if not g.de_base and dernier and g.nom.startswith(dernier)), None)
        self._remplir_groupes(nom_groupe)
        if self.isVisible():
            QMessageBox.information(self, tr("Ajouter des fichiers…"), "\n".join(messages))
        return messages

    def _retirer(self) -> None:
        g = self.groupe()
        if g is None or g.de_base:
            return
        r = QMessageBox.question(self, tr("Retirer ce groupe"),
                                 tr("Retirer « {nom} » de la bibliothèque ?", nom=g.nom))
        if r == QMessageBox.Yes:
            self.biblio.retirer(g)
            self._remplir_groupes()

    def _rond(self) -> None:
        self.choisi = None
        QDialog.accept(self)

    def accept(self) -> None:
        it = self.grille.currentItem()
        self.choisi = it.data(Qt.UserRole) if it is not None else None
        super().accept()
