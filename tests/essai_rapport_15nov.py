"""Corrections du 15/11 : Négatif et Postérisation (Image > Réglages) changent l'image dès l'ouverture de la fenêtre ;
boutons du panneau Calques plus grands (deux rangées) ; Pinceau d'historique facile à trouver.
Usage : essai_rapport_15nov.py dossier_sortie"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PIL import Image
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from pixane.fenetre import BoutonFamille, Fenetre
from pixane.moteur import Moteur

Moteur.demarrer = lambda self, signaler=None: (_ for _ in ()).throw(Exception("moteur désactivé pour l'essai"))
Fenetre._moteur_en_echec = lambda self, *a: None
sortie = Path(sys.argv[1])
sortie.mkdir(parents=True, exist_ok=True)
h, w = 120, 160
img = np.zeros((h, w, 3), np.uint8)
img[..., 0] = np.linspace(0, 255, w)[None, :]
img[..., 1] = np.linspace(0, 255, h)[:, None]
img[..., 2] = 90
Image.fromarray(img).save(sortie / "degrade.png")
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
f.charger(str(sortie / "degrade.png"))
app.processEvents()
doc = f.doc
pix = lambda: tableau(doc.calques[0].image.convertToFormat(FORMAT_IMAGE))[..., :3].astype(int)


def ouvrir(type_, nom_capture):
    """Ouvre Image > Réglages > type_, regarde l'aperçu sans toucher aux curseurs, puis valide."""
    vu = {}

    def regarder():
        for d in QApplication.topLevelWidgets():
            if isinstance(d, DialogueReglage) and d.isVisible():
                def plus_tard():
                    vu["apercu"] = pix()                    # l'aperçu en direct est posé sur le calque
                    f.grab().save(str(sortie / nom_capture))
                    d.accept()
                QTimer.singleShot(1500, plus_tard)
                return
        QTimer.singleShot(50, regarder)

    QTimer.singleShot(100, regarder)
    f.reglage(type_)
    app.processEvents()
    return vu.get("apercu"), pix()


depart = pix()
apercu, final = ouvrir("negatif", "negatif.png")
verifier(apercu is not None and np.abs(apercu - (255 - depart)).max() <= 1, "Négatif : l'aperçu est en négatif dès l'ouverture")
verifier(np.abs(final - (255 - depart)).max() <= 1, "Négatif : après OK, l'image est en négatif")
verifier(f.historique.count() >= 1, "Négatif : une étape dans l'historique")
f.historique.undo()
verifier(np.array_equal(pix(), depart), "Annuler : l'image revient")
apercu, final = ouvrir("posterisation", "posterisation.png")
n = len(np.unique(final[..., 0]))
verifier(apercu is not None and len(np.unique(apercu[..., 0])) < 20, "Postérisation : l'aperçu a peu de niveaux dès l'ouverture")
verifier(n < 20, f"Postérisation : après OK, peu de niveaux ({n} au lieu de {len(np.unique(depart[..., 0]))})")
f.historique.undo()

# panneau Calques : deux rangées de boutons à leur taille normale (plus tassés)
b = f.calques.boutons
verifier(all(x.width() >= x.sizeHint().width() for x in b.values()), "boutons du panneau Calques à leur taille (pas tassés)")
verifier(all(x.iconSize().width() >= 22 for x in b.values()), "icônes des boutons du panneau Calques : 22 px")
verifier(b["calque_nouveau"].y() != b["supprimer"].y(), "boutons du panneau Calques sur deux rangées")
r = b["calque_nouveau"].geometry().united(b["supprimer"].geometry()).united(b["style"].geometry())
b["calque_nouveau"].parentWidget().grab(r.adjusted(-4, -4, 4, 4)).save(str(sortie / "boutons_calques.png"))

# Pinceau d'historique : triangle sur les familles, bouton dans le panneau Historique
from pixane.canevas import HISTORIQUE
verifier(isinstance(f._bouton_groupe[HISTORIQUE], BoutonFamille), "famille du Tampon : bouton avec le triangle « autres outils »")
f.bouton_pinceau_historique.click()
verifier(f.canevas.outil == HISTORIQUE, "bouton « Pinceau d'historique » du panneau Historique : choisit l'outil")
f.dock_historique.raise_()
app.processEvents()
f.grab().save(str(sortie / "historique.png"))

print("ERREURS :", erreurs if erreurs else "aucune")
doc.modifie = False
sys.stdout.flush()
QTimer.singleShot(200, f.close)
app.exec()
sys.exit(1 if erreurs else 0)
