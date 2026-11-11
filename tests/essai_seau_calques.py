"""Pot de peinture et calques : case « Tous les calques » décochée par défaut (comme Photoshop) : la zone est cherchée
dans le calque choisi ; sur un calque vide, un clic remplit tout le calque. Cochée : d'après l'image visible.
Cas de Christophe : fond rouge, pochette sur un autre calque, calque vide rempli, puis pochette supprimée : plus
de trou. Usage : essai_seau_calques.py"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PySide6.QtCore import QEvent, QPointF, QSettings, Qt
from PySide6.QtGui import QColor, QMouseEvent
from PySide6.QtWidgets import QApplication, QCheckBox

from pixane.canevas import SEAU
from pixane.document import FORMAT_IMAGE, Calque, Document, qimage_rgba, tableau
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
f = Fenetre()
f.resize(1300, 900)
f.show()
c = f.canevas
case = next(b for b in f.opt_seau.findChildren(QCheckBox))
verifier(case.text() in ("Tous les calques", "All layers") and not case.isChecked(),
         "case « Tous les calques » dans la barre du pot, décochée par défaut")
verifier(bool(case.toolTip()), "la case a une explication (bulle d'aide)")
H, W = 300, 400


def scene():
    fond = np.zeros((H, W, 4), np.uint8)
    fond[:] = [225, 60, 50, 255]                                   # fond rouge
    poch = np.zeros((H, W, 4), np.uint8)
    poch[50:250, 120:280] = [250, 250, 250, 255]                   # « pochette » blanche
    doc = Document(calques=[Calque("Fond", qimage_rgba(fond)), Calque("Pochette", qimage_rgba(poch)),
                            Calque("Vide", qimage_rgba(np.zeros((H, W, 4), np.uint8)))])
    doc.actif = 2
    f._installer_document(doc)
    f._choisir_outil(SEAU)
    c.couleur_peinture = QColor(0, 200, 0)
    c.opacite = 1.0
    app.processEvents()
    return doc


def clic(x, y):
    e = c.vers_ecran(QPointF(x, y))
    c.event(QMouseEvent(QEvent.MouseButtonPress, e, e, Qt.LeftButton, Qt.LeftButton, Qt.NoModifier))
    c.event(QMouseEvent(QEvent.MouseButtonRelease, e, e, Qt.LeftButton, Qt.NoButton, Qt.NoModifier))
    app.processEvents()


def vert(doc, i):
    a = tableau(doc.calques[i].image.convertToFormat(FORMAT_IMAGE))
    return (a[..., 1] == 200) & (a[..., 3] == 255)


# décochée : tout le calque vide se remplit, même sous la pochette
doc = scene()
clic(30, 30)
v = vert(doc, 2)
verifier(v.all(), f"case décochée : le calque vide est rempli en entier ({v.mean():.0%})")
doc.appliquer_etat(doc.etat_avec(doc.calques[:1] + doc.calques[2:], 1))        # pochette supprimée
verifier(vert(doc, 1).all(), "pochette supprimée ensuite : pas de trou")
# cochée : comme avant (d'après l'image visible)
case.setChecked(True)
verifier(c.seau_tous_calques and QSettings("Pixane-essais", "Pixane").value("seau_tous_calques", type=bool) in (True, False),
         "case cochée : prise en compte")
doc = scene()
clic(30, 30)
v = vert(doc, 2)
verifier(v[30, 30] and not v[150, 200], "case cochée : le remplissage s'arrête à la pochette (image visible)")
case.setChecked(False)
# calque avec du contenu, case décochée : la zone suit le calque choisi
doc = scene()
doc.actif = 1                                                       # calque Pochette
clic(200, 150)
v = vert(doc, 1)
verifier(v[150, 200] and not v[20, 20], "case décochée, clic dans la pochette : seule la pochette est remplie")
clic(20, 20)
v = vert(doc, 1)
verifier(v[20, 20] and v[150, 200], "clic dans la partie vide du calque : le vide autour se remplit")

print("ERREURS :", erreurs if erreurs else "aucune")
sys.stdout.flush()
for dd in f.documents:
    dd.modifie = False
f.close()
sys.exit(1 if erreurs else 0)
