"""Motifs (étape 3 de la bibliothèque) : un motif de la bibliothèque répété sur toute la surface (« pavage »), pour
le pot de peinture, Édition > Remplir avec un motif, le style « Incrustation de motif » et le tampon de motif ; et le
bouton qui le choisit.

Le pavage part du coin haut gauche de l'image : deux remplissages avec le même motif se raccordent (comme l'option
« Aligné » de Photoshop)."""
from __future__ import annotations

import numpy as np
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon, QImage, QPixmap
from PySide6.QtWidgets import QToolButton

from .bibliotheque import MOTIFS, bibliotheque
from .langue import tr

DEFAUT = "Krita 4/01_canvas.png#0"
_cache: dict = {}


def motif(cle: str | None):
    return bibliotheque().trouver(MOTIFS, cle) if cle else None


def tuile(cle: str | None, echelle: float = 1.0) -> np.ndarray | None:
    """Le motif (h, w, 4) RGBA uint8, à l'échelle voulue (1 = taille réelle) ; None : motif introuvable."""
    k = (cle, round(float(echelle), 3))
    if k in _cache:
        return _cache[k]
    e = motif(cle)
    if e is None:
        return None
    a = e.image
    if abs(echelle - 1) > 1e-3:
        from PIL import Image
        h, w = a.shape[:2]
        a = np.asarray(Image.fromarray(np.ascontiguousarray(a), "RGBA").resize(
            (max(1, round(w * echelle)), max(1, round(h * echelle))), Image.LANCZOS))
    if len(_cache) > 12:
        _cache.clear()
    _cache[k] = a
    return a


def pavage(t: np.ndarray, W: int, H: int, x0: int = 0, y0: int = 0) -> np.ndarray:
    """Le motif t répété sur W × H ; (x0, y0) : position de la zone dans l'image (pour que les pavés se raccordent)."""
    th, tw = t.shape[:2]
    ry = (np.arange(H) + y0) % th
    rx = (np.arange(W) + x0) % tw
    return t[ry[:, None], rx[None, :]]


def image_pavee(cle: str | None, W: int, H: int, echelle: float = 1.0, gris: bool = False) -> QImage | None:
    """QImage W × H (ARGB32 prémultiplié) couverte du motif ; gris : en niveaux de gris (pour un masque)."""
    t = tuile(cle, echelle)
    if t is None:
        return None
    a = pavage(t, W, H)
    if gris:
        lum = (a[..., :3].astype(np.float32) @ np.array([0.299, 0.587, 0.114], np.float32) + 0.5).astype(np.uint8)
        a = np.dstack([lum, lum, lum, a[..., 3]])
    a = np.ascontiguousarray(a)
    return QImage(a.data, W, H, 4 * W, QImage.Format_RGBA8888).convertToFormat(QImage.Format_ARGB32_Premultiplied)


class BoutonMotif(QToolButton):
    """Bouton « vignette + nom » ; un clic ouvre la bibliothèque des motifs. Signal change(clé)."""
    change = Signal(str)

    def __init__(self, cle: str | None = None, parent=None, compact: bool = False):
        super().__init__(parent)
        self.compact = compact          # barre du haut : la vignette seule (le nom est dans la bulle d'aide)
        self.setToolButtonStyle(Qt.ToolButtonIconOnly if compact else Qt.ToolButtonTextBesideIcon)
        self.setIconSize(QSize(22, 22))
        self.setToolTip(tr("Motif : clic pour choisir dans la bibliothèque (Krita, Photoshop .pat, GIMP, images…)"))
        self.clicked.connect(self.choisir)
        self.cle = None
        self.definir(cle or DEFAUT)

    def definir(self, cle: str | None):
        e = motif(cle)
        if e is None:
            e = motif(DEFAUT)
        self.cle = e.cle if e is not None else None
        if e is None:
            self.setText(tr("Motif"))
            self.setIcon(QIcon())
            return
        from .choix_bibliotheque import vignette
        self.setText(e.nom if len(e.nom) <= 18 else e.nom[:17] + "…")
        self.setIcon(QIcon(QPixmap.fromImage(vignette(e, 22))))
        if self.compact:
            self.setToolTip(tr("Motif « {nom} » : clic pour en choisir un autre dans la bibliothèque", nom=e.nom))

    def choisir(self):
        from .choix_bibliotheque import ChoixBibliotheque
        d = ChoixBibliotheque(MOTIFS, self.window(), cle=self.cle)
        if d.exec() and d.choisi is not None:
            self.definir(d.choisi.cle)
            self.change.emit(self.cle)


class DialogueRemplirMotif:
    """Édition > Remplir avec un motif… : motif, échelle et opacité. Après exec() : cle, echelle (1 = 100 %),
    opacite (0..1)."""

    def __init__(self, parent, cle: str | None, echelle: float, opacite: float, ou: str):
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLabel, QSpinBox
        self.d = d = QDialog(parent)
        d.setWindowTitle(tr("Remplir avec un motif"))
        form = QFormLayout(d)
        form.addRow(QLabel(ou))
        self.bouton = BoutonMotif(cle)
        form.addRow(tr("Motif"), self.bouton)
        self.champ_echelle = QSpinBox()
        self.champ_echelle.setRange(10, 1000)
        self.champ_echelle.setSingleStep(10)
        self.champ_echelle.setSuffix(" %")
        self.champ_echelle.setValue(round(echelle * 100))
        form.addRow(tr("Échelle"), self.champ_echelle)
        self.champ_opacite = QSpinBox()
        self.champ_opacite.setRange(1, 100)
        self.champ_opacite.setSuffix(" %")
        self.champ_opacite.setValue(round(opacite * 100))
        form.addRow(tr("Opacité"), self.champ_opacite)
        boutons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        boutons.accepted.connect(d.accept)
        boutons.rejected.connect(d.reject)
        form.addRow(boutons)

    def exec(self) -> bool:
        return bool(self.d.exec())

    @property
    def cle(self):
        return self.bouton.cle

    @property
    def echelle(self) -> float:
        return self.champ_echelle.value() / 100

    @property
    def opacite(self) -> float:
        return self.champ_opacite.value() / 100
