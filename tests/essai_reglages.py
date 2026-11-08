"""Réglages de l'image : calculs (luminosité, contraste, saturation, teinte, température, netteté, sélection,
transparence) et fenêtre (aperçu, Appliquer, Annuler, Ctrl+Z, calque verrouillé).
Usage : essai_reglages.py dossier_sortie   (une image d'essai est fabriquée ; le moteur n'est pas démarré)"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["CHRYPIX_REGLAGES"] = "Chrypix-essais"   # ne touche pas aux réglages de l'utilisateur
import numpy as np
from PIL import Image
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMessageBox
from chrypix.document import FORMAT_CALQUE, FORMAT_IMAGE, qimage_rgba, tableau
from chrypix.fenetre import Fenetre
from chrypix.moteur import Moteur
from chrypix.reglages_image import FenetreReglages, ajuster

Moteur.demarrer = lambda self, signaler=None: (_ for _ in ()).throw(Exception("moteur désactivé pour l'essai"))
Fenetre._moteur_en_echec = lambda self, *a: None
messages = []
QMessageBox.information = lambda *a, **k: messages.append(a[2] if len(a) > 2 else "") or QMessageBox.Ok
sortie = Path(sys.argv[1])
sortie.mkdir(parents=True, exist_ok=True)
yy, xx = np.mgrid[0:300, 0:400]
fond = np.dstack([xx * 255 // 400, yy * 255 // 300, np.full_like(xx, 120)]).astype(np.uint8)
Image.fromarray(fond).save(sortie / "fond.png")

app = QApplication(sys.argv)
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


def rgb(img):
    return tableau(img.convertToFormat(FORMAT_IMAGE))[:, :, :3].astype(int)


# ------------------------------------------------------------------ calculs
t = np.dstack([fond, np.full((300, 400), 255, np.uint8)])
img = qimage_rgba(t).convertToFormat(FORMAT_CALQUE)
base = rgb(img)
z = {k: 0 for k in ("luminosite", "contraste", "saturation", "teinte", "temperature", "nettete")}
verifier(np.array_equal(rgb(ajuster(img, z)), base), "réglages à zéro : image inchangée")
plus = rgb(ajuster(img, dict(z, luminosite=50)))
verifier(plus.mean() > base.mean() + 20, f"luminosité + : plus clair ({base.mean():.0f} -> {plus.mean():.0f})")
verifier(plus.max() <= 255 and plus[0, 0].sum() <= base[0, 0].sum() + 60, "luminosité : le noir reste presque noir")
verifier(rgb(ajuster(img, dict(z, contraste=60))).std() > base.std() * 1.2, "contraste + : écarts plus grands")
gris = rgb(ajuster(img, dict(z, saturation=-100)))
verifier(np.abs(gris[..., 0] - gris[..., 2]).max() <= 2, "saturation -100 : noir et blanc")
verifier(np.abs(rgb(ajuster(img, dict(z, teinte=120))) - base).mean() > 30, "teinte : couleurs changées")
chaud = rgb(ajuster(img, dict(z, temperature=60)))
verifier(chaud[..., 0].mean() > base[..., 0].mean() and chaud[..., 2].mean() < base[..., 2].mean(),
         "température + : plus de rouge, moins de bleu")
net = rgb(ajuster(img, dict(z, nettete=150)))
verifier(net.shape == base.shape, "netteté : image de même taille")
t2 = t.copy()
t2[:, :200, 3] = 0                                             # moitié transparente
img2 = qimage_rgba(t2).convertToFormat(FORMAT_CALQUE)
verifier(np.array_equal(tableau(ajuster(img2, dict(z, luminosite=50)))[:, :, 3], tableau(img2)[:, :, 3]),
         "transparence gardée")
sel = qimage_rgba(np.zeros((300, 400, 4), np.uint8)).convertToFormat(FORMAT_CALQUE)
s = tableau(sel)
s[100:200, 100:200] = 255
sel = qimage_rgba(s).convertToFormat(FORMAT_CALQUE)
res = rgb(ajuster(img, dict(z, luminosite=60), sel))
verifier(np.array_equal(res[:90], base[:90]) and res[150, 150].sum() > base[150, 150].sum() + 30,
         "sélection : seule la zone choisie change")

# ------------------------------------------------------------------ fenêtre
f = Fenetre()
f.resize(1440, 920)
f.show()
f.charger(str(sortie / "fond.png"))
app.processEvents()
doc = f.doc
avant = rgb(doc.image)


def regler(valeurs, accepter, verifs=None):
    def agir():
        d = next(w for w in app.topLevelWidgets() if isinstance(w, FenetreReglages) and w.isVisible())
        for cle, v in valeurs.items():
            d.curseurs[cle].setValue(v)
        def finir():
            if verifs:
                verifs(d)
            d.accept() if accepter else d.reject()
        QTimer.singleShot(900, finir)                 # laisse l'aperçu se calculer
    QTimer.singleShot(200, agir)
    f.reglages_image()


apercu = {}
regler({"luminosite": 50}, False, lambda d: apercu.update(v=rgb(doc.image).mean()))
verifier(apercu.get("v", 0) > avant.mean() + 20, "aperçu en direct sur la photo")
verifier(np.array_equal(rgb(doc.image), avant) and f.historique.index() == 0 and not doc.modifie,
         "Annuler : photo d'origine, rien dans l'historique")
regler({"luminosite": 50, "saturation": -40}, True)
verifier(rgb(doc.image).mean() > avant.mean() + 20 and f.historique.index() == 1, "Appliquer : réglage gardé")
f.grab().save(str(sortie / "fenetre.png"))
f.historique.undo()
verifier(np.array_equal(rgb(doc.image), avant), "Ctrl+Z : réglage annulé")
doc.appliquer_etat(doc.etat_calque_modifie(0, verrou=True))
n = f.historique.index()
f.reglages_image()
verifier(messages and f.historique.index() == n, "calque verrouillé : refusé avec un message")

print("ERREURS :", erreurs if erreurs else "aucune")
sys.stdout.flush()
doc.modifie = False
f.close()
os._exit(1 if erreurs else 0)
