"""Orthographe (soulignement, suggestions, ajouter / ignorer), césure, langues (téléchargement simulé), option
Affichage > Orthographe et césure, Rechercher et remplacer dans les textes.
Usage : essai_orthographe.py dossier_sortie   (une image d'essai est fabriquée ; le moteur n'est pas démarré)"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"   # ne touche pas aux réglages de l'utilisateur
import time
import numpy as np
from PIL import Image
from PySide6.QtCore import QEvent, QPointF, Qt, QTimer
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication
from pixane.canevas import TEXTE
from pixane.fenetre import Fenetre
from pixane.moteur import Moteur

Moteur.demarrer = lambda self, signaler=None: (_ for _ in ()).throw(Exception("moteur désactivé pour l'essai"))
Fenetre._moteur_en_echec = lambda self, *a: None
sortie = Path(sys.argv[1])
sortie.mkdir(parents=True, exist_ok=True)
Image.fromarray(np.full((600, 1000, 3), 60, np.uint8)).save(sortie / "fond.png")

app = QApplication(sys.argv)
from pixane.fenetre import reglages
for cle in ("texte_defaut", "mots_perso", "orthographe", "orthographe_langues"):
    reglages().remove(cle)
from pixane import orthographe as o
from pixane.texte import Texte, _horizontal, forme
f = Fenetre()
f.resize(1440, 920)
f.show()
f.charger(str(sortie / "fond.png"))
app.processEvents()
doc, c, pt_ = f.doc, f.canevas, f.panneau_texte
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


def clic(x, y):
    e = c.vers_ecran(QPointF(x, y))
    c.event(QMouseEvent(QEvent.MouseButtonPress, e, e, Qt.LeftButton, Qt.LeftButton, Qt.NoModifier))
    c.event(QMouseEvent(QEvent.MouseButtonRelease, e, e, Qt.LeftButton, Qt.NoButton, Qt.NoModifier))


def attendre(cond, secondes=10):
    fin = time.time() + secondes
    while not cond() and time.time() < fin:
        app.processEvents()
        time.sleep(0.02)
    return cond()


def soulignes():
    """Mots soulignés dans la case du panneau : [(début, fin)]."""
    res = []
    bloc = pt_.saisie.document().begin()
    while bloc.isValid():
        for fr in bloc.layout().formats():
            if fr.format.underlineStyle() != 0:
                res.append((bloc.position() + fr.start, bloc.position() + fr.start + fr.length))
        bloc = bloc.next()
    return res


T = lambda: doc.calque_actif.texte

# 1. le module
verifier(o.disponible() and o.active(), "pyphen et spylls présents, option cochée par défaut")
verifier(o.langues_actives() == ["fr", "en"], f"langues : {o.langues_actives()}")
verifier(o.fautes("Bonjoure, l’éléphant est extraordinnaire aujourd'hui.", "fr") == [(0, 8), (25, 40)],
         "fautes trouvées (apostrophes comprises)")
verifier(o.suggestions("eleve", "fr")[:2] == ["élevé", "élève"] or "élève" in o.suggestions("eleve", "fr"),
         "suggestions : accents")
verifier("aujourd'hui" in o.suggestions("aujourdhui", "fr"), "suggestions : apostrophe")
verifier("la pomme" in o.suggestions("lapomme", "fr"), "suggestions : deux mots collés")
verifier("Maison" in o.suggestions("Maisonn", "fr"), "suggestions : majuscule gardée")
verifier("beautiful" in o.suggestions("beatiful", "en"), "anglais : beautiful")
verifier(o.couper("anticonstitutionnellement", "fr").count("­") >= 5, "césure française")

# 2. soulignement et clic droit dans le panneau
f._choisir_outil(TEXTE)
clic(500, 300)
pt_.saisie.selectAll()
pt_.saisie.insertPlainText("Une phrase avec bonjoure dedans")
verifier(attendre(lambda: soulignes() == [(16, 24)]), f"« bonjoure » souligné en rouge ({soulignes()})")
pt_._remplacer_mot((16, 24), "bonjour")
verifier(T().texte == "Une phrase avec bonjour dedans" and attendre(lambda: soulignes() == []),
         "suggestion choisie : mot remplacé, plus souligné")
pt_.saisie.selectAll()
pt_.saisie.insertPlainText("Signé chrypox")
verifier(attendre(lambda: soulignes() == [(6, 13)]), "nom propre inconnu souligné")
o.ajouter_mot("chrypox")
pt_.soulignement.rehighlight()
verifier(soulignes() == [] and "chrypox" in reglages().value("mots_perso", ""), "ajouté au dictionnaire (gardé)")
pt_.saisie.selectAll()
pt_.saisie.insertPlainText("Hello wrold")
pt_._choisir_liste(pt_.langue_texte, "en")
verifier(T().langue == "en" and attendre(lambda: soulignes() == [(6, 11)]), "texte en anglais : « wrold » souligné")
o.ignorer_mot("wrold")
pt_.soulignement.rehighlight()
verifier(soulignes() == [], "ignoré")

# 3. césure (texte en cadre)
pt_._choisir_liste(pt_.langue_texte, "fr")
pt_.saisie.selectAll()
pt_.saisie.insertPlainText("Une phrase extraordinairement longue et anticonstitutionnellement découpée.")
pt_.taille.setValue(30)
pt_.cadre.setChecked(True)
pt_.cadre_l.setValue(260)
verifier(pt_.cesure.isEnabled(), "case Césure active (texte en cadre)")
sans = len(_horizontal(T())[2])
lettres_sans = len(_horizontal(T())[0])
pt_.cesure.setChecked(True)
avec = _horizontal(T())
verifier(T().cesure and len(avec[0]) > lettres_sans, f"césure : tirets ajoutés en fin de ligne ({len(avec[0]) - lettres_sans})")
verifier(len(avec[2]) <= sans, "pas plus de lignes avec la césure")
t_styles = T().avec_style(11, 29, couleur="#ffff0000")
verifier(len([1 for l in _horizontal(t_styles)[0] if l.couleur == "#ffff0000"]) >= 18,
         "style par lettre gardé avec la césure")

# 4. option décochée
f.a_option_orthographe.setChecked(False)
verifier(not o.active() and not pt_.cesure.isEnabled() and soulignes() == [], "option décochée : rien souligné")
verifier(len(_horizontal(T())[0]) == lettres_sans, "option décochée : plus de césure")
pt_.saisie.selectAll()
pt_.saisie.insertPlainText("Bonjoure")
app.processEvents()
verifier(soulignes() == [], "option décochée : pas de soulignement")
f.a_option_orthographe.setChecked(True)
verifier(attendre(lambda: soulignes() == [(0, 8)]), "option recochée : souligné de nouveau")

# 5. langues : décocher, réinstaller (téléchargement simulé depuis les fichiers de Pixane)
o.choisir_langues(["fr"])
verifier(o.langues_actives() == ["fr"] and not o.verifiable("en"), "anglais décoché : plus vérifié")
import urllib.request


class FausseReponse:
    def __init__(self, donnees):
        self.donnees = donnees

    def read(self):
        return self.donnees

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


telecharges = []


def faux_urlopen(req, timeout=0):
    nom = req.full_url.rsplit("/", 1)[1]
    telecharges.append(req.full_url)
    return FausseReponse((o.DOSSIER / nom).read_bytes())


vrai_urlopen = urllib.request.urlopen
urllib.request.urlopen = faux_urlopen
o.installer_langue("en")
urllib.request.urlopen = vrai_urlopen
verifier(len(telecharges) == 3 and all(u.startswith("https://raw.githubusercontent.com/LibreOffice/dictionaries/")
                                       for u in telecharges), "téléchargement depuis les dictionnaires LibreOffice")
verifier(o.fichiers_langue("en").parent == o.dossier_perso(), "rangé dans le dossier perso (pas Program Files)")
o.choisir_langues(["fr", "en"])
verifier(o.verifiable("en") and o.correct("hello", "en"), "anglais recoché et utilisable")
o.retirer_langue("en")
verifier(o.fichiers_langue("en").parent == o.DOSSIER, "retiré : celui de l'installation reste")

# 6. rechercher et remplacer
pt_.saisie.selectAll()
pt_.saisie.insertPlainText("Le chat dort. Un chat noir.")
pt_.cadre.setChecked(False)
t1 = doc.actif
pt_.saisie.selectAll()
f._nouveau_texte(QPointF(300, 450))
pt_.saisie.selectAll()
pt_.saisie.insertPlainText("Chat perché, chatte")
t2 = doc.actif
f.rechercher_textes()
r = f._rechercher
r.cherche.setText("chat")
verifier(r.suivant() and r.position == (t1, 7), "Suivant : 1er « chat »")
verifier(pt_.saisie.textCursor().selectedText() == "chat" and doc.actif == t1, "le mot est sélectionné dans le panneau")
r.suivant()
verifier(r.position == (t1, 21), "Suivant : 2e")
r.suivant()
verifier(r.position == (t2, 4) and doc.actif == t2, "Suivant : dans l'autre texte (sans tenir compte des majuscules)")
r.mot.setChecked(True)
r.position = None
trouves = []
for _ in range(4):
    r.suivant()
    trouves.append(r.position)
verifier(trouves == [(t1, 7), (t1, 21), (t2, 4), (t1, 7)], f"mot entier : « chatte » ignoré, on repart du début ({trouves})")
r.par.setText("chien")
r.remplacer()
verifier(doc.calques[t1].texte.texte == "Le chien dort. Un chat noir.", "Remplacer")
from pixane.fenetre import CommandeEtat
st = doc.calques[t2].texte.avec_style(5, 11, couleur="#ff00ff00")
f.historique.push(CommandeEtat(doc, doc.etat(), doc.etat_texte_modifie(t2, st), "vert"))
n = f.historique.count()
r.mot.setChecked(False)
r.tout_remplacer()
verifier(doc.calques[t1].texte.texte == "Le chien dort. Un chien noir." and
         doc.calques[t2].texte.texte == "chien perché, chiente", "Tout remplacer (2 textes)")
verifier(f.historique.count() == n + 1, "une seule étape d'Annuler")
t = doc.calques[t2].texte
verifier(t.style_de(6)["couleur"] == "#ff00ff00" and t.style_de(0)["couleur"] != "#ff00ff00",
         "le style par lettre suit (« perché » toujours vert)")
f.historique.undo()
verifier(doc.calques[t1].texte.texte == "Le chien dort. Un chat noir.", "Annuler")
r.cherche.setText("introuvable")
verifier(not r.suivant() and "introuvable" in r.info.text(), "introuvable signalé")
r.close()

print("ERREURS :", erreurs if erreurs else "aucune")
doc.modifie = False
QTimer.singleShot(200, f.close)
app.exec()
os._exit(1 if erreurs else 0)
