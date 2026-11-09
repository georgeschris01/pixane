"""Zone d'affichage : zoom, déplacement, outils de sélection (rectangle, lasso, pinceau, gomme, baguette
magique, sélection rapide, sélection d'objet), texte, recadrage, pinceau de couleur et tampon."""
from __future__ import annotations

import math
from dataclasses import replace

from PySide6.QtCore import QLineF, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QImage, QPainter, QPainterPath, QPen, QPixmap, QPolygonF, QTransform
from PySide6.QtWidgets import QWidget

from .document import COULEUR_SELECTION, Document
from .langue import tr
from .retouche import Trait
from .texte import contient, contour_bloc, rendre
from .transformation import POIGNEES, Transformation

MAIN, RECTANGLE, LASSO, PINCEAU, GOMME = "main", "rectangle", "lasso", "pinceau", "gomme"
GOMME_CALQUE = "gomme_calque"                  # efface pour de vrai les pixels du calque actif
TEXTE = "texte"                                # écrire, déplacer, tourner un texte
DEPLACER = "deplacer"                          # déplacer le contenu du calque choisi
RECADRER = "recadrer"                          # garder une partie de la photo
PEINTURE = "peinture"                          # pinceau de couleur sur le calque choisi
TAMPON = "tampon"                              # copier une zone de la photo sur une autre (Alt+clic : source)
BAGUETTE = "baguette"                          # baguette magique : zone de couleur proche (glisser = tolérance)
RAPIDE = "rapide"                              # sélection rapide (IA) : peindre sur l'objet
OBJET = "objet"                                # sélection d'objet (IA) : cadre autour, ou clic dessus
SUPPRIMER = "supprimer"                        # pinceau Supprimer (IA, LaMa) : le défaut peint disparaît au lâcher
OUTILS_ROND = (PINCEAU, GOMME, GOMME_CALQUE, PEINTURE, TAMPON, RAPIDE, SUPPRIMER)   # curseur rond (taille)
OUTILS_AUTO = (BAGUETTE, RAPIDE, OBJET)                                  # sélections calculées
OUTILS_CALQUE = (GOMME_CALQUE, PEINTURE, TAMPON)                  # outils qui changent les pixels du calque
OPACITE_SELECTION = 0.45


class Canevas(QWidget):
    selection_modifiee = Signal(object, str)   # (état avant, nom de l'action) -> pour annuler (sélection ou calque)
    infos = Signal(int, int, float)             # largeur, hauteur, zoom
    refus = Signal(str)                         # action impossible (ex. calque verrouillé) : message
    cadre_change = Signal(object, object)       # Agrandir : (ajout, bord abîmé), chacun (haut, bas, gauche, droite) px
    cadre_valide = Signal()                     # Entrée pendant Agrandir
    cadre_annule = Signal()                     # Échap pendant Agrandir
    texte_nouveau = Signal(object)              # outil Texte : clic hors des textes -> point (image)
    texte_choisi = Signal(int)                  # outil Texte : clic sur un calque de texte -> son index
    couleur_prise = Signal(str)                 # pinceau de couleur : Alt+clic (pipette) -> couleur « #rrggbb »
    recadre_change = Signal(object)             # outil Recadrer : QRect (image) ou None
    recadre_valide = Signal()                   # Entrée ou double-clic dans le cadre
    transfo_change = Signal()                   # Transformer (Ctrl+T) : taille ou angle modifié
    transfo_valide = Signal()                   # Entrée ou double-clic dans le cadre
    transfo_annule = Signal()                   # Échap
    message = Signal(str)                       # information (barre d'état)
    baguette_clic = Signal(object, str)         # point (image), mode « nouvelle » / « ajouter » / « retirer »
    baguette_glisse = Signal(float)             # écart horizontal (écran) depuis le clic -> tolérance
    baguette_lache = Signal()
    trait_ia = Signal(list, bool, bool)         # sélection rapide : points (image), Alt (retirer), Maj (nouvel objet)
    objet_ia = Signal(object, str)              # sélection d'objet : QRectF (cadre) ou QPointF (clic), mode
    fin_session_ia = Signal()                   # Échap avec la sélection rapide : l'objet suivant repart de zéro
    suppression = Signal(list, float)           # pinceau Supprimer : points (image), taille du pinceau
    poignee_sol_bouge = Signal(object)          # style « ombre au sol » : bout de l'ombre tiré (point image)

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
        self.mode_retirer = False    # pinceau de sélection : pastilles Ajouter / Retirer
        self.mode_forme = "nouvelle" # rectangle et lasso : « nouvelle » (remplace), « ajouter » ou « retirer »
        self._nouvelle = False       # tracé en cours qui remplacera la sélection
        self.couleur_fond = QColor(40, 40, 40)
        self.couleur_texte = QColor(150, 150, 150)
        self.couleur_accent = QColor(0, 120, 215)
        self.cadre = None            # Agrandir : px ajoutés [haut, bas, gauche, droite], sinon None
        self.abime = [0, 0, 0, 0]    # Agrandir : px de bord abîmé à refaire [haut, bas, gauche, droite]
        self._poignee = None         # (cible « ext » / « int » / « ? », côtés parmi "h", "b", "g", "d")
        self._depart = None          # point (image) où le glisser du cadre a commencé
        self._texte_glisse = None    # (index, « deplacer » / « tourner », départ, Texte d'origine, état d'avant)
        self._calque_glisse = None   # outil Déplacer : (index, départ, image d'origine, état d'avant)
        # pinceau de couleur et tampon
        self.couleur_peinture = QColor(0, 0, 0)
        self.opacite = 1.0           # 0..1
        self.durete = 0.8            # 0 = bord très doux, 1 = bord net
        self._trait: Trait | None = None
        self.source_tampon: QPointF | None = None    # point (image) choisi par Alt+clic
        self._decalage_tampon: QPointF | None = None # source - point peint, fixé au premier coup (aligné)
        # recadrage
        self.recadre: QRectF | None = None           # cadre (image) à garder
        self.proportion: float | None = None         # largeur / hauteur imposée, ou libre
        self._recadre_glisse = None  # (mode « nouveau » / « deplacer » / côtés, point de départ, cadre d'origine)
        # transformer un calque (Ctrl+T)
        self.transfo: Transformation | None = None
        self._transfo_index = 0
        self._transfo_glisse = False
        # sélections calculées
        self.apercu_selection: QImage | None = None  # baguette pendant le glisser (petite image, étirée)
        self.points_ia: list = []                    # sélection rapide : (point image, garder ?)
        self.trait_en_attente = None                 # trait ou cadre envoyé à l'IA, montré pendant le calcul
        self._auto = None                            # geste en cours : (outil, départ écran, données)
        self._transfo_glisse = False
        # fenêtre Style du calque ouverte : seuls le zoom, la main et la poignée de l'ombre au sol répondent
        self.style_ouvert = False
        self.poignee_sol = None                      # ((x, y) du pied, (x, y) du bout), en pixels image
        self._sol_glisse = False
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
            p.drawText(self.rect(), Qt.AlignCenter, tr("Fichier > Ouvrir…  (ou glisse une photo ici)"))
            return
        # damier sous la photo : les zones transparentes des calques se voient
        photo = QRectF(self.decalage, self.decalage + QPointF(self.doc.image.width(),
                                                              self.doc.image.height()) * self.zoom)
        p.fillRect(photo, QBrush(self._damier()))
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
        if self.apercu_selection is not None:
            p.drawImage(QRectF(0, 0, self.doc.image.width(), self.doc.image.height()), self.apercu_selection)
        elif not (self._trace and self._nouvelle):   # nouvelle sélection en cours : l'ancienne va disparaître
            p.drawImage(QPointF(0, 0), self.doc.selection)
        p.setOpacity(1)
        self._dessiner_auto(p)
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
        if self.style_ouvert:
            self._dessiner_poignee_sol(p)
            return
        self._dessiner_cadre_texte(p)
        if self.transfo is not None:
            self._dessiner_transfo(p)
            return
        if self.outil == RECADRER and self.recadre is not None:
            self._dessiner_recadre(p)
        if self.outil == TAMPON and self.source_tampon is not None and not self._espace:
            if self._trait is not None and self._souris is not None:
                croix = self._souris + self._decalage_tampon * self.zoom
            elif self._trait is None and self._decalage_tampon is not None and self._souris is not None:
                croix = self._souris + self._decalage_tampon * self.zoom
            else:
                croix = self.vers_ecran(self.source_tampon)
            for couleur, epaisseur in ((QColor(0, 0, 0), 3), (QColor(255, 255, 255), 1)):
                p.setPen(QPen(couleur, epaisseur))
                p.drawLine(croix + QPointF(-8, 0), croix + QPointF(8, 0))
                p.drawLine(croix + QPointF(0, -8), croix + QPointF(0, 8))
        # curseur du pinceau
        if self._souris is not None and self.outil in OUTILS_ROND and not self._espace and self.cadre is None:
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

    # ---------------------------------------------------------- outil Texte
    def _texte_actif(self):
        """Réglages du calque choisi s'il est un texte visible, sinon None."""
        c = self.doc.calque_actif if self.doc else None
        return c.texte if c is not None and c.texte is not None and c.visible else None

    def _texte_sous(self, pt: QPointF):
        """Index du calque de texte visible le plus haut sous le point (image), ou None."""
        for i in range(len(self.doc.calques) - 1, -1, -1):
            c = self.doc.calques[i]
            if c.visible and c.texte is not None and contient(c.texte, pt):
                return i
        return None

    def _cadre_texte_ecran(self, t):
        """(polygone du bloc à l'écran, milieu du haut, poignée de rotation) pour le texte t."""
        ecran = QPolygonF([self.vers_ecran(pt) for pt in contour_bloc(t)])
        haut = (ecran[0] + ecran[1]) / 2
        v = QLineF(self.vers_ecran(QPointF(t.x, t.y)), haut)
        if v.length() < 1:
            return ecran, haut, haut + QPointF(0, -28)
        v.setLength(v.length() + 28)
        return ecran, haut, v.p2()

    def _dessiner_cadre_texte(self, p: QPainter):
        if self.outil != TEXTE or self.cadre is not None:
            return
        t = self._texte_actif()
        if t is None:
            return
        ecran, haut, poignee = self._cadre_texte_ecran(t)
        p.save()
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(0, 0, 0, 150), 1))
        p.drawPolygon(ecran)
        p.setPen(QPen(self.couleur_accent, 1.5, Qt.DashLine))
        p.drawPolygon(ecran)
        if not self.doc.calque_actif.verrou:
            p.setPen(QPen(self.couleur_accent, 1.5))
            p.drawLine(haut, poignee)
            p.setPen(QPen(QColor(255, 255, 255), 1.5))
            p.setBrush(self.couleur_accent)
            p.drawEllipse(poignee, 6, 6)
        p.restore()

    def _sur_poignee_texte(self, pos: QPointF) -> bool:
        t = self._texte_actif()
        if t is None or self.doc.calque_actif.verrou:
            return False
        return QLineF(pos, self._cadre_texte_ecran(t)[2]).length() <= 10

    def _presser_texte(self, pos: QPointF):
        pt = self.vers_image(pos)
        if self._sur_poignee_texte(pos):
            index, mode = self.doc.actif, "tourner"
        else:
            index, mode = self._texte_sous(pt), "deplacer"
            if index is None:
                self.texte_nouveau.emit(pt)
                return
            self.texte_choisi.emit(index)
        c = self.doc.calques[index]
        if c.verrou:
            self.refus.emit(tr("Le calque « {nom} » est verrouillé : clique sur son cadenas pour pouvoir le "
                               "modifier.", nom=c.nom))
            return
        self._texte_glisse = (index, mode, pt, c.texte, self.doc.etat())

    def _glisser_texte(self, pos: QPointF, magnetique: bool):
        index, mode, depart, t0, _ = self._texte_glisse
        pt = self.vers_image(pos)
        if mode == "deplacer":
            t = t0.deplace(pt.x() - depart.x(), pt.y() - depart.y())
        else:
            angle = math.degrees(math.atan2(pt.y() - t0.y, pt.x() - t0.x)) + 90
            if magnetique:                       # Maj : par pas de 15°
                angle = round(angle / 15) * 15
            angle = (angle + 180) % 360 - 180
            t = replace(t0, angle=round(angle, 1))
        w, h = self.doc.taille()
        self.doc.apercu_calque(index, rendre(t, w, h), texte=t)

    def _lacher_texte(self):
        index, mode, _, t0, avant = self._texte_glisse
        self._texte_glisse = None
        if self.doc.calques[index].texte != t0:
            self.selection_modifiee.emit(avant, tr("Déplacer le texte") if mode == "deplacer"
                                         else tr("Tourner le texte"))

    # ---------------------------------------------------------- outil Déplacer
    def _presser_deplacer(self, pos: QPointF):
        c = self.doc.calque_actif
        if c.verrou:
            self.refus.emit(tr("Le calque « {nom} » est verrouillé : clique sur son cadenas pour pouvoir le "
                               "modifier.", nom=c.nom))
            return
        if c.texte is not None:              # un texte se déplace comme avec l'outil Texte (il reste modifiable)
            self._texte_glisse = (self.doc.actif, "deplacer", self.vers_image(pos), c.texte, self.doc.etat())
            return
        self._calque_glisse = (self.doc.actif, self.vers_image(pos), c.image, self.doc.etat())
        self._decalage_calque = (0, 0)

    def _glisser_calque(self, pos: QPointF):
        index, depart, image, _ = self._calque_glisse
        pt = self.vers_image(pos)
        dx, dy = round(pt.x() - depart.x()), round(pt.y() - depart.y())
        w, h = self.doc.taille()
        nouvelle = QImage(w, h, image.format())
        nouvelle.fill(Qt.transparent)
        p = QPainter(nouvelle)
        p.drawImage(dx, dy, image)
        p.end()
        self.doc.apercu_calque(index, nouvelle)
        self._decalage_calque = (dx, dy)

    def _lacher_calque(self):
        avant = self._calque_glisse[3]
        self._calque_glisse = None
        if getattr(self, "_decalage_calque", (0, 0)) != (0, 0):
            self.selection_modifiee.emit(avant, tr("Déplacer le calque"))
        self._decalage_calque = (0, 0)

    # ---------------------------------------------------------- pinceau de couleur et tampon
    def _presser_retouche(self, pos: QPointF, alt: bool):
        pt = self.vers_image(pos)
        if alt and self.outil == PEINTURE:               # pipette : couleur de la photo visible
            x, y = int(pt.x()), int(pt.y())
            if 0 <= x < self.doc.image.width() and 0 <= y < self.doc.image.height():
                self.couleur_prise.emit(QColor(self.doc.image.pixel(x, y)).name())
            return
        if alt and self.outil == TAMPON:                 # point source
            self.source_tampon = pt
            self._decalage_tampon = None
            self.message.emit(tr("Endroit à copier choisi : peins maintenant là où il doit être recopié."))
            self.update()
            return
        c = self.doc.calque_actif
        if c.verrou:
            self.refus.emit(tr("Le calque « {nom} » est verrouillé : clique sur son cadenas pour pouvoir le "
                               "modifier.", nom=c.nom))
            return
        if self.outil == TAMPON and self.source_tampon is None:
            self.refus.emit(tr("Tampon : fais d'abord Alt+clic sur l'endroit à copier."))
            return
        if c.texte is not None:
            self.refus.emit(tr("Le texte « {nom} » devient une image : il n'est plus modifiable comme texte "
                               "(Ctrl+Z pour revenir).", nom=c.nom))
        self._avant = self.doc.etat()
        if self.outil == TAMPON:
            if self._decalage_tampon is None:
                self._decalage_tampon = self.source_tampon - pt
            self._trait = Trait("tampon", c.image, self.taille_pinceau, self.durete, self.opacite,
                                source=self.doc.image.copy(), decalage=self._decalage_tampon)
        else:
            self._trait = Trait("peinture", c.image, self.taille_pinceau, self.durete, self.opacite,
                                couleur=self.couleur_peinture)
        self._trait.ajouter(pt)
        self.doc.apercu_calque(self.doc.actif, self._trait.image)

    def _glisser_retouche(self, pos: QPointF):
        self._trait.ajouter(self.vers_image(pos))
        self.doc.apercu_calque(self.doc.actif, self._trait.image)

    def _lacher_retouche(self):
        nom = tr("Tampon") if self._trait.mode == "tampon" else tr("Pinceau de couleur")
        self._trait = None
        self.selection_modifiee.emit(self._avant, nom)
        self._avant = None

    # ---------------------------------------------------------- recadrer
    def definir_proportion(self, proportion: float | None):
        self.proportion = proportion
        if self.recadre is not None and proportion:
            c = self.recadre.center()
            w = self.recadre.width()
            h = w / proportion
            if h > self.recadre.height():
                h = self.recadre.height()
                w = h * proportion
            self.recadre = self._dans_image(QRectF(c.x() - w / 2, c.y() - h / 2, w, h))
            self._emettre_recadre()
        self.update()

    def annuler_recadre(self):
        self.recadre = None
        self._recadre_glisse = None
        self._emettre_recadre()
        self.update()

    def rect_recadre(self):
        """Cadre arrondi au pixel (QRect), ou None."""
        if self.recadre is None:
            return None
        r = self.recadre.toRect().intersected(self.doc.image.rect())
        return r if r.width() >= 1 and r.height() >= 1 else None

    def _emettre_recadre(self):
        self.recadre_change.emit(self.rect_recadre())

    def _dans_image(self, r: QRectF) -> QRectF:
        """Garde le cadre dans la photo (le déplace, puis le réduit si besoin, en gardant la proportion)."""
        iw, ih = self.doc.image.width(), self.doc.image.height()
        w, h = min(r.width(), iw), min(r.height(), ih)
        if self.proportion:
            if w / max(h, 1e-6) > self.proportion:
                w = h * self.proportion
            else:
                h = w / self.proportion
        x = max(0.0, min(r.center().x() - w / 2, iw - w))
        y = max(0.0, min(r.center().y() - h / 2, ih - h))
        return QRectF(x, y, w, h)

    def _depuis_coin(self, ancre: QPointF, pt: QPointF) -> QRectF:
        """Cadre entre un coin fixe et la souris, avec la proportion, sans sortir de la photo."""
        iw, ih = self.doc.image.width(), self.doc.image.height()
        sx = 1 if pt.x() >= ancre.x() else -1
        sy = 1 if pt.y() >= ancre.y() else -1
        maxw = iw - ancre.x() if sx > 0 else ancre.x()
        maxh = ih - ancre.y() if sy > 0 else ancre.y()
        w = min(abs(pt.x() - ancre.x()), maxw)
        h = min(abs(pt.y() - ancre.y()), maxh)
        if self.proportion:
            if w / max(h, 1e-6) > self.proportion:
                h = w / self.proportion
            else:
                w = h * self.proportion
            f = min(1.0, maxw / max(w, 1e-6), maxh / max(h, 1e-6))
            w, h = w * f, h * f
        return QRectF(ancre, ancre + QPointF(sx * w, sy * h)).normalized()

    def _rect_recadre_ecran(self) -> QRectF:
        return QRectF(self.vers_ecran(self.recadre.topLeft()), self.vers_ecran(self.recadre.bottomRight()))

    def _presser_recadre(self, pos: QPointF):
        pt = self.vers_image(pos)
        if self.recadre is not None:
            cotes = self._cotes_sous(self._rect_recadre_ecran(), pos)
            if cotes:
                self._recadre_glisse = (frozenset(cotes), pt, QRectF(self.recadre))
                return
            if self.recadre.contains(pt):
                self._recadre_glisse = ("deplacer", pt, QRectF(self.recadre))
                return
        iw, ih = self.doc.image.width(), self.doc.image.height()
        pt = QPointF(max(0.0, min(pt.x(), iw)), max(0.0, min(pt.y(), ih)))
        self._recadre_glisse = ("nouveau", pt, None)
        self.recadre = QRectF(pt, pt)

    def _glisser_recadre(self, pos: QPointF):
        mode, depart, r0 = self._recadre_glisse
        pt = self.vers_image(pos)
        if mode == "nouveau":
            self.recadre = self._depuis_coin(depart, pt)
        elif mode == "deplacer":
            r = r0.translated(pt - depart)
            self.recadre = self._dans_image(QRectF(r.topLeft(), r0.size()))
        else:
            cotes = set(mode)
            if len(cotes) == 2:                          # coin : le coin opposé reste fixe
                ancre = QPointF(r0.right() if "g" in cotes else r0.left(),
                                r0.bottom() if "h" in cotes else r0.top())
                self.recadre = self._depuis_coin(ancre, pt)
            else:
                iw, ih = self.doc.image.width(), self.doc.image.height()
                g, h_, d, b = r0.left(), r0.top(), r0.right(), r0.bottom()
                if "g" in cotes:
                    g = max(0.0, min(pt.x(), d - 1))
                elif "d" in cotes:
                    d = min(float(iw), max(pt.x(), g + 1))
                elif "h" in cotes:
                    h_ = max(0.0, min(pt.y(), b - 1))
                else:
                    b = min(float(ih), max(pt.y(), h_ + 1))
                r = QRectF(QPointF(g, h_), QPointF(d, b))
                if self.proportion:                      # l'autre dimension suit, centrée
                    c = r.center()
                    if cotes & {"g", "d"}:
                        hh = r.width() / self.proportion
                        r = QRectF(r.left(), c.y() - hh / 2, r.width(), hh)
                    else:
                        ww = r.height() * self.proportion
                        r = QRectF(c.x() - ww / 2, r.top(), ww, r.height())
                    r = self._dans_image(r)
                self.recadre = r
        self._emettre_recadre()
        self.update()

    def _lacher_recadre(self):
        self._recadre_glisse = None
        if self.recadre is not None and (self.recadre.width() < 4 or self.recadre.height() < 4):
            self.recadre = None
        self._emettre_recadre()
        self.update()

    def _dessiner_recadre(self, p: QPainter):
        r = self._rect_recadre_ecran()
        photo = QRectF(self.decalage, self.decalage + QPointF(self.doc.image.width(),
                                                              self.doc.image.height()) * self.zoom)
        dehors = QPainterPath()
        dehors.addRect(photo)
        dedans = QPainterPath()
        dedans.addRect(r)
        p.save()
        p.fillPath(dehors.subtracted(dedans), QColor(0, 0, 0, 140))       # partie coupée assombrie
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(255, 255, 255, 110), 1))                     # grille des tiers
        for i in (1, 2):
            x = r.left() + r.width() * i / 3
            y = r.top() + r.height() * i / 3
            p.drawLine(QPointF(x, r.top()), QPointF(x, r.bottom()))
            p.drawLine(QPointF(r.left(), y), QPointF(r.right(), y))
        p.setPen(QPen(QColor(0, 0, 0, 160), 1))
        p.drawRect(r)
        p.setPen(QPen(QColor(255, 255, 255), 1, Qt.DashLine))
        p.drawRect(r)
        c = r.center()
        p.setPen(QPen(QColor(0, 0, 0, 180), 1))
        p.setBrush(self.couleur_accent)
        for pt in (r.topLeft(), QPointF(c.x(), r.top()), r.topRight(), QPointF(r.right(), c.y()),
                   r.bottomRight(), QPointF(c.x(), r.bottom()), r.bottomLeft(), QPointF(r.left(), c.y())):
            p.drawRect(QRectF(pt.x() - 5, pt.y() - 5, 10, 10))
        rr = self.rect_recadre()
        if rr is not None:                               # taille du résultat
            texte = f"{rr.width()} × {rr.height()} px"
            boite = p.fontMetrics().boundingRect(texte).adjusted(-6, -3, 6, 3)
            boite.moveTopLeft(QPointF(r.left(), r.bottom() + 8).toPoint())
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 0, 0, 170))
            p.drawRoundedRect(QRectF(boite), 4, 4)
            p.setPen(QColor(255, 255, 255))
            p.drawText(boite, Qt.AlignCenter, texte)
        p.restore()

    # ---------------------------------------------------------- transformer un calque (Ctrl+T)
    def commencer_transfo(self, t: Transformation, index: int):
        self.transfo = t
        self._transfo_index = index
        self._apercu_transfo(lisse=True)
        self.setFocus()
        self.update()

    def finir_transfo(self):
        self.transfo = None
        self._transfo_glisse = False
        self._curseur()
        self.update()

    def _apercu_transfo(self, lisse: bool):
        w, h = self.doc.taille()
        self.doc.apercu_calque(self._transfo_index, self.transfo.rendu(w, h, lisse))

    def _sous_transfo(self, pos: QPointF):
        """Ce qui est sous la souris : nom de poignée, « deplacer » ou « tourner »."""
        for nom, (gx, gy) in POIGNEES.items():
            if QLineF(self.vers_ecran(self.transfo.point(gx, gy)), pos).length() <= 9:
                return nom
        return "deplacer" if self.transfo.dedans(self.vers_image(pos)) else "tourner"

    def _curseur_transfo(self, quoi):
        if quoi == "deplacer":
            self.setCursor(Qt.SizeAllCursor)
        elif quoi == "tourner":
            self.setCursor(Qt.CrossCursor)
        else:
            gx, gy = POIGNEES[quoi]
            a = (math.degrees(math.atan2(gy, gx)) + self.transfo.angle) % 180
            self.setCursor(Qt.SizeHorCursor if a < 22.5 or a >= 157.5 else
                           Qt.SizeFDiagCursor if a < 67.5 else
                           Qt.SizeVerCursor if a < 112.5 else Qt.SizeBDiagCursor)

    def _dessiner_transfo(self, p: QPainter):
        coins = [self.vers_ecran(c) for c in self.transfo.coins()]
        p.save()
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(0, 0, 0, 160), 1))
        p.drawPolygon(QPolygonF(coins))
        p.setPen(QPen(QColor(255, 255, 255), 1, Qt.DashLine))
        p.drawPolygon(QPolygonF(coins))
        p.setPen(QPen(QColor(0, 0, 0, 180), 1))
        p.setBrush(self.couleur_accent)
        for gx, gy in POIGNEES.values():
            pt = self.vers_ecran(self.transfo.point(gx, gy))
            p.drawRect(QRectF(pt.x() - 5, pt.y() - 5, 10, 10))
        c = self.vers_ecran(self.transfo.centre)
        p.setPen(QPen(QColor(255, 255, 255), 1))
        p.drawLine(QPointF(c.x() - 6, c.y()), QPointF(c.x() + 6, c.y()))
        p.drawLine(QPointF(c.x(), c.y() - 6), QPointF(c.x(), c.y() + 6))
        p.restore()

    def _damier(self) -> QPixmap:
        if getattr(self, "_motif_damier", None) is None:
            pm = QPixmap(16, 16)
            pm.fill(QColor(255, 255, 255))
            p = QPainter(pm)
            p.fillRect(0, 0, 8, 8, QColor(214, 214, 214))
            p.fillRect(8, 8, 8, 8, QColor(214, 214, 214))
            p.end()
            self._motif_damier = pm
        return self._motif_damier

    # ---------------------------------------------------------- gomme de calque
    def _coup_de_gomme_calque(self, a: QPointF, b: QPointF):
        p = QPainter(self._img_calque)
        p.setRenderHint(QPainter.Antialiasing)
        p.setCompositionMode(QPainter.CompositionMode_DestinationOut)
        if a == b:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 0, 0))
            r = self.taille_pinceau / 2
            p.drawEllipse(a, r, r)
        else:
            p.setPen(QPen(QColor(0, 0, 0), self.taille_pinceau, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawLine(a, b)
        p.end()
        self.doc.apercu_calque(self.doc.actif, QImage(self._img_calque))

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

    def _dessiner_auto(self, p: QPainter):
        """Trait de la sélection rapide, cadre de la sélection d'objet (en cours ou en calcul), points de l'IA.
        Appelé avec la transformation de l'image (coordonnées image)."""
        trait = None
        if self._auto is not None and self._auto[0] in (RAPIDE, OBJET, SUPPRIMER):
            trait = (self._auto[0], self._auto[2])
        elif self.trait_en_attente is not None:
            trait = self.trait_en_attente
        if trait is not None:
            genre, d = trait
            if genre in (RAPIDE, SUPPRIMER) and len(d["points"]) > 0:
                c = QColor(self.couleur_accent)
                c.setAlpha(110)
                if genre == SUPPRIMER:
                    c = QColor(255, 60, 150, 120)
                if d.get("alt"):
                    c = QColor(255, 255, 255, 130)
                p.setPen(QPen(c, d.get("taille", self.taille_pinceau), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                if len(d["points"]) == 1:
                    p.drawPoint(d["points"][0])
                else:
                    p.drawPolyline(QPolygonF(d["points"]))
            elif genre == OBJET and d.get("fin") is not None:
                r = QRectF(d["debut"], d["fin"]).normalized()
                for couleur, style in ((QColor(0, 0, 0), Qt.SolidLine), (QColor(255, 255, 255), Qt.DashLine)):
                    stylo = QPen(couleur, 0, style)
                    stylo.setCosmetic(True)
                    stylo.setWidth(2 if style == Qt.SolidLine else 1)
                    p.setPen(stylo)
                    p.drawRect(r)
        if self.points_ia:
            rayon = 5 / self.zoom
            for pt, garder in self.points_ia:
                p.setPen(QPen(QColor(255, 255, 255), 1.5 / self.zoom))
                p.setBrush(QColor(40, 180, 90) if garder else QColor(220, 50, 50))
                p.drawEllipse(pt, rayon, rayon)
            p.setBrush(Qt.NoBrush)

    def _presser_auto(self, e, pos: QPointF):
        mods = e.modifiers()
        pt = self.vers_image(pos)
        alt, maj = bool(mods & Qt.AltModifier), bool(mods & Qt.ShiftModifier)
        mode = "retirer" if alt else "ajouter" if maj else self.mode_forme
        if self.outil == BAGUETTE:
            self._auto = (BAGUETTE, pos, {})
            self.baguette_clic.emit(pt, mode)
        elif self.outil == RAPIDE:
            self._auto = (RAPIDE, pos, {"points": [pt], "alt": alt, "maj": maj})
        elif self.outil == SUPPRIMER:
            self._auto = (SUPPRIMER, pos, {"points": [pt], "taille": float(self.taille_pinceau)})
        else:
            self._auto = (OBJET, pos, {"debut": pt, "fin": None, "mode": mode})
        self.update()

    def _glisser_auto(self, pos: QPointF):
        outil, depart, d = self._auto
        if outil == BAGUETTE:
            self.baguette_glisse.emit(pos.x() - depart.x())
        elif outil in (RAPIDE, SUPPRIMER):
            d["points"].append(self.vers_image(pos))
        elif (pos - depart).manhattanLength() > 4:
            d["fin"] = self.vers_image(pos)
        self.update()

    def _lacher_auto(self):
        outil, depart, d = self._auto
        self._auto = None
        if outil == BAGUETTE:
            self.baguette_lache.emit()
        elif outil == SUPPRIMER:
            self.trait_en_attente = (SUPPRIMER, d)
            self.suppression.emit([(pt.x(), pt.y()) for pt in d["points"]], d["taille"])
        elif outil == RAPIDE:
            self.trait_en_attente = (RAPIDE, d)
            self.trait_ia.emit([(pt.x(), pt.y()) for pt in d["points"]], d["alt"], d["maj"])
        else:
            self.trait_en_attente = (OBJET, d)
            quoi = QRectF(d["debut"], d["fin"]).normalized() if d["fin"] is not None else d["debut"]
            self.objet_ia.emit(quoi, d["mode"])
        self.update()

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

    def definir_poignee_sol(self, points):
        self.poignee_sol = points
        self.update()

    def _bout_sol_ecran(self):
        if self.poignee_sol is None:
            return None
        return self.vers_ecran(QPointF(*self.poignee_sol[1]))

    def _dessiner_poignee_sol(self, p: QPainter):
        if self.poignee_sol is None:
            return
        a, b = self.vers_ecran(QPointF(*self.poignee_sol[0])), self._bout_sol_ecran()
        for couleur, epaisseur in ((QColor(0, 0, 0, 160), 3), (QColor(255, 255, 255), 1)):
            p.setPen(QPen(couleur, epaisseur, Qt.DashLine))
            p.drawLine(a, b)
        p.setPen(QPen(QColor(255, 255, 255), 2))
        p.setBrush(self.couleur_accent)
        p.drawEllipse(b, 7, 7)
        p.setBrush(Qt.NoBrush)

    def mousePressEvent(self, e):
        if not self.doc:
            return
        pos = e.position()
        if self.style_ouvert:
            b = self._bout_sol_ecran()
            if e.button() == Qt.LeftButton and b is not None and (pos - b).manhattanLength() < 16:
                self._sol_glisse = True
                return
            if e.button() == Qt.MiddleButton or e.button() == Qt.LeftButton:
                self._glisse = pos                     # pendant le style : glisser = se déplacer dans la photo
                self.setCursor(Qt.ClosedHandCursor)
            return
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
        if self.transfo is not None:
            self.transfo.commencer(self._sous_transfo(pos), self.vers_image(pos))
            self._transfo_glisse = True
            return
        if self.outil == TEXTE:
            self._presser_texte(pos)
            self.update()
            return
        if self.outil == DEPLACER:
            self._presser_deplacer(pos)
            return
        if self.outil == RECADRER:
            self._presser_recadre(pos)
            self.update()
            return
        if self.outil in (PEINTURE, TAMPON):
            self._presser_retouche(pos, bool(e.modifiers() & Qt.AltModifier))
            self.update()
            return
        if self.outil in OUTILS_AUTO or self.outil == SUPPRIMER:
            self._presser_auto(e, pos)
            return
        if self.outil == GOMME_CALQUE and self.doc.calque_actif.verrou:
            self.refus.emit(tr("Le calque « {nom} » est verrouillé : clique sur son cadenas pour pouvoir le "
                               "gommer.", nom=self.doc.calque_actif.nom))
            return
        mods = e.modifiers()
        self._nouvelle = False
        if self.outil in (RECTANGLE, LASSO):           # comme Photoshop : Maj ajoute, Alt retire
            mode = ("retirer" if mods & Qt.AltModifier else "ajouter" if mods & Qt.ShiftModifier
                    else self.mode_forme)
            self._soustraire = mode == "retirer"
            self._nouvelle = mode == "nouvelle"
        else:
            self._soustraire = self.mode_retirer != bool(mods & Qt.AltModifier)
        self._avant = self.doc.etat()
        pt = self.vers_image(pos)
        self._trace = [pt]
        if self.outil == GOMME_CALQUE:
            if self.doc.calque_actif.texte is not None:
                self.refus.emit(tr("Le texte « {nom} » devient une image : il n'est plus modifiable comme texte "
                                   "(Ctrl+Z pour revenir).", nom=self.doc.calque_actif.nom))
            self._img_calque = self.doc.calque_actif.image.copy()   # copie : l'état d'avant reste intact
            self._coup_de_gomme_calque(pt, pt)
        elif self.outil in (PINCEAU, GOMME):
            self._coup_de_pinceau(pt, pt)
        self.update()

    def mouseMoveEvent(self, e):
        pos = e.position()
        self._souris = pos
        if self.style_ouvert and self._sol_glisse:
            self.poignee_sol_bouge.emit(self.vers_image(pos))
            return
        if self.style_ouvert and self._glisse is None:
            b = self._bout_sol_ecran()
            self.setCursor(Qt.SizeAllCursor if b is not None and (pos - b).manhattanLength() < 16
                           else Qt.OpenHandCursor)
            return
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
        if self.transfo is not None:
            if self._transfo_glisse:
                self.transfo.glisser(self.vers_image(pos), bool(e.modifiers() & Qt.ShiftModifier))
                self._apercu_transfo(lisse=False)        # rapide pendant le geste, lissé au lâcher
                self.transfo_change.emit()
            else:
                self._curseur_transfo(self._sous_transfo(pos))
            self.update()
            return
        if self._texte_glisse is not None:
            self._glisser_texte(pos, bool(e.modifiers() & Qt.ShiftModifier))
            return
        if self._calque_glisse is not None:
            self._glisser_calque(pos)
            return
        if self._recadre_glisse is not None:
            self._glisser_recadre(pos)
            return
        if self._trait is not None:
            self._glisser_retouche(pos)
            self.update()
            return
        if self._auto is not None:
            self._glisser_auto(pos)
            return
        if self.outil == RECADRER and self.doc and not self._espace:
            if self.recadre is not None:
                cotes = self._cotes_sous(self._rect_recadre_ecran(), pos)
                if cotes:
                    self._curseur_cadre((None, cotes))
                elif self.recadre.contains(self.vers_image(pos)):
                    self.setCursor(Qt.SizeAllCursor)
                else:
                    self.setCursor(Qt.CrossCursor)
            else:
                self.setCursor(Qt.CrossCursor)
        if self.outil == TEXTE and self.doc and not self._espace:
            if self._sur_poignee_texte(pos):
                self.setCursor(Qt.PointingHandCursor)
            elif self._texte_sous(self.vers_image(pos)) is not None:
                self.setCursor(Qt.SizeAllCursor)
            else:
                self.setCursor(Qt.IBeamCursor)
        if self._trace is not None:
            pt = self.vers_image(pos)
            if self.outil == GOMME_CALQUE:
                self._coup_de_gomme_calque(self._trace[-1], pt)
                self._trace.append(pt)
            elif self.outil in (PINCEAU, GOMME):
                self._coup_de_pinceau(self._trace[-1], pt)
                self._trace.append(pt)
            elif self.outil == RECTANGLE:
                self._trace = [self._trace[0], pt]
            else:
                self._trace.append(pt)
        self.update()

    def mouseReleaseEvent(self, e):
        if self.style_ouvert and self._sol_glisse:
            self._sol_glisse = False
            return
        if self._glisse is not None:
            self._glisse = None
            self._curseur()
            return
        if self.cadre is not None:
            self._poignee = None
            return
        if self.transfo is not None:
            if self._transfo_glisse:
                self._transfo_glisse = False
                self.transfo.finir()
                self._apercu_transfo(lisse=True)
                self.transfo_change.emit()
            return
        if self._texte_glisse is not None:
            self._lacher_texte()
            return
        if self._calque_glisse is not None:
            self._lacher_calque()
            return
        if self._recadre_glisse is not None:
            self._lacher_recadre()
            return
        if self._trait is not None:
            self._lacher_retouche()
            self.update()
            return
        if self._auto is not None:
            self._lacher_auto()
            return
        if self._trace is None:
            return
        if self.outil in (RECTANGLE, LASSO):
            if self._nouvelle:                         # un simple clic, sans tracé, désélectionne
                self.doc.selection.fill(0)
            if len(self._trace) > 1:
                self._remplir_forme()
        self._nouvelle = False
        noms = {PINCEAU: "Pinceau de sélection", GOMME: "Gomme de sélection", RECTANGLE: "Sélection rectangle",
                LASSO: "Lasso", GOMME_CALQUE: "Gomme de calque"}
        self._img_calque = None
        self._trace = None
        self.selection_modifiee.emit(self._avant, tr(noms[self.outil]))
        self._avant = None
        self.update()

    def mouseDoubleClickEvent(self, e):
        if self.style_ouvert:
            return
        if self.transfo is not None and e.button() == Qt.LeftButton:
            if self.transfo.dedans(self.vers_image(e.position())):
                self.transfo_valide.emit()
            return
        if (self.outil == RECADRER and self.recadre is not None and e.button() == Qt.LeftButton
                and self.recadre.contains(self.vers_image(e.position()))):
            self.recadre_valide.emit()
            return
        super().mouseDoubleClickEvent(e)

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
        if self.transfo is not None and e.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.transfo_valide.emit()
        elif self.transfo is not None and e.key() == Qt.Key_Escape:
            self.transfo_annule.emit()
        elif self.cadre is not None and e.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.cadre_valide.emit()
        elif self.cadre is not None and e.key() == Qt.Key_Escape:
            self.cadre_annule.emit()
        elif self.outil == RECADRER and self.recadre is not None and e.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.recadre_valide.emit()
        elif self.outil == RECADRER and self.recadre is not None and e.key() == Qt.Key_Escape:
            self.annuler_recadre()
        elif self.outil == RAPIDE and e.key() == Qt.Key_Escape:
            self.fin_session_ia.emit()
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
        if outil != RECADRER and self.recadre is not None:
            self.annuler_recadre()
        self.outil = outil
        self._curseur()
        self.update()

    def _curseur(self):
        if self.style_ouvert:
            self.setCursor(Qt.OpenHandCursor)
            return
        if self.cadre is not None:
            self.setCursor(Qt.ArrowCursor)
            return
        self.setCursor(Qt.OpenHandCursor if self.outil == MAIN else
                       Qt.BlankCursor if self.outil in OUTILS_ROND else
                       Qt.IBeamCursor if self.outil == TEXTE else
                       Qt.SizeAllCursor if self.outil == DEPLACER else Qt.CrossCursor)
