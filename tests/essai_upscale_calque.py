"""Upscale d'un seul calque : « plus net » (même taille, même place) ou « agrandi » (l'image entière garde sa taille) ;
« toute l'image » comme avant. L'IA est simulée (agrandissement ×2). Usage : essai_upscale_calque.py"""
import io
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
from dataclasses import replace

import numpy as np
from PIL import Image
from PySide6.QtWidgets import QApplication

import pixane.fenetre as fen
from pixane.document import FORMAT_IMAGE, Calque, Document, qimage_rgb, qimage_rgba, tableau
from pixane.fenetre import Fenetre
from pixane.moteur import Moteur

Moteur.demarrer = lambda self, signaler=None: None
Fenetre._moteur_en_echec = lambda self, *a: None
fen.recettes.schnell_disponible = lambda: True
lances = []
Fenetre._lancer = lambda self, titre, sel, fab, apres=None, png=None, placer=None, **kw: lances.append(
    dict(fab=fab, apres=apres, png=png, placer=placer))
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


app = QApplication(sys.argv)
f = Fenetre()
f.show()
f.a_ia_nouveau_calque.setChecked(False)
VRAIS = (fen.ReglagesUpscale.exec, fen.ReglagesUpscale.valeurs)

W, H = 500, 400
fond = np.zeros((H, W, 4), np.uint8)
fond[:, :] = [230, 230, 230, 255]
photo = np.zeros((H, W, 4), np.uint8)
yy, xx = np.mgrid[0:100, 0:120]
photo[150:250, 190:310, 0] = 40 + xx
photo[150:250, 190:310, 1] = 90
photo[150:250, 190:310, 2] = 60 + yy
photo[150:250, 190:310, 3] = 255


def preparer(cible, nouveau=False, verrou=False):
    doc = Document(calques=[Calque("Fond", qimage_rgba(fond)), Calque("Photo", qimage_rgba(photo), verrou=verrou)])
    doc.actif = 1
    f._installer_document(doc)
    f.a_ia_nouveau_calque.setChecked(nouveau)
    fen.ReglagesUpscale.exec = lambda self: 1
    fen.ReglagesUpscale.valeurs = lambda self: {"net": False, "facteur": 2.0, "force": 0.35, "cible": cible}
    n = len(lances)
    f.ia_upscale()
    return doc, (lances[-1] if len(lances) > n else None)


def ia_x2(l):
    """Fausse IA : l'image envoyée, agrandie ×2."""
    im = Image.open(io.BytesIO(l["png"])).convert("RGB")
    im = im.resize((im.width * 2, im.height * 2), Image.BICUBIC)
    r = qimage_rgb(np.ascontiguousarray(np.asarray(im)))
    return l["apres"](r)


# « agrandi » : la photo 120 × 100 devient 240 × 200, centrée ; l'image reste 500 × 400
doc, l = preparer("agrandi")
envoi = Image.open(io.BytesIO(l["png"]))
verifier(envoi.size == (120, 100), f"seul le contenu du calque est envoyé à l'IA {envoi.size}")
doc.appliquer_etat(l["placer"](ia_x2(l)))
b = doc.bornes([1])
verifier(doc.taille() == (W, H) and (b.width(), b.height()) == (240, 200) and (b.x(), b.y()) == (130, 100),
         f"calque agrandi : 240 × 200 centré, image entière inchangée {doc.taille()} {b}")
verifier(doc.bornes([0]).width() == W and len(doc.calques) == 2, "l'autre calque ne change pas")
# « net » : même taille, même place
doc, l = preparer("net")
doc.appliquer_etat(l["placer"](ia_x2(l)))
b = doc.bornes([1])
k = tableau(doc.calques[1].image.convertToFormat(FORMAT_IMAGE)).astype(int)
verifier(doc.taille() == (W, H) and (b.x(), b.y(), b.width(), b.height()) == (190, 150, 120, 100)
         and np.abs(k[160:240, 200:300, :3] - photo[160:240, 200:300, :3].astype(int)).max() <= 6,
         f"calque plus net : même taille, même place, même image {b}")
# option nouveau calque : le calque d'origine reste
doc, l = preparer("agrandi", nouveau=True)
doc.appliquer_etat(l["placer"](ia_x2(l)))
verifier(len(doc.calques) == 3 and doc.bornes([1]).width() == 120 and doc.bornes([2]).width() == 240
         and doc.actif == 2, "option nouveau calque : le résultat au-dessus, l'original garde sa taille")
# bord transparent gardé (pas de fond ajouté autour de la photo)
k = tableau(doc.calques[2].image.convertToFormat(FORMAT_IMAGE))
verifier(k[50, 50, 3] == 0 and k[200, 250, 3] == 255, "autour de la photo, le calque reste transparent")
# calque verrouillé : refusé
messages = []
fen.QMessageBox.information = lambda *a, **k: messages.append(a[2])
doc, l = preparer("net", verrou=True)
verifier(l is None and messages and ("verrouillé" in messages[-1] or "cadenas" in messages[-1]), "calque verrouillé : refusé avec un message")
from pixane.dialogues import ReglagesUpscale as RU
du = RU(W, H, f, calque=("Photo", (120, 100)), cible="image", image_possible=False)
verifier(not du.cibles["image"].isEnabled(), "un calque verrouillé : « toute l'image » grisé dans la fenêtre")
# « toute l'image » : comme avant (l'image entière est envoyée)
doc, l = preparer("image")
verifier(l is not None and l["png"] is None and l["placer"] is None, "toute l'image : Upscale d'avant")

# fenêtre : les trois choix quand il y a un calque à traiter
from pixane.dialogues import ReglagesUpscale
fen.ReglagesUpscale.exec, fen.ReglagesUpscale.valeurs = VRAIS
d = ReglagesUpscale(W, H, f, calque=("Photo", (120, 100)), cible="agrandi")
verifier(set(d.cibles) == {"image", "net", "agrandi"} and d.cible() == "agrandi"
         and "240 × 200" in d.resultat.text() and "500 × 400" in d.resultat.text(), d.resultat.text())
d.cibles["net"].setChecked(True)
verifier(not d.facteur.isEnabled() and "120 × 100" in d.resultat.text(), d.resultat.text())
d2 = ReglagesUpscale(W, H, f)
verifier(not d2.cibles and d2.valeurs()["cible"] == "image", "sans calque à traiter : Upscale de toute l'image")

print("ERREURS :", erreurs if erreurs else "aucune")
sys.stdout.flush()
for dd in f.documents:
    dd.modifie = False
f.close()
sys.exit(1 if erreurs else 0)
