"""Onglets (plusieurs photos, un historique chacune) et récupération après plantage. Moteur non démarré.
Usage : essai_onglets.py dossier_sortie image1 image2"""
import json
import os
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["CHRYPIX_REGLAGES"] = "Chrypix-essais"
from PySide6.QtWidgets import QApplication, QMessageBox

from chrypix.fenetre import Fenetre
from chrypix.moteur import Moteur

Moteur.demarrer = lambda self, signaler=None: None
Fenetre._moteur_en_echec = lambda self, *a: None
QMessageBox.question = lambda *a, **k: QMessageBox.Discard
sortie = Path(sys.argv[1])
sortie.mkdir(parents=True, exist_ok=True)
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


app = QApplication(sys.argv)
f = Fenetre()
f.resize(1440, 920)
f.show()
f.charger(sys.argv[2])
d1 = f.doc
verifier(not f.barre_onglets.isVisible(), "une seule photo : pas de barre d'onglets")
f.charger(sys.argv[3])
d2 = f.doc
app.processEvents()
verifier(d2 is not d1 and len(f.documents) == 2 and f.barre_onglets.isVisible() and f.barre_onglets.count() == 2,
         "deux photos : deux onglets")
f.calques.nouveau()
f.calques.nouveau()
verifier(f.historique.count() == 2 and len(d2.calques) == 3, "2e photo : deux étapes dans son historique")
f.barre_onglets.setCurrentIndex(0)
app.processEvents()
verifier(f.doc is d1 and f.historique.count() == 0 and f.canevas.doc is d1 and f.calques.doc is d1,
         "retour à la 1re photo : son historique (vide), son canevas, ses calques")
f.a_annuler.trigger()
verifier(len(d2.calques) == 3, "Ctrl+Z sur la 1re photo ne touche pas la 2e")
f.charger(sys.argv[3])
verifier(len(f.documents) == 2 and f.doc is d2, "rouvrir une photo déjà ouverte : retour à son onglet")
verifier("•" in f.barre_onglets.tabText(1), f"onglet modifié marqué : {f.barre_onglets.tabText(1)}")

# ------------------------------------------------------------ récupération
r = f._recuperation
for p in r.dossier.glob("*"):
    p.unlink()
ecrits = []
r.ecrit.connect(ecrits.append)
r.copier()
for _ in range(300):
    app.processEvents()
    if ecrits:
        break
    time.sleep(0.02)
verifier(len(ecrits) == 1 and Path(ecrits[0]).is_file(), "copie automatique de la photo modifiée (seulement elle)")
r.copier()
time.sleep(0.3)
app.processEvents()
verifier(len(ecrits) == 1, "rien de changé depuis : pas de nouvelle copie")
verifier(r.restes() == [], "copie d'un Chrypix encore ouvert : pas proposée")
j = Path(ecrits[0]).with_suffix(".json")
infos = json.loads(j.read_text(encoding="utf-8"))
infos["pid"] = 999999                        # comme si ce Chrypix avait planté
j.write_text(json.dumps(infos), encoding="utf-8")
restes = r.restes()
verifier(len(restes) == 1, "après un plantage : la copie est proposée")
r.rouvrir(*restes[0])
d3 = f.doc
verifier(d3 not in (d1, d2) and len(d3.calques) == 3 and d3.modifie and d3.chemin == d2.chemin,
         "photo récupérée : ses calques, à enregistrer, même fichier d'origine")
f.fermer_onglet()
verifier(len(f.documents) == 2, "fermer la photo récupérée (sans enregistrer)")
r.tout_effacer()
verifier(not list(r.dossier.glob(f"{os.getpid()}-*")), "fermeture normale : copies effacées")
f.fermer_onglet()
f.fermer_onglet()
verifier(f.doc is None and not f.documents and not f.a_enregistrer.isEnabled(), "toutes fermées : fenêtre vide")
f.grab().save(str(sortie / "onglets_vide.png"))
print("ERREURS :", erreurs if erreurs else "aucune")
sys.stdout.flush()
f.close()
os._exit(1 if erreurs else 0)
