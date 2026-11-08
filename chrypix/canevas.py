"""Zone d'affichage : zoom, déplacement, outils de sélection (rectangle, lasso, pinceau, gomme)."""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen, QPixmap, QTransform
from PySide6.QtWidgets import QWidget

from .document import COULEUR_SELECTION, Document

MAIN, RECTANGLE, LASSO, PINCEAU, GOMME = "main", "rectangle", "lasso", "pinceau", "gomme"
OPACITE_SELECTION = 0.45


class Canevas(QWidget):
    selection_modifiee = Signal(object, str)   # (état avant, nom de l'action) -> pour annuler
    infos = Signal(str)                         # zoom, position

    def __init__(self, parent=None):
        super().__init__(parent)
        self.doc: Document | None = None
        self.zoom = 1.0
        self.decalage = QPointF(0, 0)
        self.outil = PINCEAU
        self.taille_pinceau = 60
        self._espace = False
        self._glisse = None          # point de départ d'un déplacement
        self._trace = None           # tracé en cours (liste de points image)
        self._soustraire = False
        self._avant = None
        self._souris = None
        self._cache = None           # (clé, pixmap réduite)
        self._ajuste = True          # l'image suit la taille de la fenêtre
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMinimumSize(300, 200)
        self.setAttribute(Qt.WA_OpaquePaintEvent)

    # ---------------------------------------------------------- document
    def definir_document(self, doc: Document | None):
        if self.doc is not None:
            try:
                self.doc.change.disconnect(self._doc_change)
                self.doc.taille_changee.disconnect(self.ajuster)
            except (RuntimeError, TypeError):
                pass
        self.doc = doc
        self._cache = None
        if doc is not None:
            doc.change.connect(self._doc_change)
            doc.taille_changee.connect(self.ajuster)
        self.ajuster()

    def _doc_change(self):
        self.update()

    # ---------------------------------------------------------- coordonnées
    def vers_image(self, p: QPointF) -> QPointF:
        return (p - self.decalage) / self.zoom

    def vers_ecran(self, p: QPointF) -> QPointF:
        return p * self.zoom + self.decalage

    # ---------------------------------------------------------- zoom
    def ajuster(self):
        if not self.doc:
            self.update()
            return
        iw, ih = self.doc.image.width(), self.doc.image.height()
        self.zoom = max(0.01, min(self.width() / iw, self.height() / ih) * 0.96)
        self._centrer()
        self._ajuste = True

    def zoom_100(self):
        if self.doc:
            self.definir_zoom(1.0, QPointF(self.width() / 2, self.height() / 2))

    def _centrer(self):
        iw, ih = self.doc.image.width() * self.zoom, self.doc.image.height() * self.zoom
        self.decalage = QPointF((self.width() - iw) / 2, (self.height() - ih) / 2)
        self._signaler()
        self.update()

    def definir_zoom(self, zoom: float, autour: QPointF):
        zoom = max(0.02, min(32.0, zoom))
        point_image = self.vers_image(autour)
        self.zoom = zoom
        self._ajuste = False
        self.decalage = autour - point_image * zoom
        self._signaler()
        self.update()

    def zoomer(self, facteur: float):
        self.definir_zoom(self.zoom * facteur, QPointF(self.width() / 2, self.height() / 2))

    def _signaler(self):
        if self.doc:
            self.infos.emit(f"{self.doc.image.width()} × {self.doc.image.height()} px   |   zoom {self.zoom * 100:.0f} %")

    def resizeEvent(self, e):
        if self.doc and self._ajuste:
            self.ajuster()
        super().resizeEvent(e)

    # ---------------------------------------------------------- dessin
    def _pixmap_reduite(self):
        """Image réduite et lissée, mise en cache, quand le zoom est < 100 %."""
        cle = (self.doc.image.cacheKey(), round(self.zoom, 4))
        if self._cache is None or self._cache[0] != cle:
            w = max(1, round(self.doc.image.width() * self.zoom))
            h = max(1, round(self.doc.image.height() * self.zoom))
            self._cache = (cle, QPixmap.fromImage(self.doc.image.scaled(w, h, Qt.IgnoreAspectRatio,
                                                                         Qt.SmoothTransformation)))
        return self._cache[1]

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(40, 40, 40))
        if not self.doc:
            p.setPen(QColor(150, 150, 150))
            p.drawText(self.rect(), Qt.AlignCenter, "Fichier > Ouvrir…  (ou glisse une photo ici)")
            return
        if self.zoom < 1:
            p.drawPixmap(self.decalage, self._pixmap_reduite())
        else:
            p.save()
            p.setTransform(QTransform(self.zoom, 0, 0, self.zoom, self.decalage.x(), self.decalage.y()))
            p.drawImage(QPointF(0, 0), self.doc.image)
            p.restore()
        # sélection (calque rouge semi-transparent)
        p.save()
        p.setTransform(QTransform(self.zoom, 0, 0, self.zoom, self.decalage.x(), self.decalage.y()))
        p.setOpacity(OPACITE_SELECTION)
        p.drawImage(QPointF(0, 0), self.doc.selection)
        p.setOpacity(1)
        # tracé en cours
        if self._trace and self.outil in (RECTANGLE, LASSO):
            stylo = QPen(QColor(255, 255, 255), 0, Qt.DashLine)
            stylo.setCosmetic(True)
            p.setPen(stylo)
            if self.outil == RECTANGLE:
                p.drawRect(QRectF(self._trace[0], self._trace[-1]).normalized())
            else:
                chemin = QPainterPath(self._trace[0])
                for pt in self._trace[1:]:
                    chemin.lineTo(pt)
                p.drawPath(chemin)
        p.restore()
        # contour de l'image
        p.setPen(QColor(90, 90, 90))
        p.drawRect(QRectF(self.decalage, self.decalage + QPointF(self.doc.image.width(),
                                                                 self.doc.image.height()) * self.zoom))
        # curseur du pinceau
        if self._souris is not None and self.outil in (PINCEAU, GOMME) and not self._espace:
            r = self.taille_pinceau * self.zoom / 2
            p.setPen(QPen(QColor(0, 0, 0), 3))
            p.drawEllipse(self._souris, r, r)
            p.setPen(QPen(QColor(255, 255, 255), 1))
            p.drawEllipse(self._souris, r, r)

    # ---------------------------------------------------------- peinture de la sélection
    def _peintre_selection(self) -> QPainter:
        p = QPainter(self.doc.selection)
        p.setRenderHint(QPainter.Antialiasing)
        if self._soustraire or self.outil == GOMME:
            p.setCompositionMode(QPainter.CompositionMode_DestinationOut)
        return p

    def _coup_de_pinceau(self, a: QPointF, b: QPointF):
        p = self._peintre_selection()
        p.setPen(QPen(COULEUR_SELECTION, self.taille_pinceau, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        if a == b:
            p.setPen(Qt.NoPen)
            p.setBrush(COULEUR_SELECTION)
            r = self.taille_pinceau / 2
            p.drawEllipse(a, r, r)
        else:
            p.drawLine(a, b)
        p.end()

    def _remplir_forme(self):
        chemin = QPainterPath()
        if self.outil == RECTANGLE:
            chemin.addRect(QRectF(self._trace[0], self._trace[-1]).normalized())
        else:
            chemin.moveTo(self._trace[0])
            for pt in self._trace[1:]:
                chemin.lineTo(pt)
            chemin.closeSubpath()
        p = self._peintre_selection()
        p.fillPath(chemin, COULEUR_SELECTION)
        p.end()

    # ---------------------------------------------------------- souris
    def _deplacement_actif(self, e) -> bool:
        return self.outil == MAIN or self._espace or e.buttons() & Qt.MiddleButton

    def mousePressEvent(self, e):
        if not self.doc:
            return
        pos = e.position()
        if e.button() == Qt.MiddleButton or (e.button() == Qt.LeftButton and (self.outil == MAIN or self._espace)):
            self._glisse = pos
            self.setCursor(Qt.ClosedHandCursor)
            return
        if e.button() != Qt.LeftButton:
            return
        self._soustraire = bool(e.modifiers() & Qt.AltModifier)
        self._avant = self.doc.etat()
        pt = self.vers_image(pos)
        self._trace = [pt]
        if self.outil in (PINCEAU, GOMME):
            self._coup_de_pinceau(pt, pt)
        self.update()

    def mouseMoveEvent(self, e):
        pos = e.position()
        self._souris = pos
        if self._glisse is not None:
            self.decalage += pos - self._glisse
            self._glisse = pos
            self._ajuste = False
            self.update()
            return
        if self._trace is not None:
            pt = self.vers_image(pos)
            if self.outil in (PINCEAU, GOMME):
                self._coup_de_pinceau(self._trace[-1], pt)
                self._trace.append(pt)
            elif self.outil == RECTANGLE:
                self._trace = [self._trace[0], pt]
            else:
                self._trace.append(pt)
        self.update()

    def mouseReleaseEvent(self, e):
        if self._glisse is not None:
            self._glisse = None
            self._curseur()
            return
        if self._trace is None:
            return
        if self.outil in (RECTANGLE, LASSO) and len(self._trace) > 1:
            self._remplir_forme()
        noms = {PINCEAU: "Pinceau de sélection", GOMME: "Gomme de sélection", RECTANGLE: "Sélection rectangle",
                LASSO: "Lasso"}
        self._trace = None
        self.selection_modifiee.emit(self._avant, noms[self.outil])
        self._avant = None
        self.update()

    def leaveEvent(self, e):
        self._souris = None
        self.update()

    def wheelEvent(self, e):
        if not self.doc:
            return
        facteur = 1.2 if e.angleDelta().y() > 0 else 1 / 1.2
        self.definir_zoom(self.zoom * facteur, e.position())

    # ---------------------------------------------------------- clavier
    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Space and not e.isAutoRepeat():
            self._espace = True
            self.setCursor(Qt.OpenHandCursor)
        elif e.key() == Qt.Key_BracketLeft:
            self.definir_taille(self.taille_pinceau / 1.2)
        elif e.key() == Qt.Key_BracketRight:
            self.definir_taille(self.taille_pinceau * 1.2)
        else:
            super().keyPressEvent(e)

    def keyReleaseEvent(self, e):
        if e.key() == Qt.Key_Space and not e.isAutoRepeat():
            self._espace = False
            self._curseur()
        else:
            super().keyReleaseEvent(e)

    taille_changee = Signal(int)

    def definir_taille(self, taille: float):
        self.taille_pinceau = int(max(2, min(2000, taille)))
        self.taille_changee.emit(self.taille_pinceau)
        self.update()

    def definir_outil(self, outil: str):
        self.outil = outil
        self._curseur()
        self.update()

    def _curseur(self):
        self.setCursor(Qt.OpenHandCursor if self.outil == MAIN else
                       Qt.BlankCursor if self.outil in (PINCEAU, GOMME) else Qt.CrossCursor)
