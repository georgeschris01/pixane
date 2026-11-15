"""Filtres > Fluidité : pousser, gonfler, contracter, tourbillon, reconstruire ; défaire ; application au calque.
Usage : essai_fluidite.py dossier_sortie   (une image d'essai est fabriquée ; le moteur n'est pas démarré)"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PIL import Image
from PySide6.QtCore import QEvent, QPointF, Qt, QTimer
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QDialog
from pixane import fluidite as fl
from pixane.fenetre import Fenetre
from pixane.moteur import Moteur

Moteur.demarrer = lambda self, signaler=None: (_ for _ in ()).throw(Exception("moteur désactivé pour l'essai"))
Fenetre._moteur_en_echec = lambda self, *a: None
sortie = Path(sys.argv[1])
sortie.mkdir(parents=True, exist_ok=True)
img = np.full((300, 400, 3), 230, np.uint8)
img[100:200, 150:250] = (200, 40, 40)             # carré rouge au milieu
Image.fromarray(img).save(sortie / "fluidite.png")
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


# 1. calcul seul
rgba = np.dstack([img, np.full(img.shape[:2], 255, np.uint8)])
champ = np.zeros((300, 400, 2), np.float32)
verifier(np.array_equal(fl.deformer(rgba, champ), rgba), "champ nul : image intacte")
for i in range(10):
    fl.touche(champ, fl.POUSSER, 250 + i * 3, 150, 40, 1.0, 3, 0)
r = fl.deformer(rgba, champ)
verifier(r[150, 262, 1] < 120, f"Pousser vers la droite : le rouge avance ({r[150, 262].tolist()})")
champ[:] = 0
for _ in range(15):
    fl.touche(champ, fl.GONFLER, 200, 150, 90, 1.0)
r = fl.deformer(rgba, champ)
verifier(r[150, 255, 1] < 120 and r[95, 200, 1] < 120, "Gonfler : le carré grossit")
champ[:] = 0
for _ in range(15):
    fl.touche(champ, fl.CONTRACTER, 200, 150, 90, 1.0)
r = fl.deformer(rgba, champ)
verifier(r[150, 245, 1] > 150, "Contracter : le carré rétrécit")
for _ in range(60):
    fl.touche(champ, fl.RECONSTRUIRE, 200, 150, 120, 1.0, origine=np.zeros_like(champ))
verifier(np.abs(champ[150, 200:250]).max() < 1, "Reconstruire : retour vers l'origine")
champ[:] = 0
for _ in range(10):
    fl.touche(champ, fl.TOURBILLON, 200, 150, 90, 1.0)
r = fl.deformer(rgba, champ)
verifier(not np.array_equal(r, rgba) and r[150, 200, 1] < 120, "Tourbillon : l'image tourne, le centre reste")
grand = fl.agrandir_champ(np.ones((10, 20, 2), np.float32), 40, 20)
verifier(grand.shape == (20, 40, 2) and abs(grand[5, 5, 0] - 2) < 1e-3 and abs(grand[5, 5, 1] - 2) < 1e-3,
         "champ agrandi : décalages mis à l'échelle")

# 2. dans Pixane
app = QApplication(sys.argv)
from pixane.document import FORMAT_IMAGE, tableau
f = Fenetre()
f.resize(1440, 920)
f.show()
f.charger(str(sortie / "fluidite.png"))
app.processEvents()
doc = f.doc
verifier(f.a_fluidite.isEnabled() and f.a_fluidite.shortcut().toString() == "Ctrl+Shift+X",
         "menu Filtres > Fluidité (Ctrl+Shift+X)")
avant = tableau(doc.calques[0].image.convertToFormat(FORMAT_IMAGE))
vu = {}


def geste():
    for d in QApplication.topLevelWidgets():
        if isinstance(d, fl.DialogueFluidite) and d.isVisible():
            vu["d"] = d
            a = d.apercu
            app.processEvents()

            def souris(type_, x, y):
                c = a._cadre()
                k = c.width() / d.travail.shape[1]
                p = QPointF(c.x() + x * k, c.y() + y * k)
                bouton = Qt.LeftButton if type_ != QEvent.MouseMove else Qt.NoButton
                boutons = Qt.NoButton if type_ == QEvent.MouseButtonRelease else Qt.LeftButton
                a.event(QMouseEvent(type_, p, p, bouton, boutons, Qt.NoModifier))
            d.taille.definir(120)
            souris(QEvent.MouseButtonPress, 240, 150)
            for i in range(1, 21):
                souris(QEvent.MouseMove, 240 + i * 2, 150)
            souris(QEvent.MouseButtonRelease, 280, 150)
            vu["gestes"] = len(d.annulations)
            d.commencer()
            d.champ[:] += 5
            d.defaire()
            vu["defait"] = len(d.annulations) == 1 and d.champ.any()
            d.grab().save(str(sortie / "fluidite_dialogue.png"))
            d.accept()
            return
    QTimer.singleShot(50, geste)


QTimer.singleShot(100, geste)
f.fluidite()
app.processEvents()
apres = tableau(doc.calques[0].image.convertToFormat(FORMAT_IMAGE))
verifier(vu.get("gestes") == 1 and vu.get("defait"), "un geste gardé ; « Défaire le dernier geste »")
verifier(apres[150, 262, 1] < 120 and avant[150, 262, 1] > 200,
         f"appliqué au calque en pleine définition ({apres[150, 262].tolist()})")
verifier(f.historique.undoText() == "Fluidité", "une étape « Fluidité » dans Annuler")
f.historique.undo()
verifier(np.array_equal(tableau(doc.calques[0].image.convertToFormat(FORMAT_IMAGE)), avant), "annulé")

print("ERREURS :", erreurs if erreurs else "aucune")
doc.modifie = False
sys.stdout.flush()
QTimer.singleShot(200, f.close)
app.exec()
sys.exit(1 if erreurs else 0)
