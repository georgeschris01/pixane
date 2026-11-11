"""Zoom dans la fenêtre de choix du résultat : molette sous la souris, glisser, double-clic, 100 %, touches ; le zoom
et l'endroit regardé restent d'une proposition à l'autre et pendant « voir l'original ». Usage : essai_zoom_choix.py"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from pixane.dialogues import ChoixResultat
from pixane.document import FORMAT_IMAGE, qimage_rgb, tableau

erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


def image(w, h, couleur):
    a = np.zeros((h, w, 3), np.uint8)
    a[:] = couleur
    a[h // 4: h // 4 + 20, w // 4: w // 4 + 20] = [255, 255, 0]   # carré jaune à 1/4, 1/4
    return qimage_rgb(a)


def molette(widget, pos, crans):
    e = QWheelEvent(QPointF(pos), QPointF(widget.mapToGlobal(pos)), QPoint(0, 0), QPoint(0, 120 * crans),
                    Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False)
    QApplication.sendEvent(widget, e)


def pixel(widget, x, y):
    g = tableau(widget.grab().toImage().convertToFormat(FORMAT_IMAGE))
    r = widget.devicePixelRatioF()
    return tuple(int(v) for v in g[int(y * r), int(x * r), :3])


app = QApplication(sys.argv)
original = image(1000, 800, [40, 40, 200])
c = ChoixResultat("Essai", original)
c.resize(900, 700)
c.show()
QTest.qWaitForWindowExposed(c)
c.ajouter([("A", image(1000, 800, [200, 40, 40])), ("B", image(1000, 800, [40, 200, 40]))])
a = c.apercu
verifier(abs(a.facteur - 1) < 1e-9 and a.echelle() < 1, f"au départ : image entière ({a.echelle():.0%})")

# molette sur le carré jaune : il reste sous la souris
s = a.echelle()
im = a._image
pos = QPoint(round(a.width() / 2 + (0.25 + 10 / im.width() - 0.5) * im.width() * s),
             round(a.height() / 2 + (0.25 + 10 / im.height() - 0.5) * im.height() * s))
verifier(pixel(a, pos.x(), pos.y()) == (255, 255, 0), f"le carré jaune est sous la souris {pixel(a, pos.x(), pos.y())}")
molette(a, pos, 3)
verifier(a.facteur > 1.9, f"molette : zoom ({a.echelle():.0%})")
verifier(pixel(a, pos.x(), pos.y()) == (255, 255, 0), "zoom sous la souris : le détail visé reste sous la souris")
z, ctr = a.facteur, QPointF(a.centre)
# autre proposition : même zoom, même endroit
c.vignettes.setCurrentRow(1)
verifier(a.facteur == z and a.centre == ctr and pixel(a, 20, 20) == (40, 200, 40),
         "autre proposition : même zoom, même endroit")
# voir l'original : même endroit
c._comparer(True)
verifier(a.facteur == z and a.centre == ctr and pixel(a, 20, 20) == (40, 40, 200)
         and pixel(a, pos.x(), pos.y()) == (255, 255, 0), "voir l'original : même zoom, même endroit")
c._comparer(False)
# glisser : l'image suit la souris
avant = QPointF(a.centre)
QTest.mousePress(a, Qt.LeftButton, Qt.NoModifier, QPoint(400, 300))
QTest.mouseMove(a, QPoint(300, 250))
QTest.mouseRelease(a, Qt.LeftButton, Qt.NoModifier, QPoint(300, 250))
verifier(a.centre.x() > avant.x() and a.centre.y() > avant.y(), "glisser : on se déplace dans l'image")
# ne pas sortir de l'image
for _ in range(20):
    QTest.mousePress(a, Qt.LeftButton, Qt.NoModifier, QPoint(100, 100))
    QTest.mouseMove(a, QPoint(480, 340))
    QTest.mouseRelease(a, Qt.LeftButton, Qt.NoModifier, QPoint(480, 340))
verifier(pixel(a, 2, 2) != (40, 40, 40) and pixel(a, 2, 2) == (40, 200, 40), "on ne sort pas de l'image (bord collé)")
# 100 %, ajuster, touches, double-clic
c.bouton_100.click()
verifier(abs(a.echelle() - 1) < 1e-6, "bouton 100 % : taille réelle")
c.bouton_ajuster.click()
verifier(a.facteur == 1 and a.centre == QPointF(0.5, 0.5), "bouton Ajuster : image entière")
QTest.keyClick(c, Qt.Key_1)
verifier(abs(a.echelle() - 1) < 1e-6, "touche 1 : 100 %")
QTest.keyClick(c, Qt.Key_Plus)
verifier(abs(a.echelle() - 1.25) < 1e-6, "touche + : zoom")
QTest.keyClick(c, Qt.Key_0)
verifier(a.facteur == 1, "touche 0 : ajusté")
QTest.mouseDClick(a, Qt.LeftButton, Qt.NoModifier, QPoint(300, 200))
verifier(abs(a.echelle() - 1) < 1e-6, "double-clic : 100 %")
QTest.mouseDClick(a, Qt.LeftButton, Qt.NoModifier, QPoint(300, 200))
verifier(a.facteur == 1, "double-clic encore : ajusté")
molette(a, QPoint(300, 200), -5)
verifier(a.facteur == 1, "pas plus petit que l'image entière")
molette(a, QPoint(300, 200), 60)
verifier(a.echelle() <= a.ZOOM_MAX + 1e-6, f"zoom limité ({a.echelle():.0%})")
# Upscale : original plus petit que la proposition, même endroit regardé
c2 = ChoixResultat("Upscale", image(500, 400, [40, 40, 200]))
c2.resize(900, 700)
c2.show()
c2.ajouter([("x2", image(1000, 800, [200, 40, 40]))])
c2.apercu.zoomer(4.0, QPointF(200, 150))
centre = QPointF(c2.apercu.centre)
c2._comparer(True)
verifier(c2.apercu.centre == centre, "Upscale : l'original (plus petit) montre le même endroit")
c2.close()
verifier(c.choix() is c.images[1], "le choix reste la proposition sélectionnée")

print("ERREURS :", erreurs if erreurs else "aucune")
sys.stdout.flush()
c.close()
sys.exit(1 if erreurs else 0)
