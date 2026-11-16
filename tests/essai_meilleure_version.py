"""Meilleure version d'un calque (comme un objet dynamique de Photoshop) : réduire, valider, faire autre chose,
enregistrer, rouvrir, puis réagrandir redonne l'image d'origine, sans perte ; par Transformer, l'outil Déplacer,
Taille de l'image, pivoter, retourner. Modifier les pixels (pinceau, IA…) fait de la version actuelle la nouvelle
référence. Usage : essai_meilleure_version.py"""
import os
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PySide6.QtCore import QPoint, QPointF
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from pixane.document import (FORMAT_IMAGE, Calque, Document, image_entiere, origine_valide, qimage_rgba,
                             tableau)
from pixane.fenetre import Fenetre

erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


app = QApplication(sys.argv)
f = Fenetre()
f.show()
W = H = 800
rng = np.random.default_rng(5)
photo = np.zeros((H, W, 4), np.uint8)
photo[200:600, 200:600, :3] = rng.integers(0, 256, (400, 400, 3))       # plein de détails fins (comme un upscale)
photo[200:600, 200:600, 3] = 255
fond = np.full((H, W, 4), 255, np.uint8)


def pixels(c):
    img, x, y = image_entiere(c)
    a = tableau(img.convertToFormat(FORMAT_IMAGE))
    ys, xs = np.nonzero(a[:, :, 3])
    return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1], (x + xs.min(), y + ys.min())


ORIGINE = photo[200:600, 200:600]


def nouveau():
    doc = Document(calques=[Calque("Fond", qimage_rgba(fond)), Calque("Photo", qimage_rgba(photo))])
    doc.actif = 1
    f._installer_document(doc)
    return doc


def transformer(echelle=None, angle=None, deplacer=(0, 0), miroir=False):
    f.transformer()
    t = f.canevas.transfo
    if echelle is not None:
        t.sx, t.sy = echelle * (1 if t.sx >= 0 else -1), echelle * (1 if t.sy >= 0 else -1)
    if angle is not None:
        t.angle = angle
    if miroir:
        t.sx = -t.sx
    t.centre = t.centre + QPointF(*deplacer)
    f._valider_transfo()


def pareil(c, texte, place=None):
    a, p = pixels(c)
    ok = a.shape == ORIGINE.shape and np.array_equal(a, ORIGINE)
    if place is not None:
        ok = ok and p == place
    verifier(ok, texte + ("" if ok else f" (taille {a.shape[:2]}, place {p}, "
                          f"écart {np.abs(a.astype(int) - ORIGINE).mean() if a.shape == ORIGINE.shape else '-'})"))


# 1. réduire, valider, réagrandir : sans perte
doc = nouveau()
transformer(0.25)
c = doc.calques[1]
verifier(origine_valide(c) is not None and pixels(c)[0].shape[:2] == (100, 100), "réduit à 25 % et validé")
f._choisir_outil("pinceau") if hasattr(f, "_choisir_outil") else None
transformer(1.0)
pareil(doc.calques[1], "réagrandi plus tard : l'image d'origine revient, pixel pour pixel", place=(200, 200))
# 2. plusieurs étapes, rotation, miroir, déplacements à l'outil Déplacer et alignement entre les deux
doc = nouveau()
transformer(0.5, angle=30, deplacer=(-120, 40))
avant = doc.etat()
img, x, y = image_entiere(doc.calques[1])
doc.apercu_calque_entier(1, img, x + 37, y - 15, avant=avant[0][1], decalage=(37, -15))     # outil Déplacer
verifier(origine_valide(doc.calques[1]) is not None, "outil Déplacer : la meilleure version suit le calque")
doc.appliquer_etat(doc.etat_aligner([1], "gauche"))
verifier(origine_valide(doc.calques[1]) is not None, "Aligner : la meilleure version suit le calque")
transformer(0.3, angle=-75, miroir=True)
transformer(0.8)
transformer(1.0, angle=0, miroir=True)
a, p = pixels(doc.calques[1])
pareil(doc.calques[1], "réduit, tourné, déplacé, aligné, retourné… puis remis à 100 % : aucune perte")
# 3. Image > Taille de l'image : réduire toute l'image puis la réagrandir
doc = nouveau()
doc.appliquer_etat(doc.etat_taille(200, 200))
verifier(doc.taille() == (200, 200), "image entière réduite à 200 × 200")
doc.appliquer_etat(doc.etat_taille(800, 800))
pareil(doc.calques[1], "Taille de l'image : réduite puis réagrandie, sans perte", place=(200, 200))
# 4. pivoter l'image (4 × 90°) et miroir de l'image
doc = nouveau()
transformer(0.4)
for _ in range(4):
    doc.appliquer_etat(doc.etat_pivote(90))
doc.appliquer_etat(doc.etat_miroir(True))
doc.appliquer_etat(doc.etat_miroir(True))
transformer(1.0)
pareil(doc.calques[1], "image pivotée et retournée entre-temps : toujours sans perte", place=(200, 200))
# 5. enregistrer, rouvrir, réagrandir
doc = nouveau()
transformer(0.2)
with tempfile.TemporaryDirectory() as d:
    chemin = Path(d) / "essai.piximg"
    doc.enregistrer(chemin)
    doc2 = Document.ouvrir(chemin)
    doc2.actif = 1
    f._installer_document(doc2)
    verifier(origine_valide(doc2.calques[1]) is not None, "projet rouvert : la meilleure version est là")
    transformer(1.0)
    pareil(doc2.calques[1], "projet rouvert puis réagrandi : sans perte", place=(200, 200))
    doc2.modifie = False
# 6. annuler / rétablir
doc = nouveau()
transformer(0.3)
transformer(1.0)
f.historique.undo()
verifier(pixels(doc.calques[1])[0].shape[:2] == (120, 120) and origine_valide(doc.calques[1]) is not None,
         "Ctrl+Z : le calque réduit revient, sa meilleure version aussi")
f.historique.redo()
pareil(doc.calques[1], "rétablir : de nouveau l'image d'origine")
# 7. pixels modifiés (pinceau, IA…) : la version actuelle devient la référence
doc = nouveau()
transformer(0.5)
img, x, y = image_entiere(doc.calques[1])
a = tableau(img.convertToFormat(FORMAT_IMAGE)).copy()
a[a[:, :, 3] > 0] = [0, 200, 0, 255]
doc.appliquer_etat(doc.etat_calque_entier(1, qimage_rgba(a), x, y))
verifier(origine_valide(doc.calques[1]) is None, "calque repeint : l'ancienne meilleure version n'est plus utilisée")
transformer(2.0)
b, _ = pixels(doc.calques[1])
verifier(b.shape[:2] == (400, 400) and abs(b[50:350, 50:350, 1].mean() - 200) < 2,
         "réagrandi : c'est bien la version repeinte (pas l'ancienne image)")
# 8. sélection : seul l'élément sélectionné est transformé (pas de meilleure version mélangée)
doc = nouveau()
transformer(0.5)
from pixane.document import nouvelle_selection
from PySide6.QtCore import QRect
from PySide6.QtGui import QPainter, QColor
sel = nouvelle_selection(W, H)
p = QPainter(sel)
p.fillRect(QRect(300, 300, 50, 50), QColor(0, 0, 0, 255))
p.end()
doc.selection = sel
transformer(0.5)
verifier(origine_valide(doc.calques[1]) is None, "transformer une partie sélectionnée : nouvelle référence")
# 9. calque vide, texte : rien de cassé
doc = nouveau()
doc.appliquer_etat(doc.etat_taille(400, 400))
verifier(origine_valide(doc.calques[0]) is not None and origine_valide(doc.calques[1]) is not None,
         "Taille de l'image : chaque calque d'image garde sa meilleure version")
# 10. calque qui dépasse de la feuille (collage) transformé puis enregistré en .piximg (bug : position prise pour
#     l'image -> « 'QPoint' object has no attribute 'convertToFormat' »)
doc = nouveau()
img = qimage_rgba(photo[200:600, 200:600].copy())
doc.appliquer_etat(doc.etat_coller(img, QPoint(-150, -100)))
c = doc.calques[doc.actif]
verifier(c.hors is not None and origine_valide(c) is None, "collage qui dépasse, sans meilleure version")
transformer(0.6)
o = origine_valide(doc.calques[doc.actif])
verifier(o is not None and isinstance(o.image, QImage), "Transformer : la meilleure version est bien une image")
import tempfile  # noqa: E402
with tempfile.TemporaryDirectory() as tmp:
    chemin = Path(tmp) / "depasse.piximg"
    try:
        doc.enregistrer(chemin)
        ok = chemin.stat().st_size > 1000
    except Exception as e:  # noqa: BLE001
        ok = False
        print("   ", e)
    verifier(ok, "enregistré en .piximg après Transformer d'un calque qui dépasse")
    transformer(1.0)
    verifier(isinstance(origine_valide(doc.calques[doc.actif]).image, QImage), "re-transformé : toujours une image")

print("ERREURS :", erreurs if erreurs else "aucune")
sys.stdout.flush()
for dd in f.documents:
    dd.modifie = False
f.close()
sys.exit(1 if erreurs else 0)
