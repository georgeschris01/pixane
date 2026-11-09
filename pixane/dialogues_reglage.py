"""Fenêtres des réglages (niveaux, courbes, balance des couleurs, noir et blanc, vibrance) et des filtres, avec
aperçu en direct sur la photo (signal `change`, envoyé après une courte pause)."""
from __future__ import annotations

import copy

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QCheckBox, QColorDialog, QComboBox, QDialog, QDoubleSpinBox, QGridLayout, QHBoxLayout,
                               QLabel, QPushButton, QSlider, QSpinBox, QVBoxLayout, QWidget)

from . import ajustements, filtres
from .langue import tr

NOMS_CANAUX = {"rvb": "RVB", "r": "Rouge", "v": "Vert", "b": "Bleu"}
COUL_CANAUX = {"rvb": QColor(200, 200, 200), "r": QColor(230, 70, 70), "v": QColor(70, 200, 90),
               "b": QColor(80, 130, 240)}


def _noms_canaux():
    return {"rvb": tr("RVB"), "r": tr("Rouge"), "v": tr("Vert"), "b": tr("Bleu")}


def histogramme(rgb: np.ndarray | None) -> dict:
    """Histogrammes (256 cases) par canal, d'un échantillon de l'image."""
    if rgb is None or not rgb.size:
        return {}
    px = rgb.reshape(-1, 3)
    if len(px) > 300000:
        px = px[:: len(px) // 300000]
    lum = np.round(px.astype(np.float32) @ np.array([0.2126, 0.7152, 0.0722], np.float32)).astype(np.int64)
    return {"rvb": np.bincount(np.clip(lum, 0, 255), minlength=256)[:256],
            "r": np.bincount(px[:, 0], minlength=256), "v": np.bincount(px[:, 1], minlength=256),
            "b": np.bincount(px[:, 2], minlength=256)}


def _dessiner_histo(p: QPainter, r: QRectF, h: np.ndarray | None, couleur: QColor):
    if h is None or not h.any():
        return
    v = np.sqrt(h.astype(np.float64))
    v = v / max(1e-9, np.percentile(v, 99.5) * 1.05)
    chemin = QPainterPath(QPointF(r.left(), r.bottom()))
    for i in range(256):
        chemin.lineTo(r.left() + i / 255 * r.width(), r.bottom() - min(1.0, v[i]) * r.height())
    chemin.lineTo(r.right(), r.bottom())
    c = QColor(couleur)
    c.setAlpha(70)
    p.fillPath(chemin, c)


class Curseur(QWidget):
    """Libellé + curseur + case numérique (valeurs entières, ou décimales avec `decimales`)."""
    change = Signal()

    def __init__(self, libelle: str, mini, maxi, valeur, unite: str = "", decimales: int = 0):
        super().__init__()
        self.k = 10 ** decimales
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.etiquette = QLabel(libelle)
        self.etiquette.setMinimumWidth(150)
        self.c = QSlider(Qt.Horizontal)
        self.c.setRange(round(mini * self.k), round(maxi * self.k))
        self.c.setMinimumWidth(220)
        if decimales:
            self.s = QDoubleSpinBox()
            self.s.setDecimals(decimales)
            self.s.setSingleStep(1 / self.k)
        else:
            self.s = QSpinBox()
        self.s.setRange(mini, maxi)
        self.s.setSuffix(unite)
        self.c.valueChanged.connect(lambda v: self._depuis_curseur(v))
        self.s.valueChanged.connect(lambda v: self._depuis_case(v))
        lay.addWidget(self.etiquette)
        lay.addWidget(self.c, 1)
        lay.addWidget(self.s)
        self.definir(valeur)

    def _depuis_curseur(self, v):
        self.s.blockSignals(True)
        self.s.setValue(v / self.k if self.k > 1 else v)
        self.s.blockSignals(False)
        self.change.emit()

    def _depuis_case(self, v):
        self.c.blockSignals(True)
        self.c.setValue(round(v * self.k))
        self.c.blockSignals(False)
        self.change.emit()

    def valeur(self):
        return self.s.value()

    def definir(self, v):
        self.c.blockSignals(True)
        self.s.blockSignals(True)
        self.s.setValue(v)
        self.c.setValue(round(v * self.k))
        self.c.blockSignals(False)
        self.s.blockSignals(False)


class EditeurCourbe(QWidget):
    """Courbe d'un canal : clic = ajouter un point, glisser = le bouger, glisser hors du cadre ou clic droit =
    l'enlever (les deux bouts restent)."""
    change = Signal()

    def __init__(self):
        super().__init__()
        self.setMinimumSize(280, 280)
        self.points = [[0, 0], [255, 255]]
        self.histo = None
        self.couleur = COUL_CANAUX["rvb"]
        self._pris = None
        self.setMouseTracking(True)

    def _cadre(self) -> QRectF:
        c = min(self.width(), self.height()) - 12
        return QRectF(6, 6, c, c)

    def _vers_ecran(self, x, y):
        r = self._cadre()
        return QPointF(r.left() + x / 255 * r.width(), r.bottom() - y / 255 * r.height())

    def _vers_valeur(self, pos):
        r = self._cadre()
        return ((pos.x() - r.left()) / r.width() * 255, (r.bottom() - pos.y()) / r.height() * 255)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self._cadre()
        p.fillRect(r, self.palette().base())
        _dessiner_histo(p, r, self.histo, self.couleur)
        p.setPen(QPen(self.palette().mid().color(), 1))
        for k in range(1, 4):
            p.drawLine(QPointF(r.left() + r.width() * k / 4, r.top()), QPointF(r.left() + r.width() * k / 4, r.bottom()))
            p.drawLine(QPointF(r.left(), r.top() + r.height() * k / 4), QPointF(r.right(), r.top() + r.height() * k / 4))
        p.drawLine(r.bottomLeft(), r.topRight())
        p.drawRect(r)
        table = ajustements.table_courbe(self.points)
        chemin = QPainterPath(self._vers_ecran(0, table[0]))
        for i in range(1, 256):
            chemin.lineTo(self._vers_ecran(i, table[i]))
        p.setPen(QPen(self.couleur, 2))
        p.drawPath(chemin)
        p.setBrush(self.palette().base())
        for x, y in self.points:
            p.drawEllipse(self._vers_ecran(x, y), 4.5, 4.5)
        p.end()

    def _proche(self, pos):
        for i, (x, y) in enumerate(self.points):
            q = self._vers_ecran(x, y)
            if abs(q.x() - pos.x()) < 8 and abs(q.y() - pos.y()) < 8:
                return i
        return None

    def mousePressEvent(self, e):
        i = self._proche(e.position())
        if e.button() == Qt.RightButton:
            if i is not None and 0 < i < len(self.points) - 1:
                del self.points[i]
                self.update()
                self.change.emit()
            return
        if i is None:
            x, y = self._vers_valeur(e.position())
            x = int(np.clip(round(x), 1, 254))
            if any(px == x for px, _ in self.points):
                return
            self.points.append([x, int(np.clip(round(y), 0, 255))])
            self.points.sort()
            i = [px for px, _ in self.points].index(x)
            self.change.emit()
        self._pris = i
        self.update()

    def mouseMoveEvent(self, e):
        if self._pris is None:
            return
        x, y = self._vers_valeur(e.position())
        i = self._pris
        n = len(self.points)
        if 0 < i < n - 1:
            x = np.clip(round(x), self.points[i - 1][0] + 1, self.points[i + 1][0] - 1)
        else:
            x = np.clip(round(x), 0, 255)
            if i == 0 and n > 1:
                x = min(x, self.points[1][0] - 1)
            if i == n - 1 and n > 1:
                x = max(x, self.points[-2][0] + 1)
        self.points[i] = [int(x), int(np.clip(round(y), 0, 255))]
        self.update()
        self.change.emit()

    def mouseReleaseEvent(self, e):
        if self._pris is not None:
            r = self._cadre().adjusted(-20, -20, 20, 20)
            i = self._pris
            if not r.contains(e.position()) and 0 < i < len(self.points) - 1:
                del self.points[i]
                self.change.emit()
        self._pris = None
        self.update()


class _Panneau(QWidget):
    """Interface d'un type de réglage : lit et écrit ses paramètres."""
    change = Signal()

    def __init__(self, params: dict, histo: dict):
        super().__init__()
        self.p = copy.deepcopy(params)
        self.histo = histo

    def params(self) -> dict:
        return copy.deepcopy(self.p)


class PanneauNiveaux(_Panneau):
    def __init__(self, params, histo):
        super().__init__(params, histo)
        lay = QVBoxLayout(self)
        haut = QHBoxLayout()
        haut.addWidget(QLabel(tr("Canal")))
        self.canal = QComboBox()
        for k, n in _noms_canaux().items():
            self.canal.addItem(n, k)
        self.canal.currentIndexChanged.connect(self._montrer)
        haut.addWidget(self.canal)
        haut.addStretch(1)
        lay.addLayout(haut)
        self.dessin = QLabel()
        self.dessin.setMinimumHeight(110)
        lay.addWidget(self.dessin)
        self.c = [Curseur(tr("Noir (entrée)"), 0, 253, 0), Curseur(tr("Gris (gamma)"), 0.1, 9.99, 1.0, decimales=2),
                  Curseur(tr("Blanc (entrée)"), 2, 255, 255), Curseur(tr("Sortie : noir"), 0, 255, 0),
                  Curseur(tr("Sortie : blanc"), 0, 255, 255)]
        for c in self.c:
            c.change.connect(self._lire)
            lay.addWidget(c)
        self._montrer()

    def _montrer(self, *_):
        k = self.canal.currentData()
        for c, v in zip(self.c, self.p[k]):
            c.definir(v)
        self._dessin()

    def _dessin(self):
        from PySide6.QtGui import QPixmap
        k = self.canal.currentData()
        pm = QPixmap(380, 110)
        pm.fill(self.palette().base().color())
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(4, 4, 372, 90)
        _dessiner_histo(p, r, self.histo.get(k), COUL_CANAUX[k])
        noir, gamma, blanc = self.p[k][:3]
        for v, coul in ((noir, QColor(0, 0, 0)), (blanc, QColor(255, 255, 255))):
            x = r.left() + v / 255 * r.width()
            p.setPen(QPen(QColor(128, 128, 128), 1))
            p.setBrush(coul)
            p.drawPolygon([QPointF(x, 96), QPointF(x - 6, 106), QPointF(x + 6, 106)])
        milieu = noir + (blanc - noir) * 0.5 ** gamma
        x = r.left() + milieu / 255 * r.width()
        p.setBrush(QColor(128, 128, 128))
        p.drawPolygon([QPointF(x, 96), QPointF(x - 6, 106), QPointF(x + 6, 106)])
        p.end()
        self.dessin.setPixmap(pm)

    def _lire(self):
        k = self.canal.currentData()
        v = [c.valeur() for c in self.c]
        if v[2] <= v[0] + 1:
            v[2] = v[0] + 2
            self.c[2].definir(v[2])
        self.p[k] = [int(v[0]), float(v[1]), int(v[2]), int(v[3]), int(v[4])]
        self._dessin()
        self.change.emit()

    def auto(self):
        """Comme « Auto » de Photoshop : 0,1 % des pixels les plus sombres au noir, les plus clairs au blanc."""
        h = self.histo.get("rvb")
        if h is None:
            return
        c = np.cumsum(h) / max(1, h.sum())
        noir = int(np.searchsorted(c, 0.001))
        blanc = int(np.searchsorted(c, 0.999))
        if blanc - noir >= 10:
            self.p["rvb"] = [noir, 1.0, blanc, 0, 255]
            self.canal.setCurrentIndex(0)
            self._montrer()
            self.change.emit()


class PanneauCourbes(_Panneau):
    def __init__(self, params, histo):
        super().__init__(params, histo)
        lay = QVBoxLayout(self)
        haut = QHBoxLayout()
        haut.addWidget(QLabel(tr("Canal")))
        self.canal = QComboBox()
        for k, n in _noms_canaux().items():
            self.canal.addItem(n, k)
        self.canal.currentIndexChanged.connect(self._montrer)
        haut.addWidget(self.canal)
        haut.addStretch(1)
        lay.addLayout(haut)
        self.editeur = EditeurCourbe()
        self.editeur.change.connect(self._lire)
        lay.addWidget(self.editeur, 1)
        aide = QLabel(tr("Clic : ajouter un point · glisser : le bouger · clic droit : l'enlever"))
        aide.setObjectName("discret")
        lay.addWidget(aide)
        self._montrer()

    def _montrer(self, *_):
        k = self.canal.currentData()
        self.editeur.points = [list(x) for x in self.p[k]]
        self.editeur.histo = self.histo.get(k)
        self.editeur.couleur = COUL_CANAUX[k]
        self.editeur.update()

    def _lire(self):
        self.p[self.canal.currentData()] = [list(x) for x in self.editeur.points]
        self.change.emit()


class PanneauBalance(_Panneau):
    def __init__(self, params, histo):
        super().__init__(params, histo)
        lay = QVBoxLayout(self)
        haut = QHBoxLayout()
        haut.addWidget(QLabel(tr("Tons")))
        self.tons = QComboBox()
        for k, n in (("ombres", tr("Ombres")), ("moyens", tr("Tons moyens")), ("lumieres", tr("Hautes lumières"))):
            self.tons.addItem(n, k)
        self.tons.setCurrentIndex(1)
        self.tons.currentIndexChanged.connect(self._montrer)
        haut.addWidget(self.tons)
        haut.addStretch(1)
        lay.addLayout(haut)
        self.c = [Curseur(tr("Cyan — Rouge"), -100, 100, 0), Curseur(tr("Magenta — Vert"), -100, 100, 0),
                  Curseur(tr("Jaune — Bleu"), -100, 100, 0)]
        for c in self.c:
            c.change.connect(self._lire)
            lay.addWidget(c)
        self.lum = QCheckBox(tr("Préserver la luminosité"))
        self.lum.setChecked(bool(self.p.get("luminosite", True)))
        self.lum.toggled.connect(self._lire)
        lay.addWidget(self.lum)
        self._montrer()

    def _montrer(self, *_):
        for c, v in zip(self.c, self.p[self.tons.currentData()]):
            c.definir(v)

    def _lire(self, *_):
        self.p[self.tons.currentData()] = [int(c.valeur()) for c in self.c]
        self.p["luminosite"] = self.lum.isChecked()
        self.change.emit()


class PanneauNoirBlanc(_Panneau):
    def __init__(self, params, histo):
        super().__init__(params, histo)
        lay = QVBoxLayout(self)
        noms = {"rouges": tr("Rouges"), "jaunes": tr("Jaunes"), "verts": tr("Verts"), "cyans": tr("Cyans"),
                "bleus": tr("Bleus"), "magentas": tr("Magentas")}
        self.c = {}
        for k in ajustements.COULEURS_NB:
            c = Curseur(noms[k], -200, 300, self.p[k], " %")
            c.change.connect(self._lire)
            lay.addWidget(c)
            self.c[k] = c
        ligne = QHBoxLayout()
        self.virage = QCheckBox(tr("Virage (teinter le gris)"))
        self.virage.setChecked(bool(self.p.get("virage")))
        self.virage.toggled.connect(self._lire)
        self.b_couleur = QPushButton()
        self.b_couleur.setFixedWidth(60)
        self.b_couleur.clicked.connect(self._couleur)
        ligne.addWidget(self.virage)
        ligne.addWidget(self.b_couleur)
        ligne.addStretch(1)
        lay.addLayout(ligne)
        self.force = Curseur(tr("Force du virage"), 0, 100, self.p.get("force", 50), " %")
        self.force.change.connect(self._lire)
        lay.addWidget(self.force)
        self._peindre()

    def _peindre(self):
        self.b_couleur.setStyleSheet(f"background: {self.p.get('couleur', '#c8a878')};")

    def _couleur(self):
        c = QColorDialog.getColor(QColor(self.p.get("couleur", "#c8a878")), self, tr("Couleur du virage"))
        if c.isValid():
            self.p["couleur"] = c.name()
            self.virage.setChecked(True)
            self._peindre()
            self._lire()

    def _lire(self, *_):
        for k, c in self.c.items():
            self.p[k] = int(c.valeur())
        self.p["virage"] = self.virage.isChecked()
        self.p["force"] = int(self.force.valeur())
        self.change.emit()


class PanneauVibrance(_Panneau):
    def __init__(self, params, histo):
        super().__init__(params, histo)
        lay = QVBoxLayout(self)
        self.v = Curseur(tr("Vibrance"), -100, 100, self.p["vibrance"])
        self.s = Curseur(tr("Saturation"), -100, 100, self.p["saturation"])
        for c in (self.v, self.s):
            c.change.connect(self._lire)
            lay.addWidget(c)
        aide = QLabel(tr("La vibrance ravive surtout les couleurs ternes et ménage celles déjà vives (peau "
                         "comprise) ; la saturation change toutes les couleurs autant."))
        aide.setObjectName("discret")
        aide.setWordWrap(True)
        lay.addWidget(aide)

    def _lire(self):
        self.p = {"vibrance": int(self.v.valeur()), "saturation": int(self.s.valeur())}
        self.change.emit()


class PanneauBase(_Panneau):
    def __init__(self, params, histo):
        super().__init__(params, histo)
        from .reglages_image import REGLAGES, _noms
        lay = QVBoxLayout(self)
        noms = _noms()
        self.c = {}
        for cle, _nom, mini, maxi, unite in REGLAGES:
            c = Curseur(noms[cle], mini, maxi, self.p.get(cle, 0), unite)
            c.change.connect(self._lire)
            lay.addWidget(c)
            self.c[cle] = c

    def _lire(self):
        self.p = {k: int(c.valeur()) for k, c in self.c.items()}
        self.change.emit()


PANNEAUX = {"base": PanneauBase, "niveaux": PanneauNiveaux, "courbes": PanneauCourbes, "balance": PanneauBalance,
            "noir_blanc": PanneauNoirBlanc, "vibrance": PanneauVibrance}


class PanneauFiltre(_Panneau):
    def __init__(self, type_: str, params, histo):
        super().__init__(params, histo)
        lay = QVBoxLayout(self)
        lib = filtres.libelles()
        self.c = {}
        for cle, libelle, mini, maxi, _d, unite in filtres.FILTRES[type_]:
            c = Curseur(lib.get(libelle, libelle), mini, maxi, self.p.get(cle, _d), unite)
            c.change.connect(self._lire)
            lay.addWidget(c)
            self.c[cle] = c

    def _lire(self):
        self.p = {k: int(c.valeur()) for k, c in self.c.items()}
        self.change.emit()


class DialogueReglage(QDialog):
    """Fenêtre d'un réglage ou d'un filtre. `change(params)` après une courte pause ; Appliquer / Annuler."""
    change = Signal(object)

    def __init__(self, parent, titre: str, explication: str, panneau: _Panneau, neutres: dict, auto: bool = False):
        super().__init__(parent)
        self.setWindowTitle(titre)
        self.neutres = neutres
        lay = QVBoxLayout(self)
        info = QLabel(explication)
        info.setObjectName("discret")
        info.setWordWrap(True)
        lay.addWidget(info)
        self.panneau = panneau
        panneau.change.connect(self._plus_tard)
        lay.addWidget(panneau, 1)
        self.c_apercu = QCheckBox(tr("Aperçu sur la photo"))
        self.c_apercu.setChecked(True)
        self.c_apercu.toggled.connect(self._plus_tard)
        lay.addWidget(self.c_apercu)
        boutons = QHBoxLayout()
        b = QPushButton(tr("Réinitialiser"))
        b.clicked.connect(self.reinitialiser)
        boutons.addWidget(b)
        if auto:
            b = QPushButton(tr("Auto"))
            b.clicked.connect(lambda: self.panneau.auto())
            boutons.addWidget(b)
        boutons.addStretch(1)
        self.b_ok = QPushButton(tr("Appliquer"))
        self.b_ok.setDefault(True)
        self.b_ok.setMinimumWidth(self.b_ok.fontMetrics().horizontalAdvance(self.b_ok.text()) + 40)
        self.b_ok.clicked.connect(self.accept)
        annuler = QPushButton(tr("Annuler"))
        annuler.clicked.connect(self.reject)
        boutons.addWidget(self.b_ok)
        boutons.addWidget(annuler)
        lay.addLayout(boutons)
        self._minuterie = QTimer(self)
        self._minuterie.setSingleShot(True)
        self._minuterie.setInterval(150)
        self._minuterie.timeout.connect(lambda: self.change.emit(self.valeurs_apercu()))

    def _plus_tard(self, *_):
        self._minuterie.start()

    def valeurs(self) -> dict:
        return self.panneau.params()

    def fermer(self):
        """Après exec() : plus d'aperçu en attente, la fenêtre est détruite proprement."""
        self._minuterie.stop()
        try:
            self.change.disconnect()
        except (RuntimeError, TypeError):
            pass
        self.deleteLater()

    def valeurs_apercu(self):
        """Réglages à montrer, ou None (case Aperçu décochée : la photo d'origine)."""
        return self.valeurs() if self.c_apercu.isChecked() else None

    def reinitialiser(self):
        lay = self.layout()
        ancien = self.panneau
        nouveau = type(ancien)(copy.deepcopy(self.neutres), ancien.histo) if not isinstance(ancien, PanneauFiltre) \
            else None
        if nouveau is None:
            for k, c in ancien.c.items():
                c.definir(self.neutres[k])
            ancien._lire()
            return
        lay.replaceWidget(ancien, nouveau)
        ancien.deleteLater()
        self.panneau = nouveau
        nouveau.change.connect(self._plus_tard)
        self._plus_tard()
