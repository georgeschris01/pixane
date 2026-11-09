"""Nouvelle image (formats, unités, résolution, mode, fond perdu), résolution gardée dans les fichiers, niveaux de
gris, taille de la zone de travail, CMJN (export et aperçu). Usage : essai_nouvelle_image.py dossier_de_sortie"""
import os
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PIL import Image
from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from pixane import formats as fmt
from pixane.dialogues_document import ExportImpression, NouvelleImage, ZoneTravail
from pixane.document import FORMAT_IMAGE, Calque, Document, image_vide, tableau
from pixane.fenetre import Fenetre, reglages
from pixane.moteur import Moteur
from pixane.psd import lire_resolution_psd
from pixane.texte import Texte

Moteur.demarrer = lambda self, signaler=None: None
Fenetre._moteur_en_echec = lambda self, *a: None
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


app = QApplication(sys.argv)
sortie = Path(sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp())
sortie.mkdir(parents=True, exist_ok=True)
r = reglages()
r.remove("formats_perso")
r.remove("nouvelle_derniere")

# 1. unités et formats
verifier(fmt.vers_px(72, "pt", 300) == 300 and fmt.vers_px(6, "pc", 300) == 300 and fmt.vers_px(2.54, "cm", 100) == 100,
         "unités : 72 pt = 6 picas = 1 pouce, 2,54 cm = 1 pouce")
cd = next(f for cat, l in fmt.formats() for f in l if f.nom.startswith("CD : livret"))
verifier(cd.pixels() == (1417 + 70, 1417 + 70), f"CD 12 cm à 300 ppp + 3 mm de fond perdu : {cd.pixels()}")
verifier(sum(len(l) for _c, l in fmt.formats()) >= 30, "plus de 30 formats tout prêts")

# 2. fenêtre Nouvelle image
d = NouvelleImage(None, None, r)
d.appliquer_format(cd)
verifier(d.pixels() == cd.pixels() and len(d.reperes()) == 8, "format CD : taille et 8 repères (fond perdu + sécurité)")
d.unite.setCurrentIndex(fmt.UNITES.index("cm"))
verifier(abs(d.largeur.value() - 12) < 0.02 and d.pixels() == cd.pixels(), "passage en cm : 12 cm, mêmes pixels")
d.unite.setCurrentIndex(fmt.UNITES.index("pt"))
verifier(abs(d.largeur.value() - 340.2) < 0.5, f"en points : {d.largeur.value():.1f} pt")
d.unite.setCurrentIndex(fmt.UNITES.index("px"))
d.largeur.setValue(1000)
d.hauteur.setValue(600)
d.b_portrait.click()
verifier((d.largeur.value(), d.hauteur.value()) == (600, 1000) and d.b_portrait.isChecked(), "bouton Portrait")
d.fond_perdu.setValue(0)
d.marge.setValue(0)
d.nom.setText("Ma pochette")
fmt.enregistrer_formats_perso(r, [d.format_choisi()])
d._remplir_arbre()
verifier(d.arbre.topLevelItem(0).text(0) == "Mes formats" and d.arbre.topLevelItem(0).childCount() == 1,
         "format enregistré dans « Mes formats »")
d.accept()
verifier(fmt.dernier_format(r) is not None and fmt.dernier_format(r).hauteur == 1000, "dernier format retenu")
d2 = NouvelleImage(None, None, r)
verifier(d2.pixels() == (600, 1000), "rouvert sur le dernier format")
d.deleteLater()
d2.deleteLater()

# 3. par le menu : nouvelle image CD, nom, mode gris, repères
f = Fenetre()
f.show()
QApplication.clipboard().clear()


def accepter(classe, reglage):
    def agir():
        dd = next(w for w in app.topLevelWidgets() if isinstance(w, classe) and w.isVisible())
        reglage(dd)
        dd.accept()
    QTimer.singleShot(150, agir)


def choisir_cd(dd):
    dd.appliquer_format(cd)
    dd.nom.setText("Pochette essai")
    dd.mode.setCurrentIndex(1)
    dd.fond.liste.setCurrentIndex(3)
    dd.fond.couleur_autre = QColor(200, 30, 30)


accepter(NouvelleImage, choisir_cd)
f.a_nouvelle.trigger()
doc = f.doc
verifier(doc.taille() == cd.pixels() and doc.dpi == 300 and doc.mode == "gris" and doc.nom == "Pochette essai",
         "nouvelle image : taille, 300 ppp, gris, nom")
verifier(len(doc.reperes) == 8 and ("v", 35.0) in doc.reperes, "repères posés au fond perdu")
t = tableau(doc.image)
verifier(int(t[5, 5, 0]) == int(t[5, 5, 1]) == int(t[5, 5, 2]) and 60 < t[5, 5, 0] < 90,
         f"fond rouge vu en gris (luminance {t[5, 5, 0]})")
verifier(f.onglets.barre_onglets.tabText(f.onglets.barre_onglets.currentIndex()).startswith("Pochette essai")
         if hasattr(f, "onglets") else True, "onglet au nom de l'image")
f.changer_mode("rvb")
verifier(tuple(tableau(doc.image)[5, 5, :3]) == (200, 30, 30), "retour en RVB : couleurs revenues")
f.changer_mode("gris")

# 4. fichiers : résolution et gris gardés
doc.enregistrer(sortie / "essai.pixane")
d3 = Document.ouvrir(sortie / "essai.pixane")
verifier(d3.dpi == 300 and d3.mode == "gris" and len(d3.reperes) == 8, ".pixane : résolution, gris et repères relus")
doc.enregistrer(sortie / "essai.jpg")
with Image.open(sortie / "essai.jpg") as im:
    verifier(im.mode == "L" and round(im.info.get("dpi", (0,))[0]) == 300, f"JPEG : gris, 300 ppp ({im.mode})")
verifier(Document.ouvrir(sortie / "essai.jpg").mode == "gris", "JPEG gris rouvert en niveaux de gris")
doc.enregistrer(sortie / "essai.psd")
verifier(lire_resolution_psd(sortie / "essai.psd") == 300 and Document.ouvrir(sortie / "essai.psd").dpi == 300,
         "PSD : 300 ppp écrits et relus")
doc.mode = "rvb"
doc._fusion = None
doc.enregistrer(sortie / "essai.png")
with Image.open(sortie / "essai.png") as im:
    verifier(im.mode == "RGB" and round(im.info.get("dpi", (0,))[0]) == 300, "PNG couleur à 300 ppp")

# 5. taille de la zone de travail
img = QImage(100, 80, FORMAT_IMAGE)
img.fill(QColor(0, 0, 255))
dz = Document(img)
dz.calques = dz.calques + (Calque("Texte", image_vide(100, 80), texte=Texte(texte="A", x=50, y=40)),)
dz._fusion = None
dz.reperes = [("v", 10.0)]
f._installer_document(dz)
avant = (dz.taille(), dz.calques[1].texte.x)


def zone(dd):
    dd.largeur.setValue(140)
    dd.hauteur.setValue(100)
    dd.fond.liste.setCurrentIndex(2)          # noir


accepter(ZoneTravail, zone)
f.a_zone_travail.trigger()
t = tableau(dz.calques[0].image.convertToFormat(FORMAT_IMAGE))
verifier(dz.taille() == (140, 100), f"zone de travail : 140 × 100 ({dz.taille()})")
verifier(tuple(t[0, 0, :3]) == (0, 0, 0) and tuple(t[50, 70, :3]) == (0, 0, 255) and tuple(t[10, 20, :3]) == (0, 0, 255),
         "bande noire ajoutée, image centrée (décalée de 20, 10)")
verifier(dz.calques[1].texte.x == 70 and dz.reperes == [("v", 30.0)], "texte et repères suivent")
f.historique.undo()
verifier(dz.taille() == (100, 80) and dz.reperes == [("v", 10.0)], "Annuler (repères compris)")
d4 = ZoneTravail(100, 80, 72)
d4.relatif.setChecked(True)
d4.largeur.setValue(20)
d4._ancres.button(0).click()
verifier(d4.pixels() == (120, 80) and d4.decalage() == (0, 0), "relative + ancrage en haut à gauche")
d4.unite.setCurrentIndex(d4.unite.findData("%"))
d4.relatif.setChecked(False)
d4.largeur.setValue(50)
verifier(d4.pixels()[0] == 50, "pourcentage : 50 % = 50 px (rogné)")
d4.deleteLater()

# 6. CMJN
from pixane import impression  # noqa: E402
profils = impression.profils_cmjn()
verifier(len(profils) > 0, f"profils CMJN de Windows : {len(profils)} (par défaut : {profils[0][0] if profils else '-'})")
if profils:
    vif = QImage(64, 64, FORMAT_IMAGE)
    vif.fill(QColor(0, 60, 255))
    for ext in (".tif", ".jpg", ".pdf"):
        impression.enregistrer_cmjn(vif, sortie / f"cmjn{ext}", profils[0][1], dpi=300)
    with Image.open(sortie / "cmjn.tif") as im:
        verifier(im.mode == "CMYK" and im.info.get("icc_profile") and round(im.info["dpi"][0]) == 300,
                 "TIFF CMJN avec profil et 300 ppp")
    with Image.open(sortie / "cmjn.jpg") as im:
        verifier(im.mode == "CMYK", "JPEG CMJN")
    verifier((sortie / "cmjn.pdf").read_bytes()[:5] == b"%PDF-", "PDF CMJN")
    a = tableau(impression.apercu_impression(vif, profils[0][1]))
    verifier(a.shape == (64, 64, 4) and abs(int(a[0, 0, 2]) - 255) > 10, f"aperçu : bleu vif terni à l'impression "
             f"{tuple(a[0, 0, :3])}")
    f.basculer_epreuve()
    verifier(dz.epreuve is not None and f.a_epreuve.isChecked() and
             dz.image_affichee().cacheKey() != dz.image.cacheKey(), "Affichage > Aperçu de l'impression allumé")
    f.basculer_epreuve()
    verifier(dz.epreuve is None and dz.image_affichee() is dz.image, "aperçu éteint")
    de = ExportImpression(300, r)
    verifier(de.profil.count() == len(profils) and de.valeurs()["profil"], "fenêtre Exporter pour l'impression")
    de.deleteLater()

print("ERREURS :", erreurs if erreurs else "aucune")
sys.stdout.flush()
r.remove("formats_perso")
r.remove("nouvelle_derniere")
for dd in f.documents:
    dd.modifie = False
f.close()
sys.exit(1 if erreurs else 0)
