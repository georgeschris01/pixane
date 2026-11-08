"""Lance Chrypix en anglais (sans moteur), ouvre une image et les principales fenêtres, capture l'écran et
cherche les textes restés en français dans tout ce qui est affiché.
Usage : essai_anglais.py image dossier_sortie"""
import os
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["CHRYPIX_REGLAGES"] = "Chrypix-essais"
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QAbstractButton, QApplication, QLabel, QLineEdit, QMenu, QWidget
from chrypix import langue
from chrypix.__main__ import traduire_qt
from chrypix.dialogues import Attente, ChoixResultat, ReglagesUpscale
from chrypix.fenetre import Fenetre
from chrypix.moteur import Moteur

Moteur.demarrer = lambda self, signaler=None: (_ for _ in ()).throw(Exception("engine off"))
Fenetre._moteur_en_echec = lambda self, *a: None
app = QApplication(sys.argv)
traduire_qt(app, langue.choisir("en"))
sortie = Path(sys.argv[2])
f = Fenetre()
f.resize(1440, 920)
f.show()
f.charger(sys.argv[1])
f.calques.nouveau()
f.ia_agrandir()
app.processEvents()
f.grab().save(str(sortie / "anglais.png"))
u = ReglagesUpscale(1200, 800, f)
c = ChoixResultat("Erase", f.doc.image, f)
a = Attente("Erase", f)
a.maj({"secondes": 75, "etape": "Flux computing — step 3 of 20", "fraction": 0.15, "restant": 300})
for d in (u, c, a):
    d.show()
app.processEvents()
u.grab().save(str(sortie / "anglais_upscale.png"))
a.grab().save(str(sortie / "anglais_attente.png"))

FRANCAIS = re.compile(r"[éèàçêùôîâœ«»]|\b(le|la|les|du|des|calque|photo|image de|Annuler|Effacer|Remplir)\b")
textes = set()
for w in app.allWidgets():
    for t in ((w.text() if isinstance(w, (QAbstractButton, QLabel, QLineEdit)) else ""), w.toolTip(),
              w.windowTitle(), (w.placeholderText() if isinstance(w, QLineEdit) else "")):
        if t:
            textes.add(t)
    for act in w.actions():
        textes.update(x for x in (act.text(), act.toolTip()) if x)
for m in f.menuBar().findChildren(QMenu):
    textes.add(m.title())
    textes.update(x.text() for x in m.actions() if x.text())
restes = sorted(t for t in textes if FRANCAIS.search(t))
print("textes affichés :", len(textes))
print("restés en français :", restes if restes else "aucun")
f.doc.modifie = False
sys.stdout.flush()
os._exit(0)   # fin directe : les fenêtres de dialogue ouvertes ne bloquent pas l'essai
