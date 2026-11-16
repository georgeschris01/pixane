"""Affichage > Taille de l'interface (au démarrage, QT_SCALE_FACTOR) et Taille des icônes des outils (tout de suite).
Usage : python tests/essai_taille_interface.py DOSSIER_SORTIE"""
import os
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))
os.environ.setdefault("PIXANE_REGLAGES", "Pixane-essais")
for v in ("QT_SCALE_FACTOR", "PIXANE_ECHELLE"):
    os.environ.pop(v, None)

from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox, QToolButton

erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ERREUR  ") + texte)
    if not cond:
        erreurs.append(texte)


reglages = QSettings("Pixane", os.environ["PIXANE_REGLAGES"])
avant = reglages.value("echelle_interface")
avant_icones = reglages.value("taille_icones")

# ---- démarrage : le réglage devient le facteur de Qt
MESURE = ("import os, sys; sys.path.insert(0, sys.argv[1]); from pixane.__main__ import echelle_interface; "
          "echelle_interface(); from PySide6.QtWidgets import QApplication; a = QApplication([]); "
          "from PySide6.QtGui import QFontMetrics; print(os.environ.get('QT_SCALE_FACTOR', '-'), "
          "a.primaryScreen().devicePixelRatio())")


def mesure(env=None):
    e = dict(os.environ, **(env or {}))
    r = subprocess.run([sys.executable, "-c", MESURE, str(RACINE)], capture_output=True, text=True, env=e,
                       timeout=60)
    facteur, ratio = r.stdout.split()
    return facteur, float(ratio)


reglages.setValue("echelle_interface", 100)
reglages.sync()
f100, r100 = mesure()
reglages.setValue("echelle_interface", 85)
reglages.sync()
f85, r85 = mesure()
verifier(f100 == "-" and f85 == "0.85" and abs(r85 / r100 - 0.85) < 0.01,
         f"85 % : facteur {f85}, interface {r85 / r100:.0%} de la normale")
reglages.setValue("echelle_interface", 150)
reglages.sync()
f150, r150 = mesure({"QT_SCALE_FACTOR": "0.85", "PIXANE_ECHELLE": "0.85"})
verifier(f150 == "1.5" and abs(r150 / r100 - 1.5) < 0.01, "relancé par Pixane : l'ancien facteur hérité est remplacé")
fm, _r = mesure({"QT_SCALE_FACTOR": "1.2"})
verifier(fm == "1.2", "QT_SCALE_FACTOR mis à la main : respecté")
reglages.setValue("echelle_interface", "abc")
reglages.sync()
fx, _r = mesure()
verifier(fx == "-", "réglage illisible : taille normale")

# ---- fenêtre : menus, icônes des outils
reglages.setValue("echelle_interface", 100)
reglages.setValue("taille_icones", 22)
reglages.sync()
app = QApplication(sys.argv)
from pixane.fenetre import Fenetre
f = Fenetre()
f.show()
app.processEvents()
pcs = [a.data() for a in f._actions_echelle.actions()]
verifier(pcs == [75, 85, 100, 115, 125, 150, 200] and next(a for a in f._actions_echelle.actions()
                                                           if a.isChecked()).data() == 100,
         "Affichage > Taille de l'interface : 75 à 200 %, 100 % coché")
questions = []
QMessageBox.question = staticmethod(lambda *a, **k: (questions.append(a), QMessageBox.No)[1])
next(a for a in f._actions_echelle.actions() if a.data() == 85).trigger()
verifier(int(QSettings("Pixane", os.environ["PIXANE_REGLAGES"]).value("echelle_interface")) == 85 and questions,
         "choix 85 % : gardé, redémarrage proposé")
next(a for a in f._actions_icones.actions() if a.data() == 36).trigger()
app.processEvents()
tailles = {b.iconSize().width() for b in f._barre_outils.findChildren(QToolButton)}
verifier(f._barre_outils.iconSize().width() == 36 and tailles == {36},
         "icônes des outils en « Très grandes » : toute la barre, tout de suite")
f.close()
f2 = Fenetre()
verifier(f2._barre_outils.iconSize().width() == 36, "taille des icônes gardée au démarrage suivant")
f2.close()

for cle, v in (("echelle_interface", avant), ("taille_icones", avant_icones)):
    if v is None:
        reglages.remove(cle)
    else:
        reglages.setValue(cle, v)
print("ERREURS :", erreurs if erreurs else "aucune")
sys.stdout.flush()
QTimer.singleShot(100, app.quit)
app.exec()
sys.exit(1 if erreurs else 0)
