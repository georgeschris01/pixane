"""Calques de remplissage : couleur unie, dégradé, motif ; modifiables (double-clic), suivent la taille de la feuille,
gardés dans le .piximg ; avec une sélection : masque.
Usage : essai_remplissage.py dossier_sortie"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PIL import Image
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from pixane import calque_remplissage as cr
from pixane.fenetre import Fenetre
from pixane.moteur import Moteur

Moteur.demarrer = lambda self, signaler=None: (_ for _ in ()).throw(Exception("moteur désactivé pour l'essai"))
Fenetre._moteur_en_echec = lambda self, *a: None
sortie = Path(sys.argv[1])
sortie.mkdir(parents=True, exist_ok=True)
Image.fromarray(np.full((300, 400, 3), 200, np.uint8)).save(sortie / "fond.png")
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


app = QApplication(sys.argv)
from pixane.dialogue_remplissage import DialogueRemplissage
from pixane.document import FORMAT_IMAGE, Document, tableau
f = Fenetre()
f.resize(1440, 920)
f.show()
f.charger(str(sortie / "fond.png"))
app.processEvents()
doc = f.doc
px = lambda c: tableau(c.image.convertToFormat(FORMAT_IMAGE))

# 1. rendu
img = cr.rendre(cr.Remplissage("couleur", "#ff204080"), 40, 30)
verifier(tuple(tableau(img.convertToFormat(FORMAT_IMAGE))[10, 10]) == (32, 64, 128, 255), "couleur unie")
deg = cr.Remplissage("degrade", degrade=None, style="lineaire", angle=90)
a = tableau(cr.rendre(deg, 40, 100).convertToFormat(FORMAT_IMAGE)).astype(int)
verifier(a[99, 20, 0] < 10 and a[0, 20, 0] > 245, "dégradé linéaire à 90° : noir en bas, blanc en haut (comme Photoshop)")
a = tableau(cr.rendre(deg.avec(angle=0), 100, 40).convertToFormat(FORMAT_IMAGE)).astype(int)
verifier(a[20, 0, 0] < 10 and a[20, 99, 0] > 245, "dégradé à 0° : de gauche à droite")
a = tableau(cr.rendre(deg.avec(style="radial"), 100, 100).convertToFormat(FORMAT_IMAGE)).astype(int)
verifier(a[50, 50, 0] < 10 and a[0, 0, 0] > 245, "dégradé radial : noir au centre")
a = tableau(cr.rendre(deg.avec(style="reflechi", angle=0), 100, 40).convertToFormat(FORMAT_IMAGE)).astype(int)
verifier(a[20, 50, 0] < 15 and a[20, 0, 0] > 245 and a[20, 99, 0] > 245, "dégradé réfléchi : noir au milieu")
a = tableau(cr.rendre(deg.avec(inverser=True), 40, 100).convertToFormat(FORMAT_IMAGE)).astype(int)
verifier(a[99, 20, 0] > 245, "Inverser")
for s in cr.STYLES:
    verifier(not cr.rendre(deg.avec(style=s), 50, 30).isNull(), f"style {s} : dessiné")
m = tableau(cr.rendre(cr.Remplissage("motif"), 80, 60).convertToFormat(FORMAT_IMAGE))
verifier(m[..., 3].max() > 0 and len(np.unique(m[..., 0])) > 4, "motif : la feuille est pavée")
verifier(cr.Remplissage.depuis_dict(deg.avec(angle=33).vers_dict()) == deg.avec(angle=33), "vers_dict / depuis_dict")

# 2. dans le document
n = len(doc.calques)
doc.appliquer_etat(doc.etat_nouveau_remplissage(cr.Remplissage("couleur", "#ffff0000"), "Couleur unie"))
c = doc.calque_actif
verifier(len(doc.calques) == n + 1 and cr.valide(c) is not None and tuple(px(c)[150, 200]) == (255, 0, 0, 255),
         "nouveau calque de remplissage rouge sur toute la feuille")
doc.appliquer_etat(doc.etat_taille(800, 600))
c = doc.calque_actif
verifier(cr.valide(c) is not None and c.image.width() == 800 and tuple(px(c)[599, 799]) == (255, 0, 0, 255),
         "image agrandie : le remplissage est redessiné à la nouvelle taille, toujours modifiable")
doc.appliquer_etat(doc.etat_taille(400, 300))
fichier = Path(os.environ.get("TEMP", ".")) / "essai_remplissage.piximg"
doc.enregistrer(fichier)
d2 = Document.ouvrir(fichier)
r2 = [cr.valide(k) for k in d2.calques if cr.valide(k) is not None]
verifier(len(r2) == 1 and r2[0].couleur == "#ffff0000", "enregistré puis rouvert : toujours un calque de remplissage")
fichier.unlink(missing_ok=True)
doc.appliquer_etat(doc.etat_en_pixels(doc.actif))
verifier(cr.valide(doc.calque_actif) is None, "Convertir en image : calque ordinaire")
# avec une sélection : masque
from PySide6.QtGui import QColor, QPainter
doc.selection.fill(0)
p = QPainter(doc.selection)
p.fillRect(0, 0, 100, 300, QColor(0, 0, 0, 255))
p.end()
doc.appliquer_etat(doc.etat_nouveau_remplissage(cr.Remplissage("couleur", "#ff00ff00"), "Couleur unie"))
mq = doc.calque_actif.masque
verifier(mq is not None and mq.pixelColor(50, 150).lightness() > 250 and mq.pixelColor(300, 150).lightness() < 5,
         "avec une sélection : elle devient le masque du calque de remplissage")
doc.selection.fill(0)

# 3. par la fenêtre (menu Calque > Nouveau calque de remplissage > Dégradé…)
def regler(action):
    def chercher():
        for d in QApplication.topLevelWidgets():
            if isinstance(d, DialogueRemplissage) and d.isVisible():
                action(d)
                return
        QTimer.singleShot(50, chercher)
    QTimer.singleShot(100, chercher)


def degrade_bleu(d):
    d.style.setCurrentIndex(cr.STYLES.index("radial"))
    d._degrade_change({"couleurs": [{"pos": 0, "couleur": "#0000ff", "milieu": 0.5},
                                    {"pos": 1, "couleur": "#ffff00", "milieu": 0.5}],
                       "opacites": [{"pos": 0, "opacite": 1, "milieu": 0.5}, {"pos": 1, "opacite": 1, "milieu": 0.5}]})
    app.processEvents()
    vu["apercu"] = tuple(px(doc.calque_actif)[150, 200])
    d.grab().save(str(sortie / "fenetre_degrade.png"))
    QTimer.singleShot(200, d.accept)


vu = {}
n = len(doc.calques)
regler(degrade_bleu)
f.nouveau_calque_remplissage("degrade")
c = doc.calque_actif
r = cr.valide(c)
verifier(vu.get("apercu", (0, 0, 0))[2] > 200, f"fenêtre : l'aperçu se voit tout de suite sur le calque ({vu.get('apercu')})")
verifier(len(doc.calques) == n + 1 and r is not None and r.genre == "degrade" and r.style == "radial"
         and tuple(px(c)[150, 200][:3])[2] > 200, "OK : calque de dégradé radial bleu → jaune")
verifier(f.historique.undoText() == "Nouveau calque de remplissage", "une étape « Nouveau calque de remplissage »")
f.historique.undo()
verifier(len(doc.calques) == n, "Annuler : le calque disparaît")
regler(lambda d: QTimer.singleShot(100, d.reject))
f.nouveau_calque_remplissage("couleur")
verifier(len(doc.calques) == n, "fenêtre annulée : pas de nouveau calque")
# double-clic (Modifier) sur un calque de couleur : changer la couleur
f.historique.redo()
regler(lambda d: (d.genre.setCurrentIndex(0), setattr(d.couleur, "valeur", "#ff112233"), d._lire(),
                  QTimer.singleShot(100, d.accept)))
f.modifier_reglage()
r = cr.valide(doc.calque_actif)
verifier(r is not None and r.genre == "couleur" and tuple(px(doc.calque_actif)[10, 10][:3]) == (17, 34, 51),
         "Modifier (double-clic) : le dégradé devient une couleur unie")
verifier(f.historique.undoText() == "Modifier le remplissage", "une étape « Modifier le remplissage »")
verifier(hasattr(f, "a_remplissage_couleur") and hasattr(f, "a_remplissage_motif"), "menu Calque > Nouveau calque de remplissage")
f.calques.grab().save(str(sortie / "panneau.png"))

print("ERREURS :", erreurs if erreurs else "aucune")
doc.modifie = False
sys.stdout.flush()
QTimer.singleShot(200, f.close)
app.exec()
sys.exit(1 if erreurs else 0)
