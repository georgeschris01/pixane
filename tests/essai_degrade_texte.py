"""Outil Dégradé sur un texte (posé sur les lettres comme style Incrustation dégradé, aperçu en direct pendant le
glissé, texte toujours modifiable, Ctrl+Z), sur un masque (étiquette et message), « Garder la transparence », et
aperçu en direct depuis l'éditeur dans la fenêtre Style du calque. Moteur non démarré.
Usage : essai_degrade_texte.py dossier_sortie"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PIL import Image
from PySide6.QtCore import QEvent, QPointF, Qt, QTimer
from PySide6.QtGui import QColor, QImage, QMouseEvent
from PySide6.QtWidgets import QApplication

from pixane import degrades as dg
from pixane.canevas import DEGRADE
from pixane.document import FORMAT_IMAGE, tableau
from pixane.fenetre import Fenetre
from pixane.moteur import Moteur
from pixane.texte import Texte

Moteur.demarrer = lambda self, signaler=None: None
Fenetre._moteur_en_echec = lambda self, *a: None
sortie = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("sortie_degrade_texte")
sortie.mkdir(parents=True, exist_ok=True)
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


Image.fromarray(np.full((400, 600, 3), 30, np.uint8)).save(sortie / "fond.png")
app = QApplication(sys.argv)
f = Fenetre()
f.resize(1280, 860)
f.show()
f.charger(str(sortie / "fond.png"))
app.processEvents()
c = f.canevas
doc = f.doc
f.historique.push(__import__("pixane.fenetre", fromlist=["CommandeEtat"]).CommandeEtat(
    doc, doc.etat(), doc.etat_nouveau_texte(Texte(texte="DEGRADE", taille=120, gras=True, couleur="#ffffffff",
                                                  x=300, y=200)), "Nouveau texte"))
app.processEvents()
i_texte = doc.actif
verifier(doc.calque_actif.texte is not None, "calque de texte créé")


def souris(genre, x, y):
    e = c.vers_ecran(QPointF(x, y))
    bouton = Qt.NoButton if genre == QEvent.MouseButtonRelease else Qt.LeftButton
    c.event(QMouseEvent(genre, e, e, Qt.LeftButton if genre != QEvent.MouseMove else Qt.NoButton, bouton,
                        Qt.NoModifier))


def attendre(ms=120):
    fin = []
    QTimer.singleShot(ms, lambda: fin.append(1))
    while not fin:
        app.processEvents()


def couleur_vue(x, y):
    return tableau(doc.image.convertToFormat(FORMAT_IMAGE))[y, x, :3].astype(int)


f._choisir_outil(DEGRADE)
c.degrade = dg.deux_couleurs("#ff0000", "#0000ff")
c.forme_degrade = "lineaire"
c.opacite = 1.0
# lettres : chercher deux points blancs à gauche et à droite du texte
a = tableau(doc.calque_actif.image.convertToFormat(FORMAT_IMAGE))[:, :, 3]
ys, xs = np.nonzero(a > 250)
gauche = (int(xs[np.argmin(xs)]), int(ys[np.argmin(xs)]))
droite = (int(xs[np.argmax(xs)]), int(ys[np.argmax(xs)]))
x0, x1 = int(xs.min()), int(xs.max())

souris(QEvent.MouseButtonPress, x0, 200)
souris(QEvent.MouseMove, (x0 + x1) // 2, 200)
attendre()
souris(QEvent.MouseMove, x1, 200)
attendre()
st = doc.calques[i_texte].style
verifier(st is not None and any(e.type == "degrade" for e in st.effets), "aperçu en direct pendant le glissé")
n_avant = f.historique.count()
souris(QEvent.MouseButtonRelease, x1, 200)
app.processEvents()
calque = doc.calques[i_texte]
eff = [e for e in calque.style.effets if e.type == "degrade"]
verifier(calque.texte is not None, "le texte reste un texte (modifiable)")
verifier(len(eff) == 1 and eff[0].r("angle") == 0, f"effet Incrustation dégradé, de gauche à droite "
                                                   f"(angle {eff[0].r('angle') if eff else None})")
verifier(eff and 80 <= eff[0].r("echelle") <= 120, f"échelle d'après le glissé ({eff[0].r('echelle') if eff else None})")
cg, cd = couleur_vue(*gauche), couleur_vue(*droite)
verifier(cg[0] > 180 and cg[2] < 80 and cd[2] > 180 and cd[0] < 80, f"lettres : rouge à gauche {cg}, bleu à droite {cd}")
verifier(tuple(couleur_vue(5, 5)) == (30, 30, 30), "le fond autour des lettres n'a rien reçu")
verifier(f.historique.count() == n_avant + 1, "une seule entrée dans Annuler")
f.grab().save(str(sortie / "degrade_texte.png"))
# deuxième dégradé : remplace l'effet (pas un deuxième)
c.degrade = dg.deux_couleurs("#00ff00", "#ffff00")
souris(QEvent.MouseButtonPress, 300, 100)
souris(QEvent.MouseMove, 300, 300)
souris(QEvent.MouseButtonRelease, 300, 300)
app.processEvents()
eff = [e for e in doc.calques[i_texte].style.effets if e.type == "degrade"]
verifier(len(eff) == 1 and eff[0].r("angle") == -90, f"nouveau dégradé : remplace l'effet (angle {eff[0].r('angle')})")
f.historique.undo()
f.historique.undo()
app.processEvents()
st = doc.calques[i_texte].style
verifier(st is None or not any(e.type == "degrade" for e in st.effets), "Ctrl+Z deux fois : plus de dégradé")
# simple clic : rien
n = f.historique.count()
souris(QEvent.MouseButtonPress, 300, 200)
souris(QEvent.MouseButtonRelease, 300, 200)
verifier(f.historique.count() == n, "simple clic : rien")
# couleur de peinture : prise au moment du dégradé
c.couleur_peinture = QColor(0, 200, 0)
c.degrade = dg.defaut()
souris(QEvent.MouseButtonPress, x0, 200)
souris(QEvent.MouseMove, x1, 200)
souris(QEvent.MouseButtonRelease, x1, 200)
eff = [e for e in doc.calques[i_texte].style.effets if e.type == "degrade"][0]
verifier(eff.r("degrade")["couleurs"][0]["couleur"] == "#00c800", "point « couleur de peinture » : la couleur du moment")
f.historique.undo()

# ------------------------------------------------------------ masque
f.ajouter_masque() if hasattr(f, "ajouter_masque") else None
if doc.calques[i_texte].masque is None:
    from pixane.composition import masque_plein
    doc.calques = tuple(c_ if k != i_texte else __import__("dataclasses").replace(c_, masque=masque_plein(*doc.taille()))
                        for k, c_ in enumerate(doc.calques))
doc.cible_masque = True
doc.calques_changes.emit()
app.processEvents()
verifier(f.opt_degrade_masque.isVisibleTo(f), "masque choisi : étiquette « → dans le masque »")
souris(QEvent.MouseButtonPress, x0, 200)
verifier("masque" in f.statusBar().currentMessage(), "message : le dégradé va dans le masque")
souris(QEvent.MouseMove, x1, 200)
souris(QEvent.MouseButtonRelease, x1, 200)
verifier(doc.calques[i_texte].texte is not None, "dégradé dans le masque : le texte reste un texte")
f.historique.undo()
doc.cible_masque = False
doc.calques_changes.emit()
app.processEvents()
verifier(not f.opt_degrade_masque.isVisibleTo(f), "calque choisi : plus d'étiquette")

# ------------------------------------------------------------ garder la transparence (calque image)
img = QImage(600, 400, QImage.Format_ARGB32_Premultiplied)
img.fill(Qt.transparent)
from PySide6.QtGui import QPainter
p = QPainter(img)
p.fillRect(200, 150, 200, 100, QColor(255, 255, 255))
p.end()
etat = doc.etat_nouveau_calque(img, "Objet")
doc.appliquer_etat(etat)
c.degrade = dg.deux_couleurs("#ff0000", "#0000ff")
c.garder_transparence = True
souris(QEvent.MouseButtonPress, 0, 200)
souris(QEvent.MouseMove, 600, 200)
souris(QEvent.MouseButtonRelease, 600, 200)
t = tableau(doc.calque_actif.image.convertToFormat(FORMAT_IMAGE))
verifier(t[50, 50, 3] == 0 and t[200, 210, 3] == 255 and t[200, 210, 0] > 150,
         "Garder la transparence : seulement sur ce qui est peint")
f.historique.undo()
c.garder_transparence = False
souris(QEvent.MouseButtonPress, 0, 200)
souris(QEvent.MouseMove, 600, 200)
souris(QEvent.MouseButtonRelease, 600, 200)
t = tableau(doc.calque_actif.image.convertToFormat(FORMAT_IMAGE))
verifier(t[50, 50, 3] == 255, "sans la case : tout le calque")
f.historique.undo()

# ------------------------------------------------------------ fenêtre Style : aperçu en direct
from pixane.dialogue_style import DialogueStyle
from pixane.styles import Effet, Style
doc.actif = i_texte
d = DialogueStyle(f, i_texte)
d.show()
d._mettre_style(Style((Effet.nouveau("degrade"),)))
d.liste.setCurrentRow(0)
app.processEvents()
bouton = d.zone.widget().findChild(dg.BoutonDegrade)
verifier(bouton is not None and bouton.en_direct, "fenêtre Style : bouton du dégradé en direct")
vus = []


def regler_editeur():
    ed = QApplication.activeModalWidget()
    if not isinstance(ed, dg.EditeurDegrade):
        QTimer.singleShot(50, regler_editeur)
        return
    ed.barre.definir(dg.deux_couleurs("#ff00ff", "#00ffff"))
    attendre(150)
    st = doc.calques[i_texte].style
    vus.append(st.effets[0].reglages.get("degrade", {}).get("couleurs", [{}])[0].get("couleur"))
    ed.reject()


QTimer.singleShot(50, regler_editeur)
bouton.choisir()
app.processEvents()
attendre(150)
verifier(vus and vus[0] == "#ff00ff", f"réglé dans l'éditeur : visible tout de suite sur le texte ({vus})")
st = doc.calques[i_texte].style
verifier(st.effets[0].reglages.get("degrade", {}).get("couleurs", [{}])[0].get("couleur") != "#ff00ff",
         "Annuler dans l'éditeur : le dégradé d'avant revient")
d.reject()

print()
print("ÉCHECS :" if erreurs else "Tout est bon.", *erreurs, sep="\n  ")
for dd in f.documents:
    dd.modifie = False
sys.stdout.flush()
sys.exit(1 if erreurs else 0)        # sortie normale : os._exit plante après la fenêtre Style (Qt, essai seulement)
