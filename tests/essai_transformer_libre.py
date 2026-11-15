"""Ctrl+T en perspective, distordre et déformation (Édition > Transformation), Ctrl+coin, gestes annulés ;
Image > Recadrage en perspective.
Usage : essai_transformer_libre.py dossier_sortie   (une image d'essai est fabriquée ; le moteur n'est pas démarré)"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PIL import Image, ImageDraw
from PySide6.QtCore import QEvent, QPointF, QRect, Qt, QTimer
from PySide6.QtGui import QColor, QImage, QKeyEvent, QMouseEvent, QPainter
from PySide6.QtWidgets import QApplication
from pixane.fenetre import Fenetre
from pixane.moteur import Moteur

Moteur.demarrer = lambda self, signaler=None: (_ for _ in ()).throw(Exception("moteur désactivé pour l'essai"))
Fenetre._moteur_en_echec = lambda self, *a: None
sortie = Path(sys.argv[1])
sortie.mkdir(parents=True, exist_ok=True)
# fond noir avec un « tableau » blanc vu de biais (quadrilatère), pour le recadrage en perspective
fond = Image.new("RGB", (600, 400), (0, 0, 0))
QUAD = [(120, 60), (470, 100), (450, 330), (100, 360)]
ImageDraw.Draw(fond).polygon(QUAD, fill=(255, 255, 255))
fond.save(sortie / "biais.png")

app = QApplication(sys.argv)
from pixane.document import Calque, FORMAT_IMAGE, image_vide, tableau
from pixane.transformation import Transformation
f = Fenetre()
f.resize(1440, 920)
f.show()
f.charger(str(sortie / "biais.png"))
app.processEvents()
doc, c = f.doc, f.canevas
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


def souris(type_, x, y, bouton=Qt.LeftButton, mods=Qt.NoModifier):
    e = c.vers_ecran(QPointF(x, y))
    boutons = Qt.NoButton if type_ == QEvent.MouseButtonRelease else bouton
    c.event(QMouseEvent(type_, e, e, bouton if type_ != QEvent.MouseMove else Qt.NoButton, boutons, mods))


def tirer(x0, y0, x1, y1, mods=Qt.NoModifier):
    souris(QEvent.MouseButtonPress, x0, y0, mods=mods)
    for k in (0.5, 1.0):
        souris(QEvent.MouseMove, x0 + (x1 - x0) * k, y0 + (y1 - y0) * k, mods=mods)
    souris(QEvent.MouseButtonRelease, x1, y1, mods=mods)
    app.processEvents()


def touche(k):
    c.keyPressEvent(QKeyEvent(QEvent.KeyPress, k, Qt.NoModifier))
    app.processEvents()


def alpha(i):
    return tableau(doc.calques[i].image.convertToFormat(FORMAT_IMAGE))[..., 3]


# 1. moteur : perspective, distordre, déformation
img = QImage(400, 300, QImage.Format_ARGB32_Premultiplied)
img.fill(QColor(200, 50, 50))
t = Transformation(img, QRect(0, 0, 400, 300))
t.passer_mode("perspective")
t.commencer("hd", QPointF(400, 0))
t.glisser(QPointF(400, 60), False)
verifier([(round(p.x()), round(p.y())) for p in t.quad] == [(0, 0), (400, 60), (400, 240), (0, 300)],
         "perspective : le bord droit rétrécit (coin du bas en miroir)")
t.commencer("hd", t.quad[1])
t.glisser(t.quad[1] + QPointF(50, 0), False)
verifier(round(t.quad[0].x()) == -50, "perspective tirée de côté : le bord du haut s'élargit des deux côtés")
t.passer_mode("distordre")
t.commencer("bg", t.quad[3])
t.glisser(t.quad[3] + QPointF(30, -20), False)
verifier(round(t.quad[3].x()) == 30 and round(t.quad[2].y()) == 240, "distordre : le coin bouge seul")
t.commencer("b", (t.quad[2] + t.quad[3]) / 2)
t.glisser((t.quad[2] + t.quad[3]) / 2 + QPointF(0, 20), False)
verifier(round(t.quad[3].y()) == 300 and round(t.quad[2].y()) == 260, "distordre : milieu de bord = tout le bord")
t.passer_mode("deformation")
verifier(t.maille is not None and len(t.maille) == 16 and t.quad is None, "déformation : grille de 16 points")
coin = QPointF(t.maille[0])
t.commencer("m0", coin)
t.glisser(coin + QPointF(-10, -10), False)
verifier(t.maille[0] == coin + QPointF(-10, -10) and t.maille[4].y() != t.maille[8].y(),
         "déformation : le coin emmène ses poignées")
t2 = Transformation(img, QRect(0, 0, 400, 300))
t2.passer_mode("deformation")
t2.commencer("m5", t2.maille[5])
t2.glisser(t2.maille[5] + QPointF(-50, -40), False)
r, x, y = t2.rendu_entier(True)
a = tableau(r)[..., 3]
verifier(a[a.shape[0] // 2, a.shape[1] // 2] == 255 and a[a.shape[0] // 3:-4, a.shape[1] // 3:-4].min() == 255,
         "déformation : rendu sans fente entre les morceaux")

# 2. dans la fenêtre : Édition > Transformation > Perspective sur un calque
carre = image_vide(600, 400)
p = QPainter(carre)
p.fillRect(200, 100, 200, 200, QColor(255, 0, 0))
p.end()
doc.calques = doc.calques + (Calque("Carré", carre),)
doc.actif = 1
doc._fusion = None
f._installer_document(doc)
app.processEvents()
f.a_transfo_perspective.trigger()
app.processEvents()
tr_ = c.transfo
verifier(tr_ is not None and tr_.mode == "perspective" and f.mode_transfo.currentData() == "perspective"
         and f.opt_transfo.isVisible() and not f.cases_transfo["a"].isEnabled(),
         "menu Transformation > Perspective : mode choisi, cases de taille grisées")
tirer(400, 100, 400, 150)                       # coin haut droit vers le bas
verifier(round(tr_.quad[2].y()) == 250, "à la souris : le coin du bas droit remonte en miroir")
f.retour()                                      # Ctrl+Z pendant la transformation : défait le geste
verifier(c.transfo is not None and round(c.transfo.quad[1].y()) == 100, "Ctrl+Z : le geste est défait")
f.suivant()
verifier(round(c.transfo.quad[1].y()) == 150, "Ctrl+Y : refait")
touche(Qt.Key_Return)
a = alpha(1)
verifier(c.transfo is None and a[110, 395] == 0 and a[200, 395] == 255 and a[110, 205] == 255,
         "validé : le carré est en perspective (bord droit plus court)")
f.historique.undo()
a = alpha(1)
verifier(a[110, 395] == 255, "Annuler : le carré revient")

# 3. Ctrl+coin en mode libre : distordre
f.transformer()
tr_ = c.transfo
verifier(tr_ is not None and tr_.mode == "libre" and f.cases_transfo["l"].isEnabled(), "Ctrl+T : mode libre")
tirer(200, 300, 240, 340, mods=Qt.ControlModifier)
verifier(tr_.mode == "distordre" and f.mode_transfo.currentData() == "distordre"
         and round(tr_.quad[3].x()) == 240 and round(tr_.quad[2].x()) == 400, "Ctrl+coin : le coin bouge seul")
f.mode_transfo.setCurrentIndex(f.mode_transfo.findData("deformation"))
f._mode_transfo_choisi()
verifier(tr_.maille is not None, "liste Mode : Déformation")
tirer(*(lambda p: (p.x(), p.y()))(tr_.maille[5]), 230, 110)
touche(Qt.Key_Return)
verifier(c.transfo is None and f.historique.undoText() != "", "déformation validée")
f.historique.undo()
f.transformer()
touche(Qt.Key_Escape)
verifier(c.transfo is None and alpha(1)[110, 395] == 255, "Échap : rien ne change")

# 4. recadrage en perspective
doc.actif = 0
f.a_recadrage_persp.trigger()
verifier(c.persp is not None and f.opt_persp.isVisible() and c.travail() == "persp", "Recadrage en perspective : 4 coins")
cible = [QPointF(*p) for p in QUAD]
for i in range(4):
    depart = c.persp[i]
    tirer(depart.x(), depart.y(), cible[i].x(), cible[i].y())
verifier(all((c.persp[i] - cible[i]).manhattanLength() < 1.5 for i in range(4)), "coins posés à la souris")
f.retour()
verifier((c.persp[3] - cible[3]).manhattanLength() > 5, "Ctrl+Z : dernier coin remis")
f.suivant()
n = f.historique.index()
touche(Qt.Key_Return)
w, h = doc.taille()
px = tableau(doc.image.convertToFormat(FORMAT_IMAGE))
verifier(c.persp is None and f.historique.index() == n + 1 and (w, h) == (352, 301),
         f"recadré : rectangle droit, bords les plus longs : 352 × 301 ({w} × {h})")
px = tableau(doc.calques[0].image.convertToFormat(FORMAT_IMAGE))
interieur = px[4:-4, 4:-4, :3]
verifier(interieur.min() > 200, f"le tableau remplit toute l'image (plus sombre : {interieur.min()})")
verifier(len(doc.calques) == 2 and doc.calques[1].image.size() == doc.calques[0].image.size(),
         "tous les calques à la nouvelle taille")
f.historique.undo()
verifier(doc.taille() == (600, 400), "Annuler : taille d'origine")
f.a_recadrage_persp.trigger()
touche(Qt.Key_Escape)
verifier(c.persp is None and not f.opt_persp.isVisible() and doc.taille() == (600, 400), "Échap : annulé")

print("ERREURS :", erreurs if erreurs else "aucune")
doc.modifie = False
QTimer.singleShot(200, f.close)
app.exec()
os._exit(1 if erreurs else 0)
