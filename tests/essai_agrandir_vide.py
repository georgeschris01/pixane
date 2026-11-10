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
from PySide6.QtCore import QPointF
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
# fins traits blancs dans le vide (restes d'un autre collage) : ils ne comptent pas
traits = rgba.copy()
for x in range(30, 140):
    y = int(150 + 80 * np.sin(x / 25))
    traits[y:y + 2, x] = [255, 255, 255, 200]
    traits[y:y + 2, 600 - x] = [255, 255, 255, 120]
traits[40:42, 460:590] = [255, 255, 255, 255]
dt = Document(calques=[Calque("Traits", qimage_rgba(traits))])
verifier(dt.contenu() == (150, 0, 450, 300), f"traits fins dans le vide ignorés {dt.contenu()}")
# photo collée sur un calque au-dessus d'autres calques qui ont des choses dans le vide : seul le calque choisi compte
dessous = np.zeros((300, 600, 4), np.uint8)
dessous[20:280, 20:120] = [200, 30, 30, 255]
dessous[100:160, 480:590] = [30, 30, 200, 255]
dc = Document(calques=[Calque("Dessous", qimage_rgba(dessous)), Calque("Photo collée", qimage_rgba(rgba))])
dc.actif = 1
verifier(dc.contenu() == (150, 0, 450, 300), f"calques du dessous ignorés {dc.contenu()}")
dc.actif = 0
verifier(dc.contenu() == (20, 20, 590, 280), f"calque du dessous choisi : sa partie à lui {dc.contenu()}")

f.ia_agrandir()
b = f.barre_agrandir
c = f.canevas
verifier(b.isVisible() and b.info_vide.isVisible() and not b.b_lancer.isEnabled(),
         "barre Agrandir : message « le cadre part de la photo », Lancer attend le cadre")
verifier(b.abime["haut"].isEnabled(), "bord abîmé : utilisable aussi quand il y a du vide")
r = c._rect_cadre()
p0, p1 = c.vers_ecran(QPointF(150, 0)), c.vers_ecran(QPointF(450, 300))
verifier(abs(r.left() - p0.x()) < 1 and abs(r.right() - p1.x()) < 1, "le cadre part des bords de la photo")
# aimant : tiré à gauche presque jusqu'au bord de l'image -> pile au bord
c._poignee = ("ext", {"g"})
c._tirer_cadre(c.vers_ecran(QPointF(3, 150)), False)
verifier(c.cadre[2] == 150 and b.b_lancer.isEnabled(), f"aimant : le cadre s'arrête au bord de l'image ({c.cadre})")
verifier(b.texte_taille.text().startswith("600 × 300"), f"taille finale : celle de l'image ({b.texte_taille.text()})")
c._poignee = None


def lancer(ajout, abime=(0, 0, 0, 0), photo=None):
    """Cadre (haut, bas, gauche, droite) en px depuis la photo ; l'IA « remplit » en orange."""
    d = Document(calques=[Calque("Photo collée", qimage_rgba(rgba if photo is None else photo))])
    f._installer_document(d)
    f.ia_agrandir()
    c.cadre = list(ajout)
    c.abime = list(abime)
    b.definir_px(tuple(ajout), tuple(abime))
    f._lancer_agrandir()
    l = lances[-1]
    toile = np.asarray(Image.open(io.BytesIO(l["png"])).convert("RGBA"))
    flux = toile[:, :, :3].copy()
    flux[toile[:, :, 3] < 128] = [230, 140, 30]
    d.appliquer_etat(l["placer"](l["apres"](qimage_rgb(np.ascontiguousarray(flux)))))
    return d, tableau(d.image.convertToFormat(FORMAT_IMAGE)).astype(int)


# 1. tout le vide (gauche et droite jusqu'au bord)
d, k = lancer((0, 0, 150, 150))
verifier(d.taille() == (600, 300) and len(d.calques) == 1, "tout le vide : même taille, un seul calque")
verifier(k[150, 20, 3] == 255 and abs(k[150, 20, 0] - 230) < 25 and k[150, 580, 3] == 255,
         f"le vide à gauche et à droite est rempli {k[150, 20]} {k[150, 580]}")
verifier(np.abs(k[:, 200:400, :3] - rgba[:, 200:400, :3].astype(int)).max() <= 2, "la photo carrée n'a pas changé")
# 2. seulement 50 px à gauche : le reste du vide reste transparent
d, k = lancer((0, 0, 50, 0))
verifier(d.taille() == (600, 300) and k[150, 120, 3] == 255 and k[150, 60, 3] == 0 and k[150, 500, 3] == 0,
         f"50 px à gauche seulement : rempli de 100 à 150, le reste du vide transparent "
         f"({k[150, 120, 3]}, {k[150, 60, 3]}, {k[150, 500, 3]})")
# 3. cadre qui dépasse : 100 px en haut (au-delà de l'image) + tout le vide
d, k = lancer((100, 0, 150, 150))
verifier(d.taille() == (600, 400) and k[30, 300, 3] == 255 and k[250, 20, 3] == 255
         and np.abs(k[160:400, 200:400, :3] - rgba[60:, 200:400, :3].astype(int)).max() <= 2,
         f"vide + 100 px en haut : {d.taille()}, tout rempli, photo à sa place (hors fondu de raccord)")

# 4. ronds rouges (bord abîmé) : 10 px du bord gauche de la photo sont redessinés par l'IA
d, k = lancer((0, 0, 150, 150), abime=(0, 0, 10, 0))
verifier(abs(k[150, 155, 0] - 230) < 25 and np.abs(k[:, 200:400, :3] - rgba[:, 200:400, :3].astype(int)).max() <= 2,
         f"bord abîmé avec du vide : 10 px redessinés par l'IA {k[150, 155]}")
# 5. photo collée puis réduite : bord à demi transparent -> pas de liseré clair entre la photo et l'ajout
flou = rgba.copy()
flou[:, 150, 3] = 110
flou[:, 449, 3] = 160
flou[:, 151, 3] = 230
d, k = lancer((0, 0, 150, 150), abime=(0, 0, 0, 0), photo=flou)   # même ronds rouges remis à 0
verifier(d.taille() == (600, 300) and k[:, 140:460, 3].min() == 255,
         f"bord flou : jonction opaque, sans liseré (alpha mini {k[:, 140:460, 3].min()})")
f._installer_document(Document(calques=[Calque("Photo collée", qimage_rgba(flou))]))
f.ia_agrandir()
verifier(tuple(c.abime) [2] >= 2 and tuple(c.abime)[3] >= 1, f"bord flou proposé d'office en bord abîmé {c.abime}")
f._fin_agrandir()

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
