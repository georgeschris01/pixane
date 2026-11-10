"""Plusieurs calques choisis : Grouper (Ctrl+G), Aligner, Répartir, Retourner le calque (symétrie).
Usage : essai_aligner.py"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PySide6.QtCore import QRect
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QApplication, QToolButton

from pixane.document import COULEUR_SELECTION, FORMAT_IMAGE, Calque, Document, qimage_rgba, tableau
from pixane.fenetre import Fenetre
from pixane.moteur import Moteur

Moteur.demarrer = lambda self, signaler=None: None
Fenetre._moteur_en_echec = lambda self, *a: None
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


W, H = 400, 300


def calque(nom, x, y, w, h, couleur):
    a = np.zeros((H, W, 4), np.uint8)
    a[y:y + h, x:x + w] = [*couleur, 255]
    a[y:y + 5, x:x + 5] = [255, 255, 0, 255]          # coin jaune en haut à gauche : pour voir la symétrie
    return Calque(nom, qimage_rgba(a))


def nouveau():
    doc = Document(calques=[calque("Rouge", 20, 30, 50, 40, (200, 0, 0)), calque("Vert", 150, 100, 80, 60, (0, 200, 0)),
                            calque("Bleu", 300, 200, 40, 40, (0, 0, 200))])
    f._installer_document(doc)
    return doc


def choisir(*idx):
    f.calques.choisis = set(idx)
    f.doc.actif = idx[-1]


def rect(i):
    return f.doc.bornes([i])


app = QApplication(sys.argv)
f = Fenetre()
f.resize(1300, 850)
f.show()

# ------------------------------------------------------------------ aligner
doc = nouveau()
choisir(0, 1, 2)
pile = f.groupe_historique.activeStack()
f.aligner("gauche")
verifier([rect(i).left() for i in range(3)] == [20, 20, 20], f"bords gauches : {[rect(i).left() for i in range(3)]}")
verifier([rect(i).top() for i in range(3)] == [30, 100, 200], "aligner à gauche ne change pas la hauteur")
f.retour()
verifier([rect(i).left() for i in range(3)] == [20, 150, 300], "un seul Ctrl+Z annule l'alignement")
f.aligner("droite")
verifier([rect(i).right() for i in range(3)] == [339] * 3, f"bords droits : {[rect(i).right() for i in range(3)]}")
f.retour()
f.aligner("centre_h")
centres = [rect(i).left() + rect(i).width() / 2 for i in range(3)]
verifier(max(centres) - min(centres) <= 1, f"centres horizontaux : {centres}")
f.retour()
f.aligner("haut")
verifier([rect(i).top() for i in range(3)] == [30] * 3, "bords hauts")
f.retour()
f.aligner("bas")
verifier([rect(i).bottom() for i in range(3)] == [239] * 3, "bords bas")
f.retour()
f.aligner("centre_v")
centres = [rect(i).top() + rect(i).height() / 2 for i in range(3)]
verifier(max(centres) - min(centres) <= 1, f"centres verticaux : {centres}")
f.retour()
# un seul calque : sur l'image, puis sur la sélection
choisir(1)
f.aligner("centre_h")
f.aligner("centre_v")
verifier(rect(1) == QRect(160, 120, 80, 60), f"un seul calque : centré dans l'image {rect(1)}")
p = QPainter(f.doc.selection)
p.fillRect(0, 0, 100, 100, COULEUR_SELECTION)
p.end()
f.aligner("gauche")
f.aligner("haut")
verifier(rect(1).topLeft().x() == 0 and rect(1).top() == 0, f"un seul calque + sélection : sur la sélection {rect(1)}")
f.doc.selection.fill(0)
# calque verrouillé : ne bouge pas
doc = nouveau()
choisir(0, 1, 2)
from dataclasses import replace
calques = list(f.doc.calques)
calques[1] = replace(calques[1], verrou=True)
f.doc.appliquer_etat((tuple(calques), 2, f.doc.selection))
f.aligner("gauche")
verifier(rect(1).left() == 150 and rect(2).left() == 20, "calque verrouillé : il ne bouge pas, les autres oui")

# ------------------------------------------------------------------ répartir
doc = nouveau()
choisir(0, 1, 2)
calques = list(f.doc.calques)
from pixane.document import _decale
calques[1] = _decale(calques[1], -100, 0, W, H)        # vert : de 150 à 50 (trop près du rouge)
f.doc.appliquer_etat((tuple(calques), 2, f.doc.selection))
f.repartir("h")
r = [rect(i) for i in range(3)]
e1, e2 = r[1].left() - (r[0].right() + 1), r[2].left() - (r[1].right() + 1)
verifier(abs(e1 - e2) <= 1 and r[0].left() == 20 and r[2].left() == 300, f"répartir : espaces égaux ({e1}, {e2})")
choisir(0, 1)
messages = []
f.statusBar().showMessage = lambda t, *a: messages.append(t)
f.repartir("v")
verifier(messages and "3" in messages[-1], "répartir avec 2 calques : message « au moins 3 »")
del f.statusBar().showMessage

# ------------------------------------------------------------------ grouper plusieurs calques
doc = nouveau()
choisir(0, 2)
f.calques.grouper()
noms = [c.nom for c in f.doc.calques]
g = f.doc.calques[-1]
verifier(len(f.doc.calques) == 4 and g.groupe and noms[:3] == ["Vert", "Rouge", "Bleu"]
         and f.doc.calques[1].dans == g.ident and f.doc.calques[2].dans == g.ident and f.doc.calques[0].dans is None,
         f"Ctrl+G sur 2 calques : un groupe avec les deux, à la place du plus haut ({noms})")
verifier(f.doc.actif == 3, "le nouveau groupe est choisi")
# grouper un groupe avec un autre calque : le groupe entre avec son contenu
choisir(0, 3)
f.calques.grouper()
c = f.doc.calques
g2 = c[-1]
verifier(len(c) == 5 and g2.groupe and c[3].ident == g.ident and c[3].dans == g2.ident
         and c[0].dans == g2.ident and c[1].dans == g.ident, f"groupe + calque groupés ensemble ({[x.nom for x in c]})")
f.retour()
f.retour()
verifier(len(f.doc.calques) == 3, "Ctrl+Z défait les groupes")
choisir(1)
f.calques.grouper()
verifier(len(f.doc.calques) == 4 and f.doc.calques[1].dans == f.doc.calques[2].ident, "un seul calque : comme avant")
# aligner un groupe : il bouge avec son contenu
doc = nouveau()
choisir(0, 1)
f.calques.grouper()                # groupe (Rouge, Vert) ; Bleu à part
choisir(2, 3)
f.aligner("droite")
verifier([x.nom for x in f.doc.calques][3] == "Bleu" and f.doc.bornes([0, 1]).right() == rect(3).right()
         and rect(1).right() == rect(3).right() and rect(0).right() < rect(1).right(),
         "un groupe s'aligne comme un seul bloc (son contenu garde sa disposition)")

# ------------------------------------------------------------------ retourner (symétrie)
doc = nouveau()
choisir(0)
avant = rect(0)
f.retourner_calques(True)
a = tableau(f.doc.calques[0].image.convertToFormat(FORMAT_IMAGE))
verifier(rect(0) == avant and a[32, 67, 1] == 255 and a[32, 22, 1] == 0,
         "symétrie horizontale d'un calque : sur place, le coin jaune passe à droite")
verifier(f.canevas.transfo is None and "Retourner" in f.groupe_historique.undoText(), f"une étape « {f.groupe_historique.undoText()} »")
f.retour()
f.retourner_calques(False)
a = tableau(f.doc.calques[0].image.convertToFormat(FORMAT_IMAGE))
verifier(a[67, 22, 1] == 255 and a[32, 22, 1] == 0, "symétrie verticale : le coin jaune passe en bas")
f.retour()
# plusieurs calques : ensemble
choisir(0, 2)
f.retourner_calques(True)
verifier(rect(0).left() == 290 and rect(2).left() == 20, f"deux calques retournés ensemble : ils échangent leur place "
                                                          f"({rect(0).left()}, {rect(2).left()})")
verifier(rect(1).left() == 150, "le calque non choisi ne bouge pas")

# ------------------------------------------------------------------ interface
verifier(all(hasattr(f, f"a_aligner_{m}") for m in ("gauche", "centre_h", "droite", "haut", "centre_v", "bas"))
         and f.a_grouper.text().startswith("Grouper les calques"), "menu Calque : Grouper les calques, Aligner")
boutons = [b for b in f.opt_deplacer.findChildren(QToolButton)]
verifier(len(boutons) == 8, f"outil Déplacer : 6 boutons Aligner + 2 Répartir ({len(boutons)})")
# barre d'accès rapide (Affichage > Barre d'accès rapide) : les boutons de Déplacer seulement quand elle est masquée
f.a_barre_rapide.setChecked(True)
app.processEvents()
dans_barre = {a.objectName() or a.text() for a in f.barre_rapide.actions() if not a.isSeparator()}
verifier(f.barre_rapide.isVisible() and f.a_transformer in f.barre_rapide.actions() and f.a_grouper in
         f.barre_rapide.actions() and f.a_aligner_gauche in f.barre_rapide.actions()
         and f.a_retourner_calque_h in f.barre_rapide.actions() and f.a_pivoter_g in f.barre_rapide.actions()
         and len(dans_barre) == 17, f"barre d'accès rapide : 17 commandes ({len(dans_barre)})")
verifier(f.alignement_deplacer.isHidden(), "barre rapide visible : pas de doublon dans la barre de Déplacer")
f.a_barre_rapide.setChecked(False)
verifier(f.barre_rapide.isHidden() and not f.alignement_deplacer.isHidden(), "barre rapide masquée : boutons dans Déplacer")
f.a_barre_rapide.setChecked(True)

print("ERREURS :", erreurs if erreurs else "aucune")
sys.stdout.flush()
for d in f.documents:
    d.modifie = False
f.close()
sys.exit(1 if erreurs else 0)
