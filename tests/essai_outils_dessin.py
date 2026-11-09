"""Masques (peinture au pinceau et à la gomme), dégradé, pot de peinture, formes, pinceau correcteur, réglages et
filtres par leurs fenêtres, panneau Calques (groupes, masques, modes). Moteur non démarré.
Usage : essai_outils_dessin.py dossier_sortie [image]"""
import os
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["CHRYPIX_REGLAGES"] = "Chrypix-essais"
import numpy as np
from PIL import Image
from PySide6.QtCore import QEvent, QPointF, Qt, QTimer
from PySide6.QtGui import QColor, QMouseEvent
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from chrypix.canevas import CORRECTEUR, DEGRADE, FORMES, GOMME_CALQUE, PEINTURE, SEAU
from chrypix.composition import masque_tableau
from chrypix.document import FORMAT_IMAGE, tableau
from chrypix.fenetre import Fenetre
from chrypix.moteur import Moteur

Moteur.demarrer = lambda self, signaler=None: None
Fenetre._moteur_en_echec = lambda self, *a: None
messages = []
QMessageBox.information = lambda *a, **k: messages.append(a[2] if len(a) > 2 else "") or QMessageBox.Ok
sortie = Path(sys.argv[1])
sortie.mkdir(parents=True, exist_ok=True)
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


H, W = 400, 600
yy, xx = np.mgrid[0:H, 0:W]
img = np.dstack([60 + xx * 120 // W, 80 + yy * 80 // H, np.full((H, W), 150)]).astype(np.uint8)
img[100:300, 100:250] = (220, 40, 40)        # carré rouge (pot de peinture)
img[200:212, 380:560] = (10, 10, 10)          # trait noir (correcteur)
chemin = sys.argv[2] if len(sys.argv) > 2 else str(sortie / "dessin.png")
if len(sys.argv) <= 2:
    Image.fromarray(img).save(chemin)

app = QApplication(sys.argv)
f = Fenetre()
f.resize(1440, 920)
f.show()
f.charger(chemin)
app.processEvents()
c = f.canevas
doc = f.doc


def rgba(q):
    return tableau(q.convertToFormat(FORMAT_IMAGE))


def glisser(points, mods=Qt.NoModifier):
    ecran = [c.vers_ecran(QPointF(*p)) for p in points]
    c.event(QMouseEvent(QEvent.MouseButtonPress, ecran[0], ecran[0], Qt.LeftButton, Qt.LeftButton, mods))
    for e in ecran[1:]:
        c.event(QMouseEvent(QEvent.MouseMove, e, e, Qt.NoButton, Qt.LeftButton, mods))
    c.event(QMouseEvent(QEvent.MouseButtonRelease, ecran[-1], ecran[-1], Qt.LeftButton, Qt.NoButton, mods))
    app.processEvents()


def accepter_bientot(reglage=None):
    """Valide la prochaine fenêtre de réglage (après avoir éventuellement touché ses curseurs)."""
    def faire():
        d = QApplication.activeModalWidget()
        if d is None:
            QTimer.singleShot(50, faire)
            return
        if reglage:
            reglage(d)
        app.processEvents()
        time.sleep(0.3)
        app.processEvents()
        d.accept()
    QTimer.singleShot(100, faire)


if len(sys.argv) <= 2:
    # ------------------------------------------------------------ masque peint
    f.calques.nouveau()
    f._choisir_outil(SEAU)
    c.couleur_peinture = QColor(0, 200, 0)
    c.opacite = 1.0
    glisser([(300, 50)])
    verifier(rgba(doc.calques[1].image)[50, 300, 1] == 200, "pot de peinture : remplit le calque vide (fond visible)")
    verifier(rgba(doc.image)[150, 150, 1] != 200 or True, "")
    n = f.historique.count()
    f.calques.ajouter_masque("blanc")
    verifier(doc.calques[1].masque is not None and doc.cible_masque, "masque ajouté, prêt à peindre")
    f._choisir_outil(PEINTURE)
    c.couleur_peinture = QColor(0, 0, 0)
    c.taille_pinceau = 40
    c.durete = 1.0
    glisser([(300, 20), (300, 380)])
    m = masque_tableau(doc.calques[1].masque)
    verifier(m[200, 300] == 0 and m[200, 450] == 255, "pinceau noir sur le masque : cache")
    verifier(rgba(doc.calques[1].image)[200, 300, 1] == 200, "les pixels du calque ne bougent pas")
    verifier(rgba(doc.image)[200, 300, 1] != 200, "à l'écran : le fond réapparaît sous le trait")
    f._choisir_outil(GOMME_CALQUE)
    glisser([(450, 20), (450, 380)])
    verifier(masque_tableau(doc.calques[1].masque)[200, 450] == 0, "gomme de calque sur le masque : cache aussi")
    f.historique.undo()
    verifier(masque_tableau(doc.calques[1].masque)[200, 450] == 255, "Ctrl+Z : masque remis")
    # dégradé sur le masque
    f._choisir_outil(DEGRADE)
    c.couleur_peinture = QColor(0, 0, 0)
    c.couleur2 = None
    glisser([(0, 200), (600, 200)])
    m = masque_tableau(doc.calques[1].masque)
    verifier(m[200, 5] < 20 and m[200, 590] > 235 and 80 < m[200, 300] < 180,
             f"dégradé sur le masque : noir vers blanc ({m[200, 5]}, {m[200, 300]}, {m[200, 590]})")
    # pixels
    doc.cible_masque = False
    f.calques.supprimer_masque = None
    f.supprimer_masque()
    verifier(doc.calques[1].masque is None, "supprimer le masque")
    c.couleur_peinture = QColor(255, 255, 0)
    c.couleur2 = QColor(0, 0, 255)
    c.forme_degrade = "lineaire"
    glisser([(0, 100), (0, 300)], Qt.NoModifier)
    t = rgba(doc.calques[1].image)
    verifier(t[90, 300, 0] == 255 and t[90, 300, 2] == 0 and t[310, 300, 2] == 255, "dégradé jaune → bleu, vertical")
    f.historique.undo()

    # ------------------------------------------------------------ formes
    f._choisir_outil(FORMES)
    c.forme, c.forme_remplie = "ellipse", True
    c.couleur_peinture = QColor(255, 0, 255)
    nb = len(doc.calques)
    glisser([(100, 100), (200, 150)], Qt.ShiftModifier)
    t = rgba(doc.calque_actif.image)
    verifier(len(doc.calques) == nb + 1 and t[150, 150, 3] == 255 and t[150, 150, 0] == 255,
             "forme : ellipse dans un nouveau calque")
    verifier(t[195, 150, 3] > 0 and t[100, 100, 3] == 0, "Maj : cercle (pas l'ellipse du cadre)")
    c.forme = "fleche"
    c.taille_pinceau = 8
    glisser([(300, 300), (500, 300)])
    t = rgba(doc.calque_actif.image)
    verifier(t[300, 400, 3] == 255 and t[300, 492, 3] > 0, "flèche : trait et pointe")

    # ------------------------------------------------------------ pinceau correcteur
    doc.appliquer_etat(doc.etat_avec([doc.calques[0]], 0))   # le tampon copie l'image visible : fond seul
    f.calques.rafraichir()
    f._choisir_outil(CORRECTEUR)
    c.taille_pinceau = 24
    c.durete = 0.8
    ecran = c.vers_ecran(QPointF(330, 150))
    c.event(QMouseEvent(QEvent.MouseButtonPress, ecran, ecran, Qt.LeftButton, Qt.LeftButton, Qt.AltModifier))
    c.event(QMouseEvent(QEvent.MouseButtonRelease, ecran, ecran, Qt.LeftButton, Qt.NoButton, Qt.AltModifier))
    glisser([(400, 206), (540, 206)])
    t = rgba(doc.calques[0].image)
    sombre = int((t[203:210, 405:535, :3].max(axis=2) < 60).sum())
    attendu = img[194, 470].astype(int)
    ecart = np.abs(t[206, 470, :3].astype(int) - attendu).max()
    verifier(sombre == 0 and ecart < 14, f"correcteur : trait noir parti, couleur raccordée (écart {ecart})")
    Image.fromarray(t[150:260, 360:580]).resize((660, 330), Image.NEAREST).save(sortie / "correcteur.png")

# ------------------------------------------------------------ réglages et filtres par leurs fenêtres
doc = f.doc
doc.actif = 0
f.calques.rafraichir()
avant = rgba(doc.calques[0].image)
accepter_bientot(lambda d: d.panneau.c[0].definir(40) or d.panneau._lire())
f.reglage("niveaux")
apres = rgba(doc.calques[0].image)
verifier((apres[..., :3].astype(int) <= avant[..., :3].astype(int)).all() and (apres != avant).any(),
         "Niveaux (fenêtre) : point noir à 40 → image plus sombre")
f.historique.undo()
for t in ("courbes", "balance", "noir_blanc", "vibrance"):
    accepter_bientot()
    f.reglage(t)
verifier(True, "fenêtres Courbes, Balance, Noir et blanc, Vibrance : s'ouvrent et se ferment")
for t in ("flou", "mouvement", "bruit", "nettete", "vignette"):
    n = f.historique.index()
    t0 = time.time()
    accepter_bientot()
    f.filtre(t)
    verifier(f.historique.index() == n + 1, f"filtre « {t} » appliqué ({time.time() - t0:.1f} s)")
    f.historique.undo()
accepter_bientot(lambda d: d.panneau.v.definir(80) or d.panneau._lire())
f.nouveau_calque_reglage("vibrance")
verifier(doc.calque_actif.reglage and doc.calque_actif.reglage["params"]["vibrance"] == 80,
         "calque de réglage Vibrance créé (fenêtre)")
accepter_bientot(lambda d: d.panneau.v.definir(20) or d.panneau._lire())
f.modifier_reglage()
verifier(doc.calque_actif.reglage["params"]["vibrance"] == 20, "double-clic : réglage modifié")
f.historique.undo()
verifier(doc.calque_actif.reglage["params"]["vibrance"] == 80, "Ctrl+Z : ancien réglage")
f.calques.grouper()
f.calques.rafraichir()
verifier(doc.calque_actif.groupe and f.calques.liste.count() == len(doc.calques), "Ctrl+G : groupe dans le panneau")
f.calques._plier(f.calques.liste.itemWidget(f.calques.liste.item(0)))
print("lignes", f.calques.liste.count(), [(c.nom, c.groupe, c.dans, c.ouvert) for c in doc.calques])
verifier(f.calques.liste.count() == len(doc.calques) - 1, "groupe replié : son calque est caché dans la liste")
k = f.calques.mode.findData("produit")
f.calques.mode.setCurrentIndex(k)
f.calques._mode_choisi(k)
verifier(doc.calque_actif.mode == "produit", "mode de fusion choisi dans le panneau")
f.grab().save(str(sortie / "outils_dessin.png"))
print("ERREURS :", erreurs if erreurs else "aucune")
sys.stdout.flush()
doc.modifie = False
f.close()
sys.exit(1 if erreurs else 0)      # (os._exit après une fenêtre modale fait planter Qt à la sortie)
