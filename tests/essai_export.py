"""Export pour le web et traitement par lot (sans moteur IA). Usage : essai_export.py dossier_images dossier_sortie"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
from PIL import Image
from PySide6.QtWidgets import QApplication, QFileDialog

from pixane.export import DialogueExport, DialogueLot, encoder, preparer, traiter_une
from pixane.fenetre import Fenetre
from pixane.moteur import Moteur

Moteur.demarrer = lambda self, signaler=None: None
Fenetre._moteur_en_echec = lambda self, *a: None
src, sortie = Path(sys.argv[1]), Path(sys.argv[2])
sortie.mkdir(parents=True, exist_ok=True)
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


photos = sorted(p for p in src.iterdir() if p.suffix.lower() in (".jpg", ".png", ".webp"))
im = Image.open(photos[0]).convert("RGBA")
petit = preparer(im, 600)
verifier(max(petit.size) == 600, f"réduction au plus grand côté 600 : {petit.size}")
verifier(preparer(im, 99999).size == im.size, "jamais agrandie")
j80, j50 = encoder(petit, "jpg", 80), encoder(petit, "jpg", 50)
verifier(j50[:2] == b"\xff\xd8" and len(j50) < len(j80), f"JPEG : qualité 50 plus léger ({len(j50)} < {len(j80)})")
w = encoder(petit, "webp", 80)
verifier(w[8:12] == b"WEBP" and len(w) < len(j80), f"WebP plus léger que JPEG ({len(w)} < {len(j80)})")
trans = petit.copy()
trans.putalpha(128)
verifier(Image.open(__import__("io").BytesIO(encoder(trans, "webp", 80))).mode == "RGBA", "WebP garde la transparence")
verifier(Image.open(__import__("io").BytesIO(encoder(trans, "jpg", 80))).mode == "RGB", "JPEG : fond blanc")
avec = encoder(petit, "jpg", 80, True, b"Exif\x00\x00MM\x00*\x00\x00\x00\x08\x00\x00", None)
verifier(b"Exif" in avec[:200] and b"Exif" not in j80[:200], "EXIF enlevé par défaut, gardé sur demande")

app = QApplication(sys.argv)
f = Fenetre()
f.resize(1200, 800)
f.show()
f.charger(str(photos[0]))
verifier(f.a_exporter_web.isEnabled(), "Exporter pour le web : actif avec une photo")
d = DialogueExport(f, im, photos[0].stem)
d.format.setCurrentIndex(d.format.findData("webp"))
d.cote_case.setChecked(True)
d.cote.setValue(800)
d._estimer()
verifier("800" in d.estimation.text() and "Ko" in d.estimation.text(), f"poids estimé : {d.estimation.text()}")
cible = sortie / "export_web.webp"
QFileDialog.getSaveFileName = lambda *a, **k: (str(cible), "")
d.exporter()
verifier(cible.is_file() and max(Image.open(cible).size) == 800, "fichier WebP écrit, 800 px")
d.grab().save(str(sortie / "dialogue_export.png"))
# par le menu Fichier > Exporter pour le web : enregistrer puis message « Exporté », sans erreur
from PySide6.QtWidgets import QDialog
import pixane.export as ex0
ex0.DialogueExport.exec = lambda self: (setattr(self, "chemin", str(cible)), QDialog.Accepted)[1]
try:
    f.exporter_web()
    verifier("export_web" in f.statusBar().currentMessage(), f"menu Exporter pour le web : {f.statusBar().currentMessage()}")
except Exception as e:
    verifier(False, f"menu Exporter pour le web : erreur {e!r}")

# ------------------------------------------------------------- lot
lot = sortie / "lot"
lot.mkdir(exist_ok=True)
for p in lot.glob("*"):
    p.unlink()
opts = {"cote": 500, "auto": True, "format": "jpg", "qualite": 85, "suffixe": "_web"}
for p in photos:
    traiter_une(p, lot, opts)
faits = sorted(lot.glob("*_web.jpg"))
verifier(len(faits) == len(photos) and all(max(Image.open(x).size) == 500 for x in faits),
         f"lot : {len(faits)} photos réduites à 500 px, réglage auto, suffixe _web")
for p in photos:
    verifier(p.stat().st_size > 0, f"original intact : {p.name}")
dl = DialogueLot(f)
dl.source.setText(str(src))
dl.sortie.setText(str(src))
dl.suffixe.setText("")
import pixane.export as ex
messages = []
ex.QMessageBox.information = lambda *a, **k: messages.append(a[2])
dl.lancer()
verifier(messages and "remplacées" in messages[-1], "même dossier sans ajout au nom : refusé (originaux protégés)")
dl.sortie.setText(str(lot))
dl.suffixe.setText("_lot")
dl.upscale.setChecked(False)
dl.fond.setChecked(False)
dl.lancer()
import time
for _ in range(600):
    app.processEvents()
    if dl._fil is None:
        break
    time.sleep(0.02)
verifier(len(list(lot.glob("*_lot.*"))) == len(photos) and "Terminé" in dl.etat.text(), dl.etat.text())
dl.grab().save(str(sortie / "dialogue_lot.png"))
print("ERREURS :", erreurs if erreurs else "aucune")
sys.stdout.flush()
f.close()
sys.exit(1 if erreurs else 0)
