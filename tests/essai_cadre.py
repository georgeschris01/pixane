"""Agrandir : ouvre le cadre, simule un glisser de la poignée droite (puis Maj sur le haut), capture l'écran.
Usage : essai_cadre.py image capture.png  (le moteur n'est pas démarré)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QEvent, QPointF, Qt, QTimer
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication
from chrypix.fenetre import Fenetre
from chrypix.moteur import Moteur

Moteur.demarrer = lambda self, signaler=None: (_ for _ in ()).throw(Exception("moteur désactivé pour l'essai"))
Fenetre._moteur_en_echec = lambda self, *a: None   # pas de message bloquant pendant l'essai
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


def souris(type_, pos, mods=Qt.NoModifier):
    boutons = Qt.NoButton if type_ == QEvent.MouseButtonRelease else Qt.LeftButton
    c.event(QMouseEvent(type_, pos, pos, Qt.LeftButton, boutons, mods))


def tirer(depart, arrivee, mods=Qt.NoModifier):
    souris(QEvent.MouseButtonPress, depart, mods)
    souris(QEvent.MouseMove, arrivee, mods)
    souris(QEvent.MouseButtonRelease, arrivee, mods)


r = c._rect_cadre()
tirer(QPointF(r.right(), r.center().y()), QPointF(r.right() + 150, r.center().y()))
r = c._rect_cadre()
tirer(QPointF(r.center().x(), r.top()), QPointF(r.center().x(), r.top() - 80), Qt.ShiftModifier)
print("cadre (h, b, g, d) px :", c.cadre, "| % :", {k: round(v, 1) for k, v in f.barre_agrandir.valeurs().items()})
print("texte :", f.barre_agrandir.texte_taille.text())
f.barre_agrandir.cotes["gauche"].setValue(10)
print("après case gauche 10 % :", c.cadre)
c.repaint()
f.grab().save(sys.argv[2])
f._fin_agrandir()
print("fini, cadre :", c.cadre, "| barre visible :", f.barre_agrandir.isVisible())
f.doc.modifie = False
QTimer.singleShot(200, f.close)
app.exec()
