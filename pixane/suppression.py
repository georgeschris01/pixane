"""Pinceau Supprimer (J), comme l'outil Suppression de Photoshop : on peint sur un défaut (fil, tache, bouton,
passant au loin…) et, au lâcher, il disparaît. Seul LaMa travaille, sur un morceau de la photo autour du trait :
environ une seconde, sans fenêtre de choix. Le résultat va dans un calque « Suppressions » (créé au-dessus du
calque choisi, puis réutilisé tant qu'il est choisi) : la photo d'origine n'est jamais touchée.
"""
from __future__ import annotations

import io
import math
import threading
from dataclasses import replace

import numpy as np
from PIL import Image
from PySide6.QtCore import QPointF, QRect, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QApplication, QMessageBox

from . import recettes
from .document import FORMAT_IMAGE, Calque, a_plat, image_vide, qimage_rgba, tableau
from .langue import tr
from .moteur import ErreurMoteur
from .styles import dilater

COTE_MAX = 1536          # au-delà, le morceau est réduit pour LaMa puis remis à sa taille


def nom_calque() -> str:
    return tr("Suppressions")


def masque_du_trait(points, taille: float, w: int, h: int) -> np.ndarray:
    """Masque 0..1 (h, w) du trait, au rond du pinceau."""
    m = QImage(w, h, QImage.Format_Grayscale8)
    m.fill(0)
    p = QPainter(m)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QPen(QColor(255, 255, 255), max(1.0, taille), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    pts = [QPointF(x, y) for x, y in points]
    if len(pts) == 1:
        p.drawPoint(pts[0])
    else:
        p.drawPolyline(QPolygonF(pts))
    p.end()
    ligne = m.bytesPerLine()
    a = np.frombuffer(m.constBits(), np.uint8, count=h * ligne).reshape(h, ligne)[:, :w]
    return a.astype(np.float32) / 255


def zone_de_travail(m: np.ndarray, taille: float) -> QRect | None:
    """Rectangle autour du trait, avec assez de photo autour pour que LaMa comprenne le décor."""
    ys, xs = np.nonzero(m > 0)
    if not len(ys):
        return None
    h, w = m.shape
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    marge = int(max(64, taille * 2, 0.6 * max(x1 - x0, y1 - y0)))
    X0, Y0, X1, Y1 = max(0, x0 - marge), max(0, y0 - marge), min(w, x1 + marge), min(h, y1 + marge)
    return QRect(int(X0), int(Y0), int(X1 - X0), int(Y1 - Y0))


class Suppression:
    def __init__(self, fenetre):
        self.f = fenetre
        self.c = fenetre.canevas
        self._occupe = False
        self._file: list = []                  # traits arrivés pendant un calcul, faits dans l'ordre
        self.c.suppression.connect(self.trait)

    def trait(self, points: list, taille: float):
        if not points or self.f.doc is None:
            self._fin_trait()
            return
        if not (self.f.moteur.etat == "prêt"):
            self._fin_trait()
            QMessageBox.information(self.f, tr("Supprimer"), tr(
                "Le pinceau Supprimer utilise le moteur IA, qui n'est pas encore prêt. Attends que la pastille "
                "en bas à gauche indique « Moteur IA prêt »."))
            return
        self._file.append((self.f.doc, list(points), float(taille)))
        if not self._occupe:
            self._suivant()

    def _fin_trait(self):
        if not self._file and not self._occupe:
            self.c.trait_en_attente = None
        self.c.update()

    def _suivant(self):
        if not self._file:
            self._occupe = False
            self._fin_trait()
            return
        doc, points, taille = self._file.pop(0)
        if doc is not self.f.doc:
            self._suivant()
            return
        self._occupe = True
        w, h = doc.taille()
        m = masque_du_trait(points, taille, w, h)
        zone = zone_de_travail(m, taille)
        if zone is None:
            self._suivant()
            return
        # bord du trait un peu élargi : le contour flou d'un défaut part aussi
        x, y, zw, zh = zone.x(), zone.y(), zone.width(), zone.height()
        mz = np.clip(dilater(m[y:y + zh, x:x + zw], max(1.5, taille * 0.06)), 0, 1)
        photo = tableau(doc.image.copy(zone).convertToFormat(FORMAT_IMAGE))
        self.f.statusBar().showMessage(tr("Suppression en cours…"))
        QApplication.setOverrideCursor(Qt.BusyCursor)

        def calcul(_progres):
            k = min(1.0, COTE_MAX / max(zw, zh))
            rgb = Image.fromarray(a_plat(photo), "RGB")
            alpha = Image.fromarray(((1 - (mz > 0.02)) * 255).astype(np.uint8), "L")
            if k < 1:
                taille_r = (max(1, round(zw * k)), max(1, round(zh * k)))
                rgb, alpha = rgb.resize(taille_r, Image.LANCZOS), alpha.resize(taille_r, Image.NEAREST)
            im = rgb.copy()
            im.putalpha(alpha)
            buf = io.BytesIO()
            im.save(buf, "PNG", compress_level=1)
            nom = self.f.moteur.envoyer_image(buf.getvalue())
            prompt, sorties = recettes.supprimer(nom)
            res = self.f.moteur.executer(prompt, sorties, threading.Event(), lambda *a: None)
            if not res:
                raise ErreurMoteur(tr("Le calcul s'est arrêté sans résultat."))
            out = Image.open(io.BytesIO(res[0][1])).convert("RGB")
            if out.size != (zw, zh):
                out = out.resize((zw, zh), Image.LANCZOS)
            return np.asarray(out)

        def ok(rgb):
            QApplication.restoreOverrideCursor()
            if doc is self.f.doc:
                self._poser(doc, zone, rgb, mz * (photo[:, :, 3] / 255))   # transparent : reste transparent
                self.f.statusBar().showMessage(tr("Supprimé. Ctrl+Z pour revenir."), 4000)
            self._suivant()

        def echec(message):
            QApplication.restoreOverrideCursor()
            self._file.clear()
            self._occupe = False
            self._fin_trait()
            if message:
                QMessageBox.warning(self.f, tr("Supprimer"), message)

        self.f._tache(calcul, ok, echec).lancer()

    def _poser(self, doc, zone: QRect, rgb: np.ndarray, mz: np.ndarray):
        """Le morceau refait, posé dans le calque « Suppressions » (bord fondu sur 1 à 2 px)."""
        from .fenetre import CommandeEtat
        avant = doc.etat()
        w, h = doc.taille()
        c = doc.calque_actif
        reutiliser = (c.nom.startswith(nom_calque()) and c.texte is None and not c.verrou and c.style is None
                      and not c.special and c.masque is None)
        a = np.clip(mz, 0, 1)
        morceau = np.dstack([rgb, (a * 255 + 0.5).astype(np.uint8)])
        img = c.image.copy() if reutiliser else image_vide(w, h)
        p = QPainter(img)
        p.drawImage(zone.topLeft(), qimage_rgba(morceau))
        p.end()
        if reutiliser:
            calques = list(doc.calques)
            calques[doc.actif] = replace(c, image=img)
            apres = doc.etat_avec(calques, doc.actif)
        else:
            apres = doc.inserer(Calque.depuis(doc.nom_libre(nom_calque()), img))
        self.f.historique.push(CommandeEtat(doc, avant, apres, tr("Supprimer")))
