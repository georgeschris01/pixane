"""Outils de retouche : Recadrer (cadre, proportions, poignées, textes suivis, annuler), Recadrer à la sélection,
pinceau de couleur (couleur, opacité sans accumulation, pipette, verrou, texte -> image), tampon (source, copie
alignée), capture de la fenêtre.
Usage : essai_outils.py dossier_sortie   (une image d'essai est fabriquée ; le moteur n'est pas démarré)"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["CHRYPIX_REGLAGES"] = "Chrypix-essais"   # ne touche pas aux réglages de l'utilisateur
import numpy as np
from PIL import Image
from PySide6.QtCore import QEvent, QPointF, QRect, Qt
from PySide6.QtGui import QColor, QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QApplication
from chrypix.canevas import PEINTURE, RECADRER, TAMPON
from chrypix.document import tableau
from chrypix.fenetre import Fenetre, reglages
from chrypix.moteur import Moteur
from chrypix.texte import Texte

Moteur.demarrer = lambda self, signaler=None: (_ for _ in ()).throw(Exception("moteur désactivé pour l'essai"))
Fenetre._moteur_en_echec = lambda self, *a: None
sortie = Path(sys.argv[1])
sortie.mkdir(parents=True, exist_ok=True)
yy, xx = np.mgrid[0:800, 0:1200]
Image.fromarray(np.dstack([xx * 255 // 1200, yy * 255 // 800, np.full_like(xx, 140)]).astype(np.uint8)).save(
    sortie / "fond.png")

app = QApplication(sys.argv)
for cle in ("peinture_couleur", "outil_opacite", "outil_durete"):
    reglages().remove(cle)
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


def touche(k):
    c.event(QKeyEvent(QEvent.KeyPress, k, Qt.NoModifier))


def rgb(img):
    return tableau(img)[:, :, :3].astype(int)


original = rgb(doc.image)
calque0 = tableau(doc.calques[0].image).copy()

# ------------------------------------------------------------------ Recadrer
f._actions_outils[RECADRER].trigger()
verifier(not f.opt_recadrer.isHidden() and f.opt_retouche.isHidden(), "Recadrer : options du recadrage seules")
verifier(not f.b_recadrer.isEnabled(), "pas de cadre -> bouton Recadrer grisé")
souris([(100, 100), (400, 300), (700, 500)])
r = c.rect_recadre()
verifier(r == QRect(100, 100, 600, 400), f"cadre tiré : {r}")
verifier(f.b_recadrer.isEnabled(), "cadre -> bouton Recadrer actif")
souris([(700, 500), (800, 560)])                      # coin bas droit
verifier(c.rect_recadre() == QRect(100, 100, 700, 460), f"coin tiré : {c.rect_recadre()}")
souris([(400, 300), (350, 280)])                      # déplacer le cadre
verifier(c.rect_recadre() == QRect(50, 80, 700, 460), f"cadre déplacé : {c.rect_recadre()}")
souris([(400, 300), (-500, -500)])                    # ne sort pas de la photo
verifier(c.rect_recadre().topLeft().x() == 0 and c.rect_recadre().topLeft().y() == 0, "cadre gardé dans la photo")
f.opt_proportion.setCurrentIndex(f.opt_proportion.findText("1:1"))
r = c.rect_recadre()
verifier(abs(r.width() - r.height()) <= 1, f"proportion 1:1 : {r.width()} × {r.height()}")
souris([(1100, 100), (900, 300)])                     # nouveau cadre carré
r = c.rect_recadre()
verifier(r.width() == r.height() == 200, f"nouveau cadre 1:1 : {r}")
c.grab().save(str(sortie / "recadrer.png"))
touche(Qt.Key_Escape)
verifier(c.rect_recadre() is None, "Échap -> plus de cadre")
f.opt_proportion.setCurrentIndex(0)
# un texte, pour vérifier qu'il suit le recadrage
t = Texte(texte="Bonjour", x=600, y=400, taille=60)
f.historique.push(__import__("chrypix.fenetre", fromlist=["CommandeEtat"]).CommandeEtat(
    doc, doc.etat(), doc.etat_nouveau_texte(t), "texte"))
souris([(200, 150), (1000, 650)])
touche(Qt.Key_Return)
verifier(doc.taille() == (800, 500), f"Entrée -> recadré : {doc.taille()}")
verifier(np.array_equal(tableau(doc.calques[0].image), calque0[150:650, 200:1000]), "pixels gardés au bon endroit")
verifier(doc.calques[1].texte is not None and (doc.calques[1].texte.x, doc.calques[1].texte.y) == (400, 250),
         "le texte reste un texte, décalé avec le recadrage")
verifier(doc.selection.width() == 800 and doc.selection.height() == 500, "sélection recadrée aussi")
f.historique.undo()
verifier(doc.taille() == (1200, 800), "Ctrl+Z -> taille d'origine")
f.historique.undo()                                   # retire le texte

# Recadrer à la sélection
f._actions_outils[RECADRER].trigger()
doc.selection.fill(0)
from PySide6.QtGui import QPainter
p = QPainter(doc.selection)
p.fillRect(QRect(300, 200, 120, 80), QColor(255, 0, 0))
p.end()
f.a_recadrer_selection.trigger()
verifier(doc.taille() == (120, 80) and doc.selection_vide(), "Recadrer à la sélection : 120 × 80, sélection vidée")
f.historique.undo()
verifier(doc.taille() == (1200, 800), "annulé")
doc.deselectionner()

# ------------------------------------------------------------------ pinceau de couleur
f._actions_outils[PEINTURE].trigger()
verifier(not f.opt_couleur.isHidden() and not f.opt_retouche.isHidden(),
         "Pinceau de couleur : couleur, opacité, dureté")
f.opt_couleur.definir("#ffff0000")
f._couleur_peinture("#ffff0000")
f.opt_opacite.setValue(50)
f.opt_durete.setValue(100)
c.definir_taille(30)
nb = f.historique.index()
souris([(100, 400), (300, 400), (100, 400), (300, 400)])          # aller-retour dans le même coup
px = rgb(doc.image)[400, 200]
attendu = (original[400, 200] + np.array([255, 0, 0])) / 2       # rouge à 50 %
verifier(np.abs(px - attendu).max() <= 2, f"rouge à 50 % sans accumulation : {px} (attendu {attendu.round()})")
verifier(np.array_equal(rgb(doc.image)[300, 200], original[300, 200]), "rien hors du trait")
verifier(f.historique.index() == nb + 1, f"un coup = une étape d'annulation ({nb} -> {f.historique.index()})")
souris([(100, 400), (300, 400)])
px2 = rgb(doc.image)[400, 200]
verifier(px2[0] > px[0] and px2[2] < px[2], f"deuxième coup par-dessus : plus rouge {px} -> {px2}")
f.historique.undo()
f.historique.undo()
verifier(np.array_equal(rgb(doc.image), original), "Ctrl+Z ×2 -> photo d'origine")
# pipette
souris([(600, 100)], Qt.AltModifier)
attendu = QColor(*[int(v) for v in original[100, 600]]).name()
verifier(QColor(f.opt_couleur.couleur).name() == attendu, f"Alt+clic : couleur prise {f.opt_couleur.couleur}")
verifier(np.array_equal(rgb(doc.image), original), "la pipette ne peint pas")
# verrou
f.historique.push(__import__("chrypix.fenetre", fromlist=["CommandeEtat"]).CommandeEtat(
    doc, doc.etat(), doc.etat_calque_modifie(0, verrou=True), "verrou"))
nb = f.historique.index()
souris([(100, 600), (300, 600)])
verifier(f.historique.index() == nb and np.array_equal(rgb(doc.image), original), "calque verrouillé : refusé")
f.historique.undo()

# ------------------------------------------------------------------ tampon
f._actions_outils[TAMPON].trigger()
verifier(not f.opt_retouche.isHidden() and f.opt_couleur.isHidden(), "Tampon : opacité, dureté, pas de couleur")
app.processEvents()
verifier(f.options.isVisible() and f.valeur_zoom.isVisible(), "barre du haut : options et zoom visibles")
f.opt_opacite.setValue(100)
nb = f.historique.index()
souris([(500, 500), (520, 500)])
verifier(f.historique.index() == nb, "tampon sans source : refusé")
souris([(100, 100)], Qt.AltModifier)                  # source
souris([(700, 500), (760, 500)])                      # peint : copie de (100,100)..(160,100)
img = rgb(doc.image)
verifier(np.abs(img[500, 730] - original[100, 130]).max() <= 2, "tampon : la zone source est recopiée")
souris([(700, 600)])                                  # coup suivant : même décalage (aligné)
img = rgb(doc.image)
verifier(np.abs(img[600, 700] - original[200, 100]).max() <= 2, "tampon aligné : même décalage au coup suivant")
c.grab().save(str(sortie / "tampon.png"))
f.historique.undo()
f.historique.undo()
verifier(np.array_equal(rgb(doc.image), original), "Ctrl+Z -> photo d'origine")

f.grab().save(str(sortie / "fenetre_outils.png"))
f.doc.modifie = False
f.close()
print("ERREURS : " + (", ".join(erreurs) if erreurs else "aucune"))
sys.stdout.flush()
os._exit(1 if erreurs else 0)
