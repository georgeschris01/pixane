"""Éditeur de dégradé (points de couleur et d'opacité, milieux, inverser, tout prêts, enregistrés), outil Dégradé à
plusieurs couleurs, effet « Incrustation dégradé » avec ses points, import PSD des points. Moteur non démarré.
Usage : essai_degrades.py dossier_sortie"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QColor, QImage, QMouseEvent
from PySide6.QtWidgets import QApplication

from pixane import degrades as dg
from pixane.document import FORMAT_IMAGE, tableau

sortie = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("sortie_degrades")
sortie.mkdir(parents=True, exist_ok=True)
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


app = QApplication(sys.argv)
dg.mettre_enregistres([])

# ------------------------------------------------------------ calcul
trois = {"couleurs": [{"pos": 0, "couleur": "#ff0000"}, {"pos": 0.5, "couleur": "#00ff00"},
                      {"pos": 1, "couleur": "#0000ff"}], "opacites": [{"pos": 0, "opacite": 1}, {"pos": 1, "opacite": 1}]}
t = dg.table(trois, None, 101)
verifier(np.allclose(t[0, :3], (1, 0, 0)) and np.allclose(t[50, :3], (0, 1, 0)) and np.allclose(t[100, :3], (0, 0, 1)),
         "trois couleurs : rouge, vert au milieu, bleu")
verifier(np.allclose(t[25, :3], (0.5, 0.5, 0), atol=0.02), "entre rouge et vert : moitié-moitié")
mil = dg.normaliser({"couleurs": [{"pos": 0, "couleur": "#000000"}, {"pos": 1, "couleur": "#ffffff", "milieu": 0.2}]})
t = dg.table(mil, None, 101)
verifier(abs(t[20, 0] - 0.5) < 0.02 and t[50, 0] > 0.7, f"milieu à 20 % : gris moyen à 20 % ({t[20, 0]:.2f})")
op = dg.deux_couleurs("#ff0000", None)
t = dg.table(op, None, 11)
verifier(t[0, 3] == 1 and t[10, 3] == 0 and abs(t[5, 3] - 0.5) < 0.01 and np.allclose(t[10, :3], (1, 0, 0)),
         "vers le transparent : opacité de 1 à 0, couleur gardée")
p = dg.table(dg.defaut(), QColor(0, 0, 255), 3)
verifier(np.allclose(p[0], (0, 0, 1, 1)), "point « couleur de peinture » : prend la couleur donnée")
inv = dg.inverse(mil)
t2 = dg.table(inv, None, 101)
verifier(np.allclose(t2[::-1, 0], dg.table(mil, None, 101)[:, 0], atol=0.01), "Inverser : le même dégradé à l'envers")
verifier(dg.normaliser("pas du json")["couleurs"] and dg.normaliser({"couleurs": [{"pos": "x", "couleur": 5}]})
         ["couleurs"][0]["couleur"] == "#000000", "données abîmées : pas de plantage")
verifier(len(dg.tout_prets()) >= 15, f"dégradés tout prêts : {len(dg.tout_prets())}")

# ------------------------------------------------------------ éditeur
ed = dg.EditeurDegrade(dg.deux_couleurs("#000000", "#ffffff"), QColor(255, 0, 0))
ed.show()
ed.resize(600, 480)
app.processEvents()
b = ed.barre


def souris(genre, x, y, bouton=Qt.LeftButton):
    pos = QPointF(x, y)
    ev = QMouseEvent(genre, pos, b.mapToGlobal(pos.toPoint()).toPointF(), bouton,
                     bouton if genre != QEvent.MouseButtonRelease else Qt.NoButton, Qt.NoModifier)
    QApplication.sendEvent(b, ev)
    app.processEvents()


y_coul = b._y_rangee("couleurs")
y_op = b._y_rangee("opacites")
souris(QEvent.MouseButtonPress, b._x(0.5), y_coul)
souris(QEvent.MouseButtonRelease, b._x(0.5), y_coul)
verifier(len(b.d["couleurs"]) == 3 and b.choix[1]["pos"] == 0.5, "clic sous la barre : un point de couleur ajouté")
verifier(QColor(b.choix[1]["couleur"]).red() in range(120, 136), "le nouveau point prend la couleur de l'endroit")
b.choix[1]["couleur"] = "#ff0000"
souris(QEvent.MouseButtonPress, b._x(0.5), y_coul)
souris(QEvent.MouseMove, b._x(0.7), y_coul)
souris(QEvent.MouseButtonRelease, b._x(0.7), y_coul)
verifier(abs(b.choix[1]["pos"] - 0.7) < 0.01 and len(b.d["couleurs"]) == 3, "glisser : le point se déplace")
verifier(ed.s_pos.value() == 70, "la case Position suit")
# milieu : losange entre le point à 0 et celui à 0,7
porteur, mx = b._milieux("couleurs", b.choix[1])[0]
souris(QEvent.MouseButtonPress, mx, b._y_milieu("couleurs"))
souris(QEvent.MouseMove, b._x(0.14), b._y_milieu("couleurs"))
souris(QEvent.MouseButtonRelease, b._x(0.14), b._y_milieu("couleurs"))
verifier(abs(porteur["milieu"] - 0.2) < 0.02, f"losange glissé : milieu à 20 % ({porteur['milieu']:.2f})")
# opacité
souris(QEvent.MouseButtonPress, b._x(0.3), y_op)
souris(QEvent.MouseButtonRelease, b._x(0.3), y_op)
verifier(len(b.d["opacites"]) == 3 and ed.pile.currentIndex() == 1, "clic au-dessus : point d'opacité, sa case montrée")
ed.s_opacite.setValue(0)
verifier(abs(dg.table(ed.degrade, None, 101)[30, 3]) < 0.01, "opacité tapée : 0 % à cet endroit")
# retirer en tirant loin
souris(QEvent.MouseButtonPress, b._x(0.3), y_op)
souris(QEvent.MouseMove, b._x(0.3), y_op - 80)
souris(QEvent.MouseButtonRelease, b._x(0.3), y_op - 80)
verifier(len(b.d["opacites"]) == 2, "point tiré loin de la barre : retiré")
souris(QEvent.MouseButtonPress, b._x(1), y_op)
souris(QEvent.MouseMove, b._x(1), y_op - 80)
souris(QEvent.MouseButtonRelease, b._x(1), y_op - 80)
verifier(len(b.d["opacites"]) == 2, "jamais moins de deux points")
# couleur de peinture
souris(QEvent.MouseButtonPress, b._x(0), y_coul)
souris(QEvent.MouseButtonRelease, b._x(0), y_coul)
ed.c_peinture.setChecked(True)
verifier(b.d["couleurs"][0]["couleur"] == dg.PEINTURE and not ed.b_couleur.isEnabled(),
         "case Couleur de peinture : le point la suit")
ed.grab().save(str(sortie / "editeur_degrade.png"))
# enregistrer dans la liste
from PySide6.QtWidgets import QInputDialog
QInputDialog.getText = staticmethod(lambda *a, **k: ("Mon dégradé", True))
n = ed.liste.count()
ed._enregistrer()
verifier(ed.liste.count() == n + 1 and dg.enregistres()[0][0] == "Mon dégradé", "Enregistrer dans la liste")
ed.liste.setCurrentRow(ed.liste.count() - 1)
verifier(ed.b_retirer_liste.isEnabled(), "un dégradé enregistré peut être retiré")
ed._retirer_liste()
verifier(not dg.enregistres() and ed.liste.count() == n, "Retirer de la liste")
ed.liste.setCurrentRow(7)
ed._pret_choisi(ed.liste.currentItem())
verifier(len(b.d["couleurs"]) == 7, "clic sur « Arc-en-ciel » : 7 couleurs")
ed.close()
e2 = dg.EditeurDegrade(dg.deux_couleurs("#000000", "#ffffff"), None, avec_peinture=False)
verifier(e2.liste.count() == len(dg.tout_prets()) - 3 and not e2.c_peinture.isVisibleTo(e2),
         "dans les styles : pas de « couleur de peinture »")

# ------------------------------------------------------------ outil Dégradé
from pixane.outils_dessin import degrade
base = QImage(300, 20, QImage.Format_ARGB32_Premultiplied)
base.fill(QColor(255, 255, 255))
res = tableau(degrade(base, QPointF(0, 10), QPointF(300, 10), "lineaire", trois, QColor(0, 0, 0), 1.0)
              .convertToFormat(FORMAT_IMAGE))
verifier(res[10, 2, 0] > 240 and res[10, 150, 1] > 240 and res[10, 297, 2] > 240, "outil : rouge, vert, bleu")
res = tableau(degrade(base, QPointF(0, 10), QPointF(300, 10), "lineaire", dg.defaut(), QColor(0, 0, 0), 1.0)
              .convertToFormat(FORMAT_IMAGE))
verifier(res[10, 2, 0] < 15 and res[10, 297, 0] > 240, "outil : couleur de peinture vers transparent (sur du blanc)")
res = tableau(degrade(base, QPointF(0, 10), QPointF(300, 10), "lineaire", trois, QColor(0, 0, 0), 1.0, gris=True)
              .convertToFormat(FORMAT_IMAGE))
verifier(res[10, 150, 0] == res[10, 150, 1] == res[10, 150, 2], "sur un masque : en gris")

# ------------------------------------------------------------ style « Incrustation dégradé »
from pixane.styles import Effet, Style, points_degrade, rendre_style
vieux = Effet.depuis_dict({"type": "degrade", "reglages": {"couleur1": "#ff0000", "couleur2": "#0000ff"}})
verifier(points_degrade(vieux)["couleurs"][1]["couleur"] == "#0000ff", "ancien style (deux couleurs) : relu")
from pixane.styles import _degrade
A = np.ones((40, 100), np.float32)
e = Effet.nouveau("degrade", degrade=trois, angle=0)
rgb, alpha = _degrade(A, e, (0, 0, 100, 40))
verifier(rgb[20, 50, 1] > 0.9 and rgb[20, 1, 0] > 0.9 and rgb[20, 98, 2] > 0.9, "style : trois couleurs")
e = Effet.nouveau("degrade", degrade=dg.deux_couleurs("#ff0000", None), angle=0)
rgb, alpha = _degrade(A, e, (0, 0, 100, 40))
verifier(alpha[20, 1] > 0.95 and alpha[20, 98] < 0.05, "style : point d'opacité respecté")
st = Style((Effet.nouveau("degrade", degrade=trois),))
verifier(Style.depuis_json(st.vers_json()).effets[0].reglages["degrade"]["couleurs"][1]["couleur"] == "#00ff00",
         "style enregistré et relu avec ses points")

# ------------------------------------------------------------ import PSD
from pixane.psd_styles import _effet
d = {"Grad": {"Clrs": [{"Clr ": {"Rd  ": 255, "Grn ": 0, "Bl  ": 0}, "Lctn": 0, "Mdpn": 50},
                       {"Clr ": {"Rd  ": 0, "Grn ": 255, "Bl  ": 0}, "Lctn": 2048, "Mdpn": 30},
                       {"Clr ": {"Rd  ": 0, "Grn ": 0, "Bl  ": 255}, "Lctn": 4096, "Mdpn": 50}],
              "Trns": [{"Opct": ("#Prc", 100.0), "Lctn": 0, "Mdpn": 50}, {"Opct": ("#Prc", 0.0), "Lctn": 4096,
                                                                         "Mdpn": 50}]},
     "Angl": ("#Ang", 90.0)}
eff, approx = _effet("GrFl", d, 120)
pts = points_degrade(eff)
verifier(len(pts["couleurs"]) == 3 and abs(pts["couleurs"][1]["milieu"] - 0.3) < 1e-6 and
         pts["opacites"][1]["opacite"] == 0 and not approx, "PSD : tous les points du dégradé repris")

dg.mettre_enregistres([])
print()
print("ÉCHECS :" if erreurs else "Tout est bon.", *erreurs, sep="\n  ")
sys.exit(1 if erreurs else 0)
