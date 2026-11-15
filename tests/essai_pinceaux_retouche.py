"""Pinceaux de retouche : Densité − / +, Éponge, Goutte d'eau, Netteté, Doigt, Pinceau d'historique (instantané).
Usage : essai_pinceaux_retouche.py dossier_sortie   (une image d'essai est fabriquée ; le moteur n'est pas démarré)"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PIL import Image
from PySide6.QtCore import QEvent, QPointF, Qt, QTimer
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication
from pixane.canevas import (DENSITE_MOINS, DENSITE_PLUS, DOIGT, EPONGE, GOUTTE, HISTORIQUE, NETTETE_PINCEAU, PEINTURE)
from pixane.fenetre import Fenetre
from pixane.moteur import Moteur

Moteur.demarrer = lambda self, signaler=None: (_ for _ in ()).throw(Exception("moteur désactivé pour l'essai"))
Fenetre._moteur_en_echec = lambda self, *a: None
sortie = Path(sys.argv[1])
sortie.mkdir(parents=True, exist_ok=True)
img = np.zeros((300, 400, 3), np.uint8)
img[:, :200] = (150, 90, 70)                      # gauche : brun moyen
img[:, 200:] = (40, 160, 60)                      # droite : vert
rng = np.random.default_rng(1)
img[200:, :] = np.clip(img[200:, :].astype(int) + rng.integers(-40, 40, (100, 400, 1)), 0, 255)   # bas : grain
Image.fromarray(img).save(sortie / "retouche.png")

app = QApplication(sys.argv)
from pixane.document import FORMAT_IMAGE, tableau
f = Fenetre()
f.resize(1440, 920)
f.show()
f.charger(str(sortie / "retouche.png"))
app.processEvents()
doc, c = f.doc, f.canevas
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


def souris(type_, x, y, mods=Qt.NoModifier):
    e = c.vers_ecran(QPointF(x, y))
    bouton = Qt.LeftButton if type_ != QEvent.MouseMove else Qt.NoButton
    boutons = Qt.NoButton if type_ == QEvent.MouseButtonRelease else Qt.LeftButton
    c.event(QMouseEvent(type_, e, e, bouton, boutons, mods))


def trait(x0, y0, x1, y1, n=12):
    souris(QEvent.MouseButtonPress, x0, y0)
    for k in range(1, n + 1):
        souris(QEvent.MouseMove, x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n)
    souris(QEvent.MouseButtonRelease, x1, y1)
    app.processEvents()


def px():
    return tableau(doc.calques[0].image.convertToFormat(FORMAT_IMAGE))[..., :3].astype(int)


def lum(a):
    return a @ np.array([0.299, 0.587, 0.114])


def outil(o, taille=40, force=60):
    f._choisir_outil(o)
    f.opt_opacite.setValue(force)
    f.valeur_taille.setValue(taille)
    app.processEvents()


avant = px()
# 1. barre d'outils et options
verifier(all(o in f._actions_outils for o in (DENSITE_MOINS, DENSITE_PLUS, EPONGE, GOUTTE, NETTETE_PINCEAU, DOIGT,
                                              HISTORIQUE)), "7 nouveaux outils dans la barre")
outil(DENSITE_MOINS)
verifier(f.opt_densite.isVisible() and f.etiquette_opacite.text() == "Force" and not f.opt_eponge.isVisible(),
         "Densité − : liste des tons, « Force »")
trait(50, 100, 150, 100)
p = px()
verifier(lum(p[100, 100]) > lum(avant[100, 100]) + 15 and np.array_equal(p[30, 100], avant[30, 100]),
         f"Densité − : éclaircit sous le pinceau seulement ({p[100, 100].tolist()})")
verifier(f.historique.undoText() == "Densité −", "une étape « Densité − » dans Annuler")
f.historique.undo()
f.opt_gamme.setCurrentIndex(0)                    # ombres : le vert clair à droite bouge peu
outil(DENSITE_PLUS)
trait(250, 100, 350, 100)
p = px()
verifier(lum(p[100, 300]) < lum(avant[100, 300]) - 5, f"Densité + : assombrit ({p[100, 300].tolist()})")
f.historique.undo()
outil(EPONGE)
verifier(f.opt_eponge.isVisible() and not f.opt_densite.isVisible(), "Éponge : liste Désaturer / Saturer")
trait(250, 100, 350, 100)
p = px()
sat = lambda v: v.max() - v.min()
verifier(sat(p[100, 300]) < sat(avant[100, 300]) - 30, f"Éponge (désaturer) : couleur ternie ({p[100, 300].tolist()})")
f.historique.undo()
f.opt_mode_eponge.setCurrentIndex(1)
trait(50, 100, 150, 100)
p = px()
verifier(sat(p[100, 100]) > sat(avant[100, 100]) + 20, f"Éponge (saturer) : couleur ravivée ({p[100, 100].tolist()})")
f.historique.undo()
outil(GOUTTE, taille=60, force=100)
trait(150, 250, 250, 250)
p = px()
grain = lambda a: a[235:265, 160:195, 0].std()     # zone unie, une couleur (sans la limite brun / vert)
verifier(grain(p) < grain(avant) * 0.7, f"Goutte d'eau : grain adouci ({grain(avant):.1f} -> {grain(p):.1f})")
f.historique.undo()
outil(NETTETE_PINCEAU, taille=60, force=100)
trait(150, 250, 250, 250)
p = px()
verifier(grain(p) > grain(avant) * 1.15, f"Netteté : détails renforcés ({grain(avant):.1f} -> {grain(p):.1f})")
f.historique.undo()
outil(DOIGT, taille=30, force=80)
trait(150, 100, 260, 100, n=30)
p = px()
verifier(p[100, 215, 0] > avant[100, 215, 0] + 30, f"Doigt : le brun est étalé sur le vert ({p[100, 215].tolist()})")
verifier(np.array_equal(p[30, 215], avant[30, 215]), "Doigt : rien ailleurs")
f.historique.undo()
verifier(np.array_equal(px(), avant), "tout annulé : photo d'origine")

# 2. pinceau d'historique
outil(PEINTURE, taille=60, force=100)
trait(50, 150, 350, 150)
peint = px()
verifier(not np.array_equal(peint[150, 100], avant[150, 100]), "trait de pinceau de couleur")
outil(HISTORIQUE, taille=40, force=100)
verifier(f.opt_historique.isVisible(), "Historique : bouton « Prendre un instantané »")
trait(80, 150, 120, 150)
p = px()
verifier(np.abs(p[150, 100] - avant[150, 100]).max() <= 2 and np.array_equal(p[150, 300], peint[150, 300]),
         "Historique : la photo d'origine revient sous le pinceau seulement")
f.prendre_instantane()
outil(PEINTURE, taille=20, force=100)
trait(290, 60, 310, 60)
outil(HISTORIQUE, taille=40, force=100)
trait(280, 60, 320, 60)
trait(280, 150, 320, 150)
p = px()
verifier(np.abs(p[60, 300] - avant[60, 300]).max() <= 2, "après l'instantané : le nouveau trait s'efface")
verifier(np.array_equal(p[150, 300], peint[150, 300]), "après l'instantané : l'ancien trait reste (il y était)")

# 3. goutte d'eau sur un masque
doc.appliquer_etat(doc.etat_ajouter_masque("blanc"))
doc.cible_masque = True
from pixane.composition import masque_tableau
m = masque_tableau(doc.calques[0].masque).copy()
m[:, :200] = 0
from pixane.composition import argb_vers_masque
from PySide6.QtGui import QImage
q = QImage(m.data, m.shape[1], m.shape[0], m.shape[1], QImage.Format_Grayscale8).copy()
from dataclasses import replace
cal = list(doc.calques)
cal[0] = replace(cal[0], masque=q)
doc.appliquer_etat(doc.etat_avec(tuple(cal), 0, doc.selection))
doc.cible_masque = True
outil(GOUTTE, taille=40, force=100)
trait(200, 50, 200, 150)
m2 = masque_tableau(doc.calques[0].masque)
verifier(0 < m2[100, 196] < 255 and 0 < m2[100, 204] < 255, f"Goutte d'eau sur le masque : bord adouci ({m2[100, 190:210:4].tolist()})")
doc.cible_masque = False

print("ERREURS :", erreurs if erreurs else "aucune")
doc.modifie = False
QTimer.singleShot(200, f.close)
app.exec()
os._exit(1 if erreurs else 0)
