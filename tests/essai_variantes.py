"""« Partir de celle-ci » : variantes d'une proposition (Effacer, Remplir, Agrandir) avec un faux moteur : l'image
envoyée est la proposition choisie avec la même zone à refaire, la force suit la glissière Proche ↔ Libre, les
variantes s'ajoutent aux vignettes et peuvent être gardées. Usage : essai_variantes.py dossier_sortie"""
import io
import os
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PIL import Image
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QApplication

from pixane import recettes
from pixane.dialogues import ChoixResultat
from pixane.document import COULEUR_SELECTION, FORMAT_IMAGE, tableau
from pixane.fenetre import Fenetre
from pixane.moteur import Moteur

Moteur.demarrer = lambda self, signaler=None: None
Fenetre._moteur_en_echec = lambda self, *a: None
sortie = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("sortie_variantes")
sortie.mkdir(parents=True, exist_ok=True)
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


Image.fromarray(np.full((200, 300, 3), 90, np.uint8)).save(sortie / "fond.png")
app = QApplication(sys.argv)
f = Fenetre()
f.resize(1300, 850)
f.show()
f.charger(str(sortie / "fond.png"))
app.processEvents()
doc = f.doc

envois, prompts = [], []
couleurs = iter([(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255),
                 (250, 128, 0), (128, 0, 250), (10, 200, 120), (200, 10, 120)] * 3)


def faux_envoi(png):
    envois.append(Image.open(io.BytesIO(png)).copy())
    return f"essai{len(envois)}.png"


def faux_calcul(prompt, sorties, annuler, progres=None, morceaux=1):
    prompts.append(prompt)
    im = envois[-1].convert("RGBA")
    a = np.asarray(im)
    nb = prompt["28"]["inputs"]["amount"] if "28" in prompt else 1
    res = []
    for cle, libelle in sorties.items():
        for _ in range(nb if cle == "32" else 1):
            rgb = a[:, :, :3].copy()
            rgb[a[:, :, 3] < 128] = next(couleurs)
            buf = io.BytesIO()
            Image.fromarray(rgb).save(buf, "PNG")
            res.append((libelle, buf.getvalue()))
    return res


f.moteur.envoyer_image = faux_envoi
f.moteur.executer = faux_calcul
f.moteur.etat = "prêt"


def attendre(choix):
    for _ in range(2000):
        app.processEvents()
        if choix.bouton_autres.isEnabled():
            break
        time.sleep(0.005)
    app.processEvents()


scenario = {}


def faux_exec(self):
    """Remplace la fenêtre modale : demande des variantes de la proposition 1, puis garde la dernière."""
    scenario["visible"] = self.zone_variante.isVisibleTo(self)
    n0 = len(self.images)
    scenario["n0"] = n0
    couleur_1 = tuple(int(v) for v in tableau(self.images[0])[100, 150, :3])
    scenario["couleur_1"] = couleur_1
    self.vignettes.setCurrentRow(0)
    self.proche_libre.setValue(0)
    self.bouton_variante.click()
    scenario["occupe"] = not self.bouton_variante.isEnabled()
    attendre(self)
    scenario["n1"] = len(self.images)
    self.grab().save(str(sortie / "choix_variantes.png"))
    self.vignettes.setCurrentRow(len(self.images) - 1)
    scenario["garde"] = tuple(int(v) for v in tableau(self.images[-1])[100, 150, :3])
    return 1


ChoixResultat.exec = faux_exec


def selection_rect():
    doc.selection.fill(0)
    p = QPainter(doc.selection)
    p.fillRect(120, 70, 60, 60, COULEUR_SELECTION)
    p.end()


# ------------------------------------------------------------ Effacer
selection_rect()
avant = len(envois)
f.ia_effacer()
for _ in range(2000):
    app.processEvents()
    if "garde" in scenario:
        break
    time.sleep(0.005)
for _ in range(50):
    app.processEvents()
verifier(scenario.get("visible"), "Effacer : « Partir de celle-ci » montré")
verifier(scenario.get("n0") == recettes.NB_EFFACER + 1, f"Effacer : {scenario.get('n0')} propositions au départ")
verifier(scenario.get("n1") == scenario.get("n0", 0) + recettes.NB_EFFACER,
         f"variantes ajoutées aux vignettes ({scenario.get('n1')})")
envoi = np.asarray(envois[-1].convert("RGBA"))
premier = np.asarray(envois[avant].convert("RGBA"))
verifier(len(envois) == avant + 2, "deux envois : l'original, puis la proposition choisie")
verifier(tuple(envoi[100, 150, :3]) == scenario.get("couleur_1"),
         f"l'image envoyée est la proposition choisie ({tuple(envoi[100, 150, :3])})")
verifier(np.array_equal(envoi[:, :, 3], premier[:, :, 3]), "avec la même zone à refaire (transparence)")
verifier(tuple(envoi[10, 10, :3]) == (90, 90, 90), "le reste de l'image est inchangé")
k = prompts[-1]["29"]["inputs"]
verifier(abs(k["denoise"] - recettes.FORCE_PROCHE) < 1e-6, f"glissière sur Proche : force {k['denoise']}")
verifier("13" not in prompts[-1] and "11" in prompts[-1], "variante : Flux seul, découpe autour de la zone")
img = tableau(doc.image.convertToFormat(FORMAT_IMAGE))
verifier(tuple(int(v) for v in img[100, 150, :3]) == scenario.get("garde"), "la variante choisie est gardée")
verifier(int(f.reglages.value("variante_curseur", -1)) == 0, "la glissière est retenue")

# ------------------------------------------------------------ Remplir (texte transmis)
scenario.clear()
f.historique.undo()
selection_rect()
f.texte_remplir.setText("a red brick wall")
f.ia_remplir()
for _ in range(2000):
    app.processEvents()
    if "garde" in scenario:
        break
    time.sleep(0.005)
for _ in range(50):
    app.processEvents()
verifier(prompts[-1]["24"]["inputs"]["text"] == "a red brick wall", "Remplir : la consigne suit dans les variantes")
verifier(scenario.get("n1") == scenario.get("n0", 0) + recettes.NB_REMPLIR, "Remplir : variantes ajoutées")
f.texte_remplir.setText("")

# ------------------------------------------------------------ recette et force
verifier(recettes.force_variante(0) == 0.25 and recettes.force_variante(100) == 0.85 and
         recettes.force_variante(50) == 0.55, "glissière : 0,25 (Proche) à 0,85 (Libre), 0,55 au milieu")
p, s = recettes.variante("x.png", 0.5, nb=3, decoupe=False)
verifier("11" not in p and p["27"]["inputs"]["pixels"] == ["10", 0] and p["28"]["inputs"]["amount"] == 3,
         "Agrandir : variante sur la toile entière")

# ------------------------------------------------------------ pas de variantes pour les autres actions
c2 = ChoixResultat("Upscale", doc.image)
verifier(not c2.zone_variante.isVisibleTo(c2), "Upscale et autres : pas de « Partir de celle-ci »")

f.reglages.remove("variante_curseur")
print()
print("ÉCHECS :" if erreurs else "Tout est bon.", *erreurs, sep="\n  ")
os._exit(1 if erreurs else 0)
