"""16 bits par couche : Image > Mode, réglages et filtres en 16 bits, pont pour les fonctions 8 bits, calques de
réglage et modes de fusion, enregistrement et relecture (PNG, TIFF, PSD, .piximg), export JPG.
Usage : python tests/essai_16bits.py DOSSIER_SORTIE"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("PIXANE_REGLAGES", "Pixane-essais")

import numpy as np
from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication, QMessageBox

from pixane import ajustements, filtres
from pixane import profondeur as P
from pixane.document import FORMAT_CALQUE, Calque, Document, qimage_rgb, tableau
from pixane.fenetre import Fenetre

sortie = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(os.environ["TEMP"]) / "essai_16bits"
sortie.mkdir(parents=True, exist_ok=True)
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ERREUR  ") + texte)
    if not cond:
        erreurs.append(texte)


app = QApplication(sys.argv)
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.Ok)
QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.Ok)
W, H = 600, 40

# dégradé sombre 16 bits très fin : 0 → 2000 (en 8 bits il n'en resterait que 8 nuances)
deg = np.tile(np.linspace(0, 2000, W).round().astype(np.uint16), (H, 1))
t16 = np.dstack([deg, deg, deg, np.full((H, W), 65535, np.uint16)])
png = sortie / "degrade16.png"
P.qimage16(t16).convertToFormat(QImage.Format_RGBX64).save(str(png))

# ---- ouverture d'un PNG 16 bits
doc = Document.ouvrir(png)
verifier(doc.profondeur == 16 and P.est_16(doc.calques[0].image), "PNG 16 bits ouvert en 16 bits")
verifier(np.array_equal(P.tab16(doc.calques[0].image)[..., 0], deg), "pixels 16 bits gardés à l'ouverture")

# ---- réglage Niveaux en 16 bits : le dégradé étiré garde ses nuances
p = ajustements.defaut("niveaux")
p["rvb"] = [0, 1.0, 8, 0, 255]                              # 0..2000 (≈ 0..7,8 sur 255) étiré sur toute l'échelle
img = filtres.appliquer_calque(doc.calques[0].image, lambda a: ajustements.appliquer_rgba(a, "niveaux", p), None,
                               "entier")
doc.appliquer_etat(doc.etat_calque_modifie(0, image=img))
n16 = len(np.unique(P.tab16(doc.image16())[0, :, 0]))
d8 = Document(qimage_rgb(np.dstack([(deg >> 8).astype(np.uint8)] * 3)))
img8 = filtres.appliquer_calque(d8.calques[0].image, lambda a: ajustements.appliquer_rgba(a, "niveaux", p), None)
n8 = len(np.unique(tableau(img8)[0, :, 0]))
verifier(n16 > 500 and n8 < 10, f"Niveaux : {n16} nuances en 16 bits, {n8} en 8 bits (cassures)")

# ---- tous les réglages et filtres marchent en 16 bits
for type_ in ajustements.TYPES:
    try:
        r = ajustements.appliquer_rgba(P.tab16(doc.calques[0].image), type_, ajustements.defaut(type_))
        ok = r.dtype == np.uint16
    except Exception as e:
        ok = False
        print("   ", type_, e)
    verifier(ok, f"réglage « {type_} » en 16 bits")
for type_, fonction in filtres.FONCTIONS.items():
    try:
        r = filtres.appliquer_calque(doc.calques[0].image, lambda a: fonction(a, filtres.defauts(type_)), None,
                                     "flottant")
        ok = P.est_16(r)
    except Exception as e:
        ok = False
        print("   ", type_, e)
    verifier(ok, f"filtre « {type_} » en 16 bits")
flou = filtres.appliquer_calque(doc.calques[0].image, lambda a: filtres.flou_gaussien(a, {"rayon": 4}), None,
                                "flottant")
verifier(len(np.unique(P.tab16(flou)[20, :, 0])) > 500, "flou gaussien sans cassures en 16 bits")

# ---- pont : une fonction 8 bits qui ne change qu'une zone
avant = P.tab16(doc.calques[0].image)
x = doc.calques[0].image.convertToFormat(FORMAT_CALQUE)
pp = QPainter(x)
pp.fillRect(0, 0, 50, 10, QColor("red"))
pp.end()
doc.appliquer_etat(doc.etat_calque_modifie(0, image=x))
apres = P.tab16(doc.calques[0].image)
verifier(P.est_16(doc.calques[0].image) and np.array_equal(avant[10:], apres[10:]) and
         np.array_equal(avant[:10, 50:], apres[:10, 50:]) and apres[0, 0, 0] == 65535,
         "pont : calque remis en 16 bits, pixels non touchés gardés exactement")

# ---- calque de réglage et mode de fusion « Couleur » en 16 bits
doc2 = Document.ouvrir(png)
reg = Calque("Niveaux", P.en_16(QImage(W, H, FORMAT_CALQUE)), reglage={"type": "niveaux", "params": p})
coul = QImage(W, H, FORMAT_CALQUE)
coul.fill(QColor(200, 30, 30))
doc2.appliquer_etat(doc2.etat_avec([*doc2.calques, reg, Calque("Couleur", coul, mode="couleur", opacite=0.5)]))
f16 = P.tab16(doc2.image16())
verifier(all(P.est_16(c.image) for c in doc2.calques) and len(np.unique(f16[0, :, 0])) > 500,
         "calque de réglage + mode Couleur : fusion en 16 bits, sans cassures")

# ---- enregistrer et relire : PNG, TIFF, PSD, .piximg
ref = P.tab16(doc.image16())
for ext in ("png", "tif", "psd", "piximg"):
    f = sortie / f"essai16.{ext}"
    doc.enregistrer(f)
    lu = Document.ouvrir(f)
    ecart = int(np.abs(P.tab16(lu.image16()).astype(int) - ref.astype(int)).max())
    verifier(lu.profondeur == 16 and ecart <= 1, f".{ext} : relu en 16 bits (écart {ecart})")
doc.enregistrer(sortie / "essai16.jpg")
verifier((sortie / "essai16.jpg").stat().st_size > 0, "export JPG d'une image 16 bits (en 8 bits)")

# ---- tramage : un dégradé 16 bits passé en 8 bits garde sa pente en moyenne (pas de marches)
from pixane import calque_remplissage, degrades, outils_dessin, retouche
from pixane.transformation import redimensionner
lent = np.tile(np.linspace(1000, 4000, W).round().astype(np.uint16), (256, 1))   # ≈ 4 à 16 sur 255
img = P.qimage16(np.dstack([lent, lent, lent, np.full(lent.shape, 65535, np.uint16)]))
vrai = lent[0].astype(np.float64) / 257
P.tramage = False
sans = tableau(P.vers_8_trame(img).convertToFormat(QImage.Format_RGBA8888))[..., 0].astype(np.float64).mean(axis=0)
P.tramage = True
avec = tableau(P.vers_8_trame(img).convertToFormat(QImage.Format_RGBA8888))[..., 0].astype(np.float64).mean(axis=0)
e_sans, e_avec = np.abs(sans - vrai).mean(), np.abs(avec - vrai).mean()
verifier(e_avec < e_sans / 3, f"tramage : écart moyen au vrai dégradé {e_avec:.3f} au lieu de {e_sans:.3f}")
d3 = Document(calques=[Calque("Fond", P.en_16(img))])
d3.definir_profondeur(16)
d3.appliquer_etat(d3.etat_profondeur(8))
d3.profondeur = 8
moy = tableau(d3.calques[0].image)[..., 0].astype(np.float64).mean(axis=0)
verifier(np.abs(moy - vrai).mean() < e_sans / 3, "Image > Mode > 8 bits : avec tramage")

# ---- outil Dégradé dessiné en 16 bits sur un calque 16 bits
base = P.en_16(QImage(W, H, FORMAT_CALQUE))
base.fill(0)
from PySide6.QtCore import QPointF
g = outils_dessin.degrade(base, QPointF(0, 0), QPointF(W, 0), "lineaire", degrades.deux_couleurs("#000000", "#101010"),
                          QColor("black"), 1.0)
verifier(P.est_16(g) and len(np.unique(P.tab16(g)[5, :, 0])) > 100,
         "outil Dégradé : dessiné en 16 bits (pas de marches)")

# ---- calque de remplissage dégradé : 16 bits, et reste modifiable dans un document 16 bits
d4 = Document.ouvrir(png)
r = calque_remplissage.Remplissage(genre="degrade", degrade=degrades.deux_couleurs("#000000", "#101010"), angle=0)
d4.appliquer_etat(d4.etat_nouveau_remplissage(r, "Dégradé"))
c = d4.calque_actif
verifier(P.est_16(c.image) and calque_remplissage.valide(c) is not None and
         len(np.unique(P.tab16(c.image)[5, :, 0])) > 100, "calque de remplissage : 16 bits et toujours modifiable")

# ---- redimensionner en 16 bits
petit = redimensionner(P.en_16(P.qimage16(t16)), W // 2, H // 2)
verifier(P.est_16(petit) and len(np.unique(P.tab16(petit)[5, :, 0])) > 250, "redimensionner : reste en 16 bits")

# ---- outil de retouche (Densité −) sur un calque 16 bits : pas d'erreur, calque remis en 16 bits
t = retouche.Trait(retouche.ECLAIRCIR, d4.calques[0].image, 20, 0.5, 1.0)
t.ajouter(QPointF(100, 20))
t.ajouter(QPointF(140, 20))
d4.appliquer_etat(d4.etat_calque_modifie(0, image=t.image))
verifier(P.est_16(d4.calques[0].image), "Densité − sur un calque 16 bits")

# ---- IA (Effacer, Remplir… et Agrandir) : son résultat 8 bits ne touche que sa zone, le reste garde ses 16 bits
d5 = Document.ouvrir(png)
ref5 = P.tab16(d5.calques[0].image)
res = QImage(d5.image)
pp = QPainter(res)
pp.fillRect(100, 10, 40, 20, QColor("green"))
pp.end()
zone = np.zeros((H, W), bool)
zone[10:30, 100:140] = True
d5.appliquer_etat(d5.etat_resultat_ia("Effacer", res, zone, nouveau_calque=False))
t5 = P.tab16(d5.calques[0].image)
loin = np.ones((H, W), bool)
loin[0:40, 90:150] = False                    # (zone et son fondu)
verifier(P.est_16(d5.calques[0].image) and np.array_equal(t5[loin], ref5[loin]) and
         np.any(t5[10:30, 100:140] != ref5[10:30, 100:140]),
         "IA dans le calque choisi : zone remplacée, reste de la photo gardé en 16 bits")
d6 = Document.ouvrir(png)
ref6 = P.tab16(d6.calques[0].image)
grand = QImage(W + 100, H, QImage.Format_RGBA8888)
grand.fill(QColor(10, 10, 10))
pp = QPainter(grand)
pp.drawImage(50, 0, d6.image)
pp.end()
d6.appliquer_etat(d6.etat_agrandi("Agrandir", grand, (50, 0), False, (0, 0, W, H)))
t6 = P.tab16(d6.calques[0].image)
verifier(P.est_16(d6.calques[0].image) and np.abs(t6[:, 60:W + 40].astype(int) - ref6[:, 10:W - 10]).max() <= 1,
         "Agrandir dans le même calque : la photo garde ses 16 bits")

# ---- géométrie : pivoter, miroir, redresser, taille, recadrer… restent en vraies 16 bits
geo = {"pivoter": lambda d: d.etat_pivote(90), "miroir": lambda d: d.etat_miroir(True),
       "redresser": lambda d: d.etat_redresse(5), "taille de l'image": lambda d: d.etat_taille(300, 20),
       "recadrer": lambda d: d.etat_recadre(__import__("PySide6.QtCore").QtCore.QRect(10, 5, 400, 30)),
       "transformer": lambda d: d.etat_geometrie(__import__("PySide6.QtGui").QtGui.QTransform().rotate(10), W, H, 10)}
for nom, op in geo.items():
    d7 = Document.ouvrir(png)
    d7.appliquer_etat(op(d7))
    n = len(np.unique(P.tab16(d7.calques[0].image)[..., 0]))
    verifier(P.est_16(d7.calques[0].image) and n > 100, f"{nom} : 16 bits gardés ({n} nuances)")

# ---- fenêtre : Image > Mode > 16 bits, titre, Annuler
f = Fenetre()
f.resize(1200, 800)
f.show()
f.charger(str(sortie / "essai16.jpg"))
app.processEvents()
verifier(f.doc.profondeur == 8 and "16 bits" not in f.windowTitle(), "JPG ouvert en 8 bits")
action = next(a for a in f._actions_bits.actions() if a.data() == 16)
action.trigger()
app.processEvents()
verifier(f.doc.profondeur == 16 and P.est_16(f.doc.calques[0].image) and "16 bits" in f.windowTitle()
         and action.isChecked(), "Image > Mode > 16 bits : calques convertis, « (16 bits) » dans le titre")
from PySide6.QtTest import QTest
P.tramage = True
f.doc._tramee = None
verifier(f.doc.image_affichee() is f.doc.image, "écran : montré tout de suite sans tramage")
QTest.qWait(500)
verifier(f.doc._tramee is not None and f.doc.image_affichee() is f.doc._tramee[2], "écran : tramé 0,3 s plus tard")
f.historique.undo()
app.processEvents()
verifier(f.doc.profondeur == 8 and not P.est_16(f.doc.calques[0].image), "Ctrl+Z : revient en 8 bits")
f.historique.redo()
verifier(f.doc.profondeur == 16, "Rétablir : de nouveau 16 bits")
f.doc.modifie = False

print("ERREURS :", erreurs if erreurs else "aucune")
sys.stdout.flush()
QTimer.singleShot(200, f.close)
app.exec()
sys.exit(1 if erreurs else 0)
