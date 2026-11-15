"""Calques de forme modifiables (outil Formes) et outil Plume (tracés en courbes -> calque de forme ou sélection).
Usage : essai_formes_plume.py dossier_sortie   (une image d'essai est fabriquée ; le moteur n'est pas démarré)"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PIL import Image
from PySide6.QtCore import QEvent, QPointF, Qt, QTimer
from PySide6.QtGui import QColor, QKeyEvent, QMouseEvent, QPainterPath
from PySide6.QtWidgets import QApplication
from pixane import calque_forme as cf
from pixane.canevas import FORMES, GOMME_CALQUE, PLUME
from pixane.fenetre import Fenetre
from pixane.moteur import Moteur

Moteur.demarrer = lambda self, signaler=None: (_ for _ in ()).throw(Exception("moteur désactivé pour l'essai"))
Fenetre._moteur_en_echec = lambda self, *a: None
sortie = Path(sys.argv[1])
sortie.mkdir(parents=True, exist_ok=True)
Image.fromarray(np.full((300, 400, 3), 240, np.uint8)).save(sortie / "formes.png")
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


# 1. calcul
ch = QPainterPath()
ch.addRect(10, 10, 100, 50)
t = cf.traces_depuis_chemin(ch)
verifier(len(t) == 1 and t[0][0] and len(t[0][1]) == 4, "rectangle : 4 points, fermé")
t = cf.traces_depuis_chemin(cf.chemin_genre("ellipse", QPointF(0, 0), QPointF(100, 60)))
verifier(t[0][0] and len(t[0][1]) == 4 and any(p[4:] != p[:2] for p in t[0][1]), "ellipse : 4 points en courbe")
t = cf.traces_depuis_chemin(cf.chemin_genre("etoile", QPointF(0, 0), QPointF(100, 100), 5))
verifier(len(t[0][1]) == 10, "étoile à 5 branches : 10 points")
f = cf.Forme(t, "#ffff0000", "#ff000000", 3.0, False, "etoile")
g = cf.Forme.depuis_dict(f.vers_dict())
verifier(len(g.traces[0][1]) == 10 and g.remplissage == f.remplissage and g.epaisseur == 3.0, "enregistrée / relue")
h = cf.deplacer_point(cf.Forme(cf.traces_depuis_chemin(cf.chemin_genre("ellipse", QPointF(0, 0), QPointF(100, 60)))),
                      0, 0, "b", 200, 200)
x, y, ax, ay, bx, by = h.traces[0][1][0]
verifier((bx, by) == (200, 200) and abs(ax - (2 * x - 200)) < 1e-6, "poignée tirée : l'autre suit en miroir")

# 2. outil Formes dans Pixane
app = QApplication(sys.argv)
from pixane.document import FORMAT_IMAGE, Document, tableau
fen = Fenetre()
fen.resize(1440, 920)
fen.show()
fen.charger(str(sortie / "formes.png"))
app.processEvents()
doc, c = fen.doc, fen.canevas


def souris(type_, x, y, mods=Qt.NoModifier):
    e = c.vers_ecran(QPointF(x, y))
    bouton = Qt.LeftButton if type_ != QEvent.MouseMove else Qt.NoButton
    boutons = Qt.NoButton if type_ == QEvent.MouseButtonRelease else Qt.LeftButton
    c.event(QMouseEvent(type_, e, e, bouton, boutons, mods))
    app.processEvents()


def glisser(x0, y0, x1, y1, n=6, mods=Qt.NoModifier):
    souris(QEvent.MouseButtonPress, x0, y0, mods)
    for k in range(1, n + 1):
        souris(QEvent.MouseMove, x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n, mods)
    souris(QEvent.MouseButtonRelease, x1, y1, mods)


def clic(x, y, mods=Qt.NoModifier):
    souris(QEvent.MouseButtonPress, x, y, mods)
    souris(QEvent.MouseButtonRelease, x, y, mods)


def touche(k):
    c.keyPressEvent(QKeyEvent(QEvent.KeyPress, k, Qt.NoModifier))
    app.processEvents()


def px(i=None):
    k = doc.actif if i is None else i
    return tableau(doc.calques[k].image.convertToFormat(FORMAT_IMAGE)).astype(int)


fen._choisir_outil(FORMES)
verifier(fen.opt_formes.isVisible() and fen.opt_genre.isVisible() and not fen.opt_mode_plume.isVisible(),
         "Formes : barre du haut (genre, remplissage, contour)")
fen.opt_genre.setCurrentIndex(fen.opt_genre.findData("rectangle"))
fen.opt_remplir.setChecked(True)
fen.opt_contour.setChecked(False)
fen.opt_couleur_forme.valeur = "#2040e0"
fen.opt_couleur_forme.change.emit("#2040e0")
n = len(doc.calques)
glisser(50, 50, 150, 120)
fo = cf.valide(doc.calque_actif)
a = px()
verifier(len(doc.calques) == n + 1 and fo is not None and fo.genre == "rectangle", "un calque de forme modifiable")
verifier(tuple(a[85, 100, :3]) == (32, 64, 224) and a[30, 100, 3] == 0, f"rectangle rempli de bleu ({a[85, 100].tolist()})")
from pixane.calques import PanneauCalques  # noqa: F401  (le panneau montre « forme modifiable »)
fen._choisir_outil(FORMES)
fen.opt_couleur_forme.valeur = "#10a010"
fen.opt_couleur_forme.change.emit("#10a010")
a = px()
verifier(tuple(a[85, 100, :3]) == (16, 160, 16) and fen.historique.undoText() == "Modifier la forme",
         f"couleur changée dans la barre : forme redessinée ({a[85, 100].tolist()})")
fen.opt_contour.setChecked(True)
fen.opt_epaisseur.setValue(8)
a = px()
verifier(a[50, 100, 3] == 255 and tuple(a[50, 100, :3]) == (0, 0, 0), "contour noir ajouté")
fen.historique.undo()
fen.historique.undo()
fen.historique.undo()
verifier(tuple(px()[85, 100, :3]) == (32, 64, 224), "Annuler : de nouveau bleu, sans contour")
# déplacé, agrandi, enregistré : reste modifiable
doc.appliquer_etat(doc.etat_taille(800, 600))
fo = cf.valide(doc.calque_actif)
verifier(fo is not None and abs(fo.traces[0][1][0][0] - 100) < 0.01, "image agrandie : forme redessinée nette")
fichier = Path(os.environ.get("TEMP", ".")) / "essai_formes_plume.pixane"
doc.enregistrer(fichier)
d2 = Document.ouvrir(fichier)
verifier(sum(cf.valide(k) is not None for k in d2.calques) == 1, "rouvert : toujours un calque de forme")
fichier.unlink(missing_ok=True)
doc.appliquer_etat(doc.etat_taille(400, 300))
# étoile et flèche
fen.opt_genre.setCurrentIndex(fen.opt_genre.findData("etoile"))
verifier(fen.opt_cotes.isVisible(), "étoile : nombre de branches")
glisser(200, 150, 300, 250)
verifier(len(cf.valide(doc.calque_actif).traces[0][1]) == 10, "étoile dessinée (10 points)")
fen.opt_genre.setCurrentIndex(fen.opt_genre.findData("fleche"))
verifier(not fen.opt_remplir.isVisible(), "flèche : pas de remplissage")
glisser(20, 280, 180, 280)
fo = cf.valide(doc.calque_actif)
verifier(fo.fleche and fo.contour and px()[280, 178, 3] > 0, "flèche dessinée avec sa pointe")
# gomme : devient une image
messages = []
c.refus.connect(messages.append)
fen._choisir_outil(GOMME_CALQUE)
clic(100, 280)
verifier(cf.valide(doc.calque_actif) is None and any("forme" in m for m in messages),
         "gomme : le calque de forme devient une image (message)")
fen.historique.undo()
verifier(cf.valide(doc.calque_actif) is not None, "Ctrl+Z : de nouveau un calque de forme")

# 3. Plume
fen._choisir_outil(PLUME)
verifier(fen.opt_mode_plume.isVisible() and not fen.opt_genre.isVisible(), "Plume : barre du haut (mode)")
fen.opt_mode_plume.setCurrentIndex(0)
fen.opt_remplir.setChecked(True)
fen.opt_contour.setChecked(False)
fen.opt_couleur_forme.valeur = "#c02020"
fen.opt_couleur_forme.change.emit("#c02020")
n = len(doc.calques)
doc.actif = 0
clic(60, 160)
glisser(160, 160, 190, 200)                        # point en courbe
clic(110, 260)
verifier(c.plume_points is not None and len(c.plume_points) == 3, "3 points posés")
verifier(c.plume_points[1][4:] == [190.0, 200.0] and c.plume_points[1][2:4] == [130.0, 120.0],
         "glisser : point en courbe, poignées symétriques")
clic(60, 160)                                      # premier point : fermé
fo = cf.valide(doc.calque_actif)
verifier(c.plume_points is None and len(doc.calques) == n + 1 and fo is not None and fo.traces[0][0],
         "clic sur le premier point : tracé fermé -> calque de forme")
a = px()
verifier(tuple(a[200, 110, :3]) == (192, 32, 32), f"forme remplie de rouge ({a[200, 110].tolist()})")
verifier(fen.historique.undoText() == "Plume", "une étape « Plume » dans Annuler")
# modifier un point de la forme
x0, y0 = fo.traces[0][1][2][:2]
glisser(x0, y0, x0, y0 + 30)
fo2 = cf.valide(doc.calque_actif)
verifier(abs(fo2.traces[0][1][2][1] - (y0 + 30)) < 0.5 and fen.historique.undoText() == "Modifier le tracé",
         "point de la forme déplacé à la souris")
fen.historique.undo()
verifier(abs(cf.valide(doc.calque_actif).traces[0][1][2][1] - y0) < 0.5, "Annuler : le point revient")
# tracé ouvert (Entrée) : un trait
doc.actif = 0
clic(250, 40)
clic(350, 40)
clic(350, 100)
touche(Qt.Key_Return)
fo = cf.valide(doc.calque_actif)
verifier(fo is not None and not fo.traces[0][0] and fo.contour and not fo.remplissage, "Entrée : tracé ouvert -> trait")
# Échap : abandon
n = len(doc.calques)
clic(20, 20)
clic(40, 20)
touche(Qt.Key_Escape)
verifier(c.plume_points is None and len(doc.calques) == n, "Échap : tracé abandonné")
# vers sélection
fen.opt_mode_plume.setCurrentIndex(1)
doc.actif = 0
clic(20, 20)
clic(120, 20)
clic(120, 100)
clic(20, 20)
from pixane.document import masque
m = masque(doc.selection)
verifier(m[50, 90] > 200 and m[90, 30] == 0 and fen.historique.undoText() == "Tracé vers sélection",
         "mode Sélection : le tracé fermé devient une sélection")
fen.grab().save(str(sortie / "formes_plume.png"))

print("ERREURS :", erreurs if erreurs else "aucune")
doc.modifie = False
sys.stdout.flush()
QTimer.singleShot(200, fen.close)
app.exec()
sys.exit(1 if erreurs else 0)
