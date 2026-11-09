"""Essai : les commandes des menus Réglages, Filtres et Nouveau calque de réglage ouvrent bien leur fenêtre
quand on passe par le menu (QAction.trigger, comme un clic ou un raccourci clavier), sans erreur.

Usage : python tests/essai_menus.py <image>
(le défaut corrigé en 0.3.1 : le menu envoyait « coché = False » à la place du nom du réglage)
"""
import os
import sys
import traceback

os.environ.setdefault("PIXANE_REGLAGES", "Pixane-essais")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication, QDialog  # noqa: E402

erreurs = []
sys.excepthook = lambda t, v, tb: erreurs.append("".join(traceback.format_exception(t, v, tb)))

app = QApplication(sys.argv)
from pixane import ajustements, filtres  # noqa: E402
from pixane.fenetre import Fenetre  # noqa: E402

f = Fenetre()
f.show()
f.charger(sys.argv[1])
app.processEvents()
ouverts = []


def fermer():
    for w in app.topLevelWidgets():
        if isinstance(w, QDialog) and w.isVisible():
            ouverts.append(w.windowTitle())
            w.reject()
            return
    QTimer.singleShot(100, fermer)


noms = [f"a_regl_{t}" for t in ("niveaux", "courbes", "balance", "noir_blanc", "vibrance")]
noms += [f"a_filtre_{t}" for t in filtres.FILTRES] + [f"a_cr_{t}" for t in ajustements.TYPES]
echecs = 0
for n in noms:
    a = getattr(f, n)
    avant = len(ouverts), len(erreurs)
    QTimer.singleShot(200, fermer)
    a.trigger()
    app.processEvents()
    ok = a.isEnabled() and len(ouverts) == avant[0] + 1 and len(erreurs) == avant[1]
    echecs += not ok
    print(("ok    " if ok else "ÉCHEC ") + n, "->", ouverts[-1] if len(ouverts) > avant[0] else "rien d'ouvert")
for e in erreurs:
    print(e)
print("ERREURS :", echecs)
sys.stdout.flush()
for d in f.documents:          # aucune question à la fermeture
    d.modifie = False
f.close()
sys.exit(1 if echecs else 0)
