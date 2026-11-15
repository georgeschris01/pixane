"""Image de la licence (la même que dans le README) dans À propos et dans la fenêtre Licence, en français et en
anglais. Captures dans le dossier de sortie.
Usage : essai_image_licence.py dossier_sortie"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication, QLabel
from pixane import langue
from pixane.aide import FenetreLicence
from pixane.dialogues_image import APropos

sortie = Path(sys.argv[1])
sortie.mkdir(parents=True, exist_ok=True)
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


app = QApplication.instance() or QApplication(sys.argv)
for code in ("fr", "en"):
    langue.choisir(code)
    for nom, fen in (("apropos", APropos(None)), ("licence", FenetreLicence())):
        fen.show()
        app.processEvents()
        img = fen.findChild(QLabel, "image_licence")
        pm = img.pixmap() if img else None
        ok = pm is not None and not pm.isNull()
        verifier(ok, f"{nom} ({code}) : image de licence affichée")
        if ok:
            verifier(img.isVisible() and img.width() >= 400, f"{nom} ({code}) : visible, {img.width()} px de large")
            verifier(fen.width() >= pm.deviceIndependentSize().width(),
                     f"{nom} ({code}) : l'image tient dans la fenêtre")
        fen.grab().save(str(sortie / f"{nom}_{code}.png"))
        fen.close()
        fen.deleteLater()
        del fen, img, pm
    QApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    app.processEvents()

print("RÉSULTAT :", "OK" if not erreurs else f"{len(erreurs)} échec(s)")
sys.exit(1 if erreurs else 0)
