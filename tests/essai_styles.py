"""Styles de calque : rendu des effets, fenêtre Style du calque, enregistrement (.pixane modifiable, .ora / .psd figés),
mise à l'échelle, lumière commune, ombre au sol (poignée), copier / coller, figer.
Usage : essai_styles.py dossier_sortie"""
import os
import sys
import time
from dataclasses import replace
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PIL import Image
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QMessageBox
from pixane.canevas import PEINTURE
from pixane.document import Calque, Document, FORMAT_IMAGE, image_vide, pil_vers_qimage, tableau
from pixane.fenetre import Fenetre
from pixane.moteur import Moteur
from pixane.styles import Effet, Style, image_rendue, rendre_style, styles_prets

Moteur.demarrer = lambda self, signaler=None: (_ for _ in ()).throw(Exception("moteur désactivé pour l'essai"))
Fenetre._moteur_en_echec = lambda self, *a: None
QMessageBox.information = lambda *a, **k: QMessageBox.Ok
sortie = Path(sys.argv[1])
sortie.mkdir(parents=True, exist_ok=True)
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


app = QApplication(sys.argv)
W, H = 900, 600
fond = np.zeros((H, W, 3), np.uint8)
fond[...] = (200, 190, 170)
Image.fromarray(fond).save(sortie / "fond.png")
# objet : un rectangle bleu au milieu (calque 1)
obj = np.zeros((H, W, 4), np.uint8)
obj[200:400, 350:550] = (40, 90, 200, 255)


def rgba(img):
    return tableau(img.convertToFormat(FORMAT_IMAGE))


# ---------------------------------------------------------------- rendu
q_obj = pil_vers_qimage(Image.fromarray(obj, "RGBA"))
ombre = Style((Effet.nouveau("ombre", angle=90, distance=20, taille=6, opacite=100, mode="normal"),))
r = rgba(rendre_style(q_obj, ombre))
verifier(r[410, 450, 3] > 150 and r[150, 450, 3] == 0, "ombre portée : lumière en haut -> ombre en bas")
verifier((r[300, 450] == rgba(q_obj)[300, 450]).all(), "ombre portée : le contenu reste intact au-dessus")
contour = Style((Effet.nouveau("contour", taille=10, couleur="#ff0000"),))
r = rgba(rendre_style(q_obj, contour))
verifier(r[195, 450, 0] > 200 and r[195, 450, 3] > 200 and r[185, 450, 3] < 30,
         f"contour extérieur de 10 px : rouge à 5 px du bord, rien à 15 px ({r[185, 450, 3]})")
interieur = Style((Effet.nouveau("contour", taille=10, couleur="#ff0000", position="interieur"),))
r = rgba(rendre_style(q_obj, interieur))
verifier(r[205, 450, 0] > 200 and r[230, 450, 2] > 150 and r[195, 450, 3] < 30, "contour intérieur")
deux = Style((Effet.nouveau("contour", taille=6, couleur="#ff0000"),
              Effet.nouveau("contour", taille=14, couleur="#00ff00")))
r = rgba(rendre_style(q_obj, deux))
verifier(r[197, 450, 0] > 200 and r[190, 450, 1] > 200, "deux contours (rouge dedans, vert dehors) : mieux que Photoshop")
vide = Style(remplissage=0.0, effets=(Effet.nouveau("contour", taille=4, couleur="#ffffff"),))
r = rgba(rendre_style(q_obj, vide))
verifier(r[300, 450, 3] == 0 and r[198, 450, 3] > 200, "remplissage 0 % : il ne reste que le contour")
dur = Style((Effet.nouveau("ombre", angle=90, distance=40, taille=40, opacite=100, mode="normal"),))
realiste = Style((Effet.nouveau("ombre", angle=90, distance=40, taille=40, opacite=100, mode="normal",
                                realiste=True),))
a1, a2 = rgba(rendre_style(q_obj, dur))[:, :, 3], rgba(rendre_style(q_obj, realiste))[:, :, 3]
verifier(a2[405, 450] > a1[405, 450] and a2[470, 450] < a1[470, 450] + 5,
         f"ombre réaliste : plus nette près de l'objet ({a2[405, 450]} > {a1[405, 450]})")
sol = Style((Effet.nouveau("ombre_sol", tx=80, ty=-30, opacite=100, estompe=0),))
r = rgba(rendre_style(q_obj, sol))[:, :, 3]
verifier(r[370, 590] > 50 and r[450, 450] == 0, "ombre au sol : couchée en arrière, vers la droite")
for nom, st in styles_prets():
    t = time.time()
    a = rgba(rendre_style(q_obj, st))
    verifier((a != rgba(q_obj)).any() and time.time() - t < 1.5, f"style tout prêt « {nom} » ({(time.time() - t) * 1000:.0f} ms)")
grand = image_vide(6000, 4000)
from PySide6.QtGui import QPainter, QColor
p = QPainter(grand)
p.fillRect(1000, 1000, 2500, 1500, QColor(30, 120, 60))
p.end()
t = time.time()
rendre_style(grand, styles_prets()[7][1])            # Or : dégradé, biseau, contour, ombre
verifier(time.time() - t < 6, f"24 Mpx, objet de 3,75 Mpx, style Or : {time.time() - t:.1f} s")

# ---------------------------------------------------------------- document : enregistrement, échelle, fusion
doc = Document(calques=[Calque.depuis("fond", pil_vers_qimage(Image.fromarray(fond))),
                        Calque.depuis("objet", q_obj, style=contour)])
verifier(rgba(doc.image)[195, 450, 0] > 200, "image affichée : le style est appliqué")
verifier((rgba(doc.calques[1].image) == rgba(q_obj)).all(), "pixels du calque intacts (non destructif)")
doc.enregistrer(sortie / "style.pixane")
d2 = Document.ouvrir(sortie / "style.pixane")
verifier(d2.calques[1].style is not None and d2.calques[1].style.effets[0].r("taille") == 10,
         ".pixane : style relu, toujours modifiable")
doc.enregistrer(sortie / "style.ora")
d3 = Document.ouvrir(sortie / "style.ora")
verifier(d3.calques[1].style is None and rgba(d3.calques[1].image)[195, 450, 0] > 200,
         ".ora (Krita, GIMP) : effets mis dans les pixels")
doc.enregistrer(sortie / "style.psd")
d4 = Document.ouvrir(sortie / "style.psd")
verifier(rgba(d4.image)[195, 450, 0] > 200, ".psd : effets visibles (mis dans les pixels)")
doc.appliquer_etat(doc.etat_taille(450, 300))
verifier(abs(doc.calques[1].style.effets[0].r("taille") - 5) < 0.01, "Taille de l'image / 2 : contour 10 -> 5 px")
doc.actif = 1
doc.appliquer_etat(doc.etat_fusionner_bas())
verifier(len(doc.calques) == 1 and doc.calques[0].style is None and rgba(doc.image)[97, 225, 0] > 200,
         "fusionner : le contour passe dans les pixels, plus de style")

# ---------------------------------------------------------------- fenêtre
f = Fenetre()
f.resize(1440, 920)
f.show()
f.charger(str(sortie / "fond.png"))
app.processEvents()
calque = Calque.depuis(f.doc.nom_libre("Objet"), q_obj)
f._commande_calques(f.doc.etat_avec(f.doc.calques + (calque,), 1), "essai")
nb = f.historique.count()
f.style_calque()
app.processEvents()
d = f._dialogue_style
verifier(d is not None and d.isVisible() and d.galerie.count() >= 14, f"fenêtre Style : {d.galerie.count()} vignettes")
d._style_pret(d.galerie.item(3))                     # Autocollant
app.processEvents()
d._apercu()
verifier(f.doc.calques[1].style is not None and f.historique.count() == nb, "style tout prêt : aperçu sans Annuler")
d._ajouter("ombre_interne")
d._changer("distance", 9.0)
verifier(d.style.effets[-1].r("distance") == 9.0 and d.liste.count() == 3, "ajouter un effet et le régler")
d._dupliquer()
verifier(d.liste.count() == 4 and "2" in d.liste.item(3).text(), "dupliquer un effet : numéroté")
# pendant la fenêtre : un clic de pinceau sur la photo ne peint pas
f._choisir_outil(PEINTURE)
f.canevas.style_ouvert = True
avant = rgba(f.doc.image)
e = f.canevas.vers_ecran(QPointF(100, 100))
f.canevas.event(QMouseEvent(QEvent.MouseButtonPress, e, e, Qt.LeftButton, Qt.LeftButton, Qt.NoModifier))
f.canevas.event(QMouseEvent(QEvent.MouseButtonRelease, e, e, Qt.LeftButton, Qt.NoButton, Qt.NoModifier))
verifier((rgba(f.doc.image) == avant).all(), "fenêtre ouverte : la photo ne se peint pas")
d.accept()
app.processEvents()
verifier(f.historique.count() == nb + 1 and len(f.doc.calques[1].style.effets) == 4 and f._dialogue_style is None,
         "OK : une seule étape « Style du calque »")
verifier("fx" in f.calques.liste.itemWidget(f.calques.liste.item(0)).details.text(), "panneau Calques : mention fx")
f.historique.undo()
verifier(f.doc.calques[1].style is None, "Ctrl+Z : style enlevé")
f.historique.redo()
# Annuler
f.style_calque()
d = f._dialogue_style
d._mettre_style(Style())
d._apercu()
d.reject()
verifier(len(f.doc.calques[1].style.effets) == 4, "Annuler : style d'avant remis")
# lumière commune
f.doc.actif = 1
f.copier_style()
f._commande_calques(f.doc.etat_avec(f.doc.calques + (replace(calque, nom="Objet 2", style=Style(
    (Effet.nouveau("ombre", angle=120),))),), 2), "essai")
f.style_calque()
d = f._dialogue_style
d._ajouter("ombre")
d._changer("angle", 45.0)
d.accept()
verifier(f.doc.calques[1].style.angle_global() == 45 and f.doc.calques[2].style.effets[0].r("angle") == 45,
         "lumière commune : changer l'angle sur un calque change tous les calques")
# ombre au sol : poignée sur la photo
f.doc.actif = 1
f.style_calque()
d = f._dialogue_style
d._mettre_style(Style((Effet.nouveau("ombre_sol"),)), choisi=0)
d._apercu()
verifier(f.canevas.poignee_sol is not None, "ombre au sol : poignée affichée sur la photo")
f.canevas.poignee_sol_bouge.emit(QPointF(450 - 100, 400 - 100))     # pied (450, 399), hauteur 200
e = d.style.effets[0]
verifier(e.r("tx") == -50 and e.r("ty") == -50, f"poignée tirée : direction {e.r('tx')}, longueur {e.r('ty')}")
f.grab().save(str(sortie / "style_fenetre.png"))
d.grab().save(str(sortie / "style_dialogue.png"))
d.accept()
verifier(f.canevas.poignee_sol is None and not f.canevas.style_ouvert, "fermée : poignée et blocage retirés")
# coller, figer, transformer
f.doc.actif = 0
f.coller_style()
verifier(f.doc.calques[0].style is not None, "coller le style sur un autre calque")
f.doc.actif = 1
attendu = rgba(image_rendue(f.doc.calques[1]))
f.figer_style()
verifier(f.doc.calques[1].style is None and (rgba(f.doc.calques[1].image) == attendu).all()
         and (attendu != rgba(q_obj)).any(), "mettre le style dans les pixels")

print("ERREURS :", erreurs if erreurs else "aucune")
sys.stdout.flush()
for d in f.documents:          # plusieurs onglets : aucune question à la fermeture
    d.modifie = False
f.close()
sys.exit(1 if erreurs else 0)
