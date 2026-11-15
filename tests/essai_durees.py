"""Durées des propositions mesurées sur le PC, et traducteur gardé ouvert.

- durees : texte de départ (RTX 3060 Ti), mesure notée par un vrai _lancer (moteur simulé), moyenne glissante, texte
  « mesuré sur ce PC » dans la fenêtre de consigne et dans le message de Restaurer.
- traduction : le traducteur est lancé à l'ouverture de la fenêtre de consigne, puis réutilisé (traduction rapide) ;
  il est arrêté à la fermeture de Pixane ; s'il meurt, la traduction se fait quand même (ancienne façon). Partie
  sautée si le traducteur n'est pas installé.
Usage : essai_durees.py dossier_sortie"""
import os
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
from PySide6.QtCore import QSettings, QTimer
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication, QLabel, QMessageBox
from pixane import durees, traduction
from pixane.consigne import DialogueConsigne
from pixane.document import Document
from pixane.fenetre import Fenetre
from pixane.moteur import Moteur

Moteur.demarrer = lambda self, signaler=None: (_ for _ in ()).throw(Exception("moteur désactivé pour l'essai"))
Fenetre._moteur_en_echec = lambda self, *a: None
sortie = Path(sys.argv[1])
sortie.mkdir(parents=True, exist_ok=True)
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


r = QSettings("Pixane", "Pixane-essais")
for c in ("creer", "kontext"):
    r.remove(f"duree_{c}")

# --- textes
verifier(durees.lisible(28) == "30 secondes", f"28 s -> {durees.lisible(28)}")
verifier(durees.lisible(62) == "1 minute", f"62 s -> {durees.lisible(62)}")
verifier(durees.lisible(150) == "2 minutes 30", f"150 s -> {durees.lisible(150)}")
verifier(durees.lisible(2) == "5 secondes", f"2 s -> {durees.lisible(2)}")
t = durees.texte("creer")
verifier("RTX 3060 Ti" in t and "30 secondes" in t, f"sans mesure : {t}")
verifier("2 minutes 30" in durees.texte("kontext"), "Kontext sans mesure : 2 min 30")
durees.noter("creer", 0.1)
verifier(durees.mesure("creer") is None, "mesure absurde ignorée")
durees.noter("creer", 20)
verifier(durees.mesure("creer") == 20, "première mesure retenue telle quelle")
durees.noter("creer", 40)
verifier(abs(durees.mesure("creer") - 28) < 0.01, f"moyenne glissante : {durees.mesure('creer')}")
verifier("mesuré sur ce PC" in durees.texte("creer") and "30 secondes" in durees.texte("creer"),
         durees.texte("creer"))
r.remove("duree_creer")

app = QApplication.instance() or QApplication(sys.argv)
f = Fenetre()
f.show()
img = QImage(400, 300, QImage.Format_ARGB32_Premultiplied)
img.fill(QColor(90, 140, 200))
f._installer_document(Document(img))
f._actualiser()


# --- mesure par un vrai _lancer (moteur simulé : 2 propositions en 1,4 s)
def executer(self, prompt, sorties, annuler, progres, morceaux=1):
    time.sleep(1.4)
    q = QImage(400, 300, QImage.Format_ARGB32_Premultiplied)
    q.fill(QColor(200, 50, 50))
    from PySide6.QtCore import QBuffer
    b = QBuffer()
    b.open(QBuffer.WriteOnly)
    q.save(b, "PNG")
    return [("1", bytes(b.data())), ("2", bytes(b.data()))]


Moteur.envoyer_image = lambda self, png: "image.png"
Moteur.executer = executer
from pixane import dialogues
dialogues.ChoixResultat.exec = lambda self: 0
f._lancer("Essai", False, lambda nom: ({}, []), duree="kontext")
fin = time.monotonic() + 10
while durees.mesure("kontext") is None and time.monotonic() < fin:
    app.processEvents()
    time.sleep(0.02)
m = durees.mesure("kontext")
verifier(m is not None and 0.5 <= m < 2, f"durée notée par _lancer : {m} s par proposition (0,7 attendu)")

# fenêtre de consigne : le texte mesuré
durees.noter("kontext", 95)
d = DialogueConsigne(f, nb=2)
textes = [l.text() for l in d.findChildren(QLabel)]
verifier(any("mesuré sur ce PC" in x for x in textes), "fenêtre de consigne : durée mesurée affichée")
d.grab().save(str(sortie / "consigne.png"))
d.reject()

# message de Restaurer
vu = []


def regarder():
    for w in app.topLevelWidgets():
        if isinstance(w, QMessageBox) and w.isVisible():
            vu.append(w.text())
            w.reject()


import pixane.recettes as rc
rc.restauration_disponible = lambda: True
QTimer.singleShot(300, regarder)
f.ia_restaurer()
verifier(vu and "mesuré sur ce PC" in vu[0], f"Restaurer : {vu[0][-80:] if vu else 'pas de message'}")
for c in ("creer", "kontext"):
    r.remove(f"duree_{c}")

# --- traducteur gardé ouvert (dossier des vrais réglages, lu seulement, s'il y en a un)
vrai = QSettings("Pixane", "Pixane").value("traducteur_dossier", "")
traduction.choisir_dossier(vrai or None)
if not traduction.installe():
    print("(traducteur pas installé : partie sautée)")
else:
    traduction.arreter()
    d = DialogueConsigne(f, nb=2)
    s = traduction._serveur
    verifier(s is not None and s["proc"].poll() is None, "traducteur lancé à l'ouverture de la fenêtre de consigne")
    d.texte.setPlainText("Remplace le ciel par un coucher de soleil")
    t0 = time.monotonic()
    ok = d.traduire()
    t1 = time.monotonic() - t0
    verifier(ok and "sunset" in d.anglais.toPlainText().lower(), f"traduit : {d.anglais.toPlainText()!r}")
    d.texte.setPlainText("Mets le texte « BONJOUR » en rouge")
    t0 = time.monotonic()
    d.traduire()
    t2 = time.monotonic() - t0
    verifier(t2 < 3, f"deuxième traduction rapide : {t2:.2f} s (première {t1:.1f} s)")
    verifier('"BONJOUR"' in d.anglais.toPlainText(), f"guillemets gardés : {d.anglais.toPlainText()!r}")
    d.reject()
    # le traducteur meurt : la traduction marche quand même
    traduction._serveur["proc"].kill()
    traduction._serveur["proc"].wait()
    res = traduction.traduire("Rends le fond flou")
    verifier("blur" in res.lower(), f"après la mort du traducteur : {res!r}")
    proc = traduction._serveur["proc"] if traduction._serveur else None
    f.close()
    verifier(traduction._serveur is None and (proc is None or proc.poll() is not None),
             "traducteur arrêté à la fermeture de Pixane")

f.close()
print("RÉSULTAT :", "OK" if not erreurs else f"{len(erreurs)} échec(s)")
sys.stdout.flush()
sys.exit(1 if erreurs else 0)        # (os._exit plante après le traducteur, pas la sortie normale)
