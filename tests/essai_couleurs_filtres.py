"""Nouveaux réglages (filtre photo, mélangeur de couches, courbe de transfert de dégradé, seuil, postérisation,
négatif), Remplacer la couleur, Plage de couleurs, flous radial / objectif / surface.
Usage : essai_couleurs_filtres.py dossier_sortie   (une image d'essai est fabriquée ; le moteur n'est pas démarré)"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PIL import Image
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QDialog
from pixane.fenetre import Fenetre
from pixane.moteur import Moteur

Moteur.demarrer = lambda self, signaler=None: (_ for _ in ()).throw(Exception("moteur désactivé pour l'essai"))
Fenetre._moteur_en_echec = lambda self, *a: None
sortie = Path(sys.argv[1])
sortie.mkdir(parents=True, exist_ok=True)
# image : moitié gauche rouge (avec un dégradé de clarté), moitié droite bleue, un carré vert au milieu
img = np.zeros((300, 400, 3), np.uint8)
ombre = np.linspace(0.6, 1.0, 300)[:, None]
img[:, :200] = (np.array([200, 30, 30])[None, None] * ombre[..., None]).astype(np.uint8)
img[:, 200:] = (30, 60, 200)
img[120:180, 170:230] = (40, 190, 60)
Image.fromarray(img).save(sortie / "couleurs.png")

app = QApplication(sys.argv)
from pixane import ajustements as A, filtres as F, plage_couleurs as pc
from pixane.document import FORMAT_IMAGE, masque, tableau
from pixane.dialogues_reglage import PANNEAUX
from pixane.actions_calques import REGLAGES_PIXELS
f = Fenetre()
f.resize(1440, 920)
f.show()
f.charger(str(sortie / "couleurs.png"))
app.processEvents()
doc = f.doc
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


def pixels():
    return tableau(doc.image.convertToFormat(FORMAT_IMAGE))


# 1. réglages : calculs
rgb = np.array([[[0, 0, 0], [255, 255, 255], [200, 100, 50], [30, 60, 90]]], np.uint8)
verifier(A.appliquer(rgb, "seuil", {"seuil": 100}).tolist() == [[[0] * 3, [255] * 3, [255] * 3, [0] * 3]], "Seuil")
verifier(A.appliquer(rgb, "negatif", {}).tolist()[0][2] == [55, 155, 205], "Négatif")
verifier(len(np.unique(A.appliquer(np.arange(256, dtype=np.uint8).repeat(3).reshape(1, 256, 3), "posterisation",
                                   {"niveaux": 4}))) == 4, "Postérisation : 4 niveaux")
m = A.defaut("mappe")
m["degrade"]["couleurs"][0]["couleur"], m["degrade"]["couleurs"][1]["couleur"] = "#ff0000", "#ffff00"
r = A.appliquer(rgb, "mappe", m)
verifier(r[0, 0].tolist() == [255, 0, 0] and r[0, 1].tolist() == [255, 255, 0], "Courbe de transfert : noir -> rouge, blanc -> jaune")
verifier(A.appliquer(rgb, "mappe", dict(m, inverser=True))[0, 0].tolist() == [255, 255, 0], "Courbe de transfert inversée")
fp = A.appliquer(rgb, "filtre_photo", {"couleur": "#ec8a00", "densite": 60, "luminosite": True})
verifier(fp[0, 3, 0] > rgb[0, 3, 0] and fp[0, 3, 2] < rgb[0, 3, 2], "Filtre photo réchauffant : plus de rouge, moins de bleu")
mel = A.defaut("melangeur")
mel["rouge"] = [0, 0, 100, 0]
verifier(A.appliquer(rgb, "melangeur", mel)[0, 2].tolist() == [50, 100, 50], "Mélangeur : le bleu va dans le rouge")
verifier(A.appliquer(rgb, "melangeur", dict(A.defaut("melangeur"), monochrome=True))[0, 2].tolist() == [130] * 3,
         "Mélangeur monochrome : gris 40/40/20")
verifier(A.neutre("melangeur", A.defaut("melangeur")) and A.neutre("filtre_photo", dict(A.defaut("filtre_photo"), densite=0)),
         "réglages neutres reconnus")

# 2. fenêtres de tous les réglages
for t in A.TYPES:
    p = PANNEAUX[t](A.defaut(t), {})
    verifier(p.params() == A.defaut(t), f"fenêtre « {A.nom(t)} »")
    p.deleteLater()
verifier(all(hasattr(f, f"a_regl_{t}") and getattr(f, f"a_regl_{t}").isEnabled() for t in REGLAGES_PIXELS)
         and f.a_regl_negatif.shortcut().toString() == "Ctrl+I", "menu Image > Réglages (Négatif : Ctrl+I)")

# 3. calques de réglage avec les nouveaux types
from pixane.fenetre import CommandeEtat
avant = pixels()
for t in ("negatif", "seuil", "mappe", "filtre_photo", "melangeur", "posterisation"):
    etat = doc.etat_nouveau_reglage(t, A.defaut(t), A.nom(t))
    f.historique.push(CommandeEtat(doc, doc.etat(), etat, A.nom(t)))
    apres = pixels()
    if t == "negatif":
        verifier(np.abs(apres[..., :3].astype(int) - (255 - avant[..., :3])).max() <= 1, "calque de réglage Négatif")
    f.historique.undo()
verifier(np.array_equal(pixels(), avant), "calques de réglage annulés : image d'origine")

# 4. Remplacer la couleur
t = tableau(doc.calque_actif.image.convertToFormat(FORMAT_IMAGE))
p = dict(pc.defaut_remplacer(), couleurs=[pc.echantillon(t, 50, 250)], teinte=120, tolerance=60)
r = pc.remplacer_couleur(t, p)
verifier(r[250, 50, 1] > r[250, 50, 0] and r[250, 50, 2] < 60, "rouge -> vert (teinte +120°)")
r2 = pc.remplacer_couleur(t, dict(p, tolerance=110))
verifier(r[30, 50, 1] < r2[30, 50, 1] and r2[30, 50, 1] > r2[30, 50, 0],
         "partie rouge plus sombre : changée en montant la tolérance")
verifier(np.array_equal(r[:, 250:], t[:, 250:]) and np.array_equal(r[150, 200], t[150, 200]), "bleu et vert intacts")
c = pc.changer_couleur(np.array([[[200, 30, 30]]], np.uint8), 0, 0, 0)
verifier(np.abs(c - [200, 30, 30]).max() < 0.6, "aller-retour TSV sans perte")


def piloter_remplacer():
    d = next(w for w in app.topLevelWidgets() if isinstance(w, QDialog) and w.isVisible())
    pan = d.panneau
    pan.choix.apercu.clic.emit(50, 250, Qt.NoModifier)
    pan.c["teinte"].definir(120)
    pan._lire()
    d.accept()


QTimer.singleShot(300, piloter_remplacer)
n = f.historique.index()
f.remplacer_couleur()
px = pixels()
verifier(f.historique.index() == n + 1 and px[250, 50, 1] > px[250, 50, 0] and px[150, 300, 2] > 150,
         "Image > Réglages > Remplacer la couleur (clic dans l'aperçu)")
f.historique.undo()

# 5. Plage de couleurs
t = pixels()
m = pc.masque_couleurs(t, {"couleurs": [pc.echantillon(t, 300, 50)], "tolerance": 40})
verifier(m[50, 300] == 255 and m[50, 50] == 0 and m[150, 200] == 0, "masque : le bleu seulement")
m2 = pc.masque_couleurs(t, {"couleurs": [pc.echantillon(t, 300, 50)], "tolerance": 40, "inverser": True})
verifier(m2[50, 300] == 0 and m2[50, 50] == 255, "Inverser")
m3 = pc.masque_couleurs(t, {"couleurs": [pc.echantillon(t, 300, 50), pc.echantillon(t, 200, 150)], "tolerance": 40,
                            "retirees": [pc.echantillon(t, 200, 150)]})
verifier(m3[150, 200] == 0 and m3[50, 300] == 255, "couleur retirée (Alt+clic)")
apercus = []


def piloter_plage():
    d = next(w for w in app.topLevelWidgets() if isinstance(w, QDialog) and w.isVisible())
    verifier(not d.b_ok.isEnabled(), "Sélectionner grisé tant qu'aucune couleur n'est choisie")
    d.choix.apercu.clic.emit(300, 50, Qt.NoModifier)
    d.choix.apercu.clic.emit(200, 150, Qt.ShiftModifier)

    def fin():
        apercus.append(f.canevas.apercu_selection is not None)
        d.accept()
    QTimer.singleShot(400, fin)


QTimer.singleShot(300, piloter_plage)
f.plage_couleurs()
sel = masque(doc.selection)
verifier(apercus == [True], "aperçu de la sélection sur la photo pendant le réglage")
verifier(sel[50, 300] == 255 and sel[150, 200] == 255 and sel[250, 50] == 0, "Sélection > Plage de couleurs : bleu + vert")
f.historique.undo()
verifier(doc.selection_vide(), "Annuler : plus de sélection")

# 6. flous
t = pixels()
for k in ("radial", "objectif", "surface"):
    p = F.defauts(k)
    r = F.FONCTIONS[k](t, p)
    verifier(r.shape == t.shape and r[..., 3].min() == 255 and not np.array_equal(r, t), f"flou « {F.noms()[k]} »")
p = dict(F.defauts("radial"), zoom=0)
r = F.flou_radial(t, p)
verifier(r[..., :3].reshape(-1, 3).min(axis=0).max() > 10 and r[5, 5, :3].sum() > 60, "flou en rotation : pas de coins noirs")
verifier(np.abs(r[150, 200].astype(int) - t[150, 200]).max() < 30, "flou radial : le centre reste net")
s = F.flou_surface(t, {"rayon": 8, "seuil": 18})
verifier(np.abs(s[150, 168].astype(int) - t[150, 168]).max() < 25, "flou de surface : les bords restent nets")
from pixane.dialogues_reglage import PanneauFiltre
pf = PanneauFiltre("radial", F.defauts("radial"), {})
verifier(pf.params()["zoom"] == 1 and pf.c["zoom"].l.count() == 2, "Méthode du flou radial : liste Rotation / Zoom")

print("ERREURS :", erreurs if erreurs else "aucune")
doc.modifie = False
QTimer.singleShot(200, f.close)
app.exec()
os._exit(1 if erreurs else 0)
