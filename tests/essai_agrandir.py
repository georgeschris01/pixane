"""Agrandir de 25 % de chaque côté et enregistre le résultat (pour examiner la jointure)."""
import sys, threading
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtGui import QGuiApplication
from chrypix.document import Document
from chrypix.moteur import Moteur
from chrypix import recettes
app = QGuiApplication(sys.argv)
doc = Document.ouvrir(sys.argv[1]); sortie = Path(sys.argv[2])
m = Moteur(); m.demarrer(lambda t: None); print("moteur", m.url)
try:
    nom = m.envoyer_image(doc.png_pour_ia(False))
    p, s = recettes.agrandir(nom, 25, 25, 25, 25, nb=1)
    for k, v in p.items():
        if v["class_type"] == "KSampler": v["inputs"]["seed"] = 7
    res = m.executer(p, s, threading.Event())
    sortie.write_bytes(res[0][1]); print("ok brut", sortie)
    import numpy as np
    from PySide6.QtGui import QImage
    from chrypix.document import tableau, qimage_rgb, FORMAT_IMAGE
    from chrypix.raccord import raccorder
    brut = tableau(QImage.fromData(res[0][1]).convertToFormat(FORMAT_IMAGE))[:, :, :3]
    fin = raccorder(tableau(doc.image)[:, :, :3], brut, 25, 25, 25, 25)
    qimage_rgb(fin).save(str(sortie).replace(".png", "_raccord.png")); print("ok raccord")
finally:
    if m.processus: m.arreter()
