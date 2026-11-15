"""IA > Supprimer les personnes : recette SAM (une image par personne), choix de départ (pas le sujet principal),
fenêtre (cases, clic sur l'image), sélection agrandie puis Effacer ; aucune personne : message.
Le moteur n'est pas démarré : les masques sont fabriqués. Usage : essai_personnes.py dossier_sortie"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PIL import Image
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QApplication, QMessageBox
from pixane import recettes
from pixane.fenetre import Fenetre
from pixane.moteur import Moteur

Moteur.demarrer = lambda self, signaler=None: (_ for _ in ()).throw(Exception("moteur désactivé pour l'essai"))
Fenetre._moteur_en_echec = lambda self, *a: None
sortie = Path(sys.argv[1])
sortie.mkdir(parents=True, exist_ok=True)
Image.fromarray(np.full((300, 400, 3), 180, np.uint8)).save(sortie / "plage.png")
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


# 1. recette
recettes._sam["fichier"] = "sam3.1_multiplex_fp16.safetensors"
p, s = recettes.personnes("x.png")
verifier(p["12"]["inputs"]["individual_masks"] and p["15"]["inputs"]["text"].startswith("person:"),
         "recette : SAM 3.1, « person », un masque par personne (plusieurs détections)")

# 2. choix de départ et réunion
from pixane.choix_personnes import ChoixPersonnes, choix_depart, union
sujet = np.zeros((300, 400), bool)
sujet[40:300, 220:380] = True                     # grande personne au premier plan
loin1 = np.zeros((300, 400), bool)
loin1[120:200, 30:60] = True
loin2 = np.zeros((300, 400), bool)
loin2[130:190, 100:120] = True
verifier(choix_depart([loin1, sujet, loin2]) == [True, False, True], "au départ : le sujet principal n'est pas coché")
verifier(choix_depart([loin1, loin2]) == [True, True], "pas de personne nettement plus grande que les autres : toutes cochées")
u = union([loin1, sujet, loin2], [True, False, True], 4)
verifier(u[160, 45] == 255 and u[160, 26] > 0 and u[160, 200] == 0 and u[160, 300] == 0,
         "sélection : personnes cochées, agrandies de quelques pixels, pas le sujet")

# 3. fenêtre
app = QApplication(sys.argv)
f = Fenetre()
f.resize(1440, 920)
f.show()
f.charger(str(sortie / "plage.png"))
app.processEvents()
d = ChoixPersonnes(f.doc.image, [loin1, sujet, loin2], f)
verifier(d.coches() == [True, False, True] and d.liste.count() == 3, "fenêtre : une case par personne")
pm = d.apercu.pixmap()
d._clic(300 / 400, 150 / 300)
verifier(d.coches() == [True, True, True], "clic sur le sujet dans l'image : il est coché")
d._clic(300 / 400, 150 / 300)
d._clic(10 / 400, 10 / 300)
verifier(d.coches() == [True, False, True], "reclic : décoché ; clic à côté : rien ne change")
d._tout(False)
verifier(d.coches() == [False, False, False], "Tout décocher")
d._tout(True)
d.show()
app.processEvents()
d.grab().save(str(sortie / "fenetre_personnes.png"))
d.close()

# 4. dans Pixane
cartes = [np.where(m, 255, 0).astype(np.uint8) for m in (loin1, sujet, loin2)]
f.moteur.etat = "prêt"
f._carte_ia = lambda titre, fabriquer, suite, toutes=False, vide_ok=False: suite(cartes if toutes else cartes[0])
lances = []
f._lancer = lambda titre, avec, fabriquer, **kw: lances.append((titre, avec))
choix = {"mode": "effacer"}


def faux_exec(self):
    self._mode = choix["mode"]
    return True


ChoixPersonnes.exec = faux_exec
f.ia_supprimer_personnes()
from pixane.document import masque
sel = masque(f.doc.selection)
verifier(sel[160, 45] == 255 and sel[160, 110] == 255 and sel[160, 300] == 0,
         "les personnes cochées deviennent la sélection (pas le sujet)")
verifier(lances and lances[-1] == ("Effacer", True), "puis Effacer est lancé sur la sélection")
n = len(lances)
choix["mode"] = "selectionner"
f.ia_supprimer_personnes()
verifier(len(lances) == n and not f.doc.selection_vide(), "« Seulement sélectionner » : la sélection, sans Effacer")
f.historique.undo()
messages = []
QMessageBox.information = staticmethod(lambda *a, **k: messages.append(a[2]))
cartes = []
f.ia_supprimer_personnes()
verifier(messages and "Aucune personne" in messages[-1], "aucune personne trouvée : message")
verifier(f.a_ia_personnes.text().startswith("Supprimer les personnes"), "menu IA > Supprimer les personnes…")

print("ERREURS :", erreurs if erreurs else "aucune")
f.doc.modifie = False
sys.stdout.flush()
QTimer.singleShot(200, f.close)
app.exec()
sys.exit(1 if erreurs else 0)
