"""IA > Réduire le bruit, Netteté, Restaurer : recettes et pose du résultat (sans moteur). Usage : essai_ameliorer.py image"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PySide6.QtCore import QRectF
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication

from pixane import recettes
from pixane.document import COULEUR_SELECTION, FORMAT_IMAGE, tableau
from pixane.fenetre import Fenetre
from pixane.moteur import Moteur

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
verifier(all(n["inputs"]["width"] == 640 and n["inputs"]["height"] == 480 for k, n in p.items()
             if n["class_type"] == "ImageScale" and k != "11"), "Restaurer : remis à la taille de la photo")
e = p["11"]["inputs"]
verifier(e["width"] % 16 == 0 and e["height"] % 16 == 0 and abs(e["width"] / e["height"] - 640 / 480) < 0.005,
         f"Restaurer : taille de travail aux mêmes proportions, sans étirement ({e['width']} × {e['height']})")
verifier("Colorize" in p["24"]["inputs"]["text"], "Coloriser : consigne")
recettes.configurer({"ReferenceLatent": {}})
verifier(not recettes.restauration_disponible() and not recettes.debruitage_disponible(), "modèles absents : repéré")

# « Restaurer » : lumière du résultat, couleurs de l'original (une photo sépia ne peut pas être colorisée)
import numpy as np  # noqa: E402
from pixane.filtres import garder_teinte  # noqa: E402
rng = np.random.default_rng(3)
gris = rng.integers(0, 256, (120, 160)).astype(np.float32)
sepia = np.dstack([gris * 0.95 + 12, gris * 0.85 + 8, gris * 0.65, np.full_like(gris, 255)]).clip(0, 255).astype(np.uint8)
colorise = sepia.copy()
colorise[:60, :, 2] = 255                                   # ciel bleu inventé
colorise[60:, :, 1] = 200                                   # herbe verte inventée
r = garder_teinte(sepia, colorise).astype(np.float32)
dom = (r[..., 0] - r[..., 2]).mean()
verifier(dom > 10 and (r[..., 2] <= r[..., 0] + 2).mean() > 0.97, "Restaurer : teinte sépia gardée, pas de couleurs ajoutées")

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

# Restaurer : nom du calque et nom proposé à l'enregistrement (« _restauree », « _restauree_colorisee »)
from PySide6.QtWidgets import QFileDialog, QMessageBox  # noqa: E402
f._lancer = lambda titre, sel, fabriquer, apres=None, **k: lance.update(titre=titre, apres=apres, **k)
for coloriser, calque_attendu, ajout in ((False, "Restaurée", "_restauree"),
                                         (True, "Restaurée et colorisée", "_restauree_colorisee")):
    lance.clear()
    QMessageBox.exec = lambda self, c=coloriser: None
    QMessageBox.clickedButton = lambda self, c=coloriser: self.buttons()[[b.text() for b in self.buttons()].index(
        "Restaurer et coloriser" if c else "Restaurer")]
    recettes.configurer(infos)
    f.ia_restaurer()
    verifier(lance.get("nom_calque") == calque_attendu and lance.get("suffixe") == ajout,
             f"Restaurer (coloriser={coloriser}) : calque « {lance.get('nom_calque')} », ajout « {lance.get('suffixe')} »")
avant = len(f.doc.calques)
f._appliquer_resultat(f.doc, f.doc.image.copy(), "Restaurer une vieille photo", None, "Restaurée")
verifier(f.doc.calques[-1].nom.startswith("Restaurée") or len(f.doc.calques) == avant,
         "calque du résultat nommé « Restaurée »")
f.doc.suffixe_nom = "_restauree"
propose = {}
QFileDialog.getSaveFileName = lambda *a, **k: (propose.update(nom=a[2]) or ("", ""))
f.enregistrer_sous()
verifier(propose.get("nom", "").endswith(("_restauree.jpg", "_restauree.piximg")), f"nom proposé : {propose.get('nom')}")
print("ERREURS :", erreurs if erreurs else "aucune")
sys.stdout.flush()
for d in f.documents:          # aucune question à la fermeture
    d.modifie = False
f.close()
sys.exit(1 if erreurs else 0)
