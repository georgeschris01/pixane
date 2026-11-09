"""Menu Image et compagnie : pivoter, retourner, redresser, taille de l'image, transformer un calque (Ctrl+T),
modifier la sélection, fichiers récents, nouvelle image (vide ou depuis le presse-papiers), historique, à propos,
mises à jour (comparaison de versions), bouton Auto des réglages, détourage (modèle absent -> message),
catalogue de l'installateur (BiRefNet).
Usage : essai_image.py dossier_sortie   (images d'essai fabriquées ; le moteur n'est pas démarré)"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["CHRYPIX_REGLAGES"] = "Chrypix-essais"   # ne touche pas aux réglages de l'utilisateur
import numpy as np
from PIL import Image
from PySide6.QtCore import QEvent, QPointF, QTimer, Qt
from PySide6.QtGui import QImage, QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QApplication, QDialog, QInputDialog, QMessageBox
from chrypix import installation_moteur, mises_a_jour, recettes
from chrypix.canevas import RECTANGLE
from chrypix.dialogues_image import APropos, NouvelleImage, Redresser, TailleImage
from chrypix.document import FORMAT_IMAGE, masque, tableau
from chrypix.fenetre import Fenetre, reglages
from chrypix.moteur import Moteur
from chrypix.reglages_image import auto

Moteur.demarrer = lambda self, signaler=None: (_ for _ in ()).throw(Exception("moteur désactivé pour l'essai"))
Fenetre._moteur_en_echec = lambda self, *a: None
messages = []
QMessageBox.information = lambda *a, **k: messages.append(a[2] if len(a) > 2 else "") or QMessageBox.Ok
sortie = Path(sys.argv[1])
sortie.mkdir(parents=True, exist_ok=True)
yy, xx = np.mgrid[0:300, 0:400]
fond = np.dstack([xx * 255 // 400, yy * 255 // 300, np.full_like(xx, 120)]).astype(np.uint8)
Image.fromarray(fond).save(sortie / "fond.png")
Image.fromarray(fond[::-1]).save(sortie / "autre.png")

app = QApplication(sys.argv)
reglages().remove("recents")
f = Fenetre()
f.resize(1440, 920)
f.show()
f.charger(str(sortie / "fond.png"))
app.processEvents()
c = f.canevas
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


def rgb():
    return tableau(f.doc.image.convertToFormat(FORMAT_IMAGE))[:, :, :3].astype(int)


def souris(points, modif=Qt.NoModifier):
    ecran = [c.vers_ecran(QPointF(*p)) for p in points]
    c.event(QMouseEvent(QEvent.MouseButtonPress, ecran[0], ecran[0], Qt.LeftButton, Qt.LeftButton, modif))
    for e in ecran[1:]:
        c.event(QMouseEvent(QEvent.MouseMove, e, e, Qt.NoButton, Qt.LeftButton, modif))
    c.event(QMouseEvent(QEvent.MouseButtonRelease, ecran[-1], ecran[-1], Qt.LeftButton, Qt.NoButton, modif))


base = rgb()
# ------------------------------------------------------------------ pivoter, retourner
f.a_pivoter_d.trigger()
verifier(f.doc.taille() == (300, 400) and np.array_equal(rgb(), np.rot90(base, -1)), "pivoter à droite : exact")
f.a_pivoter_g.trigger()
verifier(np.array_equal(rgb(), base), "pivoter à gauche : retour à l'original")
f.a_miroir_h.trigger()
verifier(np.array_equal(rgb(), base[:, ::-1]), "retourner horizontalement")
f.a_miroir_v.trigger()
verifier(np.array_equal(rgb(), base[::-1, ::-1]), "retourner verticalement")
f.a_pivoter_180.trigger()
verifier(np.array_equal(rgb(), base), "pivoter de 180° : retour à l'original")
n = f.historique.index()
f.historique.undo()
verifier(np.array_equal(rgb(), base[::-1, ::-1]) and f.historique.index() == n - 1, "Ctrl+Z annule une rotation")
f.historique.redo()

# ------------------------------------------------------------------ taille, redresser (fenêtres simulées)
def accepter(classe, reglage):
    def agir():
        d = next(w for w in app.topLevelWidgets() if isinstance(w, classe) and w.isVisible())
        reglage(d)
        d.accept()
    QTimer.singleShot(150, agir)


accepter(TailleImage, lambda d: d.pct.setValue(50))
f.a_taille.trigger()
verifier(f.doc.taille() == (200, 150), f"taille 50 % : {f.doc.taille()}")
f.historique.undo()
accepter(TailleImage, lambda d: d._cote_long(1920))
f.a_taille.trigger()
verifier(f.doc.taille() == (1920, 1440), f"bouton 1920 px (proportions gardées) : {f.doc.taille()}")
f.historique.undo()
accepter(Redresser, lambda d: d.angle.setValue(8))
f.a_redresser.trigger()
w, h = f.doc.taille()
verifier(w < 400 and h < 300 and abs(w / h - 4 / 3) < 0.02 and tableau(f.doc.image)[:, :, 3].min() == 255,
         f"redresser 8° recadré : {w} × {h}, sans coin vide")
f.historique.undo()
accepter(Redresser, lambda d: (d.angle.setValue(-8), d.c_recadrer.setChecked(False)))
f.a_redresser.trigger()
w, h = f.doc.taille()
verifier(w > 400 and h > 300 and tableau(f.doc.image)[0, 0, 3] == 0, f"redresser sans recadrer : {w} × {h}, coins vides")
f.historique.undo()

# ------------------------------------------------------------------ transformer un calque
f.a_transformer.trigger()
verifier(c.transfo is not None and not f.opt_transfo.isHidden(), "Ctrl+T : cadre de transformation affiché")
souris([(200, 150), (250, 170)])                                   # déplacer
verifier(abs(c.transfo.centre.x() - 250) < 1 and abs(c.transfo.centre.y() - 170) < 1, "transformer : déplacer")
souris([(250 + 200, 170 + 150), (250, 170)])                      # coin bas droit jusqu'au centre : moitié
l, h_, a = c.transfo.resume()
verifier(abs(l - 50) < 2 and abs(h_ - 50) < 2, f"transformer : coin = taille proportionnelle ({l:.0f} %, {h_:.0f} %)")
c.event(QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier))
verifier(c.transfo is None and np.array_equal(rgb(), base), "Échap : transformation annulée, calque intact")
f.a_transformer.trigger()
p0 = c.transfo.point(1, 0)
souris([(p0.x() + 60, p0.y()), (p0.x() + 60, p0.y() + 200)])      # dehors : tourner
verifier(abs(c.transfo.resume()[2]) > 30, f"transformer : tourner ({c.transfo.resume()[2]:.0f}°)")
n = f.historique.index()
c.event(QKeyEvent(QEvent.KeyPress, Qt.Key_Return, Qt.NoModifier))
verifier(c.transfo is None and f.historique.index() == n + 1 and tableau(f.doc.image)[0, 0, 3] == 0,
         "Entrée : transformation gardée (coins devenus transparents), une étape d'historique")
f.historique.undo()
verifier(np.array_equal(rgb(), base), "Ctrl+Z : transformation annulée")

# ------------------------------------------------------------------ modifier la sélection
f._choisir_outil(RECTANGLE)
souris([(100, 100), (200, 200)])
QInputDialog.getInt = lambda *a, **k: (10, True)
f.a_sel_agrandir.trigger()
m = masque(f.doc.selection) > 127
ys, xs = np.nonzero(m)
verifier(abs(xs.min() - 90) <= 1 and abs(xs.max() - 209) <= 1, f"agrandir la sélection de 10 px ({xs.min()}..{xs.max()})")
f.a_sel_reduire.trigger()
f.a_sel_reduire.trigger()
ys, xs = np.nonzero(masque(f.doc.selection) > 127)
verifier(abs(xs.min() - 110) <= 2, f"réduire la sélection ({xs.min()})")
f.a_sel_adoucir.trigger()
a_ = masque(f.doc.selection)
verifier(((a_ > 10) & (a_ < 245)).sum() > 200, "adoucir les bords : bord progressif")
f._modifier_selection("rien")

# ------------------------------------------------------------------ fichiers récents, nouvelle image
f.charger(str(sortie / "autre.png"))
r = f._recents()
verifier(len(r) == 2 and r[0].endswith("autre.png") and r[1].endswith("fond.png"), "fichiers récents : le dernier en haut")
f._remplir_recents()
verifier(len([a for a in f.m_recents.actions() if a.text() and not a.isSeparator()]) == 3, "menu Fichiers récents rempli")
QApplication.clipboard().setImage(QImage(str(sortie / "fond.png")))
f.doc.modifie = False
f.nouvelle_depuis_presse_papiers()
verifier(f.doc.taille() == (400, 300) and f.doc.chemin is None, "nouvelle image depuis le presse-papiers")
f.doc.modifie = False
accepter(NouvelleImage, lambda d: (d.largeur.setValue(640), d.hauteur.setValue(480), d.fond.setCurrentIndex(1)))
f.a_nouvelle.trigger()
verifier(f.doc.taille() == (640, 480) and tableau(f.doc.image)[:, :, 3].max() == 0, "nouvelle image vide transparente")
f.doc.modifie = False
f.doc = None
f.coller()
verifier(f.doc is not None and f.doc.taille() == (400, 300), "Ctrl+V sans photo : nouvelle image")

# ------------------------------------------------------------------ historique, à propos, mises à jour, Auto
verifier(f.vue_historique.stack() is f.historique, "panneau Historique relié à Annuler / Rétablir")
d = APropos(None, f)
verifier("Chrypix" in d.findChildren(type(f.info_transfo))[0].text(), "fenêtre À propos")
d.deleteLater()
verifier(mises_a_jour.plus_recente("0.2.0", "0.1.0") and not mises_a_jour.plus_recente("0.1.0", "0.1.0")
         and mises_a_jour.plus_recente("v1.0", "0.9.9"), "comparaison des versions")
sombre = QImage(str(sortie / "fond.png")).convertToFormat(QImage.Format_ARGB32_Premultiplied)
t = tableau(sombre.convertToFormat(FORMAT_IMAGE))
t[..., :3] = t[..., :3] // 3 + 20
from chrypix.document import qimage_rgba
r_auto = auto(qimage_rgba(t))
verifier(r_auto["luminosite"] > 10 and r_auto["contraste"] > 10, f"Auto sur une photo sombre et terne : {r_auto}")

# ------------------------------------------------------------------ détourage, catalogue
messages.clear()
recettes._detourage["ok"] = False
f.supprimer_arriere_plan()
verifier(messages and "BiRefNet" in messages[-1], "modèle BiRefNet absent : message clair")
p, s = recettes.detourer("x.png")
verifier(p["12"]["class_type"] == "RemoveBackground" and "14" in s, "recette de détourage")
cles = [e.cle for e in installation_moteur.catalogue(True, False)]
verifier("birefnet" in cles, "BiRefNet dans le téléchargement du moteur")
f.grab().save(str(sortie / "fenetre.png"))

print("ERREURS :", erreurs if erreurs else "aucune")
sys.stdout.flush()
for d in f.documents:          # plusieurs onglets : aucune question à la fermeture
    d.modifie = False
f.close()
sys.exit(1 if erreurs else 0)
