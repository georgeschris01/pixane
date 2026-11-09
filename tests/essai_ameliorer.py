"""IA > Réduire le bruit, Netteté, Restaurer : recettes et pose du résultat (sans moteur). Usage : essai_ameliorer.py image"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["CHRYPIX_REGLAGES"] = "Chrypix-essais"
import numpy as np
from PySide6.QtCore import QRectF
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication

from chrypix import recettes
from chrypix.document import COULEUR_SELECTION, FORMAT_IMAGE, tableau
from chrypix.fenetre import Fenetre
from chrypix.moteur import Moteur

Moteur.demarrer = lambda self, signaler=None: None
Fenetre._moteur_en_echec = lambda self, *a: None
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


infos = {"UpscaleModelLoader": {"input": {"required": {"model_name": [[recettes.SCUNET, "RealESRGAN_x4plus.pth"]]}}},
         "UNETLoader": {"input": {"required": {"unet_name": [[recettes.KONTEXT]]}}}, "ReferenceLatent": {}}
recettes.configurer(infos)
verifier(recettes.debruitage_disponible() and recettes.restauration_disponible(), "SCUNet et Kontext détectés")
p, s = recettes.restaurer("x.png", (640, 480), coloriser=True, nb=2)
ks = [n for n in p.values() if n["class_type"] == "KSampler"]
verifier(len(s) == 2 and len({k["inputs"]["seed"] for k in ks}) == 2, "Restaurer : 2 propositions, graines différentes")
verifier(all(n["inputs"]["width"] == 640 for n in p.values() if n["class_type"] == "ImageScale"),
         "Restaurer : remis à la taille de la photo")
verifier("Colorize" in p["24"]["inputs"]["text"], "Coloriser : consigne")
recettes.configurer({"ReferenceLatent": {}})
verifier(not recettes.restauration_disponible() and not recettes.debruitage_disponible(), "modèles absents : repéré")

app = QApplication(sys.argv)
f = Fenetre()
f.show()
f.charger(sys.argv[1])
w, h = f.doc.taille()
pa = QPainter(f.doc.selection)
pa.fillRect(QRectF(0, 0, w / 2, h), COULEUR_SELECTION)
pa.end()
lance = {}
f._lancer = lambda titre, sel, fabriquer, apres=None, **k: lance.update(titre=titre, fabriquer=fabriquer, apres=apres)
recettes.configurer(infos)
f.ia_debruiter()
blanc = QImage(w // 3, h // 3, FORMAT_IMAGE)
blanc.fill(0xFFFFFFFF)
res = lance["apres"](blanc)
t = tableau(res)
orig = tableau(f.doc.image.convertToFormat(FORMAT_IMAGE))
verifier(res.size() == f.doc.image.size(), "résultat remis à la taille de la photo")
verifier(np.all(t[:, : w // 2 - 2, :3] == 255) and np.array_equal(t[:, w // 2 + 2:], orig[:, w // 2 + 2:]),
         "avec une sélection : changé seulement dedans")
verifier(lance["fabriquer"]("a.png")[0]["11"]["inputs"]["model_name"] == recettes.SCUNET, "Réduire le bruit : SCUNet")
f.ia_nettete()
verifier("RealESRGAN" in str(lance["fabriquer"]("a.png")[0]), "Netteté : RealESRGAN")
print("ERREURS :", erreurs if erreurs else "aucune")
sys.stdout.flush()
f.close()
sys.exit(1 if erreurs else 0)
