"""Agrandir : cadre extérieur (agrandir) et cadre intérieur (bord abîmé) tirés à la souris, capture d'écran.
Usage : essai_cadre.py image capture.png [outil]   (le moteur n'est pas démarré : _lancer est intercepté)"""
import io
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image
from PySide6.QtCore import QEvent, QPointF, Qt, QTimer
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication
from chrypix.fenetre import Fenetre
from chrypix.moteur import Moteur

Moteur.demarrer = lambda self, signaler=None: (_ for _ in ()).throw(Exception("moteur désactivé pour l'essai"))
Fenetre._moteur_en_echec = lambda self, *a: None   # pas de message bloquant pendant l'essai
lances = []
Fenetre._lancer = lambda self, titre, sel, fab, apres=None, png=None: lances.append((titre, png))
app = QApplication(sys.argv)
f = Fenetre()
f.resize(1440, 920)
f.show()
f.charger(sys.argv[1])
app.processEvents()
c = f.canevas
c.definir_outil(sys.argv[3] if len(sys.argv) > 3 else "pinceau")
f.ia_agrandir()
app.processEvents()
print("bord abîmé détecté au départ :", c.abime)


def souris(type_, pos, mods=Qt.NoModifier):
    boutons = Qt.NoButton if type_ == QEvent.MouseButtonRelease else Qt.LeftButton
    c.event(QMouseEvent(type_, pos, pos, Qt.LeftButton, boutons, mods))


def tirer(depart, arrivee, mods=Qt.NoModifier):
    souris(QEvent.MouseButtonPress, depart, mods)
    milieu = (depart + arrivee) / 2
    souris(QEvent.MouseMove, depart + (milieu - depart) * 0.1, mods)
    souris(QEvent.MouseMove, milieu, mods)
    souris(QEvent.MouseMove, arrivee, mods)
    souris(QEvent.MouseButtonRelease, arrivee, mods)


# droite : vers l'extérieur = agrandir
r = c._rect_cadre()
tirer(QPointF(r.right(), r.center().y()), QPointF(r.right() + 150, r.center().y()))
# haut avec Maj : agrandir en haut et en bas
r = c._rect_cadre()
tirer(QPointF(r.center().x(), r.top()), QPointF(r.center().x(), r.top() - 80), Qt.ShiftModifier)
# gauche : vers l'intérieur = bord abîmé (les deux cadres se touchent : choix au premier mouvement)
s = c._rect_sain()
tirer(QPointF(s.left(), s.center().y()), QPointF(s.left() + 30, s.center().y()))
# droite : le cadre intérieur, sous le cadre extérieur déjà tiré, rentre de 20 px écran
s = c._rect_sain()
tirer(QPointF(s.right(), s.center().y()), QPointF(s.right() - 20, s.center().y()))
print("ajout :", c.cadre, "| bord abîmé :", c.abime)
print("barre :", {k: v.value() for k, v in f.barre_agrandir.ajout.items()},
      {k: v.value() for k, v in f.barre_agrandir.abime.items()}, "|", f.barre_agrandir.texte_taille.text())
f.barre_agrandir.abime["haut"].setValue(12)
print("après case « bord abîmé haut » 12 px :", c.abime)
c.repaint()
f.grab().save(sys.argv[2])
ajout, abime = f.barre_agrandir.valeurs_px()
iw, ih = f.doc.image.width(), f.doc.image.height()
f._lancer_agrandir()
titre, png = lances[-1]
toile = Image.open(io.BytesIO(png))
print("lancé :", titre, "| toile de travail :", toile.size, toile.mode,
      "| taille finale attendue :", iw + ajout[2] + ajout[3], "x", ih + ajout[0] + ajout[1])
print("fini, cadre :", c.cadre, "| barre visible :", f.barre_agrandir.isVisible())
f.doc.modifie = False
QTimer.singleShot(200, f.close)
app.exec()
