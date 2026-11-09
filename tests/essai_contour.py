"""Améliorer le contour : calcul (image synthétique avec « cheveux ») et dialogue dans la fenêtre.
Usage : essai_contour.py dossier_sortie [image_de_test]"""
import os
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["CHRYPIX_REGLAGES"] = "Chrypix-essais"
import numpy as np
from PIL import Image, ImageDraw

from chrypix import contour

sortie = Path(sys.argv[1])
sortie.mkdir(parents=True, exist_ok=True)
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


# sujet clair (disque + mèches fines) sur fond sombre ; sélection grossière : disque un peu trop grand, sans mèches
W = H = 400
im = Image.new("RGB", (W, H), (30, 40, 70))
dr = ImageDraw.Draw(im)
dr.ellipse((120, 120, 280, 280), fill=(235, 200, 160))
for k in range(16):
    ang = k * np.pi / 8
    x0, y0 = 200 + 80 * np.cos(ang), 200 + 80 * np.sin(ang)
    x1, y1 = 200 + 125 * np.cos(ang), 200 + 125 * np.sin(ang)
    dr.line((x0, y0, x1, y1), fill=(235, 200, 160), width=2)
rgb = np.asarray(im)
sel = Image.new("L", (W, H), 0)
ImageDraw.Draw(sel).ellipse((108, 108, 292, 292), fill=255)
m = np.asarray(sel)
sujet = np.asarray(im.convert("L")) > 120

t = time.time()
a = contour.affiner(rgb, m, {"rayon": 40, "lissage": 0, "contraste": 0, "decalage": 0})
print(f"   ({time.time() - t:.2f} s)")
bandes = contour.bande(m, 40)
fond_avant = m[bandes & ~sujet].mean()
fond_apres = a[bandes & ~sujet].mean()
meches = bandes & sujet & (m < 128)
verifier(fond_apres < fond_avant * 0.5, f"fond près du bord retiré ({fond_avant:.0f} -> {fond_apres:.0f})")
verifier(a[meches].mean() > 100, f"mèches hors de la sélection retrouvées (moyenne {a[meches].mean():.0f} / 255)")
verifier(np.all(a[~bandes] == m[~bandes]), "hors de la bande : rien de changé")
c = contour.affiner(rgb, m, {"rayon": 0, "lissage": 0, "contraste": 100, "decalage": 0})
verifier(set(np.unique(c)) <= {0, 255} or np.mean((c > 5) & (c < 250)) < 0.001, "contraste 100 : bord net")
d1 = contour.affiner(rgb, m, {"rayon": 0, "lissage": 3, "contraste": 0, "decalage": -60})
d2 = contour.affiner(rgb, m, {"rayon": 0, "lissage": 3, "contraste": 0, "decalage": 60})
verifier((d1 > 128).sum() < (m > 128).sum() < (d2 > 128).sum(), "décaler : négatif rentre, positif sort")
Image.fromarray(np.hstack([m, a])).save(sortie / "contour_synthetique.png")
Image.fromarray(contour.apercu(rgb, a, "noir")).save(sortie / "contour_sur_noir.png")

if len(sys.argv) > 2:
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication, QDialog

    from chrypix.document import _masque_vers_selection, masque
    from chrypix.fenetre import Fenetre
    from chrypix.moteur import Moteur
    Moteur.demarrer = lambda self, signaler=None: None
    Fenetre._moteur_en_echec = lambda self, *a: None
    app = QApplication(sys.argv)
    f = Fenetre()
    f.resize(1300, 900)
    f.show()
    f.charger(sys.argv[2])
    w, h = f.doc.taille()
    s = Image.new("L", (w, h), 0)
    ImageDraw.Draw(s).ellipse((w * 0.25, h * 0.2, w * 0.75, h * 0.8), fill=255)
    f.doc.selection = _masque_vers_selection(np.asarray(s)).convertToFormat(f.doc.selection.format())
    ancien = masque(f.doc.selection).copy()
    t0 = time.time()
    a = contour.affiner(np.asarray(Image.open(sys.argv[2]).convert("RGB")), ancien,
                        {"rayon": 30, "lissage": 1, "contraste": 20, "decalage": 0})
    print(f"   photo {w}×{h}, rayon 30 : {time.time() - t0:.2f} s")
    etapes = []

    def dans_dialogue():
        d = next(x for x in app.topLevelWidgets() if isinstance(x, QDialog) and x.isVisible())
        def regarder():
            app.processEvents()
            etapes.append(f.canevas.apercu_plein is not None)
            f.grab().save(str(sortie / "contour_fenetre.png"))
            d.accept()
        QTimer.singleShot(2500, regarder)
    QTimer.singleShot(300, dans_dialogue)
    n = f.historique.count()
    f.ameliorer_contour()
    verifier(etapes == [True], "aperçu « sur noir » affiché pendant le dialogue")
    verifier(f.canevas.apercu_plein is None, "aperçu enlevé à la fermeture")
    verifier(f.historique.count() == n + 1 and not np.array_equal(masque(f.doc.selection), ancien),
             "Appliquer : nouvelle sélection, une étape dans Annuler")
    f.a_annuler.trigger()
    verifier(np.array_equal(masque(f.doc.selection), ancien), "Annuler : sélection d'avant")
    f.close()
print("ERREURS :", erreurs if erreurs else "aucune")
sys.stdout.flush()
sys.exit(1 if erreurs else 0)
