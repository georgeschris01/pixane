"""Police semblable, dans la fenêtre : lettres écrites en Impact sélectionnées, recherche (sur une petite liste de
polices, pour aller vite), « Créer un texte avec cette police » puis « Appliquer au texte choisi » ; option
Affichage > Recherche de police semblable (menu et bouton cachés, mémoire effacée). Moteur non démarré.
Usage : essai_polices.py dossier_sortie"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter
from PySide6.QtWidgets import QApplication

from pixane import dialogue_polices, polices_semblables as ps
from pixane.document import FORMAT_IMAGE, _masque_vers_selection, tableau
from pixane.fenetre import Fenetre
from pixane.moteur import Moteur
from pixane.texte import Texte

Moteur.demarrer = lambda self, signaler=None: None
Fenetre._moteur_en_echec = lambda self, *a: None
sortie = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("sortie_polices")
sortie.mkdir(parents=True, exist_ok=True)
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


app = QApplication(sys.argv)
# image : « DISCO » en Impact, rouge foncé sur blanc
img = QImage(700, 300, FORMAT_IMAGE)
img.fill(QColor(255, 255, 255))
p = QPainter(img)
f_ = QFont("Impact")
f_.setPixelSize(120)
p.setFont(f_)
p.setPen(QColor(150, 20, 20))
p.drawText(img.rect(), Qt.AlignCenter, "DISCO")
p.end()
img.save(str(sortie / "disco.png"))

toutes = ps.familles()
petite = [x for x in ("Impact", "Arial", "Times New Roman", "Comic Sans MS", "Consolas", "Georgia", "Verdana",
                      "Courier New", "Segoe UI", "Tahoma") if x in toutes]
verifier("Impact" in petite and len(petite) >= 5, f"polices de l'essai présentes ({len(petite)})")
ps.familles = lambda: petite

f = Fenetre()
f.resize(1200, 800)
f.show()
f.charger(str(sortie / "disco.png"))
app.processEvents()


def selectionner_lettres():
    a = tableau(f.doc.image.convertToFormat(FORMAT_IMAGE))
    lettres = ((a[:, :, :3].astype(int).sum(axis=2) < 500) * 255).astype(np.uint8)
    f.doc.selection = _masque_vers_selection(lettres)


choix = {"action": "creer", "texte": "DISCO"}


def faux_exec(self):
    self.texte.setText(choix["texte"])
    self.chercher()
    choix["resultats"] = [r.famille for r in self.resultats]
    self._finir(choix["action"])
    return self.result()


dialogue_polices.FenetrePolices.exec = faux_exec

# --- créer
selectionner_lettres()
n = len(f.doc.calques)
f.police_semblable()
app.processEvents()
verifier(choix["resultats"][:1] == ["Impact"], f"Impact trouvée en premier ({choix['resultats'][:3]})")
c = f.doc.calques[-1]
verifier(len(f.doc.calques) == n + 1 and c.texte is not None and c.texte.police == "Impact",
         "Créer : nouveau calque de texte en Impact")
verifier(c.texte is not None and c.texte.texte == "DISCO", "Créer : avec les lettres tapées")
coul = QColor(c.texte.couleur) if c.texte is not None else QColor()
verifier(coul.red() > 100 and coul.green() < 80, f"Créer : couleur des lettres reprise ({coul.name()})")
f.historique.undo()
verifier(len(f.doc.calques) == n, "Annuler retire le texte créé")

# --- appliquer : un texte en Arial devient Impact
t = Texte(texte="DISCO", police="Arial", taille=100.0, couleur="#ff000000", x=350, y=150)
f.historique.push(__import__("pixane.fenetre", fromlist=["CommandeEtat"]).CommandeEtat(
    f.doc, f.doc.etat(), f.doc.etat_nouveau_texte(t), "texte"))
selectionner_lettres()
choix["action"] = "appliquer"
n = len(f.doc.calques)
f.police_semblable()
app.processEvents()
c = f.doc.calque_actif
verifier(len(f.doc.calques) == n and c.texte is not None and c.texte.police == "Impact",
         "Appliquer : le texte choisi passe en Impact")
f.historique.undo()
verifier(f.doc.calque_actif.texte.police == "Arial", "Annuler remet Arial")
verifier(t.police == "Arial" and f.doc.calques[-1].texte is t,
         "changer de calque de texte ne lui donne pas la police du texte d'avant (aperçu du panneau Texte)")

# --- sélection pleine refusée
from PySide6.QtWidgets import QMessageBox
messages = []
QMessageBox.information = lambda *a, **k: messages.append(a[2])
plein = np.zeros((300, 700), np.uint8)
plein[100:200, 100:400] = 255
f.doc.selection = _masque_vers_selection(plein)
f.police_semblable()
verifier(len(messages) == 1 and "bloc plein" in messages[0], "sélection en bloc plein : message, pas de recherche")

# --- option (installateur / Affichage)
ps.fichier_memoire().parent.mkdir(parents=True, exist_ok=True)
ps.fichier_memoire().write_bytes(b"x")
f.a_option_polices.setChecked(False)
app.processEvents()
verifier(not f.a_police_semblable.isVisible() and f.b_police.isHidden(), "option décochée : menu et bouton cachés")
verifier(f.reglages.value("polices_semblables", True, type=bool) is False, "option décochée : réglage enregistré")
import time
fin = time.time() + 6                       # (fichier juste écrit : l'antivirus peut le tenir un instant)
while ps.fichier_memoire().exists() and time.time() < fin:
    app.processEvents()
    time.sleep(0.05)
verifier(not ps.fichier_memoire().exists(), "option décochée : mémoire des polices effacée")
f.a_option_polices.setChecked(True)
app.processEvents()
verifier(f.a_police_semblable.isVisible() and not f.b_police.isHidden(), "option recochée : menu et bouton revenus")
verifier(f.reglages.value("polices_semblables", False, type=bool) is True, "option recochée : réglage enregistré")
# réglage écrit par l'installateur (« false » en texte) lu au démarrage
f.reglages.setValue("polices_semblables", "false")
f.reglages.sync()
f.historique.setClean()
f._peut_fermer_tout = lambda: True
f.close()
f2 = Fenetre()
verifier(not f2.a_option_polices.isChecked() and not f2.a_police_semblable.isVisible(),
         "« false » écrit par l'installateur : option décochée au démarrage")
f2.reglages.remove("polices_semblables")
f2._peut_fermer_tout = lambda: True
f2.close()

print()
print("ÉCHECS :" if erreurs else "Tout est bon.", *erreurs, sep="\n  ")
sys.exit(1 if erreurs else 0)
