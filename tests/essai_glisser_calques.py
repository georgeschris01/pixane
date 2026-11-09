"""Essai : changer la place d'un calque en le glissant à la souris dans le panneau Calques (une seule entrée dans
Annuler ; entre dans un groupe ouvert et en sort, comme Monter / Descendre).

Usage : python tests/essai_glisser_calques.py
"""
import os
import sys

os.environ.setdefault("PIXANE_REGLAGES", "Pixane-essais")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PySide6.QtCore import QPoint, Qt  # noqa: E402
from PySide6.QtGui import QImage  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication(sys.argv)
from pixane.fenetre import Fenetre  # noqa: E402

f = Fenetre()
f.resize(1300, 900)
f.show()
img = QImage(400, 300, QImage.Format_ARGB32_Premultiplied)
img.fill(Qt.white)
from pixane.document import Document  # noqa: E402
f._installer_document(Document(img))
erreurs = []


def verifier(nom, ok, detail=""):
    print(("ok    " if ok else "ÉCHEC ") + nom, detail)
    if not ok:
        erreurs.append(nom)


doc = f.doc
p = f.calques
for _ in range(3):
    doc.appliquer_etat(doc.etat_nouveau_calque())
noms = lambda: [doc.calques[i].nom for i in p._indexes]          # du haut vers le bas
app.processEvents()
depart = noms()
print("départ :", depart)

# 1) glisser la ligne du haut tout en bas (vraie souris simulée)
vp = p.liste.viewport()
r0 = p.liste.visualItemRect(p.liste.item(0))
rn = p.liste.visualItemRect(p.liste.item(p.liste.count() - 1))
QTest.mousePress(vp, Qt.LeftButton, pos=r0.center())
for y in range(r0.center().y(), rn.bottom() - 2, 8):
    QTest.mouseMove(vp, QPoint(r0.center().x(), y))
QTest.mouseRelease(vp, Qt.LeftButton, pos=QPoint(r0.center().x(), rn.bottom() - 2))
app.processEvents()
verifier("haut -> bas", noms() == depart[1:] + depart[:1], noms())
verifier("calque déplacé choisi", doc.calques[doc.actif].nom == depart[0])
f.historique.undo()
app.processEvents()
verifier("une seule annulation", noms() == depart, noms())

# 2) deposer() : la ligne 3 entre la 0 et la 1
p.deposer(3, 1)
app.processEvents()
attendu = [depart[0], depart[3], depart[1], depart[2]]
verifier("bas -> 2e place", noms() == attendu, noms())
p.deposer(1, 1)
verifier("lâché sur place : rien", noms() == attendu)

# 3) groupe : un calque glissé sous un groupe ouvert y entre
f.historique.undo()
doc.actif = 3
doc.appliquer_etat(doc.etat_grouper())
app.processEvents()
print("avec groupe :", noms())
from pixane.composition import parents  # noqa: E402
bas = p._indexes[-1]
nom_bas = doc.calques[bas].nom
verifier("groupe déplacé avec son calque", noms()[:2] == ["Groupe 1", "Calque 3"], noms())
p.deposer(len(p._indexes) - 1, 2)                   # juste sous « Calque 3 », dans le groupe ouvert
app.processEvents()
i = next(k for k, c in enumerate(doc.calques) if c.nom == nom_bas)
verifier("entre dans le groupe", len(parents(doc.calques, i)) == 1, noms())

print("ERREURS :", erreurs if erreurs else "aucune")
sys.stdout.flush()
for d in f.documents:
    d.modifie = False
f.close()
sys.exit(1 if erreurs else 0)
