"""Résultat de l'IA posé dans le calque choisi (pas de nouveau calque), sans déborder de la sélection ; option
« nouveau calque » ; cas où le calque choisi ne peut pas le recevoir ; Agrandir et Upscale.
Usage : essai_ia_calque.py"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication

from pixane.document import FORMAT_IMAGE, MARGE_IA, Document, nouvelle_selection, qimage_rgb, tableau
from pixane.fenetre import Fenetre
from pixane.moteur import Moteur
from pixane.texte import Texte

Moteur.demarrer = lambda self, signaler=None: None
Fenetre._moteur_en_echec = lambda self, *a: None
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


def rgb(img):
    return tableau(img.convertToFormat(FORMAT_IMAGE))[:, :, :3].astype(int)


app = QApplication(sys.argv)
f = Fenetre()
f.show()
f.a_ia_nouveau_calque.setChecked(False)


def nouveau_doc():
    fond = QImage(300, 200, FORMAT_IMAGE)
    fond.fill(QColor(120, 120, 120))
    d = Document(fond)
    f._installer_document(d)
    return d


def selection(d, x, y, w, h):
    s = nouvelle_selection(*d.taille())
    p = QPainter(s)
    p.fillRect(x, y, w, h, QColor(0, 0, 0, 255))
    p.end()
    d.selection = s


def resultat_avec_halo(d):
    """Comme Flux : la zone repeinte en vert, plus un halo de 40 px un peu changé autour, et un pixel loin."""
    r = rgb(d.image)
    r[60:140, 60:160] = [124, 120, 120]                  # halo (changement « minime »)
    r[100:180, 100:200] = [124, 120, 120]
    r[80:120, 80:140] = [20, 200, 40]                    # la zone sélectionnée, vraiment repeinte
    r[5, 290] = [0, 0, 0]                                # un pixel loin de tout
    return qimage_rgb(r.astype(np.uint8))


# 1. Remplir sur la photo (un seul calque) : dans le calque, pas de nouveau calque, rien hors de la sélection
doc = nouveau_doc()
selection(doc, 80, 80, 60, 40)
f._appliquer_resultat(doc, resultat_avec_halo(doc), "Remplir", zone=tableau(doc.selection)[:, :, 3].copy())
k = rgb(doc.calques[0].image)
verifier(len(doc.calques) == 1, "le résultat est dans le calque de la photo (pas de nouveau calque)")
verifier((k[85:115, 85:135] == [20, 200, 40]).all(), "la zone sélectionnée est repeinte")
loin = int(MARGE_IA * 3) + 2
verifier((k[60:80 - loin, 60:160] == 120).all() and (k[5, 290] == 120).all(),
         f"rien d'ajouté à plus de {loin} px de la sélection (halo et pixel lointain ignorés)")
verifier(120 < k[78, 100, 0] <= 124 and k[78 - loin + 4, 100, 0] <= 121,
         f"juste au bord : le résultat de l'IA est gardé en fondu ({k[78, 100, 0]}), puis s'éteint")
f.historique.undo()
verifier((rgb(doc.calques[0].image) == 120).all(), "Ctrl+Z : la photo revient")
f.historique.redo()

# 2. le calque bouge et change de taille : le résultat suit
avant = rgb(doc.calques[0].image)
doc.appliquer_etat(doc.etat_taille(150, 100))
k = rgb(doc.calques[0].image)
verifier(len(doc.calques) == 1 and np.abs(k[50, 55] - [20, 200, 40]).sum() < 60, "taille de l'image : le résultat suit")

# 3. option « nouveau calque » : nouveau calque, mais lui aussi limité à la sélection
doc = nouveau_doc()
f.a_ia_nouveau_calque.setChecked(True)
selection(doc, 80, 80, 60, 40)
f._appliquer_resultat(doc, resultat_avec_halo(doc), "Remplir", zone=tableau(doc.selection)[:, :, 3].copy())
a = tableau(doc.calques[-1].image)[:, :, 3]
verifier(len(doc.calques) == 2 and a[100, 100] == 255 and a[5, 290] == 0 and not a[60:80 - loin].any(),
         "option cochée : nouveau calque, sans halo ni pixel lointain")
f.a_ia_nouveau_calque.setChecked(False)

# 4. calque choisi = texte : le résultat va dans un nouveau calque (le texte reste un texte)
doc = nouveau_doc()
doc.appliquer_etat(doc.etat_nouveau_texte(Texte(texte="Titre", x=150, y=40, taille=30)))
selection(doc, 80, 80, 60, 40)
f._appliquer_resultat(doc, resultat_avec_halo(doc), "Remplir", zone=tableau(doc.selection)[:, :, 3].copy())
verifier(len(doc.calques) == 3 and doc.calques[1].texte is not None, "calque de texte choisi : nouveau calque, texte intact")

# 5. sans sélection, avec plusieurs calques : nouveau calque (sinon les autres seraient copiés dedans)
doc.actif = 0
r = rgb(doc.image)
r[:, :] = r[:, :] // 2
f._appliquer_resultat(doc, qimage_rgb(r.astype(np.uint8)), "Netteté (IA)", zone=None)
verifier(len(doc.calques) == 4, "toute l'image et plusieurs calques : nouveau calque")

# 6. Agrandir : l'ajout va dans le calque de la photo
doc = nouveau_doc()
grand = np.zeros((250, 400, 3), np.uint8)
grand[:, :] = [30, 60, 90]
grand[50:, 100:] = rgb(doc.image)
f._appliquer_resultat(doc, qimage_rgb(grand), "Agrandir",
                      lambda img: doc.etat_agrandi("Agrandir", img, (100, 50), nouveau_calque=False))
k = rgb(doc.calques[0].image)
verifier(len(doc.calques) == 1 and doc.taille() == (400, 250) and (k[10, 10] == [30, 60, 90]).all()
         and (k[100, 200] == 120).all(), "Agrandir : l'ajout est dans le calque de la photo")

# 7. Upscale d'une photo d'un seul calque : le calque est remplacé, pas de calque en plus
big = np.ascontiguousarray(np.repeat(np.repeat(rgb(doc.image), 2, 0), 2, 1).astype(np.uint8))
f._appliquer_resultat(doc, qimage_rgb(big), "Upscale")
verifier(len(doc.calques) == 1 and doc.taille() == (800, 500), "Upscale : un seul calque, agrandi")
f.historique.undo()
verifier(doc.taille() == (400, 250), "Ctrl+Z")

print("ERREURS :", erreurs if erreurs else "aucune")
sys.stdout.flush()
for dd in f.documents:
    dd.modifie = False
f.close()
sys.exit(1 if erreurs else 0)
