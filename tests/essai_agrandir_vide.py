"""Agrandir une image entourée de vide (photo carrée collée dans une image plus large) : l'IA part de la photo et
remplit le vide autour, puis l'agrandissement éventuel ; sans vide, rien ne change.
Usage : essai_agrandir_vide.py"""
import io
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PIL import Image
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from pixane.document import FORMAT_IMAGE, Calque, Document, image_vide, qimage_rgb, qimage_rgba, tableau
from pixane.fenetre import Fenetre
from pixane.moteur import Moteur

Moteur.demarrer = lambda self, signaler=None: None
Fenetre._moteur_en_echec = lambda self, *a: None
lances = []
Fenetre._lancer = lambda self, titre, sel, fab, apres=None, png=None, placer=None, **kw: lances.append(
    dict(titre=titre, png=png, apres=apres, placer=placer))
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


app = QApplication(sys.argv)
f = Fenetre()
f.show()
f.a_ia_nouveau_calque.setChecked(False)
f.barre_agrandir.pleine.setChecked(False)

# image 600 × 300 : une photo carrée 300 × 300 au milieu, vide transparent à gauche et à droite
rgba = np.zeros((300, 600, 4), np.uint8)
yy, xx = np.mgrid[0:300, 0:300]
rgba[:, 150:450, 0] = 40 + xx * 0.5
rgba[:, 150:450, 1] = 90
rgba[:, 150:450, 2] = 60 + yy * 0.4
rgba[:, 150:450, 3] = 255
doc = Document(calques=[Calque("Photo collée", qimage_rgba(rgba))])
f._installer_document(doc)
verifier(doc.contenu() == (150, 0, 450, 300), f"partie visible trouvée {doc.contenu()}")

f.ia_agrandir()
b = f.barre_agrandir
verifier(b.isVisible() and b.info_vide.isVisible() and b.b_lancer.isEnabled(),
         "barre Agrandir : message « vide rempli », Lancer possible sans tirer le cadre")
verifier(not b.abime["haut"].isEnabled(), "bord abîmé : pas utilisé quand il y a du vide")
f._lancer_agrandir()
l = lances[-1]
toile = np.asarray(Image.open(io.BytesIO(l["png"])).convert("RGBA"))
h, w = toile.shape[:2]
verifier(abs(w / h - 2) < 0.02, f"toile envoyée à l'IA : proportions de l'image entière ({w} × {h})")
a = toile[:, :, 3]
verifier(a[h // 2, w // 2] == 255 and a[h // 2, 3] == 0 and a[h // 2, w - 4] == 0,
         "toile : la photo au milieu, le vide à gauche et à droite marqué « à remplir »")
# l'IA « remplit » : on rend la toile avec les côtés peints en orange
flux = toile[:, :, :3].copy()
flux[a < 128] = [230, 140, 30]
res = l["apres"](qimage_rgb(np.ascontiguousarray(flux)))
verifier((res.width(), res.height()) == (600, 300), f"résultat à la taille de l'image ({res.width()} × {res.height()})")
doc.appliquer_etat(l["placer"](res))
k = tableau(doc.calques[0].image.convertToFormat(FORMAT_IMAGE)).astype(int)
verifier(doc.taille() == (600, 300) and len(doc.calques) == 1, "même taille, toujours un seul calque")
verifier(k[150, 20, 3] == 255 and abs(k[150, 20, 0] - 230) < 25 and k[150, 580, 3] == 255,
         f"le vide à gauche et à droite est rempli {k[150, 20]} {k[150, 580]}")
verifier(np.abs(k[:, 200:400, :3] - rgba[:, 200:400, :3].astype(int)).max() <= 2,
         "la photo carrée n'a pas changé")

# avec un agrandissement en plus (100 px en haut) : vide rempli + ajout
doc = Document(calques=[Calque("Photo collée", qimage_rgba(rgba))])
f._installer_document(doc)
f.ia_agrandir()
f.canevas.cadre = (100, 0, 0, 0)
b.definir_px((100, 0, 0, 0), (0, 0, 0, 0))
f._lancer_agrandir()
l = lances[-1]
toile = np.asarray(Image.open(io.BytesIO(l["png"])).convert("RGBA"))
flux = toile[:, :, :3].copy()
flux[toile[:, :, 3] < 128] = [230, 140, 30]
res = l["apres"](qimage_rgb(np.ascontiguousarray(flux)))
doc.appliquer_etat(l["placer"](res))
k = tableau(doc.image.convertToFormat(FORMAT_IMAGE)).astype(int)
verifier(doc.taille() == (600, 400) and k[30, 300, 3] == 255 and k[250, 20, 3] == 255,
         f"vide + 100 px en haut : {doc.taille()}, tout est rempli")

# image sans vide : comportement d'avant (pas de message, bord abîmé utilisable)
plein = np.full((200, 300, 3), 120, np.uint8)
doc = Document(qimage_rgb(plein))
f._installer_document(doc)
f.ia_agrandir()
verifier(doc.contenu() is None and not b.info_vide.isVisible() and b.abime["haut"].isEnabled()
         and not b.b_lancer.isEnabled(), "image sans vide : Agrandir comme avant")
f._fin_agrandir()

print("ERREURS :", erreurs if erreurs else "aucune")
sys.stdout.flush()
for dd in f.documents:
    dd.modifie = False
f.close()
sys.exit(1 if erreurs else 0)
