"""Motifs (étape 3) : pavage, pot de peinture avec un motif, Édition > Remplir avec un motif (calque entier et
sélection, une entrée d'historique, calque verrouillé refusé), style « Incrustation de motif » (enregistré et relu),
tampon de motif. Usage : essai_motifs.py"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QComboBox, QMessageBox

from pixane import motifs
from pixane.canevas import SEAU, TAMPON_MOTIF
from pixane.document import FORMAT_IMAGE, Calque, Document, qimage_rgba, tableau
from pixane.fenetre import Fenetre
from pixane.moteur import Moteur
from pixane.styles import Effet, Style, rendre_style

Moteur.demarrer = lambda self, signaler=None: None
Fenetre._moteur_en_echec = lambda self, *a: None
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.Ok)
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


app = QApplication(sys.argv)
# ---- pavage
t = motifs.tuile(motifs.DEFAUT)
verifier(t is not None and t.ndim == 3 and t.shape[2] == 4, f"motif par défaut trouvé ({motifs.DEFAUT})")
th, tw = t.shape[:2]
p = motifs.pavage(t, tw * 2 + 5, th + 3)
verifier(np.array_equal(p[:th, :tw], t) and np.array_equal(p[:th, tw:2 * tw], t) and np.array_equal(p[th:, :tw], t[:3]),
         "pavage : le motif se répète à l'identique")
p2 = motifs.pavage(t, 10, 10, 7, 4)
verifier(np.array_equal(p2, p[4:14, 7:17]), "pavage décalé : raccord avec la position dans l'image")
t2 = motifs.tuile(motifs.DEFAUT, 0.5)
verifier(abs(t2.shape[0] - th / 2) <= 1 and abs(t2.shape[1] - tw / 2) <= 1, "échelle 50 % : motif deux fois plus petit")
verifier(motifs.tuile("inexistant/x.png#0") is None, "motif inconnu : None (pas d'erreur)")

from PySide6.QtCore import QSettings
QSettings("Pixane", "Pixane-essais").setValue("seau_remplir", "couleur")
f = Fenetre()
f.resize(1280, 900)
f.show()
c = f.canevas
H, W = 200, 260


def scene():
    fond = np.zeros((H, W, 4), np.uint8)
    fond[:] = [225, 60, 50, 255]
    doc = Document(calques=[Calque("Fond", qimage_rgba(fond)), Calque("Vide", qimage_rgba(np.zeros((H, W, 4), np.uint8)))])
    doc.actif = 1
    f._installer_document(doc)
    app.processEvents()
    return doc


def clic(x, y):
    e = c.vers_ecran(QPointF(x, y))
    c.event(QMouseEvent(QEvent.MouseButtonPress, e, e, Qt.LeftButton, Qt.LeftButton, Qt.NoModifier))
    c.event(QMouseEvent(QEvent.MouseButtonRelease, e, e, Qt.LeftButton, Qt.NoButton, Qt.NoModifier))
    app.processEvents()


def pixels(doc, i):
    return tableau(doc.calques[i].image.convertToFormat(FORMAT_IMAGE))


attendu = motifs.pavage(t, W, H)
opaque = attendu[..., 3] == 255

# ---- pot de peinture en mode motif
doc = scene()
f._choisir_outil(SEAU)
app.processEvents()
avec = next(b for b in f.opt_seau.findChildren(QComboBox) if b.findData("motif") >= 0)
verifier(not f.opt_motif.isVisibleTo(f), "pot en mode Couleur : pas de choix de motif")
avec.setCurrentIndex(avec.findData("motif"))
app.processEvents()
verifier(c.seau_motif and f.opt_motif.isVisibleTo(f), "Remplir avec : Motif → le choix du motif apparaît")
c.motif_cle, c.motif_echelle, c.opacite = motifs.DEFAUT, 1.0, 1.0
clic(30, 30)
a = pixels(doc, 1)
ecart = np.abs(a[..., :3].astype(int) - attendu[..., :3].astype(int))[opaque].max() if opaque.any() else 0
verifier(a[..., 3].min() > 0 and ecart <= 2, f"pot de peinture : le calque vide est couvert du motif (écart {ecart})")
verifier(f.historique.undoText() == "Pot de peinture", "une entrée d'historique « Pot de peinture »")
avec.setCurrentIndex(avec.findData("couleur"))
app.processEvents()
verifier(not c.seau_motif and not f.opt_motif.isVisibleTo(f), "retour en mode Couleur")

# ---- Édition > Remplir avec un motif
doc = scene()
f.remplir_motif((motifs.DEFAUT, 1.0, 1.0))
a = pixels(doc, 1)
verifier(a[..., 3].min() > 0, "Remplir avec un motif sans sélection : tout le calque")
verifier(f.historique.undoText() == "Remplir avec un motif", "une entrée d'historique")
f.historique.undo()
verifier(pixels(doc, 1)[..., 3].max() == 0, "Ctrl+Z : le calque redevient vide")
# par le menu (Qt envoie un booléen à remplir_motif : il ne doit pas être pris pour un choix)
motifs.DialogueRemplirMotif.exec = lambda self: True
f.a_remplir_motif.trigger()
app.processEvents()
verifier(pixels(doc, 1)[..., 3].min() > 0 and f.historique.undoText() == "Remplir avec un motif",
         "Édition > Remplir avec un motif… par le menu")
f.historique.undo()
sel = np.zeros((H, W), np.uint8)
sel[50:100, 60:160] = 255
from pixane.document import nouvelle_selection
s = nouvelle_selection(W, H)
s.fill(Qt.transparent)
from PySide6.QtGui import QPainter
pp = QPainter(s)
pp.fillRect(60, 50, 100, 50, Qt.white)
pp.end()
doc.selection = s
f.remplir_motif((motifs.DEFAUT, 1.0, 1.0))
a = pixels(doc, 1)
verifier(a[50:100, 60:160, 3].min() > 0 and a[:40, :, 3].max() == 0 and a[:, 170:, 3].max() == 0,
         "avec une sélection : seulement dans la sélection")
doc.selection.fill(Qt.transparent)
from dataclasses import replace
doc.appliquer_etat(doc.etat_calque_modifie(1, verrou=True, image=qimage_rgba(np.zeros((H, W, 4), np.uint8))))
f.remplir_motif((motifs.DEFAUT, 1.0, 1.0))
verifier(pixels(doc, 1)[..., 3].max() == 0, "calque verrouillé : rien n'est rempli")

# ---- style « Incrustation de motif »
forme = np.zeros((H, W, 4), np.uint8)
forme[40:160, 40:220] = [0, 0, 255, 255]
img = qimage_rgba(forme)
st = Style((Effet.nouveau("motif", motif=motifs.DEFAUT),))
r = tableau(rendre_style(img, st).convertToFormat(FORMAT_IMAGE))
zone = (forme[..., 3] == 255) & opaque
ecart = np.abs(r[..., :3].astype(int) - attendu[..., :3].astype(int))[zone].max()
verifier(ecart <= 2, f"Incrustation de motif : la forme montre le motif, aligné sur l'image (écart {ecart})")
verifier(r[:30, :, 3].max() == 0, "hors de la forme : rien")
st2 = Style.depuis_json(st.vers_json())
verifier(st2.effets[0].type == "motif" and st2.effets[0].r("motif") == motifs.DEFAUT, "style enregistré puis relu")
st3 = Style((Effet.nouveau("motif", motif=motifs.DEFAUT, opacite=50),))
r3 = tableau(rendre_style(img, st3).convertToFormat(FORMAT_IMAGE))
verifier(np.abs(r3[100, 100, :3].astype(int) - r[100, 100, :3].astype(int)).sum() > 0 or
         np.array_equal(r[100, 100, :3], forme[100, 100, :3]), "opacité 50 % : mélange avec la couleur du calque")
from pixane.dialogue_style import DialogueStyle
doc = scene()
doc.appliquer_etat(doc.etat_calque_modifie(1, image=img, style=st))
d = DialogueStyle(f, 1)
d._effet_choisi(0)
verifier(bool(d.zone.widget().findChildren(motifs.BoutonMotif)), "fenêtre Style : bouton de choix du motif")
d.reject()

# ---- tampon de motif
doc = scene()
f._choisir_outil(TAMPON_MOTIF)
app.processEvents()
verifier(f.opt_motif.isVisibleTo(f) and f.opt_taille.isVisibleTo(f), "tampon de motif : taille et motif dans la barre")
c.definir_taille(40)
c.durete, c.opacite = 1.0, 1.0
clic(130, 100)
a = pixels(doc, 1)
verifier(a[100, 130, 3] > 0 and a[10, 10, 3] == 0, "tampon de motif : peint là où on clique, pas ailleurs")
ok = np.abs(a[100, 130, :3].astype(int) - attendu[100, 130, :3].astype(int)).max() <= 3 if opaque[100, 130] else True
verifier(ok, "la couleur peinte est celle du motif à cet endroit")
verifier(f.historique.undoText() == "Tampon de motif", "une entrée d'historique « Tampon de motif »")

print("ERREURS :", erreurs if erreurs else "aucune")
sys.stdout.flush()
for dd in f.documents:
    dd.modifie = False
f.close()
sys.exit(1 if erreurs else 0)
