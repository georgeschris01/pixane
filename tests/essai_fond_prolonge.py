"""Agrandir : la proposition « Fond prolongé » (sans IA) s'ajoute aux propositions de Flux quand les bords sont unis,
est posée telle quelle (pas de pleine définition, pas de variantes) ; absente quand un objet touche le bord.
Faux moteur, rien d'envoyé. Usage : essai_fond_prolonge.py"""
import io
import os
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PIL import Image
from PySide6.QtWidgets import QApplication

from pixane import dialogues, fenetre as module_fenetre
from pixane.document import Calque, Document, qimage_rgb, tableau
from pixane.fenetre import Fenetre
from pixane.moteur import Moteur

Moteur.demarrer = lambda self, signaler=None: None
Fenetre._moteur_en_echec = lambda self, *a: None
Fenetre._peut_fermer_tout = lambda self: True
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


app = QApplication(sys.argv)
f = Fenetre()
f.show()
f.a_ia_nouveau_calque.setChecked(False)
f.barre_agrandir.pleine.setChecked(True)
affinages = []
f._affiner_agrandir = lambda img, m, fin, accorder=None: (affinages.append(1), fin(img))

# faux Flux : une image grise de la taille de travail
envoyes = []
f.moteur.envoyer_image = lambda donnees: (envoyes.append(donnees), "x.png")[1]


def executer(prompt, sorties, annuler, progres, morceaux=1):
    png = Image.open(io.BytesIO(envoyes[-1])).convert("RGB")
    tampon = io.BytesIO()
    Image.new("RGB", png.size, (90, 90, 90)).save(tampon, "PNG")
    yield "Proposition 1", tampon.getvalue()


f.moteur.executer = executer

vus = {}


def exec_choix(self, choisir="Fond prolongé"):
    libelles = [self.vignettes.item(i).text() for i in range(self.vignettes.count())]
    vus["libelles"] = libelles
    if choisir in libelles:
        self.vignettes.setCurrentRow(libelles.index(choisir))
        # « Partir de celle-ci » sur Fond prolongé : refusé avec un message
        self._variante()
        vus["message"] = self.etat.text()
    return 1


dialogues.ChoixResultat.exec = exec_choix
module_fenetre.ChoixResultat.exec = exec_choix


def attendre(cond, s=20):
    t = time.monotonic()
    while not cond() and time.monotonic() - t < s:
        app.processEvents()
        time.sleep(0.02)


def agrandir(image: np.ndarray):
    f._installer_document(Document(calques=[Calque("Photo", qimage_rgb(np.ascontiguousarray(image)))]))
    vus.clear()
    affinages.clear()
    w0 = f.doc.image.width()
    f.ia_agrandir()
    f.canevas.cadre = [0, 0, 200, 200]
    f.canevas.abime = [0, 0, 0, 0]
    f.barre_agrandir.definir_px((0, 0, 200, 200), (0, 0, 0, 0))
    f._lancer_agrandir()
    attendre(lambda: f.doc.image.width() != w0)
    return w0


# 1. fond en dégradé uni : Fond prolongé proposé, choisi, posé tel quel
rng = np.random.default_rng(2)
y = np.arange(300)[:, None, None]
fond = np.concatenate([np.full((300, 400, 1), 15.0), np.full((300, 400, 1), 25.0),
                       40 + y * 0.4 * np.ones((1, 400, 1))], axis=2)
img = (fond + rng.normal(0, 1.2, fond.shape)).clip(0, 255).astype(np.uint8)
img[120:180, 170:230] = [240, 200, 40]                     # un objet au milieu (ne touche pas les bords)
w0 = agrandir(img)
verifier("Fond prolongé" in vus.get("libelles", []), f"proposition « Fond prolongé » ajoutée ({vus.get('libelles')})")
verifier(f.doc.image.width() == w0 + 400, f"image agrandie ({w0} -> {f.doc.image.width()})")
verifier(not affinages, "pas de pleine définition pour Fond prolongé (déjà à la vraie taille)")
verifier("sans IA" in vus.get("message", ""), f"pas de variantes : message ({vus.get('message')})")
r = tableau(f.doc.image)[:, :, :3].astype(np.float32)
gauche = r[:, 20:180, 2].mean(axis=1)
attendu = img[:, :8, 2].astype(np.float32).mean(axis=1)
verifier(np.abs(gauche - attendu).max() < 3, "le dégradé continue à gauche (pas le gris de Flux)")
f.historique.undo()
verifier(f.doc.image.width() == w0, "Ctrl+Z revient à l'image d'avant")

# 2. un objet touche le bord : seulement la proposition de Flux
img2 = img.copy()
img2[100:200, :50] = [240, 200, 40]
agrandir(img2)
verifier(vus.get("libelles") == ["Proposition 1"], f"objet au bord : pas de Fond prolongé ({vus.get('libelles')})")

f.close()
print()
print("ERREURS :", *erreurs, sep="\n  ") if erreurs else print("ERREURS : aucune")
sys.exit(1 if erreurs else 0)
