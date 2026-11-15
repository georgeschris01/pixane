"""IA pour la photo : sélectionner / remplacer le ciel, coloriser, changer la lumière, flou selon la profondeur.
Le moteur n'est pas démarré : ses réponses (masque du ciel, carte de profondeur) sont fabriquées.
Usage : essai_ia_photo.py dossier_sortie"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PIL import Image
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QDialog, QInputDialog
from pixane import ia_photo, recettes
from pixane.fenetre import Fenetre
from pixane.moteur import Moteur

Moteur.demarrer = lambda self, signaler=None: (_ for _ in ()).throw(Exception("moteur désactivé pour l'essai"))
Fenetre._moteur_en_echec = lambda self, *a: None
sortie = Path(sys.argv[1])
sortie.mkdir(parents=True, exist_ok=True)
h, w = 300, 400
img = np.zeros((h, w, 3), np.uint8)
img[:150] = (120, 170, 235)                                 # ciel
img[150:] = (60, 120, 50)                                   # herbe
rng = np.random.default_rng(3)
img = np.clip(img.astype(int) + rng.integers(-30, 30, (h, w, 1)), 0, 255).astype(np.uint8)
img[180:260, 170:230] = (200, 40, 40)                       # sujet proche
Image.fromarray(img).save(sortie / "photo.png")
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


# 1. calcul du flou selon la profondeur
rgba = np.dstack([img, np.full((h, w), 255, np.uint8)])
prof = np.zeros((h, w), np.float32)
prof[150:] = np.linspace(0.3, 0.7, h - 150)[:, None]        # herbe : de loin à près
prof[180:260, 170:230] = 1.0                                # sujet : le plus proche
grain = lambda a, ys, xs: a[ys, xs, 1].astype(float).std()
r = ia_photo.flou_profondeur(rgba, prof, {"x": 200, "y": 220, "flou": 12, "zone": 10})
verifier(np.array_equal(r[200:240, 180:220], rgba[200:240, 180:220]), "le point net (sujet) reste intact")
verifier(grain(r, slice(20, 120), slice(20, 380)) < grain(rgba, slice(20, 120), slice(20, 380)) * 0.4,
         "le ciel (loin) est flouté")
r0 = ia_photo.flou_profondeur(rgba, prof, {"x": 200, "y": 220, "flou": 0, "zone": 10})
verifier(np.array_equal(r0, rgba), "flou 0 : image intacte")
r2 = ia_photo.flou_profondeur(rgba, prof, {"x": 200, "y": 40, "flou": 12, "zone": 10, "arriere": True})
verifier(grain(r2, slice(20, 120), slice(20, 380)) > grain(rgba, slice(20, 120), slice(20, 380)) * 0.9
         and grain(r2, slice(190, 250), slice(180, 220)) < grain(rgba, slice(190, 250), slice(180, 220)) + 1,
         "net sur le ciel, « arrière-plan seulement » : rien de plus loin à flouter")
# pas de halo : un sujet clair net ne bave pas sur le fond flou autour de lui
fond = np.zeros((200, 200, 4), np.uint8)
fond[..., 3] = 255
fond[..., :3] = 40
fond[60:140, 60:140, :3] = 250
pf = np.full((200, 200), 0.1, np.float32)
pf[60:140, 60:140] = 1.0
r3 = ia_photo.flou_profondeur(fond, pf, {"x": 100, "y": 100, "flou": 20, "zone": 10})
verifier(r3[100, 52, 0] <= 42 and r3[100, 100, 0] == 250, f"pas de halo clair autour du sujet net (fond : {r3[100, 52, 0]})")
# une partie du sujet que la carte met au loin (veste grise devant un mur gris) : le détourage la garde nette
suj = np.zeros((200, 200), np.float32)
suj[60:140, 60:140] = 1
pf2 = pf.copy()
pf2[60:140, 60:100] = 0.1
r4 = ia_photo.flou_profondeur(fond, pf2, {"x": 120, "y": 100, "flou": 20, "zone": 10}, suj)
r5 = ia_photo.flou_profondeur(fond, pf2, {"x": 120, "y": 100, "flou": 20, "zone": 10, "sujet": False}, suj)
verifier(np.array_equal(r4[60:140, 60:140], fond[60:140, 60:140]) and not np.array_equal(r5, r4),
         "« Garder net tout le sujet » : la partie mal classée reste nette (case décochée : floutée)")

# 2. dans Pixane (réponses du moteur fabriquées)
app = QApplication(sys.argv)
from pixane.document import FORMAT_IMAGE, masque, tableau
f = Fenetre()
f.resize(1440, 920)
f.show()
f.charger(str(sortie / "photo.png"))
app.processEvents()
doc = f.doc
for nom in ("a_sel_ciel", "a_ia_ciel", "a_ia_coloriser", "a_ia_lumiere", "a_ia_profondeur"):
    verifier(hasattr(f, nom), f"action {nom} dans les menus")
recettes._sam["fichier"] = "sam3.1_multiplex_fp16.safetensors"
recettes._kontext.update(type="complet", fichier=recettes.KONTEXT)
recettes._profondeur["fichier"] = recettes.PROFONDEUR
recettes._detourage["ok"] = True
carte_ciel = np.zeros((h, w), np.uint8)
carte_ciel[:150] = 255
carte_ciel[40:60, 50:90] = 0                                # un nuage, laissé de côté par SAM
reponses = {}


def faux_carte(titre, fabriquer, suite, toutes=False):
    reponses["recette"] = fabriquer("image.png")
    if fabriquer is recettes.ciel:
        suite(carte_ciel)
        return
    sujet_rouge = np.zeros((h, w), np.uint8)
    sujet_rouge[180:260, 170:230] = 255
    suite([(prof * 255).astype(np.uint8), sujet_rouge] if toutes else (prof * 255).astype(np.uint8))


f._carte_ia = faux_carte
lances = []
f._lancer = lambda titre, avec, fabriquer, **kw: lances.append((titre, avec, fabriquer("image.png"), kw))
f.ia_selection_ciel()
m = masque(doc.selection)
verifier(m[50, 200] == 255 and m[250, 200] == 0 and (0 < m[150, 200] < 255 or 0 < m[149, 200] < 255),
         f"Sélectionner le ciel : sélection du ciel, bord adouci ({m[147:153, 200].tolist()})")
verifier(m[50, 70] == 255, "le nuage (entouré de ciel) fait partie du ciel")
p, _s = reponses["recette"]
verifier(p["15"]["inputs"]["text"] == "sky" and p["12"]["class_type"] == "SAM3_Detect", "recette : SAM 3.1 avec « sky »")
verifier(f.historique.undoText() == "Sélectionner le ciel", "une étape « Sélectionner le ciel »")
f.historique.undo()
QInputDialog.getItem = staticmethod(lambda *a, **k: (ia_photo.noms_ciels()["coucher"], True))
f.ia_remplacer_ciel()
titre, avec, (prompt, _s), kw = lances[-1]
textes = [n["inputs"].get("text", "") for n in prompt.values() if n["class_type"] == "CLIPTextEncode"]
verifier(titre == "Remplacer le ciel" and not avec and any("sunset" in t and "Replace the sky" in t for t in textes) and kw.get("apres"),
         "Remplacer le ciel : Flux Kontext avec la consigne « coucher de soleil », gardé dans le ciel sélectionné")
verifier(not doc.selection_vide(), "le ciel est sélectionné avant le remplissage")
f.ia_coloriser()
titre, _a, (prompt, _s), kw = lances[-1]
textes = [n["inputs"].get("text", "") for n in prompt.values() if n["class_type"] == "CLIPTextEncode"]
verifier(titre == "Coloriser" and any("Colorize" in t for t in textes), "Coloriser : Flux Kontext, consigne prête")
QInputDialog.getItem = staticmethod(lambda *a, **k: (ia_photo.noms_lumieres()["gauche"], True))
f.ia_lumiere()
titre, _a, (prompt, _s), kw = lances[-1]
textes = [n["inputs"].get("text", "") for n in prompt.values() if n["class_type"] == "CLIPTextEncode"]
verifier(titre == "Changer la lumière" and any("from the left" in t for t in textes),
         "Changer la lumière : consigne « lumière venant de la gauche »")
# flou selon la profondeur : la fenêtre de réglage s'ouvre, on l'accepte
from pixane.dialogues_reglage import DialogueReglage
doc.selection.fill(0)
vu = {}


def accepter():
    for d in QApplication.topLevelWidgets():
        if isinstance(d, DialogueReglage) and d.isVisible():
            d.grab().save(str(sortie / "profondeur.png"))
            vu["ok"] = True
            QTimer.singleShot(1500, d.accept)              # le temps de l'aperçu
            return
    QTimer.singleShot(50, accepter)


avant = tableau(doc.calques[0].image.convertToFormat(FORMAT_IMAGE))
QTimer.singleShot(100, accepter)
f.ia_flou_profondeur()
app.processEvents()
apres = tableau(doc.calques[0].image.convertToFormat(FORMAT_IMAGE))
verifier(vu.get("ok") and grain(apres, slice(20, 120), slice(20, 380)) < grain(avant, slice(20, 120), slice(20, 380)) * 0.7
         and np.array_equal(apres[200:240, 180:220], avant[200:240, 180:220]),
         "Flou selon la profondeur : le loin est flou, le sujet (le plus proche, choisi d'office) reste net")
verifier(f.historique.undoText() == "Flou selon la profondeur", "une étape « Flou selon la profondeur »")
p, _s = reponses["recette"]
verifier(p["11"]["class_type"] == "LoadDA3Model" and p["13"]["inputs"]["output"] == "depth"
         and p["22"]["class_type"] == "RemoveBackground" and len(_s) == 2,
         "recette : Depth Anything 3, sortie profondeur, et détourage du sujet dans le même calcul")
# modèle absent : message clair
recettes._profondeur["fichier"] = None
from PySide6.QtWidgets import QMessageBox
messages = []
QMessageBox.information = staticmethod(lambda *a, **k: messages.append(a[2]))
f.ia_flou_profondeur()
verifier(messages and "Depth Anything 3" in messages[-1], "modèle absent : message (installer le moteur IA)")

# 3. installation : case facultative
from pixane.installation_moteur import catalogue
verifier(any(e.cle == "profondeur" and e.licence == "Apache-2.0" for e in catalogue(True, False, False, True))
         and not any(e.cle == "profondeur" for e in catalogue(True)), "catalogue : Depth Anything 3 facultatif")
texte_iss = (Path(__file__).resolve().parents[1] / "installateur" / "Pixane.iss").read_text(encoding="utf-8-sig")
verifier("CaseProfondeur" in texte_iss and "--sans-profondeur" in texte_iss, "installateur : case « Flou de profondeur »")

print("ERREURS :", erreurs if erreurs else "aucune")
doc.modifie = False
sys.stdout.flush()
QTimer.singleShot(200, f.close)
app.exec()
sys.exit(1 if erreurs else 0)
