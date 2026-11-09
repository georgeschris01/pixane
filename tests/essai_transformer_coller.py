"""Coller une image plus grande que la photo (réduite, cadre Transformer ouvert, rien de perdu) et Transformer (Ctrl+T)
seulement la sélection. Usage : essai_transformer_coller.py"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication

from pixane.document import FORMAT_IMAGE, Document, nouvelle_selection, tableau
from pixane.fenetre import Fenetre
from pixane.moteur import Moteur

Moteur.demarrer = lambda self, signaler=None: None
Fenetre._moteur_en_echec = lambda self, *a: None
erreurs = []
ROUGE, BLEU = (0, 0, 255), (255, 0, 0)          # tableau() : ordre B, V, R, alpha


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


app = QApplication(sys.argv)
f = Fenetre()
f.show()

fond = QImage(200, 100, FORMAT_IMAGE)
fond.fill(QColor(255, 255, 255))
doc = Document(fond)
f._installer_document(doc)

# 1. coller une image 800 × 400 (rouge à gauche, bleu à droite) dans une photo 200 × 100
grande = QImage(800, 400, FORMAT_IMAGE)
grande.fill(QColor(255, 0, 0))
p = QPainter(grande)
p.fillRect(400, 0, 400, 400, QColor(0, 0, 255))
p.end()
QApplication.clipboard().setImage(grande)
f.coller()
t = f.canevas.transfo
verifier(len(doc.calques) == 2 and t is not None, "collée sur un nouveau calque, cadre Transformer ouvert")
verifier(t is not None and abs(t.sx - 0.25) < 1e-6 and t.source.size() == grande.size(),
         "réduite à 25 %, toute l'image gardée dans le cadre")
a = tableau(doc.calques[1].image)
verifier(a[50, 5, 3] == 255 and a[50, 194, 3] == 255 and a[50, 5, 2] > 200 and a[50, 194, 0] > 200,
         "l'image entière tient dans la photo (rouge à gauche, bleu à droite)")
# l'agrandir de nouveau x2 puis valider : on voit le milieu, net (pas de perte due à la réduction)
t.sx = t.sy = 0.5
f._valider_transfo()
a = tableau(doc.calques[1].image)
verifier(f.canevas.transfo is None and a[50, 5, 2] > 200 and a[50, 194, 0] > 200 and a[50, 99, 3] == 255,
         "réagrandie à 50 % puis validée")
f.historique.undo()
f.historique.undo()
verifier(len(doc.calques) == 1, "Ctrl+Z deux fois : transformation puis collage annulés")

# 2. petite image : collée telle quelle, pas de cadre
petite = QImage(20, 10, FORMAT_IMAGE)
petite.fill(QColor(0, 255, 0))
QApplication.clipboard().setImage(petite)
f.coller()
verifier(f.canevas.transfo is None and len(doc.calques) == 2, "petite image : collée sans cadre")
f.historique.undo()

# 3. Ctrl+T avec une sélection : seul l'élément sélectionné bouge
calque = QImage(200, 100, FORMAT_IMAGE)
calque.fill(QColor(255, 255, 255))
p = QPainter(calque)
p.fillRect(10, 10, 20, 20, QColor(255, 0, 0))     # élément sélectionné
p.fillRect(150, 10, 20, 20, QColor(0, 0, 255))    # reste du calque
p.end()
doc2 = Document(calque)
f._installer_document(doc2)
sel = nouvelle_selection(200, 100)
p = QPainter(sel)
p.fillRect(5, 5, 30, 30, QColor(0, 0, 0, 255))
p.end()
doc2.selection = sel
f.transformer()
t = f.canevas.transfo
verifier(t is not None and (t.bw, t.bh) == (30, 30) and t.fond is not None, "cadre autour de la sélection seule")
t.centre = QPointF(100, 50)
f._valider_transfo()
a = tableau(doc2.calques[0].image)
verifier(tuple(a[50, 100, :3]) == ROUGE, "élément sélectionné déplacé au centre")
verifier(tuple(a[20, 20, :3]) != ROUGE and a[20, 20, 3] == 0, "sa place d'origine est vide")
verifier(tuple(a[20, 160, :3]) == BLEU, "le reste du calque n'a pas bougé")
verifier(doc2.rect_selection() is None, "sélection retirée après la transformation")
f.historique.undo()
verifier(tuple(tableau(doc2.calques[0].image)[20, 20, :3]) == ROUGE and doc2.rect_selection() is not None,
         "Ctrl+Z : élément et sélection revenus")

# 4. Ctrl+T sans sélection : tout le calque (inchangé)
doc2.selection = nouvelle_selection(200, 100)
f.transformer()
verifier(f.canevas.transfo is not None and f.canevas.transfo.fond is None and f.canevas.transfo.bw == 200,
         "sans sélection : tout le calque")
f._annuler_transfo()

print("ERREURS :", erreurs if erreurs else "aucune")
sys.stdout.flush()
for dd in f.documents:
    dd.modifie = False
f.close()
sys.exit(1 if erreurs else 0)
