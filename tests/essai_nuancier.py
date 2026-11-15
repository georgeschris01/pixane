"""Nuancier : panneau, ajouter / retirer / choisir, enregistré, fichiers Photoshop .aco (lus et écrits) et GIMP .gpl.
Usage : essai_nuancier.py dossier_sortie"""
import os
import struct
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PIL import Image
from PySide6.QtCore import QSettings, QTimer, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QColorDialog
from pixane import nuancier
from pixane.fenetre import Fenetre
from pixane.moteur import Moteur

Moteur.demarrer = lambda self, signaler=None: (_ for _ in ()).throw(Exception("moteur désactivé pour l'essai"))
Fenetre._moteur_en_echec = lambda self, *a: None
sortie = Path(sys.argv[1])
sortie.mkdir(parents=True, exist_ok=True)
Image.fromarray(np.full((100, 100, 3), 200, np.uint8)).save(sortie / "fond.png")
QSettings("Pixane", "Pixane-essais").remove("nuancier")
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


# 1. fichiers
couleurs = [("Rouge label", "#c81e32"), ("", "#102030")]
aco = nuancier.ecrire_aco(couleurs)
verifier(nuancier.lire_aco(aco) == couleurs, "Photoshop .aco : écrit puis relu, noms compris")
v1 = struct.pack(">HH", 1, 3) + struct.pack(">HHHHH", 0, 65535, 0, 0, 0) \
    + struct.pack(">HHHHH", 2, 65535, 0, 65535, 65535) + struct.pack(">HHHHH", 8, 5000, 0, 0, 0)
lu = nuancier.lire_aco(v1)
verifier([c for _n, c in lu] == ["#ff0000", "#ff00ff", "#808080"],   # CMJN : magenta 100 % (valeurs inversées)
         f"Photoshop .aco version 1 : RVB, CMJN, gris ({[c for _n, c in lu]})")
gpl = "GIMP Palette\nName: Essai\n#\n255 0 0\tRouge\n  0 128 255 Bleu ciel\n"
verifier(nuancier.lire_gpl(gpl) == [("Rouge", "#ff0000"), ("Bleu ciel", "#0080ff")], "GIMP .gpl")

# 2. panneau
app = QApplication(sys.argv)
f = Fenetre()
f.resize(1440, 920)
f.show()
f.charger(str(sortie / "fond.png"))
app.processEvents()
n = f.nuancier
verifier(hasattr(f, "dock_nuancier") and len(n.couleurs) == len(nuancier.DEPART), "panneau NUANCIER, couleurs de départ")
verifier(QColorDialog.customColor(0) == QColor(nuancier.DEPART[0]) and QColorDialog.customColor(4) == QColor(nuancier.DEPART[4]),
         "les couleurs du nuancier sont dans « Couleurs personnalisées » des fenêtres de couleur")
f._couleur_nuancier("#112233")
f.canevas.couleur_peinture = QColor("#3366cc")
n.ajouter()
verifier(n.couleurs[-1][1] == "#3366cc" and n.liste.count() == len(nuancier.DEPART) + 1, "+ : la couleur de peinture est ajoutée")
verifier(nuancier.charger()[-1][1] == "#3366cc", "enregistré (retrouvé au prochain démarrage)")
it = n.liste.item(4)
n.liste.itemClicked.emit(it)
verifier(f.canevas.couleur_peinture.name() == nuancier.DEPART[4] and QColor(f.opt_couleur.couleur).name() == nuancier.DEPART[4],
         "clic sur une couleur : elle devient la couleur de peinture")
n.liste.setCurrentRow(n.liste.count() - 1)
n.retirer()
verifier(len(n.couleurs) == len(nuancier.DEPART), "− : la couleur choisie est retirée")
fichier = sortie / "label.aco"
fichier.write_bytes(aco)
n.importer(str(fichier))
verifier(n.couleurs[-2:] == couleurs, "Importer un .aco : ses couleurs s'ajoutent")
n.exporter(str(sortie / "export.aco"))
verifier(nuancier.lire_aco((sortie / "export.aco").read_bytes()) == n.couleurs, "Exporter en .aco")
n.remettre()
verifier([c for _n, c in n.couleurs] == nuancier.DEPART, "Remettre les couleurs de départ")
f.dock_nuancier.raise_()
app.processEvents()
f.dock_nuancier.grab().save(str(sortie / "nuancier.png"))
QSettings("Pixane", "Pixane-essais").remove("nuancier")

print("ERREURS :", erreurs if erreurs else "aucune")
f.doc.modifie = False
sys.stdout.flush()
QTimer.singleShot(200, f.close)
app.exec()
sys.exit(1 if erreurs else 0)
