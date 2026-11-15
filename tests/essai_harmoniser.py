"""Calque > Harmoniser avec l'arrière-plan : un objet collé (lumière froide, contraste faible) posé sur une photo à
lumière chaude prend ses noirs, ses blancs et sa couleur de lumière ; bord adouci ; calque opaque : message.
Usage : essai_harmoniser.py dossier_sortie"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PIL import Image
from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox
from pixane import harmoniser as hm
from pixane.fenetre import Fenetre
from pixane.moteur import Moteur

Moteur.demarrer = lambda self, signaler=None: (_ for _ in ()).throw(Exception("moteur désactivé pour l'essai"))
Fenetre._moteur_en_echec = lambda self, *a: None
sortie = Path(sys.argv[1])
sortie.mkdir(parents=True, exist_ok=True)
for k in ("lumiere", "couleur", "bord"):
    QSettings("Pixane", "Pixane-essais").remove("harmoniser_" + k)
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


H, W = 300, 400
yy, xx = np.mgrid[0:H, 0:W]
t = (xx / W)[..., None]
fond = (np.array([40, 25, 10]) * (1 - t) + np.array([255, 205, 140]) * t).astype(np.uint8)   # coucher de soleil
Image.fromarray(fond).save(sortie / "fond.png")
objet = np.zeros((H, W, 4), np.uint8)
rond = ((xx - 200) / 60) ** 2 + ((yy - 150) / 60) ** 2 < 1
v = (110 + 50 * (xx - 140) / 120).clip(0, 255)
objet[..., 0], objet[..., 1], objet[..., 2] = v * 0.85, v * 0.95, v * 1.15                    # gris bleuté, terne
objet[..., 3] = np.where(rond, 255, 0)

# 1. calcul
ref = hm.mesures(hm.lab(fond)[hm.reference(np.dstack([fond, np.full((H, W), 255, np.uint8)]), objet[..., 3])])
r = hm.harmoniser(objet, ref, {"lumiere": 100, "couleur": 100, "bord": 0})
lo, lr = hm.lab(objet[..., :3])[rond], hm.lab(r[..., :3])[rond]
verifier(ref["b"] > 15, f"référence : lumière chaude autour de l'objet (b = {ref['b']:.0f})")
verifier(np.percentile(lr[:, 2], 90) > np.percentile(lo[:, 2], 90) + 15,
         "couleur de la lumière : l'objet bleuté se réchauffe")
verifier(np.ptp(np.percentile(lr[:, 0], [3, 97])) > np.ptp(np.percentile(lo[:, 0], [3, 97])) * 1.3,
         "noirs et blancs : l'objet terne prend le contraste de la photo")
verifier((r[~rond] == objet[~rond]).all(), "hors de l'objet : rien ne change")
verifier((hm.harmoniser(objet, ref, hm.NEUTRES) == objet).all(), "réglages à zéro : rien ne change")
b = hm.harmoniser(objet, ref, {"lumiere": 0, "couleur": 0, "bord": 4})
verifier(b[150, 200, 3] == 255 and 0 < b[150, 142, 3] < 255 and b[150, 138, 3] == 0,
         "Adoucir le bord : le bord devient progressif, vers l'intérieur (pas de débord)")

# 2. dans Pixane
app = QApplication(sys.argv)
from pixane.dialogues_reglage import DialogueReglage
from pixane.document import FORMAT_IMAGE, qimage_rgba, tableau
f = Fenetre()
f.resize(1440, 920)
f.show()
f.charger(str(sortie / "fond.png"))
app.processEvents()
f.doc.appliquer_etat(f.doc.etat_nouveau_calque(qimage_rgba(objet), "Objet collé"))
DialogueReglage.exec = lambda self: QDialog.Accepted
f.harmoniser()
a = tableau(f.doc.calque_actif.image.convertToFormat(FORMAT_IMAGE))
la = hm.lab(a[..., :3])[rond & (a[..., 3] > 250)]
verifier(np.percentile(la[:, 2], 90) > np.percentile(lo[:, 2], 90) + 8, "Calque > Harmoniser : l'objet est réchauffé")
Image.fromarray(np.hstack([np.dstack([fond, np.full((H, W), 255, np.uint8)]), objet, a])).save(sortie / "harmoniser.png")
f.historique.undo()
verifier((tableau(f.doc.calque_actif.image.convertToFormat(FORMAT_IMAGE))[rond] == objet[rond]).all(), "Ctrl+Z")
messages = []
QMessageBox.information = staticmethod(lambda *a, **k: messages.append(a[2]))
f.doc.appliquer_etat(f.doc.etat_nouveau_calque(qimage_rgba(np.dstack([fond, np.full((H, W), 255, np.uint8)])), "Opaque"))
f.harmoniser()
verifier(messages and "objet collé" in messages[-1], "calque sans transparence : message")
verifier(f.a_harmoniser.isEnabled(), "menu Calque > Harmoniser avec l'arrière-plan…")

print("ERREURS :", erreurs if erreurs else "aucune")
f.doc.modifie = False
sys.stdout.flush()
QTimer.singleShot(200, f.close)
app.exec()
sys.exit(1 if erreurs else 0)
