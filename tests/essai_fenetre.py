"""Ouvre la fenêtre (sans affichage), charge une photo, simule une sélection au pinceau, annule, puis ferme."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QPointF, QTimer
from PySide6.QtWidgets import QApplication
from chrypix.fenetre import Fenetre
from chrypix.moteur import Moteur

Moteur.demarrer = lambda self, signaler=None: (_ for _ in ()).throw(Exception("moteur désactivé pour l'essai"))
app = QApplication(sys.argv)
f = Fenetre(); f.show(); f.charger(sys.argv[1])
c = f.canevas
c._avant = f.doc.etat(); c._trace = [QPointF(100, 100)]; c._coup_de_pinceau(QPointF(100, 100), QPointF(300, 200)); c._trace = None
c.selection_modifiee.emit(c._avant, "Pinceau")
print("sélection vide ?", f.doc.selection_vide(), "| historique :", f.historique.count())
f.historique.undo(); print("après annuler, vide ?", f.doc.selection_vide())
f._modifier_selection("inverser"); print("inversée, vide ?", f.doc.selection_vide())
c.zoomer(2); c.repaint(); c.ajuster(); c.repaint()
f.resize(1440, 920); f._modifier_selection("rien"); c._avant = f.doc.etat(); c._coup_de_pinceau(QPointF(1000, 700), QPointF(1050, 720)); c.ajuster(); f.grab().save(sys.argv[2]); f.changer_theme("clair"); c.repaint(); f.grab().save(sys.argv[2].replace(".png", "_clair.png")); print("captures", sys.argv[2], "| titre :", f.windowTitle())
f.doc.modifie = False
QTimer.singleShot(200, f.close); app.exec(); print("fermé proprement")
