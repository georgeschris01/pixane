"""Tous les réglages (Image > Réglages), tous les filtres (Filtres) et tous les calques de réglage : la fenêtre
s'ouvre, l'aperçu change la photo dès l'ouverture quand les valeurs de départ ne sont pas neutres, et OK applique.
(Le 15/11, Négatif et Postérisation s'ouvraient sans rien changer.)
Usage : essai_tous_reglages.py dossier_sortie"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PIL import Image
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from pixane import ajustements, filtres
from pixane.fenetre import Fenetre
from pixane.moteur import Moteur

Moteur.demarrer = lambda self, signaler=None: (_ for _ in ()).throw(Exception("moteur désactivé pour l'essai"))
Fenetre._moteur_en_echec = lambda self, *a: None
sortie = Path(sys.argv[1])
sortie.mkdir(parents=True, exist_ok=True)
h, w = 120, 160
rng = np.random.default_rng(5)
img = np.zeros((h, w, 3), np.uint8)
img[..., 0] = np.linspace(20, 235, w)[None, :]
img[..., 1] = np.linspace(30, 220, h)[:, None]
img[..., 2] = 120
img[40:80, 50:110] = (200, 60, 60)
img = np.clip(img.astype(int) + rng.integers(-12, 12, (h, w, 3)), 0, 255).astype(np.uint8)
Image.fromarray(img).save(sortie / "photo.png")
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


app = QApplication(sys.argv)
from pixane.composition import fusionner
from pixane.dialogues_reglage import DialogueReglage
from pixane.document import FORMAT_IMAGE, tableau
f = Fenetre()
f.resize(1440, 920)
f.show()
f.charger(str(sortie / "photo.png"))
app.processEvents()
doc = f.doc
pixels = lambda: tableau(doc.calques[0].image.convertToFormat(FORMAT_IMAGE))[..., :3].astype(int)
vue = lambda: tableau(fusionner(doc.calques, w, h).convertToFormat(FORMAT_IMAGE))[..., :3].astype(int)


def ouvrir(lancer, lire):
    """Lance la fenêtre, lit l'image pendant l'aperçu (sans toucher aux réglages), puis OK."""
    vu = {}

    def regarder():
        for d in QApplication.topLevelWidgets():
            if isinstance(d, DialogueReglage) and d.isVisible():
                def plus_tard():
                    vu["apercu"] = lire()
                    d.accept()
                QTimer.singleShot(1200, plus_tard)
                return
        QTimer.singleShot(50, regarder)

    QTimer.singleShot(100, regarder)
    lancer()
    app.processEvents()
    return vu.get("apercu"), lire()


depart = pixels()
for type_ in ajustements.TYPES:
    neutre = ajustements.neutre(type_, ajustements.defaut(type_))
    apercu, final = ouvrir(lambda: f.reglage(type_), pixels)
    change_apercu = apercu is not None and not np.array_equal(apercu, depart)
    change_final = not np.array_equal(final, depart)
    if neutre:
        verifier(apercu is not None and not change_final, f"réglage {type_} : neutre au départ, rien ne change")
    else:
        verifier(change_apercu and change_final and np.array_equal(apercu, final),
                 f"réglage {type_} : l'aperçu change dès l'ouverture, OK applique le même résultat")
        f.historique.undo()
    verifier(np.array_equal(pixels(), depart), f"réglage {type_} : la photo est revenue (Annuler)")

for type_ in filtres.FILTRES:
    apercu, final = ouvrir(lambda: f.filtre(type_), pixels)
    verifier(apercu is not None and not np.array_equal(apercu, depart) and np.array_equal(apercu, final),
             f"filtre {type_} : l'aperçu change dès l'ouverture, OK applique le même résultat")
    f.historique.undo()
    verifier(np.array_equal(pixels(), depart), f"filtre {type_} : Annuler")

for type_ in ajustements.TYPES:
    neutre = ajustements.neutre(type_, ajustements.defaut(type_))
    n = len(doc.calques)
    apercu, final = ouvrir(lambda: f.nouveau_calque_reglage(type_), vue)
    verifier(len(doc.calques) == n + 1 and doc.calques[-1].reglage is not None,
             f"calque de réglage {type_} : ajouté")
    if not neutre:
        verifier(apercu is not None and not np.array_equal(final, depart),
                 f"calque de réglage {type_} : l'image vue change dès l'ouverture et après OK")
    f.historique.undo()
    verifier(len(doc.calques) == n and np.array_equal(vue(), depart), f"calque de réglage {type_} : Annuler")

print("ERREURS :", erreurs if erreurs else "aucune")
doc.modifie = False
sys.stdout.flush()
QTimer.singleShot(200, f.close)
app.exec()
sys.exit(1 if erreurs else 0)
