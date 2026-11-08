"""Essai de bout en bout sans interface : ouvrir, sélectionner, Effacer + Upscale rapide par le moteur, enregistrer."""
import sys, threading, time
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[1]))
from pathlib import Path
from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QGuiApplication, QImage, QPainter, QPainterPath
from retouche_ia.document import Document, COULEUR_SELECTION, FORMAT_IMAGE
from retouche_ia.moteur import Moteur
from retouche_ia import recettes

app = QGuiApplication(sys.argv)
photo, sortie = Path(sys.argv[1]), Path(sys.argv[2])
doc = Document.ouvrir(photo)
p = QPainter(doc.selection); ch = QPainterPath(); ch.addEllipse(QRectF(890, 610, 220, 220)); p.fillPath(ch, COULEUR_SELECTION); p.end()
assert not doc.selection_vide()
m = Moteur(); t = time.time(); m.demarrer(print); print("moteur prêt en %.0f s sur %s" % (time.time() - t, m.url))
try:
    nom = m.envoyer_image(doc.png_pour_ia(True))
    tous = {}
    for titre, (prompt, sorties) in (("Effacer", recettes.effacer(nom)), ("Upscale rapide", recettes.upscale_rapide(nom, 2))):
        t = time.time(); res = m.executer(prompt, sorties, threading.Event()); print(titre, "%.0f s" % (time.time() - t), [(l, QImage.fromData(d).size().toTuple()) for l, d in res])
        tous.update(res)
    img = QImage.fromData(tous["Flux 1"]).convertToFormat(FORMAT_IMAGE)
    doc.appliquer_etat((img, doc.selection))
    doc.enregistrer(sortie); print("enregistré", sortie, Document.ouvrir(sortie).image.size())
finally:
    m.arreter(); print("moteur arrêté")
