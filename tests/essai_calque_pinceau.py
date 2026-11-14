"""Calque de pinceau modifiable : la case « Calque modifiable » crée un calque de pinceau au premier coup ; ses traits
sont redessinés quand on change la couleur, la taille, l'opacité, la dureté, la rotation dans la barre ; il reste
modifiable après déplacement, Ctrl+T, pivoter, Upscale, recadrer, enregistrer / rouvrir ; une gomme en fait une image
(message) ; Annuler revient à chaque étape. Sans moteur. Usage : essai_calque_pinceau.py"""
import os
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication

from pixane import calque_pinceau as cp
from pixane.canevas import GOMME_CALQUE, PEINTURE
from pixane.document import Calque, Document, qimage_rgb, tableau
from pixane.fenetre import Fenetre
from pixane.moteur import Moteur

Moteur.demarrer = lambda self, signaler=None: None
Fenetre._moteur_en_echec = lambda self, *a: None
Fenetre._peut_fermer_tout = lambda self: True
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


app = QApplication(sys.argv)
f = Fenetre()
f.resize(1440, 920)
f.show()
c = f.canevas


def attendre(s=0.2):
    t = time.monotonic()
    while time.monotonic() - t < s:
        app.processEvents()
        time.sleep(0.01)


f._installer_document(Document(calques=[Calque("Photo", qimage_rgb(np.full((300, 400, 3), 200, np.uint8)))]))
attendre()
f._choisir_outil(PEINTURE)
verifier(f.case_calque_pinceau.isVisibleTo(f), "case « Calque modifiable » montrée avec le pinceau de couleur")
f.case_calque_pinceau.setChecked(True)
from pixane.pointe import Reglages
c.pinceaux["peinture"] = {"cle": None, "reglages": Reglages()}   # rond (un autre essai a pu choisir une forme)
f._enregistrer_pinceau("peinture")
f.opt_couleur.definir("#ffff0000")
f._couleur_peinture("#ffff0000")
c.definir_taille(20)
f.opt_opacite.setValue(100)
f.opt_durete.setValue(80)


def trait(points):
    c._pression_evt = 1.0
    ecran = [c.vers_ecran(QPointF(x, y)) for x, y in points]
    c._presser_retouche(ecran[0], False)
    for e in ecran[1:]:
        c._glisser_retouche(e)
    c._lacher_retouche()
    attendre(0.1)


doc = f.doc
photo = tableau(doc.calques[0].image).copy()
trait([(50 + i * 10, 100) for i in range(20)])
verifier(len(doc.calques) == 2, f"premier coup : un calque de pinceau est créé ({len(doc.calques)} calques)")
p = cp.valide(doc.calque_actif)
verifier(p is not None and len(p.traits) == 1, "le calque garde le tracé du coup")
verifier(np.array_equal(tableau(doc.calques[0].image), photo), "la photo n'est pas touchée")
trait([(50 + i * 10, 200) for i in range(20)])
p = cp.valide(doc.calque_actif)
verifier(len(doc.calques) == 2 and p is not None and len(p.traits) == 2, "deuxième coup : dans le même calque")
a = tableau(doc.calque_actif.image)
verifier(a[100, 100, 2] > 200 and a[200, 100, 2] > 200 and a[150, 100, 3] == 0, "les deux traits rouges sont dessinés")

# couleur, taille, opacité, dureté, rotation : redessinés
n_hist = f.historique.count()
f.opt_couleur.definir("#ff0000ff")
f._couleur_peinture("#ff0000ff")
attendre()
a = tableau(doc.calque_actif.image)
verifier(a[100, 100, 0] > 200 and a[100, 100, 2] < 50 and a[200, 100, 0] > 200, "couleur changée : tous les traits bleus")
c.definir_taille(60)
attendre()
a = tableau(doc.calque_actif.image)
verifier(a[120, 100, 3] > 240, f"taille changée : les traits sont plus épais ({a[120, 100, 3]})")
f.opt_opacite.setValue(50)
attendre()
a = tableau(doc.calque_actif.image)
verifier(100 < a[100, 100, 3] < 160, f"opacité 50 % ({a[100, 100, 3]})")
f.opt_opacite.setValue(100)
attendre()
f.angle_pinceau.setValue(45)
attendre()
verifier(cp.valide(doc.calque_actif).r().angle == 45, "rotation du pinceau gardée dans le calque")
verifier(f.historique.count() > n_hist, "les changements sont dans Annuler")
f.historique.undo()
attendre()
verifier(cp.valide(doc.calque_actif) is not None, "Annuler : toujours un calque de pinceau")
f.angle_pinceau.setValue(0)
attendre()

# sur un autre calque puis retour : la barre reprend ses réglages
f._choisir_outil(PEINTURE)
doc.actif = 0
doc.calques_changes.emit()
f.opt_couleur.definir("#ff00ff00")
f._couleur_peinture("#ff00ff00")
c.definir_taille(10)
attendre()
verifier(np.array_equal(tableau(doc.calques[0].image), photo), "réglages changés sur la photo : elle n'est pas touchée")
doc.actif = 1
doc.calques_changes.emit()
attendre()
p = cp.valide(doc.calque_actif)
verifier(c.taille_pinceau == round(p.taille) and f.opt_couleur.couleur.lower() == p.couleur.lower(),
         f"retour sur le calque de pinceau : la barre montre ses réglages ({c.taille_pinceau} px, {f.opt_couleur.couleur})")

# déplacer, Ctrl+T, pivoter, taille de l'image, recadrer
x0 = p.traits[0].points[0][0]
etat = doc._decaler_blocs({0: ([1], 30, 0)})
doc.appliquer_etat(doc.etat_avec(etat))
p = cp.valide(doc.calque_actif)
verifier(p is not None and abs(p.traits[0].points[0][0] - x0 - 30) < 1e-6, "déplacé : reste modifiable")
f.transformer()
t = c.transfo
t.sx = t.sy = 0.5
f._valider_transfo()
attendre()
p = cp.valide(doc.calque_actif)
verifier(p is not None and abs(p.taille - 30) < 1, f"Ctrl+T (moitié) : reste modifiable, taille {p.taille if p else '-'}")
doc.appliquer_etat(doc.etat_pivote(90))
verifier(cp.valide(doc.calque_actif) is not None and doc.taille() == (300, 400), "pivoté : reste modifiable")
doc.appliquer_etat(doc.etat_taille(600, 800))
p = cp.valide(doc.calque_actif)
verifier(p is not None and abs(p.taille - 60) < 1, "image agrandie : traits redessinés nets, taille doublée")

# enregistrer / rouvrir
fichier = Path(os.environ.get("TEMP", ".")) / "essai_calque_pinceau.pixane"
doc.enregistrer(fichier)
d2 = Document.ouvrir(fichier)
q = [cp.valide(k) for k in d2.calques if cp.valide(k) is not None]
verifier(len(q) == 1 and len(q[0].traits) == 2, "rouvert : toujours un calque de pinceau, avec ses 2 traits")
fichier.unlink(missing_ok=True)

# gomme : devient une image (message), Annuler revient
messages = []
c.refus.connect(messages.append)
f._choisir_outil(GOMME_CALQUE)
centre = p.traits[0].points[5]
e = c.vers_ecran(QPointF(centre[0], centre[1]))
from PySide6.QtCore import Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtCore import QEvent
for typ in (QEvent.MouseButtonPress, QEvent.MouseButtonRelease):
    ev = QMouseEvent(typ, e, c.mapToGlobal(e.toPoint()), Qt.LeftButton,
                     Qt.LeftButton if typ == QEvent.MouseButtonPress else Qt.NoButton, Qt.NoModifier)
    (c.mousePressEvent if typ == QEvent.MouseButtonPress else c.mouseReleaseEvent)(ev)
attendre()
verifier(cp.valide(doc.calque_actif) is None, "gomme : le calque devient une image")
verifier(any("pinceau" in m for m in messages), f"message « devient une image » ({messages[-1:] or '-'})")
f.historique.undo()
attendre()
verifier(cp.valide(doc.calque_actif) is not None, "Ctrl+Z : de nouveau un calque de pinceau")

# case décochée : on peint sur le calque choisi, comme avant
f._choisir_outil(PEINTURE)
f.case_calque_pinceau.setChecked(False)
doc.actif = 0
doc.calques_changes.emit()
n = len(doc.calques)
trait([(20, 20), (60, 20)])
verifier(len(doc.calques) == n and cp.valide(doc.calques[0]) is None, "case décochée : peint sur la photo, comme avant")

f.close()
print()
print("ERREURS :", *erreurs, sep="\n  ") if erreurs else print("ERREURS : aucune")
sys.exit(1 if erreurs else 0)
