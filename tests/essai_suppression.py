"""Pinceau Supprimer (J). Le moteur est simulé : il renvoie le morceau reçu, zone à refaire peinte en vert.
Avec --vrai : vrai moteur (LaMa), sur une image fabriquée (fil noir sur un dégradé).
Usage : essai_suppression.py dossier_sortie [--vrai]"""
import io
import os
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PIL import Image
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QMessageBox
from pixane.canevas import SUPPRIMER
from pixane.document import FORMAT_IMAGE, tableau
from pixane.fenetre import Fenetre
from pixane.moteur import Moteur

VRAI = "--vrai" in sys.argv
if not VRAI:
    Moteur.demarrer = lambda self, signaler=None: (_ for _ in ()).throw(Exception("moteur désactivé pour l'essai"))
Fenetre._moteur_en_echec = lambda self, *a: None
messages = []
QMessageBox.information = lambda *a, **k: messages.append(a[2] if len(a) > 2 else "") or QMessageBox.Ok
QMessageBox.warning = lambda *a, **k: messages.append(a[2] if len(a) > 2 else "") or QMessageBox.Ok
sortie = Path(sys.argv[1])
sortie.mkdir(parents=True, exist_ok=True)
H, W = 700, 1000
yy, xx = np.mgrid[0:H, 0:W]
img = np.dstack([90 + xx * 100 // W, 140 + yy * 60 // H, np.full((H, W), 200)]).astype(np.uint8)
img[150:350, 498:504] = (20, 20, 20)                 # rayure à enlever (entièrement peinte)
img[480:690, 498:504] = (20, 20, 20)                 # autre rayure, non peinte au 1er trait
Image.fromarray(img).save(sortie / "fil.png")
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


app = QApplication(sys.argv)
f = Fenetre()
f.resize(1440, 920)
f.show()
f.charger(str(sortie / "fil.png"))
app.processEvents()
c = f.canevas
envois = []

if not VRAI:
    def faux_envoi(png):
        envois.append(Image.open(io.BytesIO(png)))
        return "essai.png"

    def faux_calcul(prompt, sorties, annuler, progres):
        im = envois[-1]
        a = np.asarray(im)
        rgb = a[:, :, :3].copy()
        rgb[a[:, :, 3] < 128] = (0, 255, 0)
        buf = io.BytesIO()
        Image.fromarray(rgb).save(buf, "PNG")
        return [("LaMa", buf.getvalue())]
    f.moteur.envoyer_image = faux_envoi
    f.moteur.executer = faux_calcul
    f.moteur.etat = "prêt"
else:
    for _ in range(600):
        app.processEvents()
        if f.moteur.etat == "prêt":
            break
        time.sleep(0.2)
    verifier(f.moteur.etat == "prêt", "moteur prêt")


def attendre():
    for _ in range(1500):
        app.processEvents()
        if not f.suppression._occupe:
            break
        time.sleep(0.01)
    app.processEvents()


def trait(points):
    ecran = [c.vers_ecran(QPointF(*p)) for p in points]
    c.event(QMouseEvent(QEvent.MouseButtonPress, ecran[0], ecran[0], Qt.LeftButton, Qt.LeftButton, Qt.NoModifier))
    for e in ecran[1:]:
        c.event(QMouseEvent(QEvent.MouseMove, e, e, Qt.NoButton, Qt.LeftButton, Qt.NoModifier))
    c.event(QMouseEvent(QEvent.MouseButtonRelease, ecran[-1], ecran[-1], Qt.LeftButton, Qt.NoButton, Qt.NoModifier))


f._choisir_outil(SUPPRIMER)
c.definir_taille(24) if hasattr(c, "definir_taille") else None
c.taille_pinceau = 24
# option « nouveau calque » décochée (par défaut) : directement dans le calque choisi, comme Effacer / Ajouter
f.a_ia_nouveau_calque.setChecked(False)
nb = f.historique.count()
trait([(501, 100), (501, 250), (501, 400)])
attendre()
d0 = tableau(f.doc.calques[0].image.convertToFormat(FORMAT_IMAGE))[:, :, :3]
verifier(len(f.doc.calques) == 1 and f.historique.count() == nb + 1 and (d0 != img).any()
         and (d0[:, :300] == img[:, :300]).all(), "trait : fait directement dans le calque choisi, une étape")
if not VRAI:
    verifier(d0[250, 501, 1] == 255 and d0[250, 470, 1] != 255, "calque choisi : la zone peinte est refaite, pas à côté")
f.historique.undo()
verifier(len(f.doc.calques) == 1 and (tableau(f.doc.calques[0].image.convertToFormat(FORMAT_IMAGE))[:, :, :3]
                                       == img).all(), "Ctrl+Z : la photo revient telle quelle")
# option cochée : calque « Suppressions »
f.a_ia_nouveau_calque.setChecked(True)
nb = f.historique.index()
t = time.time()
trait([(501, 100), (501, 250), (501, 400)])
attendre()
duree = time.time() - t
verifier(len(f.doc.calques) == 2 and f.doc.calques[1].nom.startswith("Suppressions"),
         f"option nouveau calque : calque « {f.doc.calques[-1].nom} » ajouté ({duree:.1f} s)")
verifier((tableau(f.doc.calques[0].image.convertToFormat(FORMAT_IMAGE))[:, :, :3] == img).all()
         and f.historique.index() == nb + 1, "photo d'origine intacte, une étape dans Annuler")
r = tableau(f.doc.image.convertToFormat(FORMAT_IMAGE))
if VRAI:
    Image.fromarray(r[60:440, 440:560, :3]).resize((360, 1140), Image.NEAREST).save(sortie / "zoom_fil.png")
    Image.fromarray(tableau(f.doc.calques[1].image.convertToFormat(FORMAT_IMAGE))[60:440, 440:560]).resize(
        (360, 1140), Image.NEAREST).save(sortie / "zoom_calque.png")
    print("valeurs au centre du fil :", r[250, 495:508, :3].max(axis=1))
    fil_restant = int((r[140:360, 495:507, :3].max(axis=2) < 60).sum())
    verifier(fil_restant == 0, f"LaMa : la rayure peinte a disparu ({fil_restant} pixels sombres restants)")
    verifier((r[500:670, 498:504, :3].max(axis=2) < 60).all(), "la rayure non peinte reste")
else:
    verifier(r[250, 501, 1] == 255 and r[250, 470, 1] != 255, "la zone peinte est refaite, pas à côté")
    verifier(envois and max(envois[-1].size) <= 1536 and envois[-1].size[0] < W, f"morceau envoyé : {envois[-1].size}")
trait([(501, 450), (501, 650)])
attendre()
verifier(len(f.doc.calques) == 2, "2e trait : même calque « Suppressions » réutilisé")
f.historique.undo()
verifier(len(f.doc.calques) == 2 and f.historique.index() == nb + 1, "Ctrl+Z annule le 2e trait seul")
f.a_ia_nouveau_calque.setChecked(False)
f.grab().save(str(sortie / ("suppression_vraie.png" if VRAI else "suppression.png")))
if not VRAI:
    f.moteur.etat = "arrêté"
    trait([(100, 100), (150, 120)])
    attendre()
    verifier(messages and "moteur" in messages[-1].lower(), "moteur pas prêt : message clair")
print("ERREURS :", erreurs if erreurs else "aucune")
sys.stdout.flush()
f.doc.modifie = False
f.close()
os._exit(1 if erreurs else 0)
