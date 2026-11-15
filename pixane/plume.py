"""Outil Plume (comme Photoshop) : tracés en lignes et en courbes, point par point.

- clic : un point d'angle ; cliquer-glisser : un point en courbe (les poignées suivent la souris) ;
- clic sur le premier point : le tracé se ferme ; Entrée ou double-clic : il reste ouvert ; Retour arrière : retire
  le dernier point ; Échap : abandonne ;
- le tracé fini devient un calque de forme (remplissage, contour) ou une sélection, selon la barre du haut ;
- sur un calque de forme choisi, sans tracé en cours : on attrape ses points ou leurs poignées pour les déplacer
  (Alt sur une poignée : elle bouge seule, le point devient un angle).

Mélangé à Canevas (classe de base) : utilise vers_image, vers_ecran, doc, zoom, couleurs et signaux du canevas.
"""
from __future__ import annotations

import math

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen

from . import calque_forme
from .langue import tr

PRISE = 7            # px d'écran : distance pour attraper un point ou une poignée


class PlumeMixin:
    def _init_plume(self):
        self.plume_points: list | None = None       # tracé en cours : [[x, y, ax, ay, bx, by], …]
        self.plume_mode = "forme"                   # « forme » (calque de forme) ou « selection »
        self._plume_prise = None                    # ce qui est tiré à la souris
        self._plume_souris: QPointF | None = None   # pour la ligne d'aperçu vers le prochain point

    # ---------------------------------------------------------- tracé en cours
    def _plume_pres(self, ecran: QPointF, x: float, y: float) -> bool:
        q = self.vers_ecran(QPointF(x, y))
        return math.hypot(q.x() - ecran.x(), q.y() - ecran.y()) <= PRISE

    def _forme_editable(self):
        c = self.doc.calque_actif if self.doc is not None else None
        if c is None or c.verrou:
            return None
        return calque_forme.valide(c)

    def _sous_forme(self, ecran: QPointF):
        """(i, j, quoi) du point ou de la poignée de la forme choisie sous la souris, ou None."""
        f = self._forme_editable()
        if f is None:
            return None
        for i, (_ferme, pts) in enumerate(f.traces):
            for j, (x, y, ax, ay, bx, by) in enumerate(pts):
                if (bx, by) != (x, y) and self._plume_pres(ecran, bx, by):
                    return i, j, "b"
                if (ax, ay) != (x, y) and self._plume_pres(ecran, ax, ay):
                    return i, j, "a"
                if self._plume_pres(ecran, x, y):
                    return i, j, "p"
        return None

    def _presser_plume(self, pos: QPointF, mods):
        pt = self.vers_image(pos)
        if self.plume_points is None:
            prise = self._sous_forme(pos)
            if prise is not None:                       # point d'une forme existante : on le déplace
                self._plume_prise = ("forme", prise, self.doc.etat(), self._forme_editable(), self.doc.actif,
                                     bool(mods & Qt.AltModifier))
                return
            self.plume_points = []
        pts = self.plume_points
        if len(pts) >= 2 and self._plume_pres(pos, pts[0][0], pts[0][1]):
            self._plume_prise = ("fermer",)             # clic sur le premier point : fermé en lâchant
            return
        if mods & Qt.ShiftModifier and pts:             # Maj : à 45° près du point précédent
            d = pt - QPointF(pts[-1][0], pts[-1][1])
            ang = round(math.atan2(d.y(), d.x()) / (math.pi / 4)) * (math.pi / 4)
            r = math.hypot(d.x(), d.y())
            pt = QPointF(pts[-1][0] + math.cos(ang) * r, pts[-1][1] + math.sin(ang) * r)
        pts.append([pt.x(), pt.y(), pt.x(), pt.y(), pt.x(), pt.y()])
        self._plume_prise = ("nouveau", len(pts) - 1)
        self.update()

    def _glisser_plume(self, pos: QPointF, mods) -> bool:
        """True si la Plume a utilisé le mouvement."""
        self._plume_souris = self.vers_image(pos)
        prise = self._plume_prise
        if prise is None:
            if self.plume_points is not None:
                self.update()
            self.setCursor(Qt.PointingHandCursor if self.plume_points is None and self._sous_forme(pos) is not None
                           else Qt.CrossCursor)
            return self.plume_points is not None
        pt = self.vers_image(pos)
        if prise[0] == "nouveau":                       # glisser : point en courbe, poignées symétriques
            p = self.plume_points[prise[1]]
            if math.hypot(pt.x() - p[0], pt.y() - p[1]) * self.zoom > 2:
                p[4], p[5] = pt.x(), pt.y()
                p[2], p[3] = 2 * p[0] - pt.x(), 2 * p[1] - pt.y()
        elif prise[0] == "forme":
            _k, (i, j, quoi), _avant, f, index, alt = prise
            n = calque_forme.deplacer_point(f, i, j, quoi, pt.x(), pt.y(), symetrique=not alt)
            self.doc.appliquer_etat(self.doc.etat_forme(index, n))
            self._plume_bouge = True
        self.update()
        return True

    def _lacher_plume(self):
        prise, self._plume_prise = self._plume_prise, None
        if prise is None:
            return
        if prise[0] == "fermer":
            self.finir_plume(fermer=True)
        elif prise[0] == "forme":
            if getattr(self, "_plume_bouge", False):
                self.selection_modifiee.emit(prise[2], tr("Modifier le tracé"))
            self._plume_bouge = False
        self.update()

    def touche_plume(self, e) -> bool:
        """Entrée, Échap, Retour arrière pendant un tracé. True si la touche a servi."""
        if self.plume_points is None:
            return False
        if e.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.finir_plume(fermer=False)
        elif e.key() == Qt.Key_Escape:
            self.abandonner_plume()
        elif e.key() in (Qt.Key_Backspace, Qt.Key_Delete):
            self.plume_points.pop()
            if not self.plume_points:
                self.plume_points = None
            self.update()
        else:
            return False
        return True

    def abandonner_plume(self):
        self.plume_points = None
        self._plume_prise = None
        self.update()

    def finir_plume(self, fermer: bool):
        """Le tracé en cours devient un calque de forme ou une sélection."""
        pts, self.plume_points = self.plume_points, None
        self.update()
        if not pts or len(pts) < 2:
            return
        traces = ((fermer, tuple(tuple(p) for p in pts)),)
        f = calque_forme.Forme(traces)
        if self.plume_mode == "selection":
            if not fermer and len(pts) < 3:
                self.refus.emit(tr("Pour une sélection, le tracé doit entourer une zone (au moins 3 points)."))
                return
            avant = self.doc.etat()
            ch = f.chemin()
            ch.closeSubpath()
            p = QPainter(self.doc.selection)
            p.setRenderHint(QPainter.Antialiasing)
            mods = self._mods_plume()
            if not mods & (Qt.ShiftModifier | Qt.AltModifier):
                self.doc.selection.fill(0)
            if mods & Qt.AltModifier:
                p.setCompositionMode(QPainter.CompositionMode_DestinationOut)
            from .document import COULEUR_SELECTION
            p.fillPath(ch, COULEUR_SELECTION)
            p.end()
            self.selection_modifiee.emit(avant, tr("Tracé vers sélection"))
            return
        remplir = self.forme_remplie and fermer
        contour = self.forme_contour or not remplir
        f = f.avec(remplissage=self.forme_couleur.name(QColor.HexArgb) if remplir else "",
                   contour=self.forme_couleur_contour.name(QColor.HexArgb) if contour else "",
                   epaisseur=max(1.0, float(self.forme_epaisseur)), genre="plume")
        avant = self.doc.etat()
        self.doc.appliquer_etat(self.doc.etat_nouvelle_forme(f, tr("Tracé")))
        self.selection_modifiee.emit(avant, tr("Plume"))

    @staticmethod
    def _mods_plume():
        from PySide6.QtWidgets import QApplication
        return QApplication.keyboardModifiers()

    # ---------------------------------------------------------- dessin à l'écran
    def _dessiner_plume(self, p: QPainter):
        p.setRenderHint(QPainter.Antialiasing)
        if self.plume_points:
            f = calque_forme.Forme(((False, tuple(tuple(q) for q in self.plume_points)),))
            ch = self._vers_ecran_chemin(f.chemin())
            if self._plume_souris is not None and self._plume_prise is None:
                ch.lineTo(self.vers_ecran(self._plume_souris))
            for couleur, ep in ((QColor(0, 0, 0, 170), 3), (QColor(255, 255, 255), 1)):
                p.setPen(QPen(couleur, ep))
                p.setBrush(Qt.NoBrush)
                p.drawPath(ch)
            self._dessiner_points(p, [self.plume_points], premier=True)
            return
        f = self._forme_editable()
        if f is not None and self.outil == "plume":
            ch = self._vers_ecran_chemin(f.chemin())
            p.setPen(QPen(self.couleur_accent, 1))
            p.setBrush(Qt.NoBrush)
            p.drawPath(ch)
            self._dessiner_points(p, [list(pts) for _ferme, pts in f.traces])

    def _vers_ecran_chemin(self, ch: QPainterPath) -> QPainterPath:
        from PySide6.QtGui import QTransform
        t = QTransform(self.zoom, 0, 0, self.zoom, self.decalage.x(), self.decalage.y())
        return t.map(ch)

    def _dessiner_points(self, p: QPainter, traces, premier: bool = False):
        for pts in traces:
            for k, (x, y, ax, ay, bx, by) in enumerate(pts):
                c = self.vers_ecran(QPointF(x, y))
                for hx, hy in ((ax, ay), (bx, by)):
                    if (hx, hy) != (x, y):
                        h = self.vers_ecran(QPointF(hx, hy))
                        p.setPen(QPen(self.couleur_accent, 1))
                        p.drawLine(c, h)
                        p.setBrush(QColor(255, 255, 255))
                        p.drawEllipse(h, 3.5, 3.5)
                p.setPen(QPen(QColor(0, 0, 0), 1))
                p.setBrush(self.couleur_accent if premier and k == 0 else QColor(255, 255, 255))
                p.drawRect(int(c.x() - 4), int(c.y() - 4), 8, 8)
        p.setBrush(Qt.NoBrush)
