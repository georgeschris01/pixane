"""Outils de texte comme Photoshop : casse, étirement, exposant / indice, ligne de base, crénage (police et à la main),
OpenType, lissage, justifié, cadre, vertical, déformation, tracé, style par lettre, fichier .piximg, Agrandir.
Usage : essai_texte_photoshop.py dossier_sortie   (une image d'essai est fabriquée ; le moteur n'est pas démarré)"""
import os
import sys
from dataclasses import replace
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"   # ne touche pas aux réglages de l'utilisateur
import numpy as np
from PIL import Image
from PySide6.QtCore import QEvent, QPointF, Qt, QTimer
from PySide6.QtGui import QKeyEvent, QMouseEvent, QTextCursor
from PySide6.QtWidgets import QApplication
from pixane.canevas import TEXTE
from pixane.document import tableau
from pixane.fenetre import Fenetre
from pixane.moteur import Moteur

Moteur.demarrer = lambda self, signaler=None: (_ for _ in ()).throw(Exception("moteur désactivé pour l'essai"))
Fenetre._moteur_en_echec = lambda self, *a: None
sortie = Path(sys.argv[1])
sortie.mkdir(parents=True, exist_ok=True)
Image.fromarray(np.full((600, 1000, 3), 60, np.uint8)).save(sortie / "fond.png")

app = QApplication(sys.argv)
from pixane.fenetre import reglages
from pixane.texte import Texte, forme, mise, rendre
reglages().remove("texte_defaut")
f = Fenetre()
f.resize(1440, 920)
f.show()
f.charger(str(sortie / "fond.png"))
app.processEvents()
doc, c, pt_ = f.doc, f.canevas, f.panneau_texte
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


def clic(x, y):
    e = c.vers_ecran(QPointF(x, y))
    c.event(QMouseEvent(QEvent.MouseButtonPress, e, e, Qt.LeftButton, Qt.LeftButton, Qt.NoModifier))
    c.event(QMouseEvent(QEvent.MouseButtonRelease, e, e, Qt.LeftButton, Qt.NoButton, Qt.NoModifier))


def largeur(t):
    return forme(t)[0].boundingRect().width()


def hauteur(t):
    return forme(t)[0].boundingRect().height()


def selectionner(a, b):
    cur = pt_.saisie.textCursor()
    cur.setPosition(a)
    cur.setPosition(b, QTextCursor.KeepAnchor)
    pt_.saisie.setTextCursor(cur)


def curseur(pos):
    cur = pt_.saisie.textCursor()
    cur.setPosition(pos)
    pt_.saisie.setTextCursor(cur)


T = lambda: doc.calque_actif.texte

# 1. un texte
f._choisir_outil(TEXTE)
clic(500, 300)
pt_.saisie.selectAll()
pt_.saisie.insertPlainText("Office AVAWA")
verifier(T().texte == "Office AVAWA", "texte tapé")
base = T()

# 2. caractère
pt_._choisir_liste(pt_.casse, "majuscules")
verifier(T().casse == "majuscules", "casse : majuscules")
haut_min = hauteur(replace(base, texte="acero"))
verifier(hauteur(replace(base, texte="acero", casse="majuscules")) >= haut_min, "majuscules plus hautes")
pt_._choisir_liste(pt_.casse, "normale")
pt_.echelle_h.setValue(150)
verifier(T().echelle_h == 150 and largeur(T()) > largeur(base) * 1.35, "largeur 150 % : texte plus large")
pt_.echelle_h.setValue(100)
pt_.echelle_v.setValue(200)
verifier(hauteur(T()) > hauteur(base) * 1.7, "hauteur 200 % : texte plus haut")
pt_.echelle_v.setValue(100)
pt_._choisir_liste(pt_.crenage, False)
verifier(T().crenage is False and largeur(T()) > largeur(base) + 1, "sans crénage : AVAWA plus large")
pt_._choisir_liste(pt_.crenage, True)
pt_.opentype["fractions"].setChecked(True)
verifier(T().fractions, "fractions")
pt_.opentype["fractions"].setChecked(False)
pt_.lissage.setChecked(False)
a = tableau(rendre(T(), 1000, 600))[:, :, 3]
verifier(T().lissage is False and set(np.unique(a)) <= {0, 255}, "sans lissage : pixels pleins ou vides")
pt_.lissage.setChecked(True)
verifier(T() == base, f"tout remis comme avant : {T() == base}")

# 3. style par lettre (sélection dans la saisie)
selectionner(0, 6)
pt_.couleur.definir("#ffff0000"); pt_.couleur.change.emit("#ffff0000")
pt_._choisir_liste(pt_.position, "exposant")
t = T()
verifier(t.couleur == base.couleur and t.style_de(0)["couleur"] == "#ffff0000" and t.style_de(7)["couleur"] == base.couleur,
         "couleur des lettres sélectionnées seulement")
verifier(t.style_de(3)["position"] == "exposant" and t.style_de(8)["position"] == "normale", "exposant sur la sélection")
m = mise(t)
verifier(len(m.morceaux) == 2, "deux couleurs dessinées")
img = tableau(rendre(t, 1000, 600))
rouge = (img[:, :, 2] > 200) & (img[:, :, 1] < 60) & (img[:, :, 3] > 200)
blanc = (img[:, :, 1] > 200) & (img[:, :, 0] > 200) & (img[:, :, 3] > 200)
ys_r, ys_b = np.nonzero(rouge)[0], np.nonzero(blanc)[0]
verifier(rouge.sum() > 50 and blanc.sum() > 50 and ys_r.max() < ys_b.max() - 5, "rouge en exposant (plus haut)")
verifier(pt_.portee.isVisible(), "panneau : réglages de la sélection annoncés")
curseur(12)
verifier(pt_._choisir_liste and pt_.position.currentData() == "normale", "sans sélection : réglages du texte entier")
pt_.saisie.insertPlainText("!")
verifier(T().texte == "Office AVAWA!" and T().style_de(0)["couleur"] == "#ffff0000", "le style suit les lettres à la saisie")
curseur(0)
pt_.saisie.insertPlainText(">")
verifier(T().style_de(1)["couleur"] == "#ffff0000" and T().style_de(7)["couleur"] == base.couleur,
         "lettre ajoutée devant : styles décalés")
f.historique.undo()
f.historique.undo()
verifier(T().texte == "Office AVAWA", "Annuler la saisie")

# 4. crénage à la main : Alt+flèches
curseur(8)                       # entre A et V
avant = largeur(T())
for _ in range(3):
    app.sendEvent(pt_.saisie, QKeyEvent(QEvent.KeyPress, Qt.Key_Right, Qt.AltModifier))
verifier(T().crenage_a(8) == 60 and pt_.crenage_ici.value() == 60, "Alt+droite x3 : +60 ‰")
verifier(abs(largeur(T()) - avant - T().taille * 0.06) < 2, "lettres écartées de 6 % de la taille")
pt_.crenage_ici.setValue(-40)
verifier(T().crenage_a(8) == -40, "crénage ici : -40 ‰")
pt_.crenage_ici.setValue(0)
verifier(T().crenages == (), "crénage remis à zéro")

# 5. paragraphe : cadre, justifié, retrait, vertical
pt_.saisie.selectAll()
pt_.saisie.insertPlainText("Un texte assez long pour être coupé en plusieurs lignes dans son cadre.\nSecond paragraphe.")
pt_.cadre.setChecked(True)
verifier(T().cadre_l > 0, "texte en cadre")
pt_.cadre_l.setValue(400)
t = T()
lignes = len({round(b) for b in [l.base for l in __import__("pixane.texte", fromlist=["_horizontal"])._horizontal(t)[0]]})
verifier(lignes >= 4, f"lignes coupées toutes seules ({lignes})")
verifier(forme(t)[1].width() == 400, "bloc à la largeur du cadre")
pt_.alignements["justifie"][0].click()
verifier(T().alignement == "justifie", "justifié")
pt_.retrait.setValue(100)
pt_.espace_paragraphe.setValue(50)
verifier(T().retrait == 100 and T().espace_paragraphe == 50, "retrait et espace entre paragraphes")
h1 = forme(T())[1].height()
pt_.cadre_h.setValue(round(T().taille * 1.5))
verifier(forme(T())[1].height() < h1, "hauteur du cadre : le reste est caché")
pt_.cadre.setChecked(False)
verifier(T().cadre_l == 0, "cadre retiré")
pt_.vertical.setChecked(True)
b = forme(T())[1]
verifier(T().vertical and b.height() > b.width(), "texte vertical : plus haut que large")
pt_.vertical.setChecked(False)

# 6. déformation et tracé
pt_.saisie.selectAll()
pt_.saisie.insertPlainText("Déformer")
droit = forme(T())[0].boundingRect()
pt_._choisir_liste(pt_.deformation, "arc")
verifier(T().deformation == "arc" and pt_.flexion.isEnabled(), "déformation arc")
verifier(forme(T())[0].boundingRect().height() > droit.height() * 1.2, "arc : texte courbé (plus haut)")
pt_.flexion.setValue(-80)
verifier(T().flexion == -80, "force -80 %")
for d in ("drapeau", "vague", "poisson", "gonflement", "oeil_de_poisson", "torsion", "arche", "montee"):
    pt_._choisir_liste(pt_.deformation, d)
    verifier(not forme(T())[0].isEmpty(), f"déformation {d} dessinée")
pt_._choisir_liste(pt_.deformation, "aucune")
pt_.distorsion_h.setValue(50)
verifier(T().distorsion_h == 50, "distorsion horizontale")
pt_.distorsion_h.setValue(0)
t = replace(T(), trace=tuple((float(x), float(40 * np.sin(x / 60))) for x in range(-300, 301, 15)))
verifier(not forme(t)[0].isEmpty() and forme(t)[0].boundingRect().height() > droit.height() * 1.3, "texte sur un tracé")

# 7. fichier .piximg et Agrandir gardent tout
t = replace(T(), casse="petites_capitales", echelle_h=120, cadre_l=300.0, trace=((0.0, 0.0), (50.0, 10.0)),
            crenages=((2, 40.0),)).avec_style(1, 3, couleur="#ff00ff00", taille=90.0)
d = t.vers_dict()
import json
t2 = Texte.depuis_dict(json.loads(json.dumps(d)))
verifier(t2 == t, "enregistré / relu à l'identique")
t3 = t.mis_a_l_echelle(2, 2)
verifier(t3.style_de(1)["taille"] == 180 and t3.cadre_l == 600 and t3.trace[1] == (100.0, 20.0),
         "agrandi : taille des lettres à style propre, cadre et tracé suivent")
ancien = Texte.depuis_dict({"texte": "Ancien", "taille": 50})
verifier(ancien.casse == "normale" and ancien.styles == (), "ancien texte (sans les nouveaux réglages) relu")


# 8. tracé dessiné à la souris
from pixane.document import Document
f._choisir_outil(TEXTE)
pt_.saisie.selectAll()
pt_.saisie.insertPlainText("Le long du tracé")
pt_.bouton_trace.setChecked(True)
verifier(c.trace_texte, "Dessiner un tracé : le canevas attend la ligne")
n = f.historique.count()
ligne = [(200 + x, 300 + 60 * np.sin(x / 90)) for x in range(0, 600, 12)]
ecran = [c.vers_ecran(QPointF(*q)) for q in ligne]
c.event(QMouseEvent(QEvent.MouseButtonPress, ecran[0], ecran[0], Qt.LeftButton, Qt.LeftButton, Qt.NoModifier))
for e in ecran[1:]:
    c.event(QMouseEvent(QEvent.MouseMove, e, e, Qt.NoButton, Qt.LeftButton, Qt.NoModifier))
c.event(QMouseEvent(QEvent.MouseButtonRelease, ecran[-1], ecran[-1], Qt.LeftButton, Qt.NoButton, Qt.NoModifier))
t = T()
verifier(len(t.trace) > 10 and not pt_.bouton_trace.isChecked() and not c.trace_texte, "tracé dessiné, bouton relâché")
verifier(f.historique.count() == n + 1 and f.historique.undoText() == "Texte sur un tracé", "tracé annulable")
r = forme(t)[0].boundingRect().translated(t.x, t.y)
verifier(r.height() > t.taille * 1.5 and abs(r.left() - 200) < t.taille, f"le texte suit la ligne ({r.left():.0f}, {r.height():.0f})")
verifier(not pt_.courbe.isEnabled() and pt_.retirer_trace.isEnabled(), "panneau : courbe grisée, Retirer actif")
pt_.trace_debut.setValue(30)
verifier(T().trace_debut == 30 and forme(T())[0].boundingRect().left() > forme(t)[0].boundingRect().left() + 50,
         "départ 30 % : texte avancé sur le tracé")
pt_.retirer_trace.click()
verifier(T().trace == (), "tracé retiré")
f.historique.undo()
verifier(T().trace != (), "Annuler : tracé revenu")

# 9. masque d'écrêtage : une photo dans les lettres
texte_index = doc.actif
yy, xx = np.mgrid[0:600, 0:1000]
photo = np.dstack([xx * 255 // 1000, yy * 255 // 600, np.full_like(xx, 30), np.full_like(xx, 255)]).astype(np.uint8)
from pixane.document import Calque, qimage_rgb
from PySide6.QtGui import QImage
qi = QImage(photo.data, 1000, 600, 4000, QImage.Format_RGBA8888).copy()
f.historique.push(__import__("pixane.fenetre", fromlist=["CommandeEtat"]).CommandeEtat(
    doc, doc.etat(), doc.inserer(Calque.depuis("Photo", qi)), "Photo"))
verifier(doc.actif == texte_index + 1, "photo au-dessus du texte")
avant = tableau(doc.image).copy()
f.calques.ecreter()
verifier(doc.calque_actif.ecretage, "Ctrl+Alt+G : masque d'écrêtage")
apres = tableau(doc.image)
alpha_texte = tableau(doc.calques[texte_index].image)[:, :, 3]
hors = alpha_texte == 0
dans = alpha_texte == 255
verifier(np.abs(apres[hors][:, :3].astype(int) - 60).max() <= 1, "hors des lettres : le fond (photo cachée)")
verifier(np.abs(apres[dans][:, :3].astype(int) - avant[dans][:, :3].astype(int)).max() <= 1, "dans les lettres : la photo")
verifier(not np.array_equal(apres, avant), "l'image a changé")
f.calques.rafraichir()
doc.enregistrer(sortie / "ecretage.piximg")
d2 = Document.ouvrir(sortie / "ecretage.piximg")
verifier(d2.calques[texte_index + 1].ecretage and np.abs(tableau(d2.image).astype(int) - apres.astype(int)).max() <= 1,
         ".piximg : écrêtage gardé, même image")
doc.enregistrer(sortie / "ecretage.psd")
d3 = Document.ouvrir(sortie / "ecretage.psd")
verifier(d3.calques[-1].ecretage and not any("écrêtage" in r for r in d3.remarques), "PSD : écrêtage gardé, sans remarque")
verifier(np.abs(tableau(d3.image)[:, :, :3].astype(int) - apres[:, :, :3].astype(int)).mean() < 1, "PSD relu : même image")
doc.enregistrer(sortie / "ecretage.ora")
d4 = Document.ouvrir(sortie / "ecretage.ora")
verifier(not any(x.ecretage for x in d4.calques) and np.abs(tableau(d4.image).astype(int) - apres.astype(int)).max() <= 2,
         ".ora (Krita, GIMP) : écrêtage mis dans les pixels, même image")
doc.actif = texte_index
f._sync_texte()
pt_.styles["gras"].setChecked(True)
dans2 = tableau(doc.calques[texte_index].image)[:, :, 3] == 255
verifier(T().gras and dans2.sum() > dans.sum() and
         np.abs(tableau(doc.image)[dans2][:, :3].astype(int) - avant[dans2][:, :3].astype(int)).max() <= 1,
         "le texte reste modifiable sous la photo")
doc.actif = texte_index + 1
f.calques.ecreter()
verifier(not doc.calque_actif.ecretage, "Ctrl+Alt+G encore : retiré")
f.historique.undo()
verifier(doc.calque_actif.ecretage, "Annuler")
doc.actif = texte_index
doc.calques_changes.emit()
app.processEvents()

# 10. glyphes
from pixane.glyphes import caracteres
cs = caracteres("Segoe UI")
verifier("€" in cs and "é" in cs and "→" in cs and len(cs) > 500, f"glyphes de Segoe UI ({len(cs)})")
pt_.ouvrir_glyphes()
g = pt_._glyphes
verifier(g.isVisible() and g.liste.count() == len(caracteres(T().police, T().gras, T().italique)), "fenêtre Glyphes : tous les caractères")
g.cherche.setText("euro")
verifier(any(g.liste.item(i).data(Qt.UserRole) == "€" for i in range(g.liste.count())), "recherche « euro »")
curseur(len(T().texte))
g._choisir("€")
verifier(T().texte.endswith("€") and g.recents[0] == "€", "clic : € inséré, gardé dans les derniers")
g.close()

# 11. styles de texte
reglages().remove("styles_texte")
pt_._remplir_styles()
pt_.saisie.selectAll()
pt_.saisie.insertPlainText("Modèle")
pt_.couleur.definir("#ff00aaff"); pt_.couleur.change.emit("#ff00aaff")
pt_.effets["contour"][0].setChecked(True)
modele = T()
pt_._copier_style()
f._nouveau_texte(QPointF(500, 500))
pt_.saisie.selectAll()
pt_.saisie.insertPlainText("Autre")
pt_.couleur.definir("#ff112233"); pt_.couleur.change.emit("#ff112233")
pt_.effets["contour"][0].setChecked(False)
pt_.coller_style.click()
t = T()
verifier(t.texte == "Autre" and t.couleur == "#ff00aaff" and t.contour and abs(t.x - 500) < 1, "coller le style : couleur et contour, texte et place gardés")
QInputDialog_ = __import__("PySide6.QtWidgets", fromlist=["QInputDialog"]).QInputDialog
QInputDialog_.getText = staticmethod(lambda *a, **k: ("Titre bleu", True))
pt_._enregistrer_style()
verifier(pt_.styles_enr.findData("Titre bleu") > 0, "style enregistré dans la liste")
pt_.couleur.definir("#ff112233"); pt_.couleur.change.emit("#ff112233")
pt_._style_choisi(pt_.styles_enr.findData("Titre bleu"))
verifier(T().couleur == "#ff00aaff", "style enregistré appliqué")
pt_.styles_enr.setCurrentIndex(pt_.styles_enr.findData("Titre bleu"))
QInputDialog_.getItem = staticmethod(lambda *a, **k: ("Titre bleu", True))
pt_._supprimer_style()
verifier(pt_.styles_enr.findData("Titre bleu") < 0, "style supprimé")

Image.fromarray(tableau(doc.image)).save(sortie / "resultat.png")
print("ERREURS :", erreurs if erreurs else "aucune")
doc.modifie = False
QTimer.singleShot(200, f.close)
app.exec()
os._exit(1 if erreurs else 0)
