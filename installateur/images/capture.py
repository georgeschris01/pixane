"""Capture de Pixane pour l'installateur, sur un paysage dessiné (aucune photo personnelle).
Usage (depuis la racine du projet) : .venv\\Scripts\\python.exe installateur\\images\\capture.py fr|en
Écrit installateur\\images\\capture-<langue>.png. Utilise ses propres réglages (ne touche pas ceux de l'utilisateur)."""
import os
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE))
os.environ["PIXANE_REGLAGES"] = "Pixane-capture"
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from PySide6.QtCore import QPointF, QTimer
from PySide6.QtWidgets import QApplication

LANGUE = sys.argv[1] if len(sys.argv) > 1 else "fr"
DOSSIER = Path(__file__).resolve().parent


def paysage(w=1600, h=1000) -> Path:
    """Coucher de soleil sur un lac, entre des montagnes."""
    y = np.linspace(0, 1, h)[:, None]
    haut, bas = np.array([38, 52, 110]), np.array([255, 150, 90])
    ciel = (haut + (bas - haut) * (y[..., None] ** 0.8)) * np.ones((1, w, 1))
    im = Image.fromarray(ciel.astype(np.uint8))
    d = ImageDraw.Draw(im)
    halo = Image.new("L", (w, h), 0)
    ImageDraw.Draw(halo).ellipse([w * .55, h * .38, w * .55 + 320, h * .38 + 320], fill=255)
    halo = halo.filter(ImageFilter.GaussianBlur(70))
    im = Image.composite(Image.new("RGB", (w, h), (255, 214, 140)), im, halo)
    d = ImageDraw.Draw(im)
    d.ellipse([w * .55 + 100, h * .38 + 100, w * .55 + 220, h * .38 + 220], fill=(255, 236, 190))
    rng = np.random.default_rng(3)
    for couleur, base, ampl in (((92, 70, 120), .58, .16), ((60, 46, 90), .64, .12), ((34, 28, 58), .70, .08)):
        xs = np.linspace(0, w, 14)
        ys = h * (base - ampl * rng.random(14))
        d.polygon([(0, h)] + list(zip(xs, ys)) + [(w, h)], fill=couleur)
    lac = int(h * .72)
    reflet = im.crop((0, lac - (h - lac), w, lac)).transpose(Image.FLIP_TOP_BOTTOM).filter(ImageFilter.GaussianBlur(3))
    reflet = Image.blend(reflet, Image.new("RGB", reflet.size, (30, 40, 80)), .35)
    im.paste(reflet, (0, lac))
    chemin = DOSSIER / "paysage-exemple.png"
    im.save(chemin)
    return chemin


from pixane import langue
langue.choisir(LANGUE)
from pixane.__main__ import traduire_qt
from pixane.canevas import TEXTE
from pixane.fenetre import Fenetre, reglages
from pixane.moteur import Moteur
from pixane.texte import CENTRE

Moteur.demarrer = lambda self, signaler=None: None
app = QApplication(sys.argv)
traduire_qt(app, LANGUE)
reglages().clear()
f = Fenetre()
f.changer_theme("sombre")
f.resize(1440, 900)
f.show()
f.charger(str(paysage()))
f.moteur.etat = "prêt"
f.etat_moteur.emit(langue.tr("prêt"))
f._actualiser()
app.processEvents()
f._choisir_outil(TEXTE)
pt = f.panneau_texte
pt.defaut = pt.defaut.__class__(texte="", gras=True, alignement=CENTRE, ombre=True, couleur="#ffffffff")
f.canevas.texte_nouveau.emit(QPointF(800, 250))
pt.saisie.setPlainText("Souvenirs d'été" if LANGUE == "fr" else "Summer memories")
pt.courbe.setValue(40)
f.doc.modifie = False
f.historique.clear()
app.processEvents()
f.canevas.repaint()
f.grab().save(str(DOSSIER / f"capture-{LANGUE}.png"))
print("capture", LANGUE, "faite")
reglages().clear()
QTimer.singleShot(100, f.close)
app.exec()
os._exit(0)
