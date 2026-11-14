"""Sélection de texte (Y) : cadre autour d'un texte -> les lettres seules (traits fins gardés, fond et taches de
photo écartés) ; corrections Alt+clic / Maj+clic / Ctrl ; « Lettres pleines » ; Ctrl+Z.
Usage : essai_selection_texte.py"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from PySide6.QtCore import QPointF, QRectF
from PySide6.QtWidgets import QApplication

from pixane.canevas import SEL_TEXTE
from pixane.document import Document, masque, qimage_rgb
from pixane.fenetre import Fenetre
from pixane.moteur import Moteur
from pixane.selection_texte import Analyse

Moteur.demarrer = lambda self, signaler=None: None
Fenetre._moteur_en_echec = lambda self, *a: None
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


app = QApplication(sys.argv)
f = Fenetre()
f.show()
f.opt_pleines.setChecked(False)

# image : fond en dégradé avec une « photo » floue, texte blanc manuscrit à déliés fins, une tache claire floue
W, H = 700, 360
y, x = np.mgrid[0:H, 0:W]
fond = np.stack([60 + x * 0.1, 70 + y * 0.15, 90 + 0 * x], -1)
rng = np.random.default_rng(1)
fond += rng.normal(0, 4, fond.shape)                            # grain
img = Image.fromarray(np.clip(fond, 0, 255).astype(np.uint8))
d = ImageDraw.Draw(img)
d.ellipse((520, 60, 640, 150), fill=(200, 200, 205))            # tache claire…
img = img.filter(ImageFilter.GaussianBlur(1)).copy()
tache = Image.new("L", (W, H), 0)
ImageDraw.Draw(tache).ellipse((520, 60, 640, 150), fill=255)
flou = img.filter(ImageFilter.GaussianBlur(14))                 # …très floue (comme un fond de photo)
img.paste(flou, (0, 0), tache)
texte = Image.new("L", (W, H), 0)
police = ImageFont.truetype("C:/Windows/Fonts/georgiai.ttf", 120)
ImageDraw.Draw(texte).text((40, 90), "Coeur", fill=255, font=police)
ImageDraw.Draw(texte).line([(40, 250), (480, 236)], fill=255, width=1)       # délié de 1 px
blanc = Image.new("RGB", (W, H), (250, 250, 250))
img.paste(blanc, (0, 0), texte)
rgb = np.asarray(img)
lettres = np.asarray(texte) > 200
doc = Document(qimage_rgb(rgb))
f._installer_document(doc)
f._choisir_outil(SEL_TEXTE)
app.processEvents()                             # (la barre se réorganise)
verifier(f.opt_sel_texte.isVisible() and not f.opt_baguette.isVisible(), "outil Y : ses options s'affichent")

# 1. cadre autour du texte (la tache floue est dedans)
f.canevas.texte_sel.emit(QRectF(20, 40, 660, 240), "nouvelle", False)
m = masque(doc.selection).astype(int)
verifier(m[lettres].mean() > 235, f"lettres sélectionnées ({m[lettres].mean():.0f}/255)")
delie = lettres & (np.arange(H)[:, None] > 225)
verifier((m[delie] > 60).mean() > 0.9, f"délié de 1 px gardé ({(m[delie] > 60).mean():.2f})")
verifier(m[80:130, 540:620].max() < 30, "tache claire floue de la photo : pas prise")
verifier(m[:40].max() == 0 and m[290:].max() == 0, "rien hors du cadre")
fond_cadre = ~np.asarray(Image.fromarray(lettres).filter(ImageFilter.MaxFilter(5)))
fond_cadre[:40], fond_cadre[290:], fond_cadre[:, :20], fond_cadre[:, 680:] = False, False, False, False
verifier((m[fond_cadre] > 30).mean() < 0.01, f"fond du cadre pas pris ({(m[fond_cadre] > 30).mean():.4f})")
verifier(m[lettres & (m < 250)].size < lettres.sum() * 0.3, "bords progressifs seulement au bord des lettres")

# 2. Alt+clic sur une lettre : ce morceau part ; Ctrl+Z le remet
C = (np.nonzero(lettres[:, :140])[0][0], np.nonzero(lettres[np.nonzero(lettres[:, :140])[0][0], :140])[0][0])
avant = m.copy()
f.canevas.texte_sel.emit(QPointF(C[1] + 0.5, C[0] + 0.5), "retirer", False)
m2 = masque(doc.selection).astype(int)
verifier(m2[C] == 0 and m2[lettres].mean() < avant[lettres].mean() - 5 and m2[lettres].mean() > 100,
         "Alt+clic : le morceau cliqué est enlevé, le reste gardé")
f.historique.undo()
verifier(np.array_equal(masque(doc.selection).astype(int), avant), "Ctrl+Z : le morceau revient")
f.historique.redo()
# Maj+clic sur le même : il revient
f.canevas.texte_sel.emit(QPointF(C[1] + 0.5, C[0] + 0.5), "ajouter", False)
verifier(masque(doc.selection)[C] > 200, "Maj+clic : le morceau est ajouté")

# 3. clic hors du cadre : rien ne change, un message guide
avant = masque(doc.selection).copy()
f.canevas.texte_sel.emit(QPointF(5, 5), "retirer", False)
verifier(np.array_equal(masque(doc.selection), avant) and "cadre" in f.statusBar().currentMessage(),
         "clic hors du cadre : rien ne change, message")

# 4. lettres pleines : l'intérieur du « o » est pris
f.canevas.texte_sel.emit(QRectF(20, 40, 660, 240), "nouvelle", False)
from pixane.selection_auto import etiquettes
trous, tailles = etiquettes(~lettres)
bord = set(trous[0]) | set(trous[-1]) | set(trous[:, 0]) | set(trous[:, -1])
ferme = [i for i in np.argsort(-tailles) if i not in bord]
ys, xs = np.nonzero(trous == ferme[0])                          # le plus grand trou fermé : intérieur d'une lettre
cy, cx = int(np.median(ys)), int(np.median(xs[ys == int(np.median(ys))]))
interieur = trous[cy, cx] == ferme[0]
m = masque(doc.selection)
f.opt_pleines.setChecked(True)
mp = masque(doc.selection)
verifier(interieur and m[cy, cx] < 40 and mp[cy, cx] > 200, "Lettres pleines : l'intérieur du o est pris")
f.opt_pleines.setChecked(False)

# 5. texte coupé par le cadre (un seul côté) : reste du texte ; Alt+cadre retire
f.canevas.texte_sel.emit(QRectF(20, 40, 660, 160), "nouvelle", False)
m = masque(doc.selection).astype(int)
verifier(m[lettres & (np.arange(H)[:, None] > 45) & (np.arange(H)[:, None] < 198)].mean() > 200, "cadre qui coupe les lettres : elles restent prises")
f.canevas.texte_sel.emit(QRectF(20, 40, 660, 240), "nouvelle", False)
f.canevas.texte_sel.emit(QRectF(20, 40, 160, 240), "retirer", False)
m = masque(doc.selection).astype(int)
dans = lettres & (np.arange(W)[None, :] >= 20) & (np.arange(W)[None, :] < 180)
verifier(m[dans].mean() < 10 and m[lettres & (np.arange(W)[None, :] > 200)].mean() > 200,
         "Alt + cadre : retire le texte de ce cadre seulement")

# 6. aplat : fond uni, texte en dégradé (rouge vers jaune) avec contour
a = np.full((200, 500, 3), 30, np.uint8)
t = Image.new("L", (500, 200), 0)
ImageDraw.Draw(t).text((20, 30), "SPEARS", fill=255, font=ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 110))
tm = np.asarray(t) > 128
grad = np.stack([np.full(200, 220), np.linspace(20, 210, 200), np.full(200, 30)], -1)[:, None, :]
a[tm] = np.broadcast_to(grad, (200, 500, 3))[tm]
an = Analyse(a)
r = an.calculer()
verifier(r[tm].mean() > 230 and r[~np.asarray(t.filter(ImageFilter.MaxFilter(5))) > 0].max() < 40,
         f"texte en dégradé : pris en entier ({r[tm].mean():.0f}/255), fond pas pris")

print("ERREURS :", erreurs if erreurs else "aucune")
sys.stdout.flush()
for dd in f.documents:
    dd.modifie = False
f.close()
sys.exit(1 if erreurs else 0)
