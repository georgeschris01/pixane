"""Effacer / Remplir sur des trous transparents (texte coupé d'une pochette : ses lettres laissent des trous) : l'IA
les remplit, opaques, dans la fenêtre de choix comme dans le calque. Le transparent qui continue hors de la
sélection (autour de la pochette) reste transparent. Les autres actions (Netteté…) ne remplissent pas.
Usage : essai_trous.py"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PySide6.QtWidgets import QApplication

from pixane.document import (FORMAT_IMAGE, Calque, Document, masque, qimage_rgb, qimage_rgba, tableau,
                             trous_a_remplir, vue_ia)
from pixane.fenetre import Fenetre
from pixane.moteur import Moteur

Moteur.demarrer = lambda self, signaler=None: None
Fenetre._moteur_en_echec = lambda self, *a: None
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


app = QApplication(sys.argv)
W, H = 400, 300
vide = np.zeros((H, W, 4), np.uint8)
poch = np.zeros((H, W, 4), np.uint8)
poch[:, 100:300] = [220, 90, 30, 255]                     # pochette orange au milieu, transparent autour
lettres = np.zeros((H, W), bool)
for k in range(6):                                         # « lettres » coupées : traits transparents
    lettres[60 + k * 12:66 + k * 12, 200:285] = True
lettres[60:130, 230:236] = True
poch[lettres] = 0
texte = np.zeros((H, W, 4), np.uint8)
texte[200:260, 10:90] = [250, 230, 120, 255]               # le texte coupé, collé ailleurs (autre calque)
sel = np.zeros((H, W), np.uint8)
yy, xx = np.mgrid[0:H, 0:W]
sel[(xx - 245) ** 2 + (yy - 95) ** 2 < 75 ** 2] = 255      # cercle : couvre les lettres, déborde à droite de la pochette


def scene():
    doc = Document(calques=[Calque("Arrière-plan", qimage_rgba(vide)), Calque("Collage 1", qimage_rgba(poch)),
                            Calque("Collage 2", qimage_rgba(texte))])
    doc.actif = 1
    s = np.zeros((H, W, 4), np.uint8)
    s[..., 3] = sel
    doc.selection = qimage_rgba(s).convertToFormat(doc.selection.format())
    return doc


doc = scene()
rgba = tableau(doc.image.convertToFormat(FORMAT_IMAGE))
t = trous_a_remplir(rgba, sel)
verifier(t is not None and t[lettres].all(), "les lettres coupées sont reconnues comme des trous")
verifier(not t[50:140, 305:320].any(), "le transparent à droite de la pochette (dans le cercle) n'est pas un trou")
verifier(trous_a_remplir(rgba, None) is None, "sans sélection : rien à remplir")
# résultat simulé de l'IA : orange partout dans la sélection (le fond reconstruit)
ia = rgba[..., :3].copy()
ia[sel > 0] = [220, 90, 30]
vue = tableau(vue_ia(qimage_rgb(ia), doc.image, t).convertToFormat(FORMAT_IMAGE))
verifier((vue[lettres][:, 3] == 255).all() and np.abs(vue[lettres][:, :3].astype(int) - [220, 90, 30]).max() <= 2,
         "fenêtre de choix : les trous sont montrés remplis (orange, opaques)")
verifier((vue[60:130, 305:320, 3] == 0).all(), "fenêtre de choix : hors de la pochette, toujours transparent")
vue_avant = tableau(vue_ia(qimage_rgb(ia), doc.image).convertToFormat(FORMAT_IMAGE))
verifier((vue_avant[lettres][:, 3] == 0).all(), "(sans la correction, les trous restaient transparents)")
# posé dans le calque choisi
doc.appliquer_etat(doc.etat_resultat_ia("Effacer", qimage_rgb(ia), sel, False, t))
k = tableau(doc.calques[1].image.convertToFormat(FORMAT_IMAGE))
verifier((k[lettres][:, 3] == 255).all() and np.abs(k[lettres][:, :3].astype(int) - [220, 90, 30]).max() <= 2,
         "calque « Collage 1 » : les trous sont remplis de la couleur autour, opaques")
verifier((k[60:130, 305:320, 3] == 0).all() and len(doc.calques) == 3, "à côté de la pochette : rien d'ajouté")
verifier(np.array_equal(tableau(doc.calques[2].image.convertToFormat(FORMAT_IMAGE)), texte),
         "le calque du texte collé n'est pas touché")

# dans Pixane : Effacer et Remplir remplissent les trous, Netteté non
lances = []
Fenetre._lancer = lambda self, titre, sel_, fab, **kw: lances.append((titre, kw.get("remplir_trous", False)))
f = Fenetre()
f.show()
f._installer_document(scene())
f.ia_effacer()
f.texte_remplir.setText("")
f.ia_remplir()
verifier(lances == [("Effacer", True), ("Remplir", True)], f"Effacer et Remplir remplissent les trous {lances}")

print("ERREURS :", erreurs if erreurs else "aucune")
sys.stdout.flush()
for dd in f.documents:
    dd.modifie = False
f.close()
sys.exit(1 if erreurs else 0)
