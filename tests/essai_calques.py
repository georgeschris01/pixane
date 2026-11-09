"""Calques : résultats IA simulés (même taille, Agrandir, Upscale), panneau, gomme de calque, annuler, .ora.
Usage : essai_calques.py image dossier_sortie   (le moteur n'est pas démarré)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from PySide6.QtCore import QEvent, QPointF, Qt, QTimer
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication
from pixane.canevas import GOMME_CALQUE
from pixane.document import FORMAT_IMAGE, Document, qimage_rgb, tableau
import os
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"   # ne touche pas aux réglages de l'utilisateur
from pixane.fenetre import Fenetre
from pixane.moteur import Moteur

Moteur.demarrer = lambda self, signaler=None: (_ for _ in ()).throw(Exception("moteur désactivé pour l'essai"))
Fenetre._moteur_en_echec = lambda self, *a: None
app = QApplication(sys.argv)
sortie = Path(sys.argv[2])
f = Fenetre()
f.resize(1440, 920)
f.show()
f.charger(sys.argv[1])
app.processEvents()
doc, c = f.doc, f.canevas
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


def rgb(img):
    return tableau(img)[:, :, :3].astype(int)


w, h = doc.taille()
original = rgb(doc.image)

# 1. résultat IA de même taille (Effacer simulé : un carré repeint)
res = original.copy()
res[100:300, 200:500] = [30, 200, 60]
doc.tout_selectionner()
f._appliquer_resultat(doc, qimage_rgb(res.astype(np.uint8)), "Effacer")
verifier(doc.selection_vide(), "travail IA fini -> plus de sélection")
f.historique.undo()
verifier(not doc.selection_vide(), "Annuler -> la sélection revient")
f.historique.redo()
verifier(len(doc.calques) == 2 and doc.calques[1].nom == "Effacer 1", "Effacer -> nouveau calque « Effacer 1 »")
alpha = tableau(doc.calques[1].image)[:, :, 3]
verifier(alpha[100:300, 200:500].all() and alpha.sum() // 255 == 200 * 300, "le calque ne contient que la zone changée")
verifier(np.array_equal(rgb(doc.image), res), "image visible = résultat de l'IA")
f.calques._oeil(f.calques.liste.itemWidget(f.calques.liste.item(0)))
verifier(np.array_equal(rgb(doc.image), original), "masquer le calque -> on revoit l'original")
f.historique.undo()
verifier(doc.calques[1].visible, "Annuler -> calque de nouveau visible")

# 2. opacité 50 %
f.calques.curseur.setValue(50)
m = rgb(doc.image)[200, 300]
verifier(abs(m[1] - (original[200, 300][1] + 200) / 2) <= 2, f"opacité 50 % -> mélange ({m})")
f.calques.curseur.setValue(100)

# 3. gomme de calque sur « Effacer 1 »
c.definir_outil(GOMME_CALQUE)
c.definir_taille(40)
p0 = c.vers_ecran(QPointF(300, 200))
p1 = c.vers_ecran(QPointF(450, 200))
for t, pos in ((QEvent.MouseButtonPress, p0), (QEvent.MouseMove, p1), (QEvent.MouseButtonRelease, p1)):
    b = Qt.NoButton if t == QEvent.MouseButtonRelease else Qt.LeftButton
    c.event(QMouseEvent(t, pos, pos, Qt.LeftButton, b, Qt.NoModifier))
verifier(np.array_equal(rgb(doc.image)[200, 350], original[200, 350]), "gomme de calque -> l'original réapparaît")
verifier(f.historique.undoText() == "Gomme de calque", "gomme de calque annulable")
f.historique.undo()
verifier(np.array_equal(rgb(doc.image)[200, 350], res[200, 350]), "Annuler la gomme -> retouche revenue")

# 4. boutons du panneau
f.calques.nouveau()
f.calques.dupliquer()
verifier(len(doc.calques) == 4, "nouveau + dupliquer -> 4 calques")
f.calques.deplacer(-1)
f.calques.supprimer()                      # supprime la copie (calque actif)
f.calques.liste.setCurrentRow(0)           # choisit le calque du haut (« Calque 1 ») dans la liste
f.calques.supprimer()
verifier(doc.calque_actif.nom == "Effacer 1", "après suppression, le calque du dessous devient actif")
verifier(len(doc.calques) == 2, "supprimer x2 -> 2 calques")
f.calques.fusionner()
verifier(len(doc.calques) == 1 and np.array_equal(rgb(doc.image), res), "fusionner -> 1 calque, même image")
f.historique.undo()
verifier(len(doc.calques) == 2, "Annuler la fusion -> 2 calques")

# 5. Agrandir simulé : +100 à gauche, +50 en haut
W, H = w + 100, h + 50
grand = np.zeros((H, W, 3), np.uint8)
grand[:] = [90, 90, 200]
grand[50:, 100:] = rgb(doc.image)
grand[50:60, 100:] = [250, 250, 250]           # bande refaite par l'IA dans l'original
avant = rgb(doc.image)
f._appliquer_resultat(doc, qimage_rgb(grand), "Agrandir", lambda img: doc.etat_agrandi("Agrandir", img, (100, 50)))
verifier(doc.taille() == (W, H) and len(doc.calques) == 3, "Agrandir -> nouvelle taille, calque « Agrandir 1 »")
verifier(np.array_equal(rgb(doc.image), grand.astype(int)), "image visible = résultat d'Agrandir")
verifier(np.array_equal(rgb(doc.calques[0].image.convertToFormat(FORMAT_IMAGE))[50:, 100:], original), "photo d'origine décalée dans son calque")

# 6. Upscale simulé x2
big = np.ascontiguousarray(np.repeat(np.repeat(rgb(doc.image), 2, 0), 2, 1).astype(np.uint8))
f._appliquer_resultat(doc, qimage_rgb(big), "Upscale")
verifier(doc.taille() == (2 * W, 2 * H) and len(doc.calques) == 4, "Upscale -> tous les calques agrandis + « Upscale 1 »")
f.historique.undo()
f.historique.undo()
verifier(doc.taille() == (w, h) and len(doc.calques) == 2, "Annuler x2 -> retour taille et calques d'avant")

# 7. .ora : enregistrer puis rouvrir
doc.calques  # 2 calques
f.calques.curseur.setValue(70)
chemin = sortie / "essai_calques.ora"
doc.enregistrer(chemin)
relu = Document.ouvrir(chemin)
verifier([x.nom for x in relu.calques] == [x.nom for x in doc.calques], ".ora : mêmes calques, même ordre")
verifier(abs(relu.calques[1].opacite - 0.7) < 0.01, ".ora : opacité gardée")
verifier(np.abs(rgb(relu.image) - rgb(doc.image)).max() <= 2, ".ora : même image")

# 8. verrou (cadenas)
messages = []
c.refus.connect(messages.append)
ligne_haut = f.calques.liste.itemWidget(f.calques.liste.item(0))
f.calques._cadenas(ligne_haut)
verifier(doc.calque_actif.verrou, "cadenas -> calque verrouillé")
verifier(not f.calques.boutons["supprimer"].isEnabled() and not f.calques.boutons["fusionner"].isEnabled()
         and not f.calques.boutons["aplatir"].isEnabled() and not f.calques.curseur.isEnabled(),
         "verrouillé : supprimer, fusionner, aplatir et opacité désactivés")
verifier(doc.etat_supprimer() is None and doc.etat_fusionner_bas() is None and doc.etat_aplatir() is None,
         "verrouillé : le document refuse aussi")
avant_gomme = rgb(doc.image)
c.definir_outil(GOMME_CALQUE)
p0 = c.vers_ecran(QPointF(300, 200))
for t in (QEvent.MouseButtonPress, QEvent.MouseButtonRelease):
    b_ = Qt.NoButton if t == QEvent.MouseButtonRelease else Qt.LeftButton
    c.event(QMouseEvent(t, p0, p0, Qt.LeftButton, b_, Qt.NoModifier))
verifier(np.array_equal(rgb(doc.image), avant_gomme) and messages, "verrouillé : la gomme refuse, avec un message")
from PySide6.QtWidgets import QMessageBox
infos, lances = [], []
QMessageBox.information = staticmethod(lambda parent, titre, texte, *a: infos.append(texte))
f._lancer = lambda *a, **kw: lances.append(a[0])
doc.tout_selectionner()
f.ia_effacer(); f.ia_remplir(); f.ia_upscale(); f.ia_agrandir()
verifier(not lances and len(infos) == 4 and c.cadre is None, "verrouillé : Effacer, Remplir, Upscale, Agrandir refusés avec message")
print("   message :", infos[0].replace(chr(10), " "))
doc.deselectionner()
doc.enregistrer(chemin)
verifier(Document.ouvrir(chemin).calques[-1].verrou, ".ora : verrou gardé")
f.historique.undo()
verifier(not doc.calque_actif.verrou, "Annuler -> déverrouillé")

c.definir_outil("pinceau")
c.repaint()
f.grab().save(str(sortie / "calques.png"))
print("ERREURS :", erreurs if erreurs else "aucune")
doc.modifie = False
QTimer.singleShot(200, f.close)
app.exec()
