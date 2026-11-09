"""Plusieurs calques choisis (Ctrl+clic, Maj+clic), fusion et suppression de ces calques, menu du clic droit,
Ctrl+E ; aperçu en direct de la police survolée sur le texte de la photo.
Usage : essai_calques_choisis.py"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication

from pixane.document import FORMAT_IMAGE, Calque, Document, image_vide, tableau
from pixane.fenetre import Fenetre
from pixane.moteur import Moteur
from pixane.texte import Texte

Moteur.demarrer = lambda self, signaler=None: None
Fenetre._moteur_en_echec = lambda self, *a: None
erreurs = []
ROUGE, BLEU, VERT = (0, 0, 255), (255, 0, 0), (0, 255, 0)      # tableau() : B, V, R


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


def couleur(img, x, y):
    return tuple(int(v) for v in tableau(img.convertToFormat(QImage.Format_ARGB32_Premultiplied))[y, x, :3])


def carre(x, coul):
    img = image_vide(200, 100)
    p = QPainter(img)
    p.fillRect(x, 10, 20, 20, QColor(*coul))
    p.end()
    return img


app = QApplication(sys.argv)
f = Fenetre()
f.show()
pc = f.calques

fond = QImage(200, 100, FORMAT_IMAGE)
fond.fill(QColor(255, 255, 255))
doc = Document(fond)
doc.calques = doc.calques + (Calque("Rouge", carre(10, (255, 0, 0))), Calque("Vert", carre(50, (0, 255, 0))),
                             Calque("Bleu", carre(90, (0, 0, 255))))
doc.actif = 3
doc._fusion = None
f._installer_document(doc)


def rang(index):
    return pc._indexes.index(index)


# 1. Ctrl+clic, Maj+clic
verifier(pc.choisis == {3}, f"au départ : le calque actif seul {pc.choisis}")
pc._choisir_avec_touches(rang(1), Qt.ControlModifier)
verifier(pc.choisis == {1, 3} and doc.actif == 1, f"Ctrl+clic : Rouge ajouté {pc.choisis}")
pc._choisir_avec_touches(rang(1), Qt.ControlModifier)
verifier(pc.choisis == {3} and doc.actif == 3, f"Ctrl+clic de nouveau : Rouge retiré {pc.choisis}")
pc._choisir_avec_touches(rang(1), Qt.ShiftModifier)
verifier(pc.choisis == {1, 2, 3}, f"Maj+clic : de Bleu à Rouge {pc.choisis}")
verifier(pc.boutons["fusionner"].isEnabled() and "3" in pc.boutons["fusionner"].toolTip(), "bouton Fusionner : 3 calques")

# 2. menu du clic droit
vus = []


def menu(pos):
    vus.extend(a.text() for a in pc.menu_calque(pos).actions() if a.text())


menu(pc.liste.visualItemRect(pc.liste.item(rang(2))).center())
verifier(any("Fusionner les 3" in t for t in vus), f"clic droit sur un choisi : « Fusionner les 3 calques choisis » {vus}")
vus.clear()
pc._choisir_avec_touches(rang(3), Qt.NoModifier)
menu(pc.liste.visualItemRect(pc.liste.item(rang(3))).center())
verifier("Renommer…" in vus and "Fusionner avec le calque du dessous" in vus, f"clic droit sur un seul calque {vus}")
vus.clear()
menu(QPoint(5, pc.liste.viewport().height() - 2))
verifier("Nouveau calque" in vus, "clic droit dans le vide : Nouveau calque")

# 3. fusionner les choisis (Ctrl+E du menu Calque)
pc.choisis = set()
pc._choisir_avec_touches(rang(3), Qt.NoModifier)
pc._choisir_avec_touches(rang(1), Qt.ControlModifier)
verifier(pc.choisis == {1, 3}, f"Rouge et Bleu choisis (pas Vert) {pc.choisis}")
f.a_fusionner_calques.trigger()
noms = [c.nom for c in doc.calques]
verifier(noms == ["Arrière-plan", "Vert", "Bleu"] or noms[1:] == ["Vert", "Bleu"], f"fusionnés à la place du plus haut {noms}")
k = doc.calques[2]
verifier(couleur(k.image, 15, 15) == ROUGE and couleur(k.image, 95, 15) == BLEU and tableau(k.image)[15, 55, 3] == 0,
         "le calque fusionné contient le rouge et le bleu, pas le vert")
verifier(doc.actif == 2 and pc.choisis == {2}, "le calque fusionné devient le calque actif")
f.historique.undo()
verifier(len(doc.calques) == 4, "Ctrl+Z : les trois calques reviennent")

# 4. refus si un choisi est verrouillé
doc.appliquer_etat(doc.etat_calque_modifie(2, verrou=True))
pc._choisir_avec_touches(rang(3), Qt.NoModifier)
pc._choisir_avec_touches(rang(2), Qt.ControlModifier)
verifier(doc.etat_fusionner_choisis(pc.choisis) is None and not pc.boutons["fusionner"].isEnabled(),
         "un calque verrouillé : fusion refusée")
doc.appliquer_etat(doc.etat_calque_modifie(2, verrou=False))

# 5. supprimer les choisis
pc._choisir_avec_touches(rang(3), Qt.NoModifier)
pc._choisir_avec_touches(rang(2), Qt.ControlModifier)
pc.supprimer()
verifier([c.nom for c in doc.calques][1:] == ["Rouge"], f"Vert et Bleu supprimés {[c.nom for c in doc.calques]}")
f.historique.undo()
verifier(len(doc.calques) == 4, "Ctrl+Z")

# 6. aperçu de la police survolée sur le texte de la photo
t = Texte(texte="Essai", x=10, y=10, taille=40)
doc.appliquer_etat(doc.etat_nouveau_texte(t))
f._calque_change() if hasattr(f, "_calque_change") else None
app.processEvents()
i = doc.actif
avant = tableau(doc.calques[i].image).copy()
texte_avant = doc.calques[i].texte
autre = next(p for p in ("Courier New", "Times New Roman", "Impact", "Consolas") if p != texte_avant.police)
pt = f.panneau_texte
pt.lie = True
pile = (f.historique.count(), f.historique.index())
pt.apercu_police.emit(autre)
verifier((tableau(doc.calques[i].image) != avant).any(), f"police survolée ({autre}) : le texte de la photo change")
verifier(doc.calques[i].texte is texte_avant, "le texte lui-même n'est pas modifié (simple aperçu)")
verifier((f.historique.count(), f.historique.index()) == pile, "rien d'ajouté à Annuler")
pt.apercu_police.emit("")
verifier((tableau(doc.calques[i].image) == avant).all(), "liste fermée sans choix : le texte revient comme avant")

print("ERREURS :", erreurs if erreurs else "aucune")
sys.stdout.flush()
for dd in f.documents:
    dd.modifie = False
f.close()
sys.exit(1 if erreurs else 0)
