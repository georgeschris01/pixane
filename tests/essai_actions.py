"""Panneau Actions : enregistrer (réglages, filtres, taille, rotation), rejouer sur une autre image (une étape
d'Annuler), gardées au redémarrage, exporter / importer, et dans le Traitement par lot.
Usage : essai_actions.py dossier_sortie"""
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PIL import Image
from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import QApplication, QDialog
from pixane import actions_auto, ajustements, filtres
from pixane.fenetre import Fenetre
from pixane.moteur import Moteur

Moteur.demarrer = lambda self, signaler=None: (_ for _ in ()).throw(Exception("moteur désactivé pour l'essai"))
Fenetre._moteur_en_echec = lambda self, *a: None
sortie = Path(sys.argv[1])
sortie.mkdir(parents=True, exist_ok=True)
QSettings("Pixane", "Pixane-essais").remove("actions")
QSettings("Pixane", "Pixane-essais").remove("lot_action")
rng = np.random.default_rng(1)
img = (rng.random((120, 200, 3)) * 120 + 60).astype(np.uint8)
Image.fromarray(img).save(sortie / "a.png")
Image.fromarray(img[:100, :160]).save(sortie / "b.png")
lot = sortie / "lot"
lot.mkdir(exist_ok=True)
for k in range(2):
    Image.fromarray(img[:90 + 10 * k]).save(lot / f"photo{k}.png")
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


app = QApplication(sys.argv)
from pixane.dialogues_reglage import DialogueReglage
from pixane.document import FORMAT_IMAGE, tableau
f = Fenetre()
f.resize(1440, 920)
f.show()
f.charger(str(sortie / "a.png"))
app.processEvents()
pa = f.panneau_actions
verifier(hasattr(f, "dock_actions") and not pa.liste_actions, "panneau ACTIONS, vide au départ")

# 1. enregistrer
pa.commencer("Pochette")
verifier(pa.enregistre() and pa.b_stop.isEnabled() and not pa.b_enr.isEnabled(), "● Enregistrer : l'enregistrement commence")
DialogueReglage.exec = lambda self: QDialog.Accepted
vraies_valeurs = DialogueReglage.valeurs


def valeurs(self):
    p = vraies_valeurs(self)
    if "rvb" in p:                                    # Niveaux : blancs à 200 (comme si on avait tiré le curseur)
        p = dict(p, rvb=[0, 1.0, 200, 0, 255])
    return p


DialogueReglage.valeurs = valeurs
f.reglage("niveaux")
f.reglage("negatif")
f.filtre("flou")
from pixane.dialogues_image import TailleImage
TailleImage.exec = lambda self: True
TailleImage.valeurs = lambda self: (100, 60)
f.taille_image()
f._geometrie("Pivoter", 90)
pa.arreter()
a = pa.liste_actions[0]
verifier([e["genre"] for e in a["etapes"]] == ["reglage", "reglage", "filtre", "taille", "geometrie"],
         f"5 étapes enregistrées ({[actions_auto.nom_etape(e) for e in a['etapes']]})")
verifier(a["etapes"][3] == {"genre": "taille", "echelle": 0.5}, "taille gardée en proportion (50 %)")
resultat_a = tableau(f.doc.image)
verifier(f.doc.taille() == (60, 100), "l'image a bien été modifiée pendant l'enregistrement")
f.reglage("negatif")
verifier(len(pa.liste_actions[0]["etapes"]) == 5, "après « Arrêter » : plus rien ne s'enregistre")
verifier(actions_auto.charger()[0]["nom"] == "Pochette", "gardée dans les réglages (retrouvée au redémarrage)")

# 2. rejouer sur une autre image
f.charger(str(sortie / "b.png"))
app.processEvents()
pa.arbre.setCurrentItem(pa.arbre.topLevelItem(0))
n = f.historique.count()
pa.lancer()
verifier(f.doc.taille() == (50, 80) and f.historique.count() == n + 1,
         "▶ Jouer sur une image 160 × 100 : 50 %, pivotée (80 × 50 -> 50 × 80), une seule étape d'Annuler")
attendu = tableau(f.doc.image)
b = np.dstack([img[:100, :160], np.full((100, 160), 255, np.uint8)])
for e in a["etapes"]:
    b = actions_auto.appliquer_tableau(b, e)
verifier(b.shape[:2] == (80, 50) and np.abs(b.astype(int) - attendu.astype(int)).max() <= 3,
         "même résultat que le calcul du traitement par lot")
f.historique.undo()
verifier(f.doc.taille() == (160, 100), "Ctrl+Z : tout revient d'un coup")

# 3. exporter / importer
pa.exporter(str(sortie / "actions.json"))
d = json.loads((sortie / "actions.json").read_text(encoding="utf-8"))
verifier(d["actions"][0]["nom"] == "Pochette", "Exporter en .json")
pa.importer(str(sortie / "actions.json"))
verifier(len(pa.liste_actions) == 2 and pa.arbre.topLevelItemCount() == 2, "Importer")
pa.arbre.setCurrentItem(pa.arbre.topLevelItem(1))
pa.supprimer()
verifier(len(pa.liste_actions) == 1, "Supprimer une action")

# 4. traitement par lot
from pixane.export import DialogueLot, traiter_une
dl = DialogueLot(f)
verifier(dl.action.count() == 2 and dl.action.itemText(1) == "Pochette", "Traitement par lot : choix de l'action")
dl.action.setCurrentIndex(1)
opts = dl.options()
verifier(opts["action"]["nom"] == "Pochette", "l'action est dans les options du lot")
opts["format"] = "png"
cible = traiter_une(lot / "photo0.png", sortie / "lot_sortie", opts)
r = np.asarray(Image.open(cible))
verifier(r.shape[:2] == (100, 45), f"photo du lot 200 × 90 -> 50 % puis pivotée : 45 × 100 ({r.shape[1]} × {r.shape[0]})")
f.dock_actions.raise_()
pa.arbre.expandAll()
app.processEvents()
f.dock_actions.grab().save(str(sortie / "panneau_actions.png"))

# clic réel sur « ● Enregistrer » (Qt envoie un booléen à commencer : il ne doit pas être pris pour le nom)
from PySide6.QtWidgets import QInputDialog
QInputDialog.getText = staticmethod(lambda *a, **k: ("Par le bouton", True))
if pa.enregistre():
    pa.b_stop.click()
n = len(pa.liste_actions)
pa.b_enr.click()
app.processEvents()
verifier(len(pa.liste_actions) == n + 1 and pa.liste_actions[-1]["nom"] == "Par le bouton",
         "clic sur ● Enregistrer : le nom est demandé, l'action est créée")
pa.b_stop.click()
QSettings("Pixane", "Pixane-essais").remove("actions")

print("ERREURS :", erreurs if erreurs else "aucune")
for doc in list(getattr(f, "_docs", [])):
    doc.modifie = False
if f.doc:
    f.doc.modifie = False
sys.stdout.flush()
QTimer.singleShot(200, f.close)
app.exec()
sys.exit(1 if erreurs else 0)
