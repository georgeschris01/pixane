"""Outil Déplacer aux flèches : 1 px, Maj 10 px, touche tenue = une étape dans Annuler, texte (reste un texte),
calque verrouillé refusé, flèches gardées par l'image après un clic dans le panneau Calques, cadre de
transformation poussé. Moteur non démarré. Usage : essai_fleches.py dossier_sortie"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PIL import Image
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QColor, QImage, QKeyEvent, QPainter
from PySide6.QtWidgets import QApplication

from pixane.canevas import DEPLACER
from pixane.document import FORMAT_IMAGE, tableau
from pixane.fenetre import CommandeEtat, Fenetre
from pixane.moteur import Moteur
from pixane.texte import Texte

Moteur.demarrer = lambda self, signaler=None: None
Fenetre._moteur_en_echec = lambda self, *a: None
sortie = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("sortie_fleches")
sortie.mkdir(parents=True, exist_ok=True)
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


Image.fromarray(np.full((300, 400, 3), 40, np.uint8)).save(sortie / "fond.png")
app = QApplication(sys.argv)
f = Fenetre()
f.resize(1200, 800)
f.show()
f.charger(str(sortie / "fond.png"))
app.processEvents()
c, doc = f.canevas, f.doc
img = QImage(400, 300, QImage.Format_ARGB32_Premultiplied)
img.fill(Qt.transparent)
p = QPainter(img)
p.fillRect(100, 100, 50, 40, QColor(255, 0, 0))
p.end()
f.historique.push(CommandeEtat(doc, doc.etat(), doc.etat_nouveau_calque(img, "Carré"), "Nouveau calque"))
app.processEvents()
i_carre = doc.actif


def touche(k, maj=False, repete=False, lacher=True):
    mods = Qt.ShiftModifier if maj else Qt.NoModifier
    c.keyPressEvent(QKeyEvent(QEvent.KeyPress, k, mods, "", repete))
    if lacher:
        c.keyReleaseEvent(QKeyEvent(QEvent.KeyRelease, k, mods, "", False))
    app.processEvents()


def coin():
    a = tableau(doc.calques[i_carre].image.convertToFormat(FORMAT_IMAGE))[:, :, 3]
    ys, xs = np.nonzero(a)
    return int(xs.min()), int(ys.min())


f._choisir_outil(DEPLACER)
n0 = f.historique.count()
touche(Qt.Key_Right)
verifier(coin() == (101, 100), f"→ : 1 px ({coin()})")
verifier(f.historique.count() == n0 + 1, "une étape dans Annuler")
touche(Qt.Key_Down, maj=True)
verifier(coin() == (101, 110), f"Maj+↓ : 10 px ({coin()})")
n1 = f.historique.count()
touche(Qt.Key_Left, lacher=False)                       # touche tenue : répétitions
for _ in range(4):
    touche(Qt.Key_Left, repete=True, lacher=False)
c.keyReleaseEvent(QKeyEvent(QEvent.KeyRelease, Qt.Key_Left, Qt.NoModifier, "", False))
app.processEvents()
verifier(coin() == (96, 110) and f.historique.count() == n1 + 1, f"← tenue (5 fois) : une seule étape ({coin()})")
f.historique.undo()
app.processEvents()
verifier(coin() == (101, 110), f"Ctrl+Z : revient d'un coup ({coin()})")
# déplacé hors de la feuille puis revenu : rien n'est coupé
for _ in range(15):
    touche(Qt.Key_Left, maj=True)
for _ in range(15):
    touche(Qt.Key_Right, maj=True)
verifier(coin() == (101, 110), "sorti de la feuille puis revenu : le carré est entier")
a = tableau(doc.calques[i_carre].image.convertToFormat(FORMAT_IMAGE))[:, :, 3]
verifier(int((a > 0).sum()) == 50 * 40, "rien n'est coupé")
# clic dans le panneau Calques : les flèches restent à l'image
verifier(f.calques.liste.focusPolicy() == Qt.NoFocus,
         "la liste des calques ne prend pas les flèches")
# verrouillé
from dataclasses import replace
doc.calques = tuple(replace(k, verrou=True) if i == i_carre else k for i, k in enumerate(doc.calques))
n2 = f.historique.count()
touche(Qt.Key_Right)
verifier(coin() == (101, 110) and f.historique.count() == n2, "calque verrouillé : ne bouge pas")
doc.calques = tuple(replace(k, verrou=False) if i == i_carre else k for i, k in enumerate(doc.calques))
# texte
f.historique.push(CommandeEtat(doc, doc.etat(), doc.etat_nouveau_texte(Texte(texte="AB", taille=60, x=200, y=150)),
                               "Nouveau texte"))
app.processEvents()
i_t = doc.actif
touche(Qt.Key_Up, maj=True)
t = doc.calques[i_t].texte
verifier(t is not None and round(t.x) == 200 and round(t.y) == 140, f"texte poussé, reste un texte ({t.x}, {t.y})")
# cadre de transformation
doc.actif = i_carre
f.transformer()
app.processEvents()
if c.transfo is not None:
    x0 = c.transfo.centre.x()
    touche(Qt.Key_Right, maj=True)
    verifier(abs(c.transfo.centre.x() - x0 - 10) < 1e-6, "cadre de transformation poussé de 10 px")
    c.transfo_annule.emit()
else:
    verifier(False, "Transformer ouvert")
f.grab().save(str(sortie / "fleches.png"))

print()
print("ÉCHECS :" if erreurs else "Tout est bon.", *erreurs, sep="\n  ")
for dd in f.documents:
    dd.modifie = False
sys.stdout.flush()
sys.exit(1 if erreurs else 0)
