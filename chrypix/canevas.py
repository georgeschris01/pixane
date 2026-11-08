"""Zone d'affichage : zoom, déplacement, outils de sélection (rectangle, lasso, pinceau, gomme)."""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QImage, QPainter, QPainterPath, QPen, QPixmap, QTransform
from PySide6.QtWidgets import QWidget

from .document import COULEUR_SELECTION, Document

MAIN, RECTANGLE, LASSO, PINCEAU, GOMME = "main", "rectangle", "lasso", "pinceau", "gomme"
OPACITE_SELECTION = 0.45


class Canevas(QWidget):
    selection_modifiee = Signal(object, str)   # (état avant, nom de l'action) -> pour annuler
    infos = Signal(int, int, float)             # largeur, hauteur, zoom
    cadre_change = Signal(object, object)       # Agrandir : (ajout, bord abîmé), chacun (haut, bas, gauche, droite) px
    cadre_valide = Signal()                     # Entrée pendant Agrandir
    cadre_annule = Signal()                     # Échap pendant Agrandir

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
        self.mode_retirer = False    # pastilles Ajouter / Retirer
        self.couleur_fond = QColor(40, 40, 40)
        self.couleur_texte = QColor(150, 150, 150)
        self.couleur_accent = QColor(0, 120, 215)
        self.cadre = None            # Agrandir : px ajoutés [haut, bas, gauche, droite], sinon None
        self.abime = [0, 0, 0, 0]    # Agrandir : px de bord abîmé à refaire [haut, bas, gauche, droite]
        self._poignee = None         # (cible « ext » / « int » / « ? », côtés parmi "h", "b", "g", "d")
        self._depart = None          # point (image) où le glisser du cadre a commencé
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
        if self.cadre is not None:   # place pour tirer le cadre : au moins 40 % de chaque côté
            h, b, g, d = self.cadre
            tw, th = iw + 2 * max(g, d, iw * 0.4), ih + 2 * max(h, b, ih * 0.4)
        else:
            tw, th = iw, ih
        self.zoom = max(0.01, min(self.width() / tw, self.height() / th) * 0.96)
        self._centrer()
        self._ajuste = True

    def zoom_100(self):
        if self.doc:
            self.definir_zoom(1.0, QPointF(self.width() / 2, self.height() / 2))

    def _centrer(self):
        iw, ih = self.doc.image.width() * self.zoom, self.doc.image.height() * self.zoom
        self.decalage = QPointF((self.width() - iw) / 2, (self.height() - ih) / 2)
        if self.cadre is not None:   # centrer le cadre entier plutôt que la photo
            h, b, g, d = self.cadre
            self.decalage += QPointF((g - d) * self.zoom / 2, (h - b) * self.zoom / 2)
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
            self.infos.emit(self.doc.image.width(), self.doc.image.height(), self.zoom)

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
        p.fillRect(self.rect(), self.couleur_fond)
        if not self.doc:
            p.setPen(self.couleur_texte)
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
        if self.cadre is not None:
            self._dessiner_cadre(p)
            return
        # contour de l'image
        p.setPen(QColor(0, 0, 0, 60))
        p.drawRect(QRectF(self.decalage, self.decalage + QPointF(self.doc.image.width(),
                                                                 self.doc.image.height()) * self.zoom))
        # curseur du pinceau
        if self._souris is not None and self.outil in (PINCEAU, GOMME) and not self._espace and self.cadre is None:
            r = self.taille_pinceau * self.zoom / 2
            p.setPen(QPen(QColor(0, 0, 0), 3))
            p.drawEllipse(self._souris, r, r)
            p.setPen(QPen(QColor(255, 255, 255), 1))
            p.drawEllipse(self._souris, r, r)

    # ---------------------------------------------------------- Agrandir : deux cadres à poignées
    # Cadre extérieur (accent, poignées carrées) : jusqu'où agrandir, en px ajoutés par côté.
    # Cadre intérieur (rouge, poignées rondes) : limite de la partie saine ; la bande entre ce cadre et le bord
    # de la photo est « abîmée » : elle est jetée et redessinée par l'IA avec l'agrandissement.
    # Ordre des valeurs partout : (haut, bas, gauche, droite).
    def commencer_cadre(self, abime=(0, 0, 0, 0)):
        self.cadre = [0, 0, 0, 0]
        self.abime = [int(v) for v in abime]
        self._poignee = None
        self.ajuster()
        self.setCursor(Qt.ArrowCursor)
        self.setFocus()
        self._emettre_cadre()

    def definir_cadre(self, ajout, abime):
        """Valeurs venant des cases de la barre (sans changer le zoom)."""
        if self.cadre is not None:
            self.cadre = [int(v) for v in ajout]
            self.abime = [int(v) for v in abime]
            self.update()

    def finir_cadre(self):
        self.cadre = None
        self._poignee = None
        self._curseur()
        self.ajuster()

    def _emettre_cadre(self):
        self.cadre_change.emit(tuple(self.cadre), tuple(self.abime))

    def _rect_cadre(self) -> QRectF:
        """Cadre extérieur (photo + ajouts) en coordonnées écran."""
        h, b, g, d = self.cadre
        iw, ih = self.doc.image.width(), self.doc.image.height()
        return QRectF(self.vers_ecran(QPointF(-g, -h)), self.vers_ecran(QPointF(iw + d, ih + b)))

    def _rect_sain(self) -> QRectF:
        """Cadre intérieur (partie saine de la photo) en coordonnées écran."""
        h, b, g, d = self.abime
        iw, ih = self.doc.image.width(), self.doc.image.height()
        return QRectF(self.vers_ecran(QPointF(g, h)), self.vers_ecran(QPointF(iw - d, ih - b)))

    @staticmethod
    def _cotes_sous(r: QRectF, pos: QPointF, tol: float = 10) -> set:
        if not r.adjusted(-tol, -tol, tol, tol).contains(pos):
            return set()
        cotes = set()
        if abs(pos.y() - r.top()) <= tol:
            cotes.add("h")
        elif abs(pos.y() - r.bottom()) <= tol:
            cotes.add("b")
        if abs(pos.x() - r.left()) <= tol:
            cotes.add("g")
        elif abs(pos.x() - r.right()) <= tol:
            cotes.add("d")
        return cotes

    def _poignee_sous(self, pos: QPointF):
        """(cible, côtés) : cible « ext », « int », ou « ? » si les deux cadres se touchent à cet endroit
        (on choisit alors au premier mouvement : vers l'extérieur = agrandir, vers l'intérieur = bord abîmé)."""
        ext = self._cotes_sous(self._rect_cadre(), pos)
        sain = self._cotes_sous(self._rect_sain(), pos)
        if ext and sain:
            return ("?", ext)
        if ext:
            return ("ext", ext)
        if sain:
            return ("int", sain)
        return None

    def _curseur_cadre(self, poignee):
        cotes = poignee[1] if poignee else set()
        if cotes in ({"h", "g"}, {"b", "d"}):
            self.setCursor(Qt.SizeFDiagCursor)
        elif cotes in ({"h", "d"}, {"b", "g"}):
            self.setCursor(Qt.SizeBDiagCursor)
        elif cotes & {"h", "b"}:
            self.setCursor(Qt.SizeVerCursor)
        elif cotes:
            self.setCursor(Qt.SizeHorCursor)
        else:
            self.setCursor(Qt.OpenHandCursor if self.outil == MAIN else Qt.ArrowCursor)

    def _tirer_cadre(self, pos: QPointF, symetrique: bool):
        pt = self.vers_image(pos)
        iw, ih = self.doc.image.width(), self.doc.image.height()
        cible, cotes = self._poignee
        # vecteur « vers l'extérieur » de chaque côté, en px image (positif = on sort de la photo)
        dehors = {"h": -pt.y(), "b": pt.y() - ih, "g": -pt.x(), "d": pt.x() - iw}
        if cible == "?":
            depart = self._depart
            dep = {"h": -depart.y(), "b": depart.y() - ih, "g": -depart.x(), "d": depart.x() - iw}
            cote = next(iter(cotes))
            if abs(dehors[cote] - dep[cote]) < 2 / self.zoom:
                return                                   # pas encore assez bougé pour décider
            cible = "ext" if dehors[cote] > dep[cote] else "int"
            self._poignee = (cible, cotes)
        index = {"h": 0, "b": 1, "g": 2, "d": 3}
        oppose = {"h": "b", "b": "h", "g": "d", "d": "g"}
        taille = {"h": ih, "b": ih, "g": iw, "d": iw}
        for cote in cotes:
            n = taille[cote]
            if cible == "ext":   # agrandir : de 0 à 200 % de la photo
                v = int(max(0, min(2 * n, round(dehors[cote]))))
                self.cadre[index[cote]] = v
                if symetrique:
                    self.cadre[index[oppose[cote]]] = v
            else:                # bord abîmé : on garde au moins 32 px de photo saine
                autre = 0 if symetrique else self.abime[index[oppose[cote]]]
                maxi = (n - 32) // 2 if symetrique else n - autre - 32
                v = int(max(0, min(maxi, round(-dehors[cote]))))
                self.abime[index[cote]] = v
                if symetrique:
                    self.abime[index[oppose[cote]]] = v
        self._emettre_cadre()
        self.update()

    def _dessiner_cadre(self, p: QPainter):
        r = self._rect_cadre()
        sain = self._rect_sain()
        photo = QRectF(self.decalage, self.decalage + QPointF(self.doc.image.width(),
                                                              self.doc.image.height()) * self.zoom)

        def chemin(rect: QRectF) -> QPainterPath:
            c = QPainterPath()
            c.addRect(rect)
            return c
        # zone ajoutée : damier gris (comme une zone vide)
        damier = QPixmap(16, 16)
        damier.fill(QColor(205, 205, 205))
        pd = QPainter(damier)
        pd.fillRect(0, 0, 8, 8, QColor(240, 240, 240))
        pd.fillRect(8, 8, 8, 8, QColor(240, 240, 240))
        pd.end()
        p.fillPath(chemin(r).subtracted(chemin(photo)), QBrush(damier))
        # bord abîmé : rouge hachuré (sera redessiné)
        bande = chemin(photo).subtracted(chemin(sain))
        p.fillPath(bande, QColor(230, 40, 40, 90))
        p.fillPath(bande, QBrush(QColor(255, 255, 255, 120), Qt.BDiagPattern))
        # cadre intérieur (rouge, pointillés) et extérieur (accent, pointillés)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(0, 0, 0, 160), 1))
        p.drawRect(r)
        p.setPen(QPen(QColor(255, 255, 255), 1, Qt.DashLine))
        p.drawRect(r)
        if sain != photo:
            p.setPen(QPen(QColor(230, 40, 40), 2, Qt.DashLine))
            p.drawRect(sain)

        def points(rect):
            c = rect.center()
            return [rect.topLeft(), QPointF(c.x(), rect.top()), rect.topRight(), QPointF(rect.right(), c.y()),
                    rect.bottomRight(), QPointF(c.x(), rect.bottom()), rect.bottomLeft(), QPointF(rect.left(), c.y())]
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor(0, 0, 0, 180), 1))
        p.setBrush(self.couleur_accent)
        for pt in points(r):
            p.drawRect(QRectF(pt.x() - 5, pt.y() - 5, 10, 10))
        p.setPen(QPen(QColor(255, 255, 255), 1.5))
        p.setBrush(QColor(230, 40, 40))
        for pt in points(sain):
            p.drawEllipse(pt, 4.5, 4.5)

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
        if self.cadre is not None and e.button() == Qt.LeftButton:   # Agrandir : les poignées d'abord
            self._poignee = self._poignee_sous(pos)
            if self._poignee:
                self._depart = self.vers_image(pos)
                return
        if e.button() == Qt.MiddleButton or (e.button() == Qt.LeftButton and (self.outil == MAIN or self._espace)):
            self._glisse = pos
            self.setCursor(Qt.ClosedHandCursor)
            return
        if e.button() != Qt.LeftButton:
            return
        if self.cadre is not None:
            return
        self._soustraire = self.mode_retirer != bool(e.modifiers() & Qt.AltModifier)
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
        if self.cadre is not None:
            if self._poignee:
                self._tirer_cadre(pos, bool(e.modifiers() & Qt.ShiftModifier))
            else:
                self._curseur_cadre(self._poignee_sous(pos))
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
        if self.cadre is not None:
            self._poignee = None
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
        if self.cadre is not None and e.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.cadre_valide.emit()
        elif self.cadre is not None and e.key() == Qt.Key_Escape:
            self.cadre_annule.emit()
        elif e.key() == Qt.Key_Space and not e.isAutoRepeat():
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

    def definir_couleurs(self, fond: str, texte: str, accent: str | None = None):
        self.couleur_fond, self.couleur_texte = QColor(fond), QColor(texte)
        if accent:
            self.couleur_accent = QColor(accent)
        self.update()

    def definir_mode_retirer(self, oui: bool):
        self.mode_retirer = oui

    def definir_outil(self, outil: str):
        self.outil = outil
        self._curseur()
        self.update()

    def _curseur(self):
        if self.cadre is not None:
            self.setCursor(Qt.ArrowCursor)
            return
        self.setCursor(Qt.OpenHandCursor if self.outil == MAIN else
                       Qt.BlankCursor if self.outil in (PINCEAU, GOMME) else Qt.CrossCursor)
