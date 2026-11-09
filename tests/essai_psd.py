"""Fichiers Photoshop : écrire un PSD à calques puis le relire (par Pixane et par Pillow, lecteur indépendant) ;
noms avec accents, visibilité, opacité, verrou, calque vide, transparence, image fusionnée.
Usage : essai_psd.py dossier_sortie   (images d'essai fabriquées)"""
import os
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PIL import Image
from PySide6.QtWidgets import QApplication
from pixane.document import FORMAT_CALQUE, FORMAT_IMAGE, Calque, Document, image_vide, qimage_rgba, tableau
from pixane.psd import _packbits

app = QApplication(sys.argv)
sortie = Path(sys.argv[1])
sortie.mkdir(parents=True, exist_ok=True)
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


def rgba(img):
    return tableau(img.convertToFormat(FORMAT_IMAGE)).astype(int)


# PackBits : aller-retour avec le décodeur de Pillow
rng = np.random.default_rng(3)
bon = True
for i in range(500):
    n = int(rng.integers(1, 900))
    a = rng.integers(0, 3, n).astype(np.uint8) if i % 2 else np.repeat(rng.integers(0, 255, n // 40 + 1), 40)[:n].astype(np.uint8)
    b = np.frombuffer(Image.frombytes("L", (n, 1), _packbits(a), "packbits", "L").tobytes(), np.uint8)
    bon &= np.array_equal(a, b)
verifier(bon, "PackBits : 500 lignes compressées puis relues à l'identique")

W, H = 640, 400
yy, xx = np.mgrid[0:H, 0:W]
fond = np.dstack([xx * 255 // W, yy * 255 // H, np.full_like(xx, 90), np.full_like(xx, 255)]).astype(np.uint8)
rond = np.zeros((H, W, 4), np.uint8)
dedans = (xx - 300) ** 2 + (yy - 200) ** 2 < 90 ** 2
rond[dedans] = (250, 200, 30, 255)
bord = ((xx - 300) ** 2 + (yy - 200) ** 2 >= 90 ** 2) & ((xx - 300) ** 2 + (yy - 200) ** 2 < 100 ** 2)
rond[bord] = (250, 200, 30, 128)                                   # bord semi-transparent
cache = np.zeros((H, W, 4), np.uint8)
cache[50:120, 400:600] = (20, 40, 220, 255)
calques = [Calque("Arrière-plan", qimage_rgba(fond).convertToFormat(FORMAT_CALQUE), verrou=True),
           Calque("Soleil éclairé", qimage_rgba(rond).convertToFormat(FORMAT_CALQUE), opacite=0.6),
           Calque("Caché", qimage_rgba(cache).convertToFormat(FORMAT_CALQUE), visible=False),
           Calque("Vide", image_vide(W, H))]
doc = Document(calques=calques)
chemin = sortie / "essai.psd"
debut = time.time()
doc.enregistrer(chemin)
verifier(chemin.is_file() and chemin.stat().st_size < W * H * 4, f"PSD écrit et compressé ({chemin.stat().st_size} octets, "
         f"{time.time() - debut:.2f} s)")

relu = Document.ouvrir(chemin)
verifier([c.nom for c in relu.calques] == ["Arrière-plan", "Soleil éclairé", "Caché", "Vide"],
         f"noms relus (accents compris) : {[c.nom for c in relu.calques]}")
verifier([c.visible for c in relu.calques] == [True, True, False, True], "visibilité gardée")
verifier(abs(relu.calques[1].opacite - 0.6) < 0.005, f"opacité gardée ({relu.calques[1].opacite:.3f})")
verifier([c.verrou for c in relu.calques] == [True, False, False, False], "verrou gardé")
ecart = max(np.abs(rgba(a.image) - rgba(b.image))[rgba(a.image)[..., 3] > 0].max(initial=0)
            for a, b in zip(calques, relu.calques))
verifier(ecart <= 2, f"pixels de chaque calque identiques (écart {ecart})")
verifier(np.array_equal(rgba(relu.calques[1].image)[..., 3], rgba(calques[1].image)[..., 3]), "transparence gardée")
verifier(rgba(relu.calques[3].image)[..., 3].max() == 0, "calque vide relu vide")

with Image.open(chemin) as im:                                     # lecteur indépendant (Pillow)
    composite = np.asarray(im.convert("RGB")).astype(int)
    noms_pillow = len(im.layers)
f = rgba(doc.image)
attendu = (f[..., :3] * f[..., 3:4] + 255 * (255 - f[..., 3:4])) // 255
verifier(np.abs(composite - attendu).max() <= 2, "image fusionnée lue par Pillow : identique")
verifier(noms_pillow == 4, f"Pillow voit les 4 calques ({noms_pillow})")
Image.fromarray(composite.astype(np.uint8)).save(sortie / "fusion_pillow.png")

print("ERREURS :", erreurs if erreurs else "aucune")
sys.stdout.flush()
os._exit(1 if erreurs else 0)
