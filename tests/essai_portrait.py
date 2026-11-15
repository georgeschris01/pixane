"""IA > Retouche portrait : recette SAM (parties du visage), zones (peau sans yeux ni bouche), peau lissée avec les
contours gardés, yeux éclaircis, dents blanchies ; dans Pixane : fenêtre de réglage, calque modifié, Ctrl+Z ; aucun
visage : message. Le moteur n'est pas démarré : les masques sont fabriqués. Usage : essai_portrait.py dossier"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PIL import Image
from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox
from pixane import portrait, recettes
from pixane.fenetre import Fenetre
from pixane.moteur import Moteur

Moteur.demarrer = lambda self, signaler=None: (_ for _ in ()).throw(Exception("moteur désactivé pour l'essai"))
Fenetre._moteur_en_echec = lambda self, *a: None
sortie = Path(sys.argv[1])
sortie.mkdir(parents=True, exist_ok=True)
QSettings("Pixane", "Pixane-essais").remove("portrait_peau")
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


# image : fond gris, « visage » couleur peau avec des taches (boutons), un trait sombre (contour), yeux, dents jaunes
rng = np.random.default_rng(3)
H, W = 400, 400
img = np.full((H, W, 4), 255, np.uint8)
img[..., :3] = 120
yy, xx = np.mgrid[0:H, 0:W]
visage = ((xx - 200) / 120) ** 2 + ((yy - 200) / 160) ** 2 < 1
peau = np.array([215, 165, 140], np.float32)
img[visage, :3] = peau
taches = rng.random((H, W)) < 0.01
img[visage & taches, :3] = (190, 120, 110)
img[(xx > 140) & (xx < 146) & (yy > 150) & (yy < 300), :3] = (60, 40, 30)        # contour net (une mèche)
yeux = (((xx - 160) / 22) ** 2 + ((yy - 160) / 10) ** 2 < 1) | (((xx - 240) / 22) ** 2 + ((yy - 160) / 10) ** 2 < 1)
img[yeux, :3] = (110, 90, 80)
dents = (np.abs(xx - 200) < 40) & (np.abs(yy - 280) < 10)
img[dents, :3] = (225, 210, 150)
Image.fromarray(img).save(sortie / "visage.png")
masques = {"visage": visage, "cou": np.zeros_like(visage), "yeux": yeux, "sourcils": np.zeros_like(visage),
           "levres": np.zeros_like(visage), "dents": dents}
cartes = [np.where(masques[n], 255, 0).astype(np.uint8) for n, _t in recettes.PARTIES_VISAGE]

# 1. recette
recettes._sam["fichier"] = "sam3.1_multiplex_fp16.safetensors"
p, s = recettes.visage("x.png")
verifier(list(s.values()) == [n for n, _t in recettes.PARTIES_VISAGE] and len(s) == 6,
         "recette : une sortie par partie du visage (visage, cou, yeux, sourcils, lèvres, dents)")

# 2. calcul
z = portrait.zones({n: c for (n, _t), c in zip(recettes.PARTIES_VISAGE, cartes)})
verifier(z["peau"][230, 200] > 0.99 and z["peau"][160, 160] < 0.01 and z["peau"][280, 200] < 0.01,
         "zones : la peau sans les yeux ni les dents")
r = portrait.retoucher(img, z, {"peau": 70, "grain": 0, "yeux": 60, "dents": 60})
zone = visage & ~taches & (z["peau"] > 0.99)
t_av = np.abs(img[visage & taches & (z["peau"] > 0.99), :3].astype(float) - peau).mean()
t_ap = np.abs(r[visage & taches & (z["peau"] > 0.99), :3].astype(float) - peau).mean()
verifier(t_ap < t_av * 0.6, f"taches de la peau atténuées ({t_av:.0f} -> {t_ap:.0f})")
verifier(abs(int(r[220, 143, 0]) - 60) < 25, f"le contour net reste net ({r[220, 143, 0]} pour 60)")
verifier(r[160, 160, :3].mean() > img[160, 160, :3].mean() + 5, "yeux éclaircis")
jaune = lambda a: (int(a[0]) + int(a[1])) / 2 - int(a[2])
verifier(jaune(r[280, 200]) < jaune(img[280, 200]) * 0.6, f"dents moins jaunes ({jaune(img[280, 200]):.0f} -> "
         f"{jaune(r[280, 200]):.0f})")
verifier((r[:20, :20] == img[:20, :20]).all(), "le reste de l'image ne bouge pas")
verifier((portrait.retoucher(img, z, portrait.NEUTRES) == img).all(), "réglages à zéro : rien ne change")
Image.fromarray(np.hstack([img, r])).save(sortie / "avant_apres.png")

# 3. dans Pixane
app = QApplication(sys.argv)
from pixane.dialogues_reglage import DialogueReglage
f = Fenetre()
f.resize(1440, 920)
f.show()
f.charger(str(sortie / "visage.png"))
app.processEvents()
f.moteur.etat = "prêt"
f._carte_ia = lambda titre, fabriquer, suite, toutes=False, vide_ok=False: suite(cartes)
DialogueReglage.exec = lambda self: QDialog.Accepted
avant = f.doc.calques[0].image.copy()
f.ia_portrait()
from pixane.document import FORMAT_IMAGE, tableau
apres = tableau(f.doc.calques[0].image.convertToFormat(FORMAT_IMAGE))
verifier(apres[160, 160, :3].mean() > img[160, 160, :3].mean() + 3 and (apres[:20, :20] == img[:20, :20]).all(),
         "IA > Retouche portrait : le calque est retouché (réglages de départ)")
f.historique.undo()
verifier(f.doc.calques[0].image == avant, "Ctrl+Z : la photo revient")
messages = []
QMessageBox.information = staticmethod(lambda *a, **k: messages.append(a[2]))
cartes = [np.zeros((H, W), np.uint8)] * 6
f.ia_portrait()
verifier(messages and "Aucun visage" in messages[-1], "aucun visage : message")
verifier(f.a_ia_portrait.text().startswith("Retouche portrait"), "menu IA > Retouche portrait…")

print("ERREURS :", erreurs if erreurs else "aucune")
f.doc.modifie = False
sys.stdout.flush()
QTimer.singleShot(200, f.close)
app.exec()
sys.exit(1 if erreurs else 0)
