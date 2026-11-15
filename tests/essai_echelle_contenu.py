"""Image > Mise à l'échelle d'après le contenu : le sujet garde ses proportions, tous les calques suivent (masques,
sélection, remplissage redessiné, texte devenu image), fenêtre et formats rapides, annuler.
Usage : essai_echelle_contenu.py dossier_sortie"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PIL import Image, ImageDraw
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from pixane import calque_remplissage as cr
from pixane.fenetre import Fenetre
from pixane.moteur import Moteur

Moteur.demarrer = lambda self, signaler=None: (_ for _ in ()).throw(Exception("moteur désactivé pour l'essai"))
Fenetre._moteur_en_echec = lambda self, *a: None
sortie = Path(sys.argv[1])
sortie.mkdir(parents=True, exist_ok=True)
# fond bleu uni (dégradé doux) et un sujet rond, plein de détails, au milieu
y = np.linspace(0, 1, 400)[:, None]
fond = np.dstack([np.full((400, 400), 90), (120 + 60 * y).repeat(400, 1), np.full((400, 400), 220)]).astype(np.uint8)
im = Image.fromarray(fond)
dr = ImageDraw.Draw(im)
dr.ellipse((150, 150, 250, 250), fill=(200, 40, 30))
for k in range(150, 250, 6):
    dr.line((k, 150, k, 250), fill=(250, 220, 0))
masque_rond = Image.new("L", (400, 400), 0)
ImageDraw.Draw(masque_rond).ellipse((150, 150, 250, 250), fill=255)
im = Image.composite(im, Image.fromarray(fond), masque_rond)
im.save(sortie / "sujet.png")
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


def boite_rouge(a):
    r = (a[..., 0] > 150) & (a[..., 1] < 120) & (a[..., 2] < 120) | (a[..., 0] > 200) & (a[..., 1] > 180) & (a[..., 2] < 80)
    ys, xs = np.nonzero(r)
    return xs.min(), xs.max(), ys.min(), ys.max()


app = QApplication(sys.argv)
from pixane.document import FORMAT_IMAGE, _masque_vers_selection, masque, tableau
from pixane.texte import Texte
f = Fenetre()
f.resize(1440, 920)
f.show()
f.charger(str(sortie / "sujet.png"))
app.processEvents()
doc = f.doc

# 1. le sujet garde ses proportions
x0, x1, y0, y1 = boite_rouge(tableau(doc.image))
avant = (x1 - x0) / (y1 - y0)
etat0 = doc.etat()
etat = doc.etat_echelle_contenu(711, 400)
doc.appliquer_etat(etat)
a = tableau(doc.image)
verifier(doc.taille() == (711, 400), "carré 400 × 400 vers 16:9 : 711 × 400")
x0, x1, y0, y1 = boite_rouge(a)
verifier(abs((x1 - x0) / (y1 - y0) - avant) < 0.12, f"le sujet reste rond (largeur/hauteur {(x1 - x0) / (y1 - y0):.2f}, "
         f"avant {avant:.2f} ; un étirement ordinaire donnerait {avant * 711 / 400:.2f})")
Image.fromarray(a).save(sortie / "resultat_16x9.png")
doc.appliquer_etat(etat0)

# 2. tous les calques suivent ; texte devenu image ; remplissage redessiné ; masque et sélection
doc.appliquer_etat(doc.etat_nouveau_texte(Texte(texte="AB", taille=40, x=10, y=10)))
doc.appliquer_etat(doc.etat_nouveau_remplissage(cr.Remplissage("couleur", "#8000ff00"), "Vert"))
doc.appliquer_etat(doc.etat_ajouter_masque("blanc"))
sel = np.zeros((400, 400), np.uint8)
sel[150:251, 150:251] = 255
doc.selection = _masque_vers_selection(sel).convertToFormat(doc.selection.format())
n = len(doc.calques)
avant_etat = doc.etat()
from pixane.fenetre import CommandeEtat
apres = doc.etat_echelle_contenu(300, 400, proteger=True)
f.historique.push(CommandeEtat(doc, avant_etat, apres, "Mise à l'échelle d'après le contenu"))
verifier(len(doc.calques) == n and all(c.image.width() == 300 and c.image.height() == 400 for c in doc.calques),
         "tous les calques sont à la nouvelle taille")
verifier(all(c.texte is None for c in doc.calques), "le texte est devenu une image")
r = [c for c in doc.calques if cr.valide(c) is not None]
verifier(len(r) == 1 and tuple(tableau(r[0].image.convertToFormat(FORMAT_IMAGE))[399, 299])[:3] == (0, 255, 0),
         "le calque de remplissage reste modifiable, redessiné sur toute la feuille")
verifier(r and r[0].masque is not None and r[0].masque.width() == 300, "son masque suit")
m = masque(doc.selection)
ys, xs = np.nonzero(m > 128)
verifier(m.shape == (400, 300) and abs((xs.max() - xs.min()) - 100) <= 6,
         f"la sélection protégée garde sa largeur ({xs.max() - xs.min()} px pour 100)")
f.historique.undo()
verifier(doc.taille() == (400, 400) and any(c.texte is not None for c in doc.calques), "Ctrl+Z : tout revient")

# 3. fenêtre
from pixane.dialogues_image import EchelleContenu
d = EchelleContenu(400, 400, doc.image, sel, f)
verifier(d.proteger(), "avec une sélection : « Protéger la sélection » cochée")
d.format(16, 9)
verifier(d.valeurs() == (400, 225), f"format 16:9 : le plus grand côté est gardé ({d.valeurs()})")
d.format(9, 16)
verifier(d.valeurs() == (225, 400), "format 9:16")
d.format(16, 9)
d._apercu()
verifier(d.apercu.pixmap().width() == 360 and d.apercu.pixmap().height() in (202, 203), "aperçu à la nouvelle forme")
d.show()
app.processEvents()
d.grab().save(str(sortie / "fenetre_echelle.png"))
d.close()
d = EchelleContenu(400, 400, doc.image, None, f)
verifier(not d.c_proteger.isEnabled(), "sans sélection : case grisée")
verifier(f.a_echelle_contenu.isEnabled(), "menu Image > Mise à l'échelle d'après le contenu…")

print("ERREURS :", erreurs if erreurs else "aucune")
for dd in list(getattr(f, "_docs", [])):
    dd.modifie = False
if f.doc:
    f.doc.modifie = False
sys.stdout.flush()
QTimer.singleShot(200, f.close)
app.exec()
sys.exit(1 if erreurs else 0)
