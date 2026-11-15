"""IA > Supprimer les personnes : fenêtre où l'on coche les personnes à effacer (trouvées par SAM 3.1).

Chaque personne trouvée a une case et une vignette ; un clic sur la grande image coche ou décoche la personne
cliquée. Au départ, tout est coché sauf la personne principale (la plus grande, si elle se détache nettement).
"""
from __future__ import annotations

import numpy as np
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon, QImage, QPixmap
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
                               QPushButton, QVBoxLayout)

from .document import FORMAT_IMAGE, qimage_rgba, tableau
from .langue import tr

ROUGE = np.array([230, 40, 40], np.float32)
VERT = np.array([40, 200, 90], np.float32)


def choix_depart(masques: list[np.ndarray]) -> list[bool]:
    """Cochées au départ : toutes, sauf la plus grande si elle se détache (au moins 1,5 fois la suivante et 4 % de
    l'image) : c'est sans doute le sujet de la photo."""
    if not masques:
        return []
    aires = [float(m.mean()) for m in masques]
    coches = [True] * len(masques)
    ordre = sorted(range(len(aires)), key=lambda i: -aires[i])
    grand = ordre[0]
    second = aires[ordre[1]] if len(ordre) > 1 else 0.0
    if aires[grand] >= 0.04 and aires[grand] >= 1.5 * second:
        coches[grand] = False
    return coches


def union(masques: list[np.ndarray], coches: list[bool], marge: float) -> np.ndarray:
    """Masque 0..255 des personnes cochées, agrandi de `marge` pixels (ombres portées, cheveux, bord flou)."""
    from PIL import Image, ImageFilter
    if not any(coches):
        return np.zeros(masques[0].shape if masques else (1, 1), np.uint8)
    m = np.zeros(masques[0].shape, bool)
    for k, c in zip(masques, coches):
        if c:
            m |= k
    if marge <= 0:
        return np.where(m, 255, 0).astype(np.uint8)
    flou = np.asarray(Image.fromarray(np.where(m, 255, 0).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(marge / 2.05)))
    dur = np.where(flou > 5, 255, 0).astype(np.uint8)
    return np.asarray(Image.fromarray(dur).filter(ImageFilter.GaussianBlur(0.7)))


class _Apercu(QLabel):
    clic = Signal(float, float)       # position dans l'image, 0..1

    def mousePressEvent(self, e):
        pm = self.pixmap()
        if pm is None or pm.isNull():
            return
        x0 = (self.width() - pm.width()) / 2
        y0 = (self.height() - pm.height()) / 2
        p = e.position()
        u, v = (p.x() - x0) / pm.width(), (p.y() - y0) / pm.height()
        if 0 <= u <= 1 and 0 <= v <= 1:
            self.clic.emit(u, v)


class ChoixPersonnes(QDialog):
    """resultat() après exec() : « effacer » ou « selectionner » ; coches() : une case par masque."""
    LARGEUR = 760
    HAUTEUR = 500

    def __init__(self, image: QImage, masques: list[np.ndarray], parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Supprimer les personnes"))
        self.masques = masques
        self._mode = "effacer"
        rgba = tableau(image.convertToFormat(FORMAT_IMAGE))
        h, w = rgba.shape[:2]
        k = min(1.0, self.LARGEUR / w, self.HAUTEUR / h)
        pw, ph = max(1, round(w * k)), max(1, round(h * k))
        self._petite = tableau(image.convertToFormat(FORMAT_IMAGE).scaled(
            pw, ph, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)).astype(np.float32)
        iy = np.minimum((np.arange(ph) / k).astype(int), h - 1)
        ix = np.minimum((np.arange(pw) / k).astype(int), w - 1)
        self._petits = [m[iy][:, ix] for m in masques]
        lay = QVBoxLayout(self)
        info = QLabel(tr("{n} personne(s) trouvée(s). Les personnes cochées (en rouge) seront effacées, l'IA "
                         "reconstruit le fond derrière elles. Clique sur une personne dans l'image pour la cocher ou "
                         "la décocher. Une personne oubliée : choisis « Seulement sélectionner », puis ajoute-la avec "
                         "l'outil Sélection d'objet (Maj + clic) avant de lancer Effacer.", n=len(masques)))
        info.setWordWrap(True)
        lay.addWidget(info)
        milieu = QHBoxLayout()
        self.apercu = _Apercu()
        self.apercu.setAlignment(Qt.AlignCenter)
        self.apercu.setMinimumSize(pw, ph)
        self.apercu.setCursor(Qt.PointingHandCursor)
        self.apercu.clic.connect(self._clic)
        milieu.addWidget(self.apercu, 1)
        droite = QVBoxLayout()
        self.liste = QListWidget()
        self.liste.setIconSize(QSize(56, 56))
        self.liste.setMinimumWidth(200)
        for i, (m, c) in enumerate(zip(masques, choix_depart(masques))):
            it = QListWidgetItem(self._vignette(rgba, m), tr("Personne {n}", n=i + 1))
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked if c else Qt.Unchecked)
            self.liste.addItem(it)
        self.liste.itemChanged.connect(lambda _it: self._dessiner())
        droite.addWidget(self.liste, 1)
        rang = QHBoxLayout()
        b = QPushButton(tr("Tout cocher"))
        b.clicked.connect(lambda: self._tout(True))
        rang.addWidget(b)
        b = QPushButton(tr("Tout décocher"))
        b.clicked.connect(lambda: self._tout(False))
        rang.addWidget(b)
        droite.addLayout(rang)
        milieu.addLayout(droite)
        lay.addLayout(milieu, 1)
        boutons = QDialogButtonBox()
        self.b_effacer = boutons.addButton(tr("Effacer les personnes cochées"), QDialogButtonBox.AcceptRole)
        self.b_selection = boutons.addButton(tr("Seulement sélectionner"), QDialogButtonBox.AcceptRole)
        for b in (self.b_effacer, self.b_selection):     # texte en entier (le style ajoute des marges)
            b.setMinimumWidth(b.fontMetrics().horizontalAdvance(b.text()) + 48)
        boutons.addButton(tr("Annuler"), QDialogButtonBox.RejectRole)
        self.b_effacer.clicked.connect(lambda: self._fin("effacer"))
        self.b_selection.clicked.connect(lambda: self._fin("selectionner"))
        boutons.rejected.connect(self.reject)
        lay.addWidget(boutons)
        self._dessiner()

    @staticmethod
    def _vignette(rgba: np.ndarray, m: np.ndarray) -> QIcon:
        ys, xs = np.nonzero(m)
        if not len(xs):
            return QIcon()
        x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
        mx, my = max(4, (x1 - x0) // 6), max(4, (y1 - y0) // 6)
        x0, y0 = max(0, x0 - mx), max(0, y0 - my)
        x1, y1 = min(rgba.shape[1], x1 + mx), min(rgba.shape[0], y1 + my)
        img = qimage_rgba(rgba[y0:y1, x0:x1])
        return QIcon(QPixmap.fromImage(img.scaled(56, 56, Qt.KeepAspectRatio, Qt.SmoothTransformation)))

    def coches(self) -> list[bool]:
        return [self.liste.item(i).checkState() == Qt.Checked for i in range(self.liste.count())]

    def resultat(self) -> str:
        return self._mode

    def _tout(self, oui: bool):
        self.liste.blockSignals(True)
        for i in range(self.liste.count()):
            self.liste.item(i).setCheckState(Qt.Checked if oui else Qt.Unchecked)
        self.liste.blockSignals(False)
        self._dessiner()

    def _clic(self, u: float, v: float):
        """La plus petite personne sous le clic (une personne devant une autre) change d'état."""
        ph, pw = self._petite.shape[:2]
        x, y = min(pw - 1, int(u * pw)), min(ph - 1, int(v * ph))
        dessous = [i for i, m in enumerate(self._petits) if m[y, x]]
        if not dessous:
            return
        i = min(dessous, key=lambda j: self._petits[j].sum())
        it = self.liste.item(i)
        it.setCheckState(Qt.Unchecked if it.checkState() == Qt.Checked else Qt.Checked)
        self.liste.setCurrentRow(i)

    def _dessiner(self):
        a = self._petite.copy()
        for m, c in zip(self._petits, self.coches()):
            if c:
                a[m, :3] = a[m, :3] * 0.45 + ROUGE * 0.55
            else:
                a[m, :3] = a[m, :3] * 0.8 + VERT * 0.2
        self.apercu.setPixmap(QPixmap.fromImage(qimage_rgba(np.clip(a, 0, 255).astype(np.uint8))))

    def _fin(self, mode: str):
        self._mode = mode
        self.accept()
