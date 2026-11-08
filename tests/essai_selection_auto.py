"""Baguette magique (W), sélection rapide (Q), sélection d'objet (O). Le moteur IA est simulé : il renvoie le
masque d'un disque, avec une miette à nettoyer.
Usage : essai_selection_auto.py dossier_sortie"""
import io
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["CHRYPIX_REGLAGES"] = "Chrypix-essais"
import numpy as np
from PIL import Image, ImageDraw
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QApplication, QMessageBox
from chrypix import recettes
from chrypix.canevas import BAGUETTE, OBJET, RAPIDE
from chrypix.document import masque
from chrypix.fenetre import Fenetre
from chrypix.moteur import Moteur
from chrypix.selection_auto import etiquettes, nettoyer

Moteur.demarrer = lambda self, signaler=None: (_ for _ in ()).throw(Exception("moteur désactivé pour l'essai"))
Fenetre._moteur_en_echec = lambda self, *a: None
messages = []
QMessageBox.information = lambda *a, **k: messages.append(a[2] if len(a) > 2 else "") or QMessageBox.Ok
QMessageBox.warning = lambda *a, **k: messages.append(a[2] if len(a) > 2 else "") or QMessageBox.Ok
sortie = Path(sys.argv[1])
sortie.mkdir(parents=True, exist_ok=True)
# fond bleu en dégradé léger + bruit, carré vert avec un trou jaune, disque rouge
rng = np.random.default_rng(1)
H, W = 600, 800
img = np.zeros((H, W, 3), np.int16)
img[...] = (60, 110, 200)
img[..., 0] += (np.arange(W) * 20 // W).astype(np.int16)
img[100:400, 450:750] = (40, 160, 70)
img[200:260, 560:620] = (240, 230, 60)
yy, xx = np.mgrid[0:H, 0:W]
disque = (xx - 200) ** 2 + (yy - 300) ** 2 < 120 ** 2
img[disque] = (210, 50, 40)
img = np.clip(img + rng.integers(-5, 6, img.shape), 0, 255).astype(np.uint8)
Image.fromarray(img).save(sortie / "formes.png")

app = QApplication(sys.argv)
f = Fenetre()
f.resize(1440, 920)
f.show()
f.charger(str(sortie / "formes.png"))
app.processEvents()
c = f.canevas
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


def souris(points, modif=Qt.NoModifier):
    ecran = [c.vers_ecran(QPointF(*p)) for p in points]
    c.event(QMouseEvent(QEvent.MouseButtonPress, ecran[0], ecran[0], Qt.LeftButton, Qt.LeftButton, modif))
    for e in ecran[1:]:
        c.event(QMouseEvent(QEvent.MouseMove, e, e, Qt.NoButton, Qt.LeftButton, modif))
    c.event(QMouseEvent(QEvent.MouseButtonRelease, ecran[-1], ecran[-1], Qt.LeftButton, Qt.NoButton, modif))


def sel():
    return masque(f.doc.selection) > 127


# ------------------------------------------------------------------ calculs
m = np.zeros((40, 40), bool)
m[5:20, 5:20] = True
m[30, 30] = True
verifier(len(etiquettes(m)[1]) == 2 and nettoyer(m).sum() == 225, "nettoyer : la miette disparaît")

# ------------------------------------------------------------------ baguette
f._choisir_outil(BAGUETTE)
verifier(not f.opt_baguette.isHidden() and not f.p_nouvelle.isHidden(), "baguette : options affichées")
f.opt_tolerance.setValue(32)
f.opt_trous.setChecked(False)
f.opt_contigu.setChecked(True)
souris([(600, 350)])
s = sel()
verifier(abs(s.sum() - (300 * 300 - 60 * 60)) < 600 and not s[230, 590], f"clic sur le carré vert : {s.sum()} px, trou exclu")
n = f.historique.index()
f.opt_trous.setChecked(True)
souris([(600, 350)])
verifier(sel()[230, 590] and f.historique.index() == n + 1, "boucher les trous : le trou jaune est pris")
f.opt_trous.setChecked(False)
souris([(50, 50)], Qt.ShiftModifier)
verifier(sel()[50, 50] and sel()[350, 600] and not sel()[300, 200], "Maj : le fond s'ajoute, le disque reste dehors")
souris([(600, 350)], Qt.AltModifier)
verifier(not sel()[350, 600] and sel()[50, 50], "Alt : le carré est retiré")
f.opt_tolerance.setValue(2)
souris([(50, 50), (60, 50), (160, 50)])           # glisser à droite : tolérance augmente
attendu = int(2 + (c.vers_ecran(QPointF(160, 50)).x() - c.vers_ecran(QPointF(50, 50)).x()) / 2)
verifier(abs(f.opt_tolerance.value() - attendu) <= 1, f"glisser à droite : tolérance 2 -> {f.opt_tolerance.value()}")
verifier(c.apercu_selection is None, "aperçu enlevé au lâcher")
f.opt_tolerance.setValue(32)
f.opt_contigu.setChecked(False)
f.opt_trous.setChecked(False)
souris([(560, 230)])
verifier(sel()[230, 590] and not sel()[350, 600], "non contiguë : seulement les pixels jaunes")
f.opt_contigu.setChecked(True)
f.opt_doux.setChecked(True)
souris([(200, 300)])
a = masque(f.doc.selection)
verifier(((a > 0) & (a < 255)).sum() > 50, "bords doux : bord progressif autour du disque")

# ------------------------------------------------------------------ IA absente
recettes._sam["fichier"] = None
messages.clear()
f._choisir_outil(OBJET)
souris([(200, 300)])
verifier(messages and "SAM 3.1" in messages[-1], "modèle SAM absent : message clair")

# ------------------------------------------------------------------ IA simulée
recettes._sam["fichier"] = recettes.SAM
demandes = []


def faux_envoi(png):
    demandes.append(("image", Image.open(io.BytesIO(png)).size))
    return "essai.png"


def faux_calcul(prompt, sorties, annuler, progres):
    det = prompt["12"]["inputs"]
    demandes.append(("calcul", json.loads(det.get("positive_coords", "[]")), json.loads(det.get("negative_coords", "[]")),
                     "bboxes" in det))
    w, h = demandes[0][1]
    im = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(im)
    e = w / W
    d.ellipse([(200 - 120) * e, (300 - 120) * e, (200 + 120) * e, (300 + 120) * e], fill=255)
    d.rectangle([5, 5, 7, 7], fill=255)           # miette
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return [("Objet", buf.getvalue())]


f.moteur.envoyer_image = faux_envoi
f.moteur.executer = faux_calcul


def attendre():
    for _ in range(400):
        app.processEvents()
        if not f.selection_auto._occupe:
            break
        import time
        time.sleep(0.01)
    app.processEvents()


f._mode_selection("nouvelle")
souris([(80, 180), (330, 430)])                   # cadre autour du disque
attendre()
s = sel()
ok_disque = s[300, 200] and not s[300, 400] and not s[6, 6]
verifier(ok_disque and demandes[-1][3], "sélection d'objet (cadre) : disque sélectionné, miette nettoyée")
verifier(demandes[0][0] == "image" and max(demandes[0][1]) <= 1536, f"image envoyée réduite : {demandes[0][1]}")
nb_images = sum(1 for d in demandes if d[0] == "image")
souris([(200, 300)], Qt.ShiftModifier)            # clic : un point
attendre()
verifier(demandes[-1][1] and not demandes[-1][3], "sélection d'objet (clic) : un point envoyé")
verifier(sum(1 for d in demandes if d[0] == "image") == nb_images, "même image : pas renvoyée au moteur")

f._choisir_outil(RAPIDE)
f.doc.selection.fill(0)
souris([(150, 300), (200, 310), (250, 300)])
attendre()
verifier(sel()[300, 200] and len(c.points_ia) >= 2, f"sélection rapide : objet trouvé, {len(c.points_ia)} points montrés")
avant = len(demandes[-1][1])
souris([(180, 250), (220, 250)], Qt.AltModifier)
attendre()
verifier(len(demandes[-1][2]) >= 1 and len(demandes[-1][1]) == avant, "Alt + peindre : points à retirer ajoutés")
c.event(QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier))
verifier(c.points_ia == [], "Échap : nouvel objet")
souris([(150, 300), (250, 300)])                  # 1er trait : un objet
attendre()
premier = demandes[-1][1]
n = len(demandes)
souris([(500, 100), (560, 120)])                  # 2e trait ailleurs : SON objet, pas mélangé au premier
attendre()
calculs = [d for d in demandes[n:] if d[0] == "calcul"]
verifier(len(calculs) == 1 and all(p not in calculs[0][1] for p in premier),
         "2e trait : demande séparée, sans les points du 1er trait")
verifier(sel()[300, 200], "2e trait : le 1er objet reste sélectionné")
f.doc.selection.fill(0)                            # sélection vidée ailleurs (comme Ctrl+D)
souris([(150, 300), (250, 300)])
attendre()
verifier(len(f.selection_auto._session["groupes"]) == 1, "sélection vidée : la sélection rapide repart de zéro")
f.grab().save(str(sortie / "selection_auto.png"))

print("ERREURS :", erreurs if erreurs else "aucune")
sys.stdout.flush()
f.doc.modifie = False
f.close()
os._exit(1 if erreurs else 0)
