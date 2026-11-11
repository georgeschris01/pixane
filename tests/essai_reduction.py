"""Réduire / agrandir un calque (Transformer, outil Déplacer) : qualité d'un vrai redimensionnement (Lanczos), pas de
crénelage ni de grain, pas de flou dû à un demi-pixel, transparence sans liseré sombre, miroir, rotation.
Usage : essai_reduction.py"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PIL import Image
from PySide6.QtCore import QPointF, QRect
from PySide6.QtWidgets import QApplication

from pixane.document import FORMAT_IMAGE, qimage_rgba, tableau
from pixane.transformation import Transformation

erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


app = QApplication(sys.argv)
W = H = 600
rng = np.random.default_rng(3)
yy, xx = np.mgrid[0:H, 0:W]
o = np.zeros((H, W, 4), np.uint8)
o[..., 0] = (127 + 127 * np.sin(xx * 0.9) * np.cos(yy * 0.7)).astype(np.uint8)      # détails très fins
o[..., 1] = ((xx // 3 + yy // 3) % 2 * 255).astype(np.uint8)                         # damier de 3 px
o[..., 2] = rng.integers(0, 256, (H, W))
o[..., 3] = 255
img = qimage_rgba(o)


def rendu(t):
    r, x, y = t.rendu_entier(True)
    return tableau(r.convertToFormat(FORMAT_IMAGE)).astype(float), x, y


def lanczos(a, w, h):
    return np.asarray(Image.fromarray(a).resize((w, h), Image.LANCZOS)).astype(float)


for k in (0.5, 0.3, 0.17):
    w = round(W * k)
    t = Transformation(img, QRect(0, 0, W, H))
    t.sx = t.sy = w / W
    t.centre = QPointF(100 + w / 2 + 0.37, 50 + w / 2 + 0.41)            # position pas entière
    a, x, y = rendu(t)
    ref = lanczos(o, w, w)
    verifier((x, y) == (100, 50) and a.shape[:2] == (w, w) and np.abs(a[..., :3] - ref[..., :3]).mean() < 1,
             f"réduit à {k:.0%} : comme un bon redimensionnement, sans grain ni flou de demi-pixel "
             f"(écart {np.abs(a[..., :3] - ref[..., :3]).mean():.2f}, place {x},{y})")
# agrandir aussi en qualité
t = Transformation(img, QRect(0, 0, 200, 200))
t.sx = t.sy = 2.5
t.centre = QPointF(250, 250)
a, x, y = rendu(t)
ref = lanczos(np.ascontiguousarray(o[:200, :200]), 500, 500)
verifier(a.shape[:2] == (500, 500) and np.abs(a[..., :3] - ref[..., :3]).mean() < 1, "agrandi : en qualité")
# transparence : disque rouge sur fond transparent, réduit : pas de liseré sombre
d = np.zeros((H, W, 4), np.uint8)
dedans = (xx - 300) ** 2 + (yy - 300) ** 2 < 200 ** 2
d[dedans] = [230, 30, 30, 255]
t = Transformation(qimage_rgba(d), QRect(0, 0, W, H))
t.sx = t.sy = 0.23
t.centre = QPointF(69, 69)
a, x, y = rendu(t)
bord = (a[..., 3] > 20) & (a[..., 3] < 235)
verifier(bord.any() and a[bord][:, 0].min() > 215 and a[bord][:, 1:3].max() < 50 and (a[..., 3] < 1).any(),
         f"transparence : bord doux, sans liseré sombre (rouge du bord {a[bord][:, 0].min():.0f}..{a[bord][:, 0].max():.0f})")
# miroir
t = Transformation(img, QRect(0, 0, W, H))
t.sx, t.sy = -0.5, 0.5
t.centre = QPointF(150, 150)
a, x, y = rendu(t)
ref = lanczos(o, 300, 300)[:, ::-1]
verifier(np.abs(a[..., :3] - ref[..., :3]).mean() < 1, "miroir et réduit : en qualité")
# rotation + réduction : la réduction est faite en qualité avant de tourner (pas de grain)
t = Transformation(img, QRect(0, 0, W, H))
t.sx = t.sy = 0.2
t.angle = 30
t.centre = QPointF(200, 200)
a, x, y = rendu(t)
l = a[..., :3] @ [0.299, 0.587, 0.114]
cx, cy = round(200 - x), round(200 - y)
zone = l[cy - 30:cy + 30, cx - 30:cx + 30]
ref = lanczos(o, 120, 120)[..., :3] @ [0.299, 0.587, 0.114]
verifier(zone.std() < 1.3 * ref.std(),
         f"tourné et réduit : pas de grain ajouté (écart type {zone.std():.1f} / bonne réduction {ref.std():.1f})")
# déplacer seulement (taille 100 %) : image identique, posée sur des pixels entiers
t = Transformation(img, QRect(0, 0, W, H))
t.centre = QPointF(W / 2 + 10.4, H / 2 + 20.6)
a, x, y = rendu(t)
verifier((x, y) == (10, 21) and np.array_equal(a.astype(np.uint8), o), "déplacé seulement : image identique, pas floutée")

print("ERREURS :", erreurs if erreurs else "aucune")
sys.stdout.flush()
sys.exit(1 if erreurs else 0)
