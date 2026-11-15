"""IA > Créer une image d'après un texte (Flux Schnell) : recette, fenêtre, nouvelle image ou nouveau calque.
Le moteur n'est pas démarré : les lancements sont observés, les résultats fabriqués.
Usage : essai_creer.py dossier_sortie"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PIL import Image
from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication
from pixane import recettes
from pixane.fenetre import Fenetre
from pixane.moteur import Moteur

Moteur.demarrer = lambda self, signaler=None: (_ for _ in ()).throw(Exception("moteur désactivé pour l'essai"))
Fenetre._moteur_en_echec = lambda self, *a: None
sortie = Path(sys.argv[1])
sortie.mkdir(parents=True, exist_ok=True)
Image.fromarray(np.full((300, 400, 3), 200, np.uint8)).save(sortie / "photo.png")
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


# 1. recette
tc = [recettes.taille_creation(t) for t in ((1344, 768), (4000, 3000), (300, 900))]
verifier(all(w % 16 == 0 and h % 16 == 0 and 0.9e6 < w * h < 1.15e6 for w, h in tc)
         and abs(tc[1][0] / tc[1][1] - 4 / 3) < 0.03 and abs(tc[2][0] / tc[2][1] - 1 / 3) < 0.03,
         f"taille de calcul : ~1 mégapixel, multiples de 16, mêmes proportions ({tc})")
recettes._schnell.update(type="complet", fichier=recettes.SCHNELL_COMPLET)
p, s = recettes.creer("a red apple", (400, 300), nb=3)
verifier(len(s) == 3 and p["23"]["class_type"] == "EmptySD3LatentImage" and p["24"]["inputs"]["text"] == "a red apple"
         and all(p[k]["inputs"]["steps"] == 4 for k in ("40", "50", "60")), "recette : Flux Schnell, 3 propositions, 4 étapes")
verifier(p["42"]["inputs"]["width"] == 400 and p["42"]["inputs"]["height"] == 300, "résultat remis à la taille voulue")
p, s = recettes.creer("a red apple", (400, 300), nb=1, image="x.png", force=0.6)
verifier(p["40"]["inputs"]["denoise"] == 0.6 and p["23"]["class_type"] == "VAEEncode", "« Partir de celle-ci » : redessinée à 60 %")

# 2. fenêtre
app = QApplication(sys.argv)
from pixane.consigne import DialogueConsigne, FORMATS_CREER
d = DialogueConsigne(None, nb=4, creer=True, image_ouverte=True)
verifier(d.windowTitle() == "Créer une image d'après un texte" and d.ou.count() == 2 and not d.format.isEnabled(),
         "fenêtre : nouveau calque (format grisé) ou nouvelle image")
d.ou.setCurrentIndex(1)
verifier(d.format.isEnabled() and d.nouvelle_image() and d.taille() == FORMATS_CREER[d.format.currentIndex()][1:],
         "nouvelle image : choix du format")
d.texte.setPlainText("Fond abstrait bleu nuit et or")
d.show()
app.processEvents()
d.grab().save(str(sortie / "fenetre_creer.png"))
d.close()
d = DialogueConsigne(None, creer=True, image_ouverte=False)
verifier(d.ou.count() == 1 and d.nouvelle_image(), "sans image ouverte : seulement « Nouvelle image »")

# 3. dans Pixane : sans image ouverte, puis dans un calque
f = Fenetre()
f.resize(1440, 920)
f.show()
app.processEvents()
lances = []
f._lancer = lambda titre, avec, fabriquer, **kw: lances.append((titre, fabriquer("image.png"), kw))
reponse = {"ou": "image", "format": 0}


def faux_exec(self):
    self.texte.setPlainText("an abstract night blue and gold background")
    self.anglais.setPlainText("an abstract night blue and gold background")
    i = self.ou.findData(reponse["ou"])
    self.ou.setCurrentIndex(i)
    self.format.setCurrentIndex(reponse["format"])
    return True


DialogueConsigne.exec = faux_exec
verifier(f.doc is None, "au départ : aucune image ouverte")
f.ia_creer()
titre, (prompt, sorties), kw = lances[-1]
verifier(f.doc is not None and f.doc.taille() == (1024, 1024) and titre == "Créer une image d'après un texte",
         "sans image ouverte : une nouvelle image (carré 1024 px) est créée pour recevoir le résultat")
img = QImage(1024, 1024, QImage.Format_ARGB32_Premultiplied)
img.fill(QColor(10, 20, 200))
etat = kw["placer"](img)
f.doc.appliquer_etat(etat)
verifier(len(f.doc.calques) == 1 and f.doc.calques[0].image.pixelColor(5, 5).blue() == 200,
         "le résultat devient l'image (un seul calque)")
f.charger(str(sortie / "photo.png"))
app.processEvents()
reponse["ou"] = "calque"
n = len(f.doc.calques)
f.ia_creer()
titre, (prompt, sorties), kw = lances[-1]
verifier(prompt["42"]["inputs"]["width"] == 400 and prompt["42"]["inputs"]["height"] == 300,
         "dans l'image ouverte : créée à sa taille (400 × 300)")
img = QImage(400, 300, QImage.Format_ARGB32_Premultiplied)
img.fill(QColor(200, 20, 10))
f.doc.appliquer_etat(kw["placer"](img))
verifier(len(f.doc.calques) == n + 1 and f.doc.calque_actif.nom.startswith("Image créée"),
         "dans l'image ouverte : un nouveau calque « Image créée »")
p2, _s2 = kw["variante"]("choisie.png", 0.5)
verifier(p2["10"]["inputs"]["image"] == "choisie.png" and p2["40"]["inputs"]["denoise"] == 0.5,
         "« Partir de celle-ci » : variantes de la proposition choisie")
recettes._schnell.update(type=None)
from PySide6.QtWidgets import QMessageBox
messages = []
QMessageBox.information = staticmethod(lambda *a, **k: messages.append(a[2]))
f.ia_creer()
verifier(messages and "Flux Schnell" in messages[-1], "modèle absent : message clair")

print("ERREURS :", erreurs if erreurs else "aucune")
for doc in list(getattr(f, "_docs", [])):
    doc.modifie = False
sys.stdout.flush()
f.close()
os._exit(1 if erreurs else 0)      # comme essai_suppression : pas de nettoyage de Python après Qt
