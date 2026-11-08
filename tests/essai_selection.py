"""Sélection et Édition : rectangle et lasso (Nouvelle / Ajouter / Retirer, Maj, Alt, clic = désélectionner),
couper, copier, coller, supprimer (calque verrouillé protégé), outils regroupés comme Photoshop.
Usage : essai_selection.py dossier_sortie   (une image d'essai est fabriquée ; le moteur n'est pas démarré)"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["CHRYPIX_REGLAGES"] = "Chrypix-essais"   # ne touche pas aux réglages de l'utilisateur
import numpy as np
from PIL import Image
from PySide6.QtCore import QEvent, QPointF, QRect, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QMessageBox
from chrypix.canevas import GOMME, GOMME_CALQUE, LASSO, PEINTURE, PINCEAU, RECTANGLE, TAMPON
from chrypix.document import masque, tableau
from chrypix.fenetre import Fenetre
from chrypix.moteur import Moteur

Moteur.demarrer = lambda self, signaler=None: (_ for _ in ()).throw(Exception("moteur désactivé pour l'essai"))
Fenetre._moteur_en_echec = lambda self, *a: None
messages = []
QMessageBox.information = lambda *a, **k: messages.append(a[2] if len(a) > 2 else "") or QMessageBox.Ok
sortie = Path(sys.argv[1])
sortie.mkdir(parents=True, exist_ok=True)
yy, xx = np.mgrid[0:600, 0:900]
Image.fromarray(np.dstack([xx * 255 // 900, yy * 255 // 600, np.full_like(xx, 140)]).astype(np.uint8)).save(
    sortie / "fond.png")

app = QApplication(sys.argv)
f = Fenetre()
f.resize(1440, 920)
f.show()
f.charger(str(sortie / "fond.png"))
app.processEvents()
doc, c = f.doc, f.canevas
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


def souris(points, modif=Qt.NoModifier):
    ecran = [c.vers_ecran(QPointF(*p)) for p in points]
    c.event(QMouseEvent(QEvent.MouseButtonPress, ecran[0], ecran[0], Qt.LeftButton, Qt.LeftButton, modif))
    for e in ecran[1:]:
        c.event(QMouseEvent(QEvent.MouseMove, e, e, Qt.NoButton, Qt.LeftButton, modif))
    c.event(QMouseEvent(QEvent.MouseButtonRelease, ecran[-1], ecran[-1], Qt.LeftButton, Qt.NoButton, modif))


def choisi(x, y):
    return masque(doc.selection)[y, x] > 0


# ------------------------------------------------------------------ rectangle
f._actions_outils[RECTANGLE].trigger()
verifier(not f.p_nouvelle.isHidden() and f.p_nouvelle.isChecked(), "rectangle : « Nouvelle » proposée et choisie")
souris([(100, 100), (200, 200)])
verifier(choisi(150, 150), "premier rectangle sélectionné")
souris([(400, 300), (500, 400)])
verifier(choisi(450, 350) and not choisi(150, 150), "nouveau rectangle : remplace l'ancien")
souris([(100, 100), (200, 200)], Qt.ShiftModifier)
verifier(choisi(450, 350) and choisi(150, 150), "Maj : ajoute")
souris([(420, 320), (480, 380)], Qt.AltModifier)
verifier(not choisi(450, 350) and choisi(410, 310) and choisi(150, 150), "Alt : retire")
f.p_ajouter.click()
souris([(600, 100), (700, 200)])
verifier(choisi(650, 150) and choisi(150, 150), "bouton Ajouter : ajoute sans Maj")
f.p_nouvelle.click()
n = f.historique.index()
souris([(800, 500)])
verifier(f.doc.selection_vide(), "simple clic : désélectionne")
f.historique.undo()
verifier(choisi(650, 150) and choisi(150, 150), "Ctrl+Z : la sélection revient")

# ------------------------------------------------------------------ lasso
f._actions_outils[LASSO].trigger()
verifier(f._bouton_groupe[LASSO].defaultAction() is f._actions_outils[LASSO], "le bouton du groupe montre le lasso")
souris([(300, 50), (380, 50), (380, 130), (300, 130)])
verifier(choisi(340, 90) and not choisi(150, 150), "lasso : remplace la sélection")

# ------------------------------------------------------------------ pinceau
f._actions_outils[PINCEAU].trigger()
verifier(f.p_nouvelle.isHidden() and f.p_ajouter.isChecked(), "pinceau : Ajouter / Retirer seulement")
souris([(150, 450), (160, 450)])
verifier(choisi(155, 450) and choisi(340, 90), "pinceau : ajoute toujours")
f._actions_outils[GOMME].trigger()
verifier(f.opt_selection.isHidden(), "gomme de sélection : pas de pastilles (elle retire toujours)")

# ------------------------------------------------------------------ copier / coller
f._actions_outils[RECTANGLE].trigger()
souris([(100, 100), (200, 180)])
avant = tableau(doc.calques[0].image)[100:180, 100:200].copy()
f.a_copier.trigger()
f.a_coller.trigger()
verifier(len(doc.calques) == 2 and doc.actif == 1, "coller : nouveau calque au-dessus, choisi")
colle = tableau(doc.calques[1].image)
verifier(np.array_equal(colle[100:180, 100:200], avant), "coller : mêmes pixels, à la même place")
verifier(colle[50, 50, 3] == 0 and colle[190, 150, 3] == 0, "coller : transparent ailleurs")
verifier(doc.selection_vide(), "coller : sélection vidée")
f.historique.undo()
verifier(len(doc.calques) == 1, "Ctrl+Z : collage annulé")

# ------------------------------------------------------------------ couper / supprimer
souris([(100, 100), (200, 180)])
f.a_couper.trigger()
img = tableau(doc.calques[0].image)
verifier(img[140, 150, 3] == 0 and img[300, 300, 3] == 255, "couper : zone transparente, reste intact")
f.a_coller.trigger()
verifier(np.array_equal(tableau(doc.calques[1].image)[100:180, 100:200], avant), "couper puis coller : pixels rendus")
f.historique.undo()
f.historique.undo()
verifier(tableau(doc.calques[0].image)[140, 150, 3] == 255, "Ctrl+Z : coupe annulée")
f._modifier_selection("rien")
n = f.historique.index()
f.a_supprimer_selection.trigger()
verifier(f.historique.index() == n, "supprimer sans sélection : rien")
souris([(300, 300), (350, 350)])
f.a_supprimer_selection.trigger()
verifier(tableau(doc.calques[0].image)[320, 320, 3] == 0, "Suppr : pixels effacés")
f.historique.undo()
doc.appliquer_etat(doc.etat_calque_modifie(0, verrou=True))
n = f.historique.index()
f.a_supprimer_selection.trigger()
verifier(f.historique.index() == n and tableau(doc.calques[0].image)[320, 320, 3] == 255 and messages,
         "calque verrouillé : Suppr refusé avec un message")

# ------------------------------------------------------------------ outils regroupés
f._actions_outils[TAMPON].trigger()
verifier(f._bouton_groupe[TAMPON].defaultAction() is f._actions_outils[TAMPON], "groupe retouche : montre le tampon")
verifier(f._bouton_groupe[PEINTURE] is f._bouton_groupe[GOMME_CALQUE], "pinceau de couleur et gomme de calque : même groupe")
verifier(f._bouton_groupe[TAMPON].menu() is not None and len(f._bouton_groupe[TAMPON].menu().actions()) == 3,
         "le groupe garde son menu de 3 outils")
f.grab().save(str(sortie / "fenetre.png"))

print("ERREURS :", erreurs if erreurs else "aucune")
sys.stdout.flush()
doc.modifie = False
f.close()
os._exit(1 if erreurs else 0)
