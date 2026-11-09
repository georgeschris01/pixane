"""Fichier > Exporter sous (copie à plat, la photo ouverte ne change pas), flèches du clavier pour décaler la sélection,
liste des polices avec un exemple du texte. Usage : essai_export_fleches_polices.py dossier_de_sortie"""
import os
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
from PIL import Image
from PySide6.QtCore import QEvent, QModelIndex, Qt
from PySide6.QtGui import QColor, QImage, QKeyEvent, QPainter, QTextCursor
from PySide6.QtWidgets import QApplication, QFileDialog, QStyleOptionViewItem

from pixane.canevas import DEPLACER, LASSO, RECTANGLE
from pixane.document import FORMAT_IMAGE, Document, nouvelle_selection, tableau
from pixane.fenetre import Fenetre
from pixane.moteur import Moteur
from pixane.panneau_texte import ApercuPolices

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
f = Fenetre()
f.show()
f.reglages.remove("exporter_format")

img = QImage(120, 80, FORMAT_IMAGE)
img.fill(QColor(30, 120, 200))
doc = Document(img)
doc.dpi = 300
original = sortie / "photo.jpg"
doc.enregistrer(original)
doc = Document.ouvrir(original)
f._installer_document(doc)
doc.modifie = True

# 1. Exporter sous
vus = {}


def faux_dialogue(parent, titre, propose, filtres, choisi):
    vus.update(titre=titre, propose=propose, filtres=filtres, choisi=choisi)
    return vus.get("reponse", ("", "")) if "reponse" in vus else (str(sortie / "envoi.png"), filtres.split(";;")[0])


QFileDialog.getSaveFileName = staticmethod(faux_dialogue)
vus["reponse"] = (str(sortie / "envoi"), "JPEG (*.jpg)")
verifier(f.a_exporter_sous.isEnabled() and f.a_exporter_sous.shortcut().toString() == "Ctrl+Alt+Shift+W",
         "menu Fichier > Exporter sous… (Ctrl+Alt+Maj+W)")
f.exporter_sous()
verifier(Path(vus["propose"]).name == "photo_retouche.jpg", f"ne propose pas d'écraser la photo ({vus['propose']})")
verifier(vus["filtres"].split(";;")[0].startswith("JPEG"), "JPEG proposé d'abord")
verifier((sortie / "envoi.jpg").exists(), "extension ajoutée selon le format choisi (envoi.jpg)")
with Image.open(sortie / "envoi.jpg") as im:
    verifier(im.size == (120, 80) and round(im.info.get("dpi", (0,))[0]) == 300, "pleine taille, 300 ppp gardés")
verifier(doc.chemin == original and doc.modifie, "la photo ouverte n'a pas changé (même fichier, toujours modifiée)")
vus["reponse"] = (str(sortie / "envoi.png"), "")
f.exporter_sous()
verifier((sortie / "envoi.png").exists() and f.reglages.value("exporter_format") == ".png", "PNG, format retenu")
f.exporter_sous()
verifier(vus["filtres"].split(";;")[0].startswith("PNG"), "la fois suivante, PNG proposé d'abord")
f.reglages.remove("exporter_format")


# 2. flèches : décaler la sélection
def touche(k, modif=Qt.NoModifier):
    f.canevas.keyPressEvent(QKeyEvent(QEvent.KeyPress, k, modif))


sel = nouvelle_selection(120, 80)
p = QPainter(sel)
p.fillRect(10, 10, 20, 20, QColor(0, 0, 0, 255))
p.end()
doc.selection = sel
f._choisir_outil(RECTANGLE)
pixels_avant = tableau(doc.calques[0].image).copy()
n = f.historique.count()
touche(Qt.Key_Right)
touche(Qt.Key_Right)
touche(Qt.Key_Down, Qt.ShiftModifier)
r = doc.rect_selection()
verifier((r.x(), r.y(), r.width(), r.height()) == (12, 20, 20, 20), f"flèches : sélection décalée (+2, +10 avec Maj) {r}")
verifier((tableau(doc.calques[0].image) == pixels_avant).all(), "les pixels ne bougent pas, seulement la sélection")
verifier(f.historique.count() == n + 1, "une seule étape dans Annuler")
f.historique.undo()
r = doc.rect_selection()
verifier((r.x(), r.y()) == (10, 10), "Ctrl+Z : sélection revenue")
f._choisir_outil(LASSO)
touche(Qt.Key_Left)
verifier(doc.rect_selection().x() == 9, "aussi avec le lasso")
f._choisir_outil(DEPLACER)
touche(Qt.Key_Left)
verifier(doc.rect_selection().x() == 9, "pas avec l'outil Déplacer")
doc.selection = nouvelle_selection(120, 80)
f._choisir_outil(RECTANGLE)
n = f.historique.count()
touche(Qt.Key_Left)
verifier(f.historique.count() == n, "sans sélection : rien")

# 3. polices : nom + exemple du texte tapé ou sélectionné
pt = f.panneau_texte if hasattr(f, "panneau_texte") else next(w for w in f.findChildren(object)
                                                              if type(w).__name__ == "PanneauTexte")
verifier(isinstance(pt.police.itemDelegate(), ApercuPolices), "liste des polices avec aperçu")
pt.saisie.setPlainText("")
verifier(pt.exemple_police() == "Aa Bb Cc 123", "sans texte : modèle Aa Bb Cc 123")
pt.saisie.setPlainText("Mon beau titre de pochette\nsur deux lignes")
verifier(pt.exemple_police() == "Mon beau titre de pochet…", f"début du texte, une ligne ({pt.exemple_police()})")
c = pt.saisie.textCursor()
c.setPosition(4)
c.setPosition(8, QTextCursor.KeepAnchor)
pt.saisie.setTextCursor(c)
verifier(pt.exemple_police() == "beau", "partie sélectionnée seulement")
pt.saisie.setPlainText("")
# dessin d'une ligne de la liste (sans erreur, exemple visible)
d = pt.police.itemDelegate()
image = QImage(460, 32, QImage.Format_ARGB32)
image.fill(QColor(255, 255, 255))
p = QPainter(image)
opt = QStyleOptionViewItem()
opt.rect = image.rect()
opt.font = pt.police.font()
opt.fontMetrics = pt.police.fontMetrics()
opt.palette = pt.police.palette()
index = pt.police.model().index(0, 0, QModelIndex())
d.paint(p, opt, index)
p.end()
a = tableau(image.convertToFormat(FORMAT_IMAGE))
verifier((a[:, 200:, :3] < 128).any() and (a[:, :180, :3] < 128).any(), "ligne dessinée : nom à gauche, exemple à droite")

print("ERREURS :", erreurs if erreurs else "aucune")
sys.stdout.flush()
for dd in f.documents:
    dd.modifie = False
f.close()
sys.exit(1 if erreurs else 0)
