"""Rotation au degré près (Transformer : souris et cases à taper ; Image > Pivoter selon un angle) et Agrandir en
pleine définition (découpe, recollage, grain ; enchaînement avec un faux moteur).
Usage : essai_rotation_pleine.py"""
import io
import math
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PIL import Image
from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication, QInputDialog

from pixane import affinage
from pixane.document import FORMAT_IMAGE, Calque, Document, image_vide, qimage_rgb, tableau
from pixane.fenetre import Fenetre
from pixane.moteur import Moteur
from pixane.transformation import Transformation

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

# ---------------------------------------------------------------- 1. Transformer : au degré près
t = Transformation(image_vide(100, 100), __import__("PySide6.QtCore", fromlist=["QRect"]).QRect(0, 0, 100, 100))
c = t.centre
t.commencer("tourner", c + QPointF(100, 0))
t.glisser(c + QPointF(100 * math.cos(math.radians(17.4)), 100 * math.sin(math.radians(17.4))), False)
verifier(t.angle == 17, f"à la souris : angle arrondi au degré ({t.angle})")
t.glisser(c + QPointF(100 * math.cos(math.radians(22)), 100 * math.sin(math.radians(22))), True)
verifier(t.angle == 15, f"Maj : par 15° ({t.angle})")

fond = QImage(200, 100, FORMAT_IMAGE)
fond.fill(QColor(255, 255, 255))
doc = Document(fond)
carre = image_vide(200, 100)
p = QPainter(carre)
p.fillRect(80, 30, 40, 40, QColor(255, 0, 0))
p.end()
doc.calques = doc.calques + (Calque("Carré", carre),)
doc.actif = 1
doc._fusion = None
f._installer_document(doc)
f.transformer()
verifier(f.canevas.transfo is not None and f.opt_transfo.isVisible(), "Ctrl+T : barre avec les cases")
f.cases_transfo["a"].setValue(33)
verifier(f.canevas.transfo.angle == 33, "angle tapé : 33°")
f.cases_transfo["l"].setValue(50)
verifier(abs(f.canevas.transfo.sx - 0.5) < 1e-6, "largeur tapée : 50 %")
f.canevas.transfo.angle = 10
f._transfo_change()
verifier(f.cases_transfo["a"].value() == 10 and f.canevas.transfo.angle == 10, "les cases suivent la souris")
f._valider_transfo()
verifier(len(doc.calques) == 2 and f.canevas.transfo is None, "validé")

# ---------------------------------------------------------------- 2. Image > Pivoter selon un angle
for angle, attendu in ((30, (224, 187)), (120, (187, 224))):
    QInputDialog.getDouble = staticmethod(lambda *a, v=angle: (float(v), True))
    avant = doc.taille()
    f.pivoter_angle()
    w, h = doc.taille()
    verifier(abs(w - attendu[0]) <= 2 and abs(h - attendu[1]) <= 2, f"pivoter de {angle}° : feuille {w} × {h}")
    f.historique.undo()
    verifier(doc.taille() == avant, "Ctrl+Z")

# ---------------------------------------------------------------- 3. pleine définition : calculs
W, H, w, h = 3000, 1200, 2000, 1200
m = affinage.masque_ajout((W, H), (0, 0, 500, 500), (h, w), 40)
verifier(m[600, 0] == 1 and m[600, 2999] == 1 and m[600, 1500] == 0 and 0 < m[600, 520] < 1,
         "masque : 1 dans l'ajout, 0 au milieu de la photo, fondu dans la bande")
r = affinage.morceaux(m)
couvert = np.zeros_like(m, bool)
for x, y, tw, th in r:
    couvert[y:y + th, x:x + tw] = True
verifier(couvert[m > 0].all() and all(tw % 16 == 0 and th % 16 == 0 for _, _, tw, th in r),
         f"{len(r)} morceaux couvrent tout l'ajout (côtés multiples de 16)")
verifier(not any(x > 600 and x + tw < 2400 for x, _, tw, _ in r), "aucun morceau au milieu de la photo")
img = np.full((H, W, 3), 128, np.uint8)
res = np.full((1024, 1024, 3), 200, np.uint8)
x, y, tw, th = r[0]
colle = affinage.coller(img, res, m, r[0])
verifier(colle[600, 1500, 0] == 128 and colle[min(y + th // 2, H - 1), x + 10, 0] > 190,
         "recollage : seulement dans l'ajout")
grand = np.zeros((6000, 9000), np.float32)
grand[:, :2000] = 1
s, _t, _m, rr = affinage.plan(np.zeros((6000, 9000, 3), np.uint8), grand)
verifier(s < 1 and len(rr) <= affinage.MAX_MORCEAUX, f"très grande photo : échelle {s:.2f}, {len(rr)} morceaux")
rng = np.random.default_rng(3)
photo = np.clip(128 + rng.normal(0, 6, (H, W, 3)), 0, 255).astype(np.uint8)
photo[m > 0.95] = 128                                       # ajout lisse, sans grain
g = affinage.accorder_grain(photo, m)
avant, apres = affinage._bruit(photo, m > 0.95), affinage._bruit(g, m > 0.95)
verifier(avant < 1 and abs(apres - affinage._bruit(photo, m < 0.01)) < 1.5,
         f"grain ajouté à l'ajout : {avant:.1f} -> {apres:.1f} (photo {affinage._bruit(photo, m < 0.01):.1f})")
verifier((g[m < 0.01] == photo[m < 0.01]).all(), "la photo d'origine n'est pas touchée")

# ---------------------------------------------------------------- 4. pleine définition : enchaînement (faux moteur)
envoyes = []


def envoyer(png):
    envoyes.append(np.asarray(Image.open(io.BytesIO(png))))
    return f"m{len(envoyes)}.png"


def executer(prompt, sorties, annuler, progres=lambda i: None, n=1):
    a = envoyes[-1]
    progres({"secondes": 1, "etape": "", "fraction": 0.5, "restant": None})
    sortie = a[:, :, :3].copy()
    sortie[a[:, :, 3] < 128] = (10, 200, 10)                # « redessiné » en vert
    tampon = io.BytesIO()
    Image.fromarray(sortie).save(tampon, "PNG")
    yield "Pleine définition", tampon.getvalue()


f.moteur.envoyer_image = envoyer
f.moteur.executer = executer
petit = np.full((400, 900, 3), 90, np.uint8)
m2 = affinage.masque_ajout((900, 400), (0, 0, 200, 200), (400, 500), 20)
recu = []
f._affiner_agrandir(qimage_rgb(petit), m2, recu.append)
for _ in range(200):
    app.processEvents()
    if recu:
        break
    import time
    time.sleep(0.02)
verifier(len(recu) == 1 and recu[0].size().width() == 900, "résultat de la pleine définition rendu")
if recu:
    a = tableau(recu[0])
    verifier(a[200, 50, 1] > 150 and a[200, 450, 1] == 90, "ajout redessiné, photo intacte")
verifier(len(envoyes) >= 1 and envoyes[0].shape[2] == 4, f"{len(envoyes)} morceau(x) envoyé(s), avec la zone à refaire")
verifier(f.barre_agrandir.pleine.text() != "", "case « Pleine définition » dans la barre Agrandir")

print("ERREURS :", erreurs if erreurs else "aucune")
sys.stdout.flush()
for dd in f.documents:
    dd.modifie = False
f.close()
sys.exit(1 if erreurs else 0)
