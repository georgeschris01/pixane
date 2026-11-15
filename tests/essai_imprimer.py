"""Fichier > Imprimer : place de l'image sur la feuille (remplir, taille réelle, largeur choisie), orientation
automatique, aperçu, avertissement si trop peu de points par pouce, impression dans un PDF (aucune vraie imprimante).
Usage : essai_imprimer.py dossier_sortie"""
import os
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PIL import Image
from PySide6.QtCore import QSizeF, QTimer
from PySide6.QtWidgets import QApplication
from pixane import imprimer as im
from pixane.fenetre import Fenetre
from pixane.moteur import Moteur

Moteur.demarrer = lambda self, signaler=None: (_ for _ in ()).throw(Exception("moteur désactivé pour l'essai"))
Fenetre._moteur_en_echec = lambda self, *a: None
sortie = Path(sys.argv[1])
sortie.mkdir(parents=True, exist_ok=True)
a = np.zeros((1200, 1800, 3), np.uint8)
a[..., 0] = 200
a[300:900, 600:1200] = (20, 120, 220)
Image.fromarray(a).save(sortie / "photo.png", dpi=(300, 300))
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


# 1. calculs
page = im.taille_page(0, False)
verifier(abs(page.width() - 210) < 0.5 and abs(page.height() - 297) < 0.5, "A4 portrait : 210 × 297 mm")
r = im.place_image(page, 10, 1800, 1200, "remplir", 300, 0)
verifier(abs(r.width() - 190) < 0.1 and abs(r.left() - 10) < 0.1, "Remplir la page : 190 mm de large dans les marges")
r = im.place_image(im.taille_page(0, True), 10, 1800, 1200, "reelle", 300, 0)
verifier(abs(r.width() - 152.4) < 0.1 and abs(r.height() - 101.6) < 0.1, "Taille réelle : 1800 px à 300 dpi = 15,24 cm")
r = im.place_image(page, 10, 1800, 1200, "largeur", 300, 12)
verifier(abs(r.width() - 120) < 0.1 and abs(r.height() - 80) < 0.1, "Largeur choisie : 12 cm")

# 2. fenêtre
app = QApplication(sys.argv)
f = Fenetre()
f.resize(1440, 920)
f.show()
f.charger(str(sortie / "photo.png"))
app.processEvents()
verifier(abs(f.doc.dpi - 300) < 1 and f.a_imprimer.isEnabled() and f.a_imprimer.shortcut().toString() == "Ctrl+P",
         "Fichier > Imprimer… (Ctrl+P)")
d = im.DialogueImprimer(f.doc.image, f.doc.dpi, f)
d.sens.setCurrentIndex(0)
verifier(d.paysage(), "orientation automatique : paysage pour une image plus large que haute")
d.mode.setCurrentIndex(d.mode.findData("reelle"))
verifier("15,2 × 10,2 cm" in d.mode.currentText() and "300 dpi" in d.info.text().replace("points par pouce", "dpi")
         or "300" in d.info.text(), f"taille réelle et résolution affichées ({d.info.text()})")
d.mode.setCurrentIndex(d.mode.findData("largeur"))
d.largeur.setValue(100)
verifier("floue" in d.info.text(), "image trop agrandie : avertissement (moins de 150 points par pouce)")
d.largeur.setValue(15)
d.mode.setCurrentIndex(d.mode.findData("remplir"))
d.show()
app.processEvents()
d.grab().save(str(sortie / "fenetre_imprimer.png"))

# 3. impression dans un PDF
pdf = sortie / "impression.pdf"
pdf.unlink(missing_ok=True)
d.imprimer(str(pdf))
data = pdf.read_bytes() if pdf.exists() else b""
boite = re.search(rb"/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)", data)
verifier(boite is not None and abs(float(boite.group(1)) - 842) < 2 and abs(float(boite.group(2)) - 595) < 2,
         "PDF : une page A4 paysage (842 × 595 points)")
verifier(len(data) > 20000 and b"/Image" in data, f"l'image est dans la page ({len(data)} octets)")
d.close()

print("ERREURS :", erreurs if erreurs else "aucune")
f.doc.modifie = False
sys.stdout.flush()
QTimer.singleShot(200, f.close)
app.exec()
sys.exit(1 if erreurs else 0)
