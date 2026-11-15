"""Masques de calque, modes de fusion, calques de réglage, groupes : calcul de l'image, déplacements, fichiers .pixane /
.ora / .psd. Sans fenêtre (sauf QApplication pour les images).
Usage : essai_composition.py dossier_sortie"""
import os
import sys
from dataclasses import replace
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PySide6.QtWidgets import QApplication

from pixane import ajustements
from pixane.composition import MODES, masque_depuis, masque_tableau
from pixane.document import FORMAT_CALQUE, FORMAT_IMAGE, Calque, Document, qimage_rgba, tableau

app = QApplication(sys.argv)
sortie = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
sortie.mkdir(parents=True, exist_ok=True)
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


def uni(w, h, rgba):
    a = np.zeros((h, w, 4), np.uint8)
    a[:] = rgba
    return qimage_rgba(a).convertToFormat(FORMAT_CALQUE)


def px(doc, x, y):
    return tuple(int(v) for v in tableau(doc.image.convertToFormat(FORMAT_IMAGE))[y, x])


W, H = 200, 100
fond = Calque("fond", uni(W, H, (200, 100, 50, 255)))
dessus = Calque("dessus", uni(W, H, (100, 100, 100, 255)))

# --- modes de fusion
doc = Document(calques=[fond, replace(dessus, mode="produit")])
r = px(doc, 10, 10)
verifier(abs(r[0] - 200 * 100 // 255) <= 1 and abs(r[2] - 50 * 100 // 255) <= 1, f"Produit : {r[:3]}")
doc = Document(calques=[fond, replace(dessus, mode="ecran")])
r = px(doc, 10, 10)
verifier(abs(r[0] - (255 - (55 * 155) // 255)) <= 1, f"Superposition (écran) : {r[:3]}")
for mode in MODES:
    d = Document(calques=[fond, replace(dessus, mode=mode)])
    _ = d.image
verifier(True, f"les {len(MODES)} modes se calculent")
doc = Document(calques=[fond, replace(Calque("bleu", uni(W, H, (40, 80, 220, 255))), mode="couleur")])
r = px(doc, 10, 10)
l0 = 0.3 * 200 + 0.59 * 100 + 0.11 * 50
l1 = 0.3 * r[0] + 0.59 * r[1] + 0.11 * r[2]
verifier(abs(l0 - l1) < 3 and r[2] > r[0], f"Couleur : garde la luminosité du dessous, teinte du dessus {r[:3]}")
doc = Document(calques=[fond, replace(dessus, mode="produit", opacite=0.5)])
r = px(doc, 10, 10)
verifier(abs(r[0] - (200 + 78) / 2) <= 2, f"Produit à 50 % : {r[:3]}")

# --- masque
m = np.zeros((H, W), np.uint8)
m[:, 100:] = 255
doc = Document(calques=[fond, replace(dessus, masque=masque_depuis(m))])
verifier(px(doc, 10, 10)[:3] == (200, 100, 50) and px(doc, 150, 10)[:3] == (100, 100, 100),
         "masque : noir cache, blanc montre")
doc.appliquer_etat(doc.etat_calque_modifie(1, masque_actif=False))
verifier(px(doc, 10, 10)[:3] == (100, 100, 100), "masque désactivé : tout se voit")
doc.appliquer_etat(doc.etat_calque_modifie(1, masque_actif=True))
doc.actif = 1
doc.appliquer_etat(doc.etat_appliquer_masque())
verifier(doc.calques[1].masque is None and px(doc, 10, 10)[:3] == (200, 100, 50)
         and tableau(doc.calques[1].image.convertToFormat(FORMAT_IMAGE))[10, 10, 3] == 0,
         "appliquer le masque : dans les pixels, même aspect")
doc = Document(calques=[fond, dessus])
doc.selection.fill(0)
doc.tout_selectionner()
doc.actif = 1
doc.appliquer_etat(doc.etat_ajouter_masque("cacher_selection"))
verifier(px(doc, 10, 10)[:3] == (200, 100, 50), "masque « cacher la sélection »")
doc.appliquer_etat(doc.etat_recadre(__import__("PySide6.QtCore", fromlist=["QRect"]).QRect(50, 0, 100, 50)))
verifier(doc.calques[1].masque.width() == 100 and doc.calques[1].masque.height() == 50, "recadrer : le masque suit")
doc.appliquer_etat(doc.etat_pivote(90))
verifier(doc.calques[1].masque.width() == 50 and doc.calques[1].masque.height() == 100, "pivoter : le masque suit")
doc.appliquer_etat(doc.etat_taille(25, 50))
verifier(doc.calques[1].masque.width() == 25, "taille de l'image : le masque suit")

# --- calques de réglage
p = ajustements.defaut("niveaux")
p["rvb"] = [0, 1.0, 200, 0, 255]
doc = Document(calques=[fond])
doc.appliquer_etat(doc.etat_nouveau_reglage("niveaux", p, "Niveaux"))
r = px(doc, 10, 10)
verifier(len(doc.calques) == 2 and r[0] == 255 and abs(r[1] - 128) <= 1, f"calque de réglage Niveaux : {r[:3]}")
doc.appliquer_etat(doc.etat_calque_modifie(1, opacite=0.5))
r = px(doc, 10, 10)
verifier(abs(r[0] - 228) <= 1, f"réglage à 50 % : {r[:3]}")
for t in ajustements.TYPES:
    a = ajustements.appliquer(np.array([[[200, 100, 50], [10, 200, 30]]], np.uint8), t, ajustements.defaut(t))
    if ajustements.neutre(t, ajustements.defaut(t)):       # (noir et blanc, négatif, seuil… changent toujours)
        verifier(np.array_equal(a, [[[200, 100, 50], [10, 200, 30]]]), f"réglage « {t} » neutre ne change rien")
    elif t == "noir_blanc":
        verifier(a[0, 0, 0] == a[0, 0, 1] == a[0, 0, 2], "noir et blanc : gris")
c = ajustements.table_courbe([[0, 0], [128, 180], [255, 255]])
verifier(c[128] == 180 and c[0] == 0 and c[255] == 255 and np.all(np.diff(c.astype(int)) >= 0),
         "courbe : passe par les points, monte toujours")
b = ajustements.defaut("balance")
b["moyens"] = [60, 0, 0]
a = ajustements.appliquer(np.array([[[120, 120, 120]]], np.uint8), "balance", b)
verifier(a[0, 0, 0] > 130 and a[0, 0, 2] < 120, f"balance : tons moyens vers le rouge {a[0, 0]}")
v = ajustements.appliquer(np.array([[[130, 120, 110], [250, 0, 0]]], np.uint8), "vibrance",
                          {"vibrance": 80, "saturation": 0})
verifier((v[0, 0, 0] - v[0, 0, 2]) > 30 and v[0, 1, 0] >= 250, f"vibrance : terne ravivé, vif presque pareil {v[0].tolist()}")

# --- groupes
rouge = Calque("rouge", uni(W, H, (255, 0, 0, 255)))
doc = Document(calques=[fond, rouge])
doc.actif = 1
doc.appliquer_etat(doc.etat_grouper())
verifier(doc.calques[2].groupe and doc.calques[1].dans == doc.calques[2].ident and doc.actif == 2,
         "Grouper : en-tête au-dessus, calque dedans")
doc.appliquer_etat(doc.etat_calque_modifie(2, visible=False))
verifier(px(doc, 10, 10)[:3] == (200, 100, 50), "groupe masqué : ses calques aussi")
doc.appliquer_etat(doc.etat_calque_modifie(2, visible=True, opacite=0.5))
r = px(doc, 10, 10)
verifier(abs(r[0] - 228) <= 1 and abs(r[1] - 50) <= 1, f"opacité du groupe : {r[:3]}")
# réglage dans le groupe : ne touche que le groupe
doc.appliquer_etat(doc.etat_calque_modifie(2, opacite=1.0))
doc.actif = 1
nb = ajustements.defaut("noir_blanc")
doc.appliquer_etat(doc.etat_nouveau_reglage("noir_blanc", nb, "N&B"))
verifier(doc.calques[2].dans == doc.calques[3].ident and doc.calques[2].reglage, "réglage créé dans le groupe")
r = px(doc, 10, 10)
verifier(r[0] == r[1] == r[2], f"réglage dans le groupe : rouge devenu gris {r[:3]}")
doc.appliquer_etat(doc.etat_calque_modifie(1, visible=False))
verifier(px(doc, 10, 10)[:3] == (200, 100, 50), "le réglage du groupe ne touche pas le fond (hors du groupe)")
doc.appliquer_etat(doc.etat_calque_modifie(1, visible=True))
# déplacer : sortir du groupe par le haut, y rentrer
doc.actif = 2
doc.appliquer_etat(doc.etat_deplacer(2, 3))
verifier(doc.calques[3].reglage and doc.calques[3].dans is None and doc.calques[2].groupe,
         "monter le réglage en haut du groupe : il en sort")
r = px(doc, 10, 10)
verifier(r[0] == r[1] == r[2], "hors du groupe, le réglage touche tout")
doc.appliquer_etat(doc.etat_deplacer(3, 2))
verifier(doc.calques[2].reglage and doc.calques[2].dans == doc.calques[3].ident, "redescendre : il rentre dans le groupe")
# déplacer le groupe entier sous le fond
doc.actif = 3
doc.appliquer_etat(doc.etat_deplacer(3, 2))
verifier([c.nom for c in doc.calques][-1] == "fond" and doc.calques[2].groupe, "un groupe bouge avec ses calques")
doc.actif = 2
doc.appliquer_etat(doc.etat_dupliquer())
verifier(len(doc.calques) == 7 and doc.calques[5].groupe and doc.calques[5].ident != doc.calques[2].ident
         and doc.calques[3].dans == doc.calques[5].ident, "dupliquer un groupe : copie complète, à part")
doc.actif = 5
doc.appliquer_etat(doc.etat_supprimer())
verifier(len(doc.calques) == 4, "supprimer un groupe : ses calques partent avec")
doc.actif = 2
doc.appliquer_etat(doc.etat_degrouper())
verifier(len(doc.calques) == 3 and all(c.dans is None for c in doc.calques), "dégrouper")

# --- fichiers
doc = Document(calques=[fond, rouge])
doc.actif = 1
doc.appliquer_etat(doc.etat_grouper())
doc.actif = 1
doc.appliquer_etat(doc.etat_calque_modifie(1, masque=masque_depuis(m), mode="produit"))
doc.actif = 2
doc.appliquer_etat(doc.etat_nouveau_reglage("vibrance", {"vibrance": 40, "saturation": 10}, "Vibrance"))
doc.appliquer_etat(doc.etat_calque_modifie(2, mode="ecran", opacite=0.8))
attendu = tableau(doc.image.convertToFormat(FORMAT_IMAGE))
doc.enregistrer(sortie / "essai.pixane")
d2 = Document.ouvrir(sortie / "essai.pixane")
verifier([(c.nom, c.groupe, c.reglage is not None, c.masque is not None, c.mode) for c in d2.calques]
         == [(c.nom, c.groupe, c.reglage is not None, c.masque is not None, c.mode) for c in doc.calques],
         ".pixane : groupes, masques, réglages et modes relus")
verifier(np.abs(tableau(d2.image.convertToFormat(FORMAT_IMAGE)).astype(int) - attendu).max() <= 1, ".pixane : même image")
doc.enregistrer(sortie / "essai.ora")
d3 = Document.ouvrir(sortie / "essai.ora")
verifier(any(c.groupe for c in d3.calques) and all(c.masque is None and c.reglage is None for c in d3.calques),
         ".ora : groupes gardés, masques et réglages mis dans les pixels")
verifier(np.abs(tableau(d3.image.convertToFormat(FORMAT_IMAGE)).astype(int) - attendu).max() <= 2, ".ora : même image")
doc.enregistrer(sortie / "essai.psd")
d4 = Document.ouvrir(sortie / "essai.psd")
verifier(any(c.groupe for c in d4.calques) and any(c.masque is not None for c in d4.calques)
         and any(c.mode == "produit" for c in d4.calques), ".psd : groupes, masques et modes relus")
diff = np.abs(tableau(d4.image.convertToFormat(FORMAT_IMAGE)).astype(int) - attendu).max()
verifier(diff <= 2, f".psd : même image (écart {diff})")
print("ERREURS :", erreurs if erreurs else "aucune")
sys.exit(1 if erreurs else 0)
