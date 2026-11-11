"""Pinceaux à forme dans les outils : pinceau de couleur, masque, gomme de calque, pinceau de sélection ; réglages
(espacement, angle, dispersion, texture, double pinceau, couleur, pression de la tablette) ; choix gardés ; le rond
simple d'avant est inchangé. Gestes à la souris (événements Qt). Usage : essai_pinceaux.py"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PySide6.QtCore import QEvent, QPointF, QSettings, Qt
from PySide6.QtGui import QColor, QImage, QMouseEvent
from PySide6.QtWidgets import QApplication

for _k in QSettings("Pixane", "Pixane-essais").allKeys():           # réglages de pinceau d'essai : propres
    if _k.startswith("pinceau_"):
        QSettings("Pixane", "Pixane-essais").remove(_k)
from pixane.bibliotheque import MOTIFS, PINCEAUX, bibliotheque
from pixane.canevas import GOMME, GOMME_CALQUE, PEINTURE, PINCEAU
from pixane.composition import argb_vers_masque
from pixane.document import FORMAT_IMAGE, Calque, Document, masque, qimage_rgba, tableau
from pixane.fenetre import Fenetre
from pixane.moteur import Moteur
from pixane.pointe import Placement, Pointe, Reglages
from pixane.reglages_pinceau import ReglagesPinceau, apercu_trait
from pixane.retouche import GOMME as EFFACER
from pixane.retouche import Trait

Moteur.demarrer = lambda self, signaler=None: None
Fenetre._moteur_en_echec = lambda self, *a: None
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


app = QApplication(sys.argv)
b = bibliotheque()
P = {p.cle.split("/", 1)[1]: p for p in b.elements(PINCEAUX)}
M = {m.cle.split("/", 1)[1]: m for m in b.elements(MOTIFS)}
herbe = P["grass.gih#0"]
feuille = P["A_leaves.gih#0"]

# ---- moteur seul
base = QImage(300, 120, QImage.Format_ARGB32_Premultiplied)
base.fill(Qt.transparent)


def trait(**kw):
    t = Trait(kw.pop("mode", "peinture"), kw.pop("base", base), kw.pop("taille", 30), 0.8, 1.0,
              couleur=QColor(200, 0, 0), graine=1, **kw)
    for i in range(41):
        t.ajouter(QPointF(20 + i * 6.5, 60), kw.get("pression", 1.0) if False else 1.0)
    return tableau(t.image.convertToFormat(FORMAT_IMAGE))


rond = trait()
rond_formes = trait(reglages=Reglages())
verifier(np.abs(rond[..., 3].astype(int) - rond_formes[..., 3].astype(int)).mean() < 3,
         "rond : moteur à formes ≈ rond d'avant")
h = trait(pointe=Pointe(herbe.formes, herbe.espacement), reglages=Reglages())
verifier(0.02 < (h[..., 3] > 30).mean() < (rond[..., 3] > 30).mean(), "forme « herbe » : trait différent du rond")
pl = Placement(Pointe(herbe.formes), Reglages(espacement=0.5), 40, QColor(0, 0, 0), graine=1)
touches = pl.ajouter(QPointF(0, 0)) + pl.ajouter(QPointF(200, 0))
verifier(len(touches) == 11 and abs(touches[1].x - 20) < 0.01, f"espacement 50 % de 40 px : une touche tous les 20 px "
                                                               f"({len(touches)})")
verifier(len({t.forme for t in touches}) == len(herbe.formes), "pinceau animé : ses formes alternent")
pl = Placement(Pointe(herbe.formes), Reglages(suivre=True), 40, QColor(0, 0, 0), graine=1)
pl.ajouter(QPointF(0, 0))
t2 = pl.ajouter(QPointF(0, 100))
verifier(all(abs(t.angle - 90) < 0.01 for t in t2), "l'angle suit le trait (vers le bas : 90°)")
pl = Placement(Pointe(herbe.formes), Reglages(dispersion=1.0, nombre=3, var_taille=0.5, var_teinte=0.3), 40,
               QColor(200, 0, 0), graine=1)
pl.ajouter(QPointF(0, 0))
t3 = pl.ajouter(QPointF(300, 0))
verifier(len(t3) > 30 and np.std([t.y for t in t3]) > 5 and np.std([t.taille for t in t3]) > 2
         and len({t.couleur.rgb() for t in t3}) > 10, "dispersion, nombre, taille et teinte variables")
pl = Placement(Pointe(herbe.formes), Reglages(pression_taille=True, taille_min=0.0), 40, QColor(0, 0, 0), graine=1)
pl.ajouter(QPointF(0, 0), 0.2)
t4 = pl.ajouter(QPointF(300, 0), 1.0)
verifier(t4[0].taille < 20 and t4[-1].taille > 35, "pression : faible = fin, forte = large")
tex = trait(reglages=Reglages(texture="x", texture_force=1.0), texture=M["01_canvas.png#0"].image)
verifier((tex[..., 3] > 0).sum() > 0 and tex[..., 3][rond[..., 3] > 250].std() > 10,
         "texture : le motif creuse le trait")
dbl = trait(reglages=Reglages(double="x", double_taille=0.5), double=Pointe(feuille.formes, feuille.espacement))
verifier((dbl[..., 3] > 30).sum() < (rond[..., 3] > 30).sum() * 0.8, "double pinceau : la deuxième forme découpe")
plein = QImage(300, 120, QImage.Format_ARGB32_Premultiplied)
plein.fill(QColor(0, 0, 255))
g = trait(mode=EFFACER, base=plein, pointe=Pointe(herbe.formes, herbe.espacement), reglages=Reglages())
verifier((g[..., 3] < 128).mean() > 0.02 and (g[..., 3] == 255).mean() > 0.5, "gomme à forme : efface la forme")
img = apercu_trait(Pointe(feuille.formes), Reglages(dispersion=1.0), 40, 1.0, QColor(0, 120, 0))
verifier(not img.isNull() and img.width() == 420, "aperçu du trait")

# ---- dans Pixane : vrais gestes
f = Fenetre()
f.resize(1300, 900)
f.show()
c = f.canevas
H, W = 300, 400


def scene(contenu=0, avec_masque=False):
    fond = np.zeros((H, W, 4), np.uint8)
    fond[:] = [240, 240, 240, 255]
    mq = None
    if avec_masque:
        mq = QImage(W, H, QImage.Format_Grayscale8)
        mq.fill(255)
    doc = Document(calques=[Calque("Fond", qimage_rgba(fond)),
                            Calque("Peinture", qimage_rgba(np.full((H, W, 4), contenu, np.uint8)), masque=mq)])
    doc.actif = 1
    f._installer_document(doc)
    app.processEvents()
    return doc


def geste(x0, x1, y=150):
    pts = [QPointF(x0 + (x1 - x0) * i / 30, y) for i in range(31)]
    e = c.vers_ecran(pts[0])
    c.event(QMouseEvent(QEvent.MouseButtonPress, e, e, Qt.LeftButton, Qt.LeftButton, Qt.NoModifier))
    for p in pts[1:]:
        e = c.vers_ecran(p)
        c.event(QMouseEvent(QEvent.MouseMove, e, e, Qt.NoButton, Qt.LeftButton, Qt.NoModifier))
    c.event(QMouseEvent(QEvent.MouseButtonRelease, e, e, Qt.LeftButton, Qt.NoButton, Qt.NoModifier))
    app.processEvents()


def alpha(doc, i=1):
    return tableau(doc.calques[i].image.convertToFormat(FORMAT_IMAGE))[..., 3]


f._choisir_outil(PEINTURE)
verifier(f.opt_pinceau.isVisible() and f.bouton_pinceau.text() == "Rond", f"pinceau de couleur : bouton « Rond » ({f.opt_pinceau.isVisible()}, {f.bouton_pinceau.text()!r})")
c.definir_taille(40)
doc = scene()
geste(50, 350)
a_rond = alpha(doc)
c.pinceaux["peinture"] = {"cle": herbe.cle, "reglages": Reglages()}
f._enregistrer_pinceau("peinture")
verifier(f.bouton_pinceau.text().lower().startswith("grass"), f"pinceau choisi affiché ({f.bouton_pinceau.text()})")
doc = scene()
geste(50, 350)
a_herbe = alpha(doc)
verifier((a_herbe > 30).sum() > 200 and (a_herbe > 30).sum() < (a_rond > 30).sum() * 0.9,
         f"trait à la souris avec la forme « herbe » ({(a_herbe > 30).sum()} / {(a_rond > 30).sum()})")
# masque
doc = scene(255, avec_masque=True)
doc.cible_masque = True
c.couleur_peinture = QColor(0, 0, 0)
geste(50, 350)
mq = tableau(doc.calques[1].masque.convertToFormat(FORMAT_IMAGE))[..., 0]
verifier(mq is not None and (mq < 128).sum() > 200 and (mq < 128).sum() < (a_rond > 30).sum(),
         "masque : peint avec la forme")
doc.cible_masque = False
# gomme de calque
f._choisir_outil(GOMME_CALQUE)
verifier(f.opt_pinceau.isVisible() and f.bouton_pinceau.text() == "Rond", "gomme : son propre choix (Rond)")
doc = scene(200)
geste(50, 350)
g_rond = (alpha(doc) == 0).sum()
c.pinceaux["gomme"] = {"cle": feuille.cle, "reglages": Reglages(dispersion=0.5)}
doc = scene(200)
geste(50, 350)
g_f = alpha(doc)
verifier(g_rond > 1000 and 50 < (g_f < 100).sum() < g_rond, "gomme de calque avec une forme")
# pinceau de sélection
f._choisir_outil(PINCEAU)
c.pinceaux["selection"] = {"cle": feuille.cle, "reglages": Reglages()}
doc = scene()
geste(50, 350)
s = masque(doc.selection)
verifier(s is not None and 50 < (s > 128).sum() < (a_rond > 30).sum(), "pinceau de sélection avec une forme")
f._choisir_outil(GOMME)
geste(50, 350)
s2 = masque(doc.selection)
verifier(s2 is None or (s2 > 128).sum() < (s > 128).sum() * 0.5, "gomme de sélection avec une forme")
# tablette
f._choisir_outil(PEINTURE)
c.pinceaux["peinture"] = {"cle": None, "reglages": Reglages()}
c._tablette = True
pressions = iter([0.1] * 10 + [1.0] * 40)
c._pression_de = lambda e: next(pressions, 1.0)
doc = scene()
geste(50, 350)
a = alpha(doc)
largeur = [(a[:, x] > 30).sum() for x in (60, 330)]
verifier(largeur[0] < largeur[1] * 0.5, f"tablette : peu appuyé = fin, appuyé = large {largeur}")
c._tablette = False
del c._pression_de
# réglages : fenêtre et mémoire
d = ReglagesPinceau(Reglages(), Pointe(herbe.formes, herbe.espacement), 40, 0.8, QColor(0, 0, 0), f)
d.cases["dispersion"][0].setValue(150)
d.cases["suivre"][0].setChecked(True)
verifier(d.reglages.dispersion == 1.5 and d.reglages.suivre and d.reglages.espacement is None
         and d.apercu.pixmap() is not None, "fenêtre des réglages : valeurs lues, aperçu")
c.pinceaux["peinture"] = {"cle": herbe.cle, "reglages": d.reglages}
f._enregistrer_pinceau("peinture")
verifier("•" in f.bouton_reglages_pinceau.text(), "bouton Réglages marqué quand un réglage est changé")
for dd in f.documents:
    dd.modifie = False
f.close()
f2 = Fenetre()
verifier(f2.canevas.pinceaux["peinture"]["cle"] == herbe.cle
         and f2.canevas.pinceaux["peinture"]["reglages"].dispersion == 1.5
         and f2.canevas.pinceaux["gomme"]["cle"] is None, "au redémarrage : choix et réglages gardés")
for dd in f2.documents:
    dd.modifie = False
f2.close()
# ---- style prêt : la forme et ses réglages en un clic ; le quitter -> réglages de départ
from pixane.choix_bibliotheque import ChoixBibliotheque  # noqa: E402
f3 = Fenetre()
f3._installer_document(Document(calques=[Calque("Fond", qimage_rgba(np.full((200, 200, 4), 255, np.uint8)))]))
f3._choisir_outil(PEINTURE)
choix_suivant = []


def faux_exec(self):
    g = self.biblio.groupes[PINCEAUX]
    self.choisi = choix_suivant.pop(0)(g)
    return 1


ChoixBibliotheque.exec = faux_exec
choix_suivant.append(lambda g: next(e for e in g[0].elements if e.cle == "Styles prêts/feuillage#0"))
f3.choisir_pinceau()
p = f3.canevas.pinceaux["peinture"]
verifier(p["cle"] == "Styles prêts/feuillage#0" and p["reglages"].dispersion == 1.0 and p["reglages"].var_angle == 1.0
         and "Feuillage" in f3.bouton_pinceau.text(), "style prêt « Feuillage » : forme et réglages appliqués")
choix_suivant.append(lambda g: g[1].elements[0])
f3.choisir_pinceau()
p = f3.canevas.pinceaux["peinture"]
verifier(p["cle"] == "Simples/rond_dur#0" and p["reglages"] == Reglages(), "puis « Rond dur » : réglages de départ")
for dd in f3.documents:
    dd.modifie = False
f3.close()
for _k in QSettings("Pixane", "Pixane-essais").allKeys():
    if _k.startswith("pinceau_"):
        QSettings("Pixane", "Pixane-essais").remove(_k)

print("ERREURS :", erreurs if erreurs else "aucune")
sys.stdout.flush()
sys.exit(1 if erreurs else 0)
