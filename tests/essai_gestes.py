"""Retour / suivant de la souris et Ctrl+Z / Ctrl+Y : pendant un travail pas encore validé (Transformer, Agrandir,
Recadrer), geste par geste ; au début du travail, retour l'abandonne ; sans travail, Annuler / Rétablir ordinaires.
Usage : essai_gestes.py"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PySide6.QtCore import QEvent, QPointF, QRectF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from pixane.canevas import RECADRER
from pixane.document import Document, qimage_rgb
from pixane.fenetre import Fenetre
from pixane.moteur import Moteur

Moteur.demarrer = lambda self, signaler=None: None
Fenetre._moteur_en_echec = lambda self, *a: None
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


app = QApplication(sys.argv)
f = Fenetre()
f.resize(1200, 800)
f.show()
f.activateWindow()
img = np.zeros((300, 400, 3), np.uint8)
img[:, :200] = [200, 60, 60]
doc = Document(qimage_rgb(img))
f._installer_document(doc)
c = f.canevas


def bouton(b):
    """Bouton « retour » ou « suivant » de la souris, sur le canevas."""
    p = QPointF(10, 10)
    ev = QMouseEvent(QEvent.MouseButtonPress, p, c.mapToGlobal(p), b, b, Qt.NoModifier)
    QApplication.sendEvent(c, ev)


# ------------------------------------------------------------------ sans travail : Annuler / Rétablir ordinaires
f._modifier_selection("tout")
pile = f.groupe_historique.activeStack()
n = pile.index()
verifier(f.a_annuler.isEnabled() and "Tout sélectionner" in f.a_annuler.text(), f"Annuler : « {f.a_annuler.text()} »")
bouton(Qt.BackButton)
verifier(pile.index() == n - 1 and doc.selection_vide(), "bouton retour : action annulée")
bouton(Qt.ForwardButton)
verifier(pile.index() == n and not doc.selection_vide(), "bouton suivant : action refaite")
f._modifier_selection("rien")
n = pile.index()

# ------------------------------------------------------------------ Transformer : geste par geste
f.transformer()
t = c.transfo
verifier(t is not None and c.travail() == "transfo", "Transformer commencé")
t.sx = t.sy = 0.5
c.noter_geste()
t.angle = 30
c.noter_geste()
verifier(f.a_annuler.isEnabled() and not f.a_retablir.isEnabled(), "pendant le travail : Annuler actif, Rétablir non")
bouton(Qt.BackButton)
verifier(c.transfo is t and t.angle == 0 and t.sx == 0.5, f"retour : rotation défaite, taille gardée ({t.sx}, {t.angle})")
verifier(f.cases_transfo["a"].value() == 0 and f.cases_transfo["l"].value() == 50, "cases Largeur / Angle suivent")
verifier(f.a_retablir.isEnabled(), "Rétablir actif après un retour")
f.retour()          # Ctrl+Z : pareil
verifier(t.sx == 1 and t.angle == 0, "Ctrl+Z : taille défaite aussi")
bouton(Qt.ForwardButton)
verifier(t.sx == 0.5 and t.angle == 0, "suivant : taille refaite")
f.suivant()
verifier(t.sx == 0.5 and t.angle == 30, "Ctrl+Y : rotation refaite")
f.suivant()
verifier(t.angle == 30 and pile.index() == n, "rien de plus à refaire : l'historique n'est pas touché")
# valeur tapée dans les cases, puis retour
f.cases_transfo["a"].setValue(45)
bouton(Qt.BackButton)
verifier(t.angle == 30, f"angle tapé (45) défait par retour ({t.angle})")
bouton(Qt.BackButton)
bouton(Qt.BackButton)
verifier(c.transfo is t and t.sx == 1 and t.angle == 0, "retour jusqu'au début du travail")
bouton(Qt.BackButton)
verifier(c.transfo is None and pile.index() == n, "au début : retour abandonne la transformation (l'historique "
                                                 "n'est pas touché)")
verifier(np.array_equal(np.asarray(doc.image.convertToFormat(doc.image.format()).constBits()).size > 0, True),
         "photo toujours là")

# ------------------------------------------------------------------ Agrandir : cadre geste par geste
f.ia_agrandir()
verifier(c.travail() == "cadre", "Agrandir commencé")
c.cadre = [0, 0, 50, 0]
c.noter_geste()
c.cadre = [0, 0, 50, 80]
c.noter_geste()
bouton(Qt.BackButton)
verifier(c.cadre == [0, 0, 50, 0] and f.barre_agrandir.valeurs_px()[0] == (0, 0, 50, 0),
         f"Agrandir : retour défait le dernier tirage, la barre suit ({c.cadre})")
bouton(Qt.ForwardButton)
verifier(c.cadre == [0, 0, 50, 80], "Agrandir : suivant le refait")
bouton(Qt.BackButton)
bouton(Qt.BackButton)
verifier(c.cadre == [0, 0, 0, 0], "Agrandir : retour au cadre de départ")
bouton(Qt.BackButton)
verifier(c.cadre is None and not f.barre_agrandir.isVisible() and pile.index() == n, "Agrandir abandonné")

# ------------------------------------------------------------------ Recadrer
f._choisir_outil(RECADRER)
c.recadre = QRectF(10, 10, 200, 150)
c.noter_geste()
c.recadre = QRectF(20, 20, 100, 100)
c.noter_geste()
bouton(Qt.BackButton)
verifier(c.recadre == QRectF(10, 10, 200, 150), "Recadrer : retour remet le cadre d'avant")
bouton(Qt.BackButton)
verifier(c.recadre is None and c.travail() is None and pile.index() == n, "Recadrer : puis le cadre est enlevé")

print("ERREURS :", erreurs if erreurs else "aucune")
sys.stdout.flush()
doc.modifie = False
f.close()
sys.exit(1 if erreurs else 0)
