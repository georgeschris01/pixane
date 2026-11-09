"""Affiche la progression envoyée par le moteur pendant Effacer et Upscale net (image de test)."""
import sys, threading, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QRectF
from PySide6.QtGui import QGuiApplication, QPainter, QPainterPath
from pixane.document import Document, COULEUR_SELECTION
from pixane.moteur import Moteur
from pixane import recettes

app = QGuiApplication(sys.argv)
doc = Document.ouvrir(sys.argv[1])
p = QPainter(doc.selection); ch = QPainterPath(); ch.addEllipse(QRectF(890, 610, 220, 220)); p.fillPath(ch, COULEUR_SELECTION); p.end()
m = Moteur(); m.demarrer(lambda t: None); print("moteur :", m.url)
vu = []
def montrer(info):
    cle = (info["etape"].split(" — ")[0], None if info["fraction"] is None else round(info["fraction"], 1))
    if cle not in vu:
        vu.append(cle); r = info["restant"]
        print(f"  {info['secondes']:>4} s | {info['etape']:<45} | {'animée' if info['fraction'] is None else str(int(info['fraction']*100))+' %':>7} | reste {r if r is not None else '?'} s")
try:
    nom = m.envoyer_image(doc.png_pour_ia(True))
    print("EFFACER"); m.executer(*recettes.effacer(nom), threading.Event(), montrer)
    vu.clear(); nom2 = m.envoyer_image(doc.png_pour_ia(False))
    p2, s2, n = recettes.upscale_net(nom2, 2.0, 0.35, (1600, 1100)); print(f"UPSCALE NET ({n} morceaux)")
    m.executer(p2, s2, threading.Event(), montrer, n)
finally:
    m.arreter()
