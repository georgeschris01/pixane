"""Agrandir de 25 % de chaque côté (préparation et raccord par Pixane) et enregistre le résultat."""
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtGui import QGuiApplication, QImage

from pixane import recettes
from pixane.document import FORMAT_IMAGE, Document, qimage_rgb, tableau
from pixane.moteur import Moteur
from pixane.raccord import finaliser, preparer

app = QGuiApplication(sys.argv)
doc = Document.ouvrir(sys.argv[1])
sortie = Path(sys.argv[2])
png, geo, orig = preparer(tableau(doc.image)[:, :, :3], 25, 25, 25, 25)
print("liseré enlevé :", geo.coupe, "| taille finale :", geo.taille, "| travail :", geo.travail)
m = Moteur()
m.demarrer(lambda t: None)
print("moteur", m.url)
try:
    nom = m.envoyer_image(png)
    p, s = recettes.agrandir(nom, nb=1)
    p["29"]["inputs"]["seed"] = 7
    res = m.executer(p, s, threading.Event())
    Path(str(sortie).replace(".png", "_flux.png")).write_bytes(res[0][1])
    flux = tableau(QImage.fromData(res[0][1]).convertToFormat(FORMAT_IMAGE))[:, :, :3]
    qimage_rgb(finaliser(orig, flux, geo)).save(str(sortie))
    print("ok", sortie)
finally:
    if m.processus:
        m.arreter()
