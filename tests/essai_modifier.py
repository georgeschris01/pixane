"""Modifier avec une consigne (Kontext) : zone de travail autour de la sélection, calque transparent vu seul sur un fond
uni, résultat recollé seulement dans la sélection et là où il change, transparence retrouvée ; image opaque :
résultat opaque. L'IA est simulée (résultat fabriqué). Usage : essai_modifier.py"""
import io
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PIL import Image
from PySide6.QtWidgets import QApplication

from pixane import modifier_ia as mi
from pixane.document import FORMAT_IMAGE, Calque, Document, qimage_rgb, qimage_rgba, tableau

erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


app = QApplication(sys.argv)
W, H = 900, 700
or_ = [250, 215, 110]
texte = np.zeros((H, W, 4), np.uint8)
texte[80:160, 100:800] = or_ + [255]          # « Juliette Armanet » (ligne du haut)
texte[450:530, 150:700] = or_ + [255]         # « Brûler le feu » (ligne à remplacer)
texte[450:530, 150:152, 3] = 128              # un bord adouci
sel = np.zeros((H, W), np.uint8)
sel[420:560, 120:740] = 255

# ---- zone de travail
x, y, l, h = mi.rect_de_travail(sel, W, H)
verifier(x <= 120 - 48 and y <= 420 - 48 and x + l >= 740 + 48 and y + h >= 560 + 48 and l >= 512 and h >= 512
         and x >= 0 and y >= 0 and x + l <= W and y + h <= H, f"zone de travail autour de la sélection {x, y, l, h}")
verifier(mi.rect_de_travail(None, W, H) == (0, 0, W, H), "sans sélection : toute l'image")
petit = np.zeros((H, W), np.uint8)
petit[10:20, 880:895] = 255
x2, y2, l2, h2 = mi.rect_de_travail(petit, W, H)
verifier(l2 >= 512 and h2 >= 512 and x2 + l2 <= W and y2 == 0, f"petite sélection au bord : 512 px, dans l'image {x2, y2, l2, h2}")

# ---- calque transparent (texte sans fond)
doc = Document(calques=[Calque("Texte", qimage_rgba(texte))])
doc.actif = 0
prep = mi.preparer(doc, sel)
verifier(prep.transparent and prep.cible == 0 and prep.fond == 0, "texte doré sans fond : vu seul, sur du noir")
envoye = np.asarray(Image.open(io.BytesIO(prep.png)).convert("RGB"))
verifier(envoye.shape[:2] == (prep.rect[3], prep.rect[2]) and envoye[0, 0].max() == 0,
         "l'IA reçoit le morceau, fond noir uni")
# résultat simulé de l'IA : ancien mot enlevé, nouveau mot plus court, et de petits écarts partout (compression)
x, y, l, h = prep.rect
ia = envoye.astype(np.int16).copy()
ia[450 - y:530 - y, 150 - x:700 - x] = 0
ia[460 - y:520 - y, 200 - x:500 - x] = or_
bruit = np.random.default_rng(1).integers(-5, 6, ia.shape)
ia = np.clip(ia + bruit, 0, 255).astype(np.uint8)
complet = mi.image_complete(prep, qimage_rgb(ia))
verifier(complet.width() == W and complet.height() == H, "résultat remis dans l'image entière")
nouveau = mi.pose(prep, complet)
verifier((nouveau[460:520, 200:500, 3] > 240).all() and np.abs(nouveau[490, 300, :3].astype(int) - or_).max() <= 8,
         "nouveau mot : opaque, couleur gardée")
verifier((nouveau[455:528, 520:690, 3] < 10).all(), "ancien mot enlevé : redevenu transparent")
verifier(np.array_equal(nouveau[80:160, 100:800], texte[80:160, 100:800]),
         "ligne du haut (hors sélection) : pixels d'origine exacts")
dedans_inchange = nouveau[425:445, 300:600]
verifier(np.array_equal(dedans_inchange, texte[425:445, 300:600]),
         "dans la sélection, là où rien ne change : pixels d'origine (petits écarts de l'IA ignorés)")
verifier((nouveau[600:700, :, 3] == 0).all(), "le fond reste transparent")
v = mi.vue(prep, complet, tableau(doc.image.convertToFormat(FORMAT_IMAGE)))
verifier(tableau(v.convertToFormat(FORMAT_IMAGE))[650, 450, 3] == 0, "fenêtre de choix : montré avec la transparence")
calques, actif, _ = mi.etat(doc, prep, complet, "Modifier")
verifier(len(calques) == 1 and tableau(calques[0].image.convertToFormat(FORMAT_IMAGE))[490, 300, 3] > 240,
         "posé dans le calque du texte")

# ---- photo opaque : résultat opaque, posé dans le calque
photo = np.zeros((H, W, 4), np.uint8)
photo[..., :3] = np.linspace(40, 200, W, dtype=np.uint8)[None, :, None]
photo[..., 3] = 255
doc2 = Document(calques=[Calque("Photo", qimage_rgba(photo))])
doc2.actif = 0
p2 = mi.preparer(doc2, sel)
verifier(not p2.transparent and p2.cible == 0, "photo : image visible, résultat opaque")
x, y, l, h = p2.rect
ia2 = np.asarray(Image.open(io.BytesIO(p2.png)).convert("RGB")).copy()
ia2[470 - y:510 - y, 300 - x:400 - x] = [200, 30, 30]           # objet devenu rouge
n2 = mi.pose(p2, mi.image_complete(p2, qimage_rgb(ia2)))
verifier((n2[..., 3] == 255).all() and np.abs(n2[490, 350, :3].astype(int) - [200, 30, 30]).max() <= 2
         and np.array_equal(n2[:400], photo[:400]), "photo : changement posé, le reste intact, tout opaque")
# plusieurs calques visibles, sélection : la photo du dessous n'est pas copiée dans le calque du dessus
doc3 = Document(calques=[Calque("Photo", qimage_rgba(photo)), Calque("Texte", qimage_rgba(texte))])
doc3.actif = 1
p3 = mi.preparer(doc3, sel)
verifier(p3.transparent and p3.cible == 1, "texte sur une photo : le calque du texte seul")

# ---- guillemets : jamais traduits
from pixane import traduction as trd  # noqa: E402
p, m = trd.proteger("Remplace le texte « brûler le feu » par \"Flamme\"")
verifier(m == ["brûler le feu", "Flamme"] and "brûler" not in p and "Q0Q" in p and "Q1Q" in p,
         f"guillemets protégés avant la traduction ({p})")
verifier(trd.remettre("Replace the text Q0Q with Q1Q", m) == 'Replace the text "brûler le feu" with "Flamme"',
         "guillemets remis tels quels")
verifier(trd.remettre("Replace the text \"Q0Q\" with Q1Q", m) == 'Replace the text "brûler le feu" with "Flamme"',
         "repère déjà entre guillemets : pas de guillemets doublés")
verifier(trd.remettre("Replace the text", m).endswith('"brûler le feu" "Flamme"'), "repère perdu : remis à la fin")
verifier(trd.guillemets_droits("le texte « Flamme »") == 'le texte "Flamme"', "« » -> guillemets droits pour l'IA")

# ---- dans Pixane
from PySide6.QtCore import QSettings  # noqa: E402
from pixane import recettes  # noqa: E402
from pixane.consigne import DialogueConsigne  # noqa: E402
from pixane.fenetre import Fenetre  # noqa: E402
from pixane.moteur import Moteur  # noqa: E402

Moteur.demarrer = lambda self, signaler=None: None
Fenetre._moteur_en_echec = lambda self, *a: None
d = DialogueConsigne(None, transparent=True)
d.texte.setPlainText("Change le texte « Brûler » en « Flamme »")
d.anglais.setPlainText("")
verifier(d.consigne() == 'Change le texte "Brûler" en "Flamme"', "sans traduction : la consigne telle quelle")
d.anglais.setPlainText("Replace the text « Brûler » with « Flamme »")
verifier(d.consigne() == 'Replace the text "Brûler" with "Flamme"', "avec l'anglais rempli : c'est lui qui part")
d._traduit_de = d.texte.toPlainText()                # comme après « Traduire »
d.exemples.activated.emit(1)
verifier("…" in d.texte.toPlainText() and d.anglais.toPlainText() == "", "exemple inséré ; traduction périmée effacée")
lances = []
Fenetre._lancer = lambda self, titre, sel_, fab, **kw: lances.append((titre, fab, kw))
recettes._kontext.update(type="complet", fichier=recettes.KONTEXT)
DialogueConsigne.exec = lambda self: (self.texte.setPlainText("Replace the text"), self.anglais.setPlainText(""), 1)[2]
f = Fenetre()
f.show()
doc = Document(calques=[Calque("Texte", qimage_rgba(texte))])
doc.actif = 0
f._installer_document(doc)
s = np.zeros((H, W, 4), np.uint8)
s[..., 3] = sel
doc.selection = qimage_rgba(s).convertToFormat(doc.selection.format())
verifier(f.b_modifier.isVisible() and f.a_modifier.shortcut().toString() == "Shift+M", "carte « Modifier », Maj+M")
f.ia_modifier()
ok = len(lances) == 1 and "png" in lances[0][2] and "placer" in lances[0][2] and "vue" in lances[0][2]
verifier(ok, "Modifier : lancé avec le morceau, la pose et la vue")
if ok:
    prompt, sorties = lances[0][1]("x.png")
    noeuds = [n for n in prompt.values() if n["class_type"] == "CLIPTextEncode"]
    echelle = [n for n in prompt.values() if n["class_type"] == "ImageScale"]
    verifier(noeuds and noeuds[0]["inputs"]["text"] == "Replace the text" and len(sorties) == 2
             and (echelle[-1]["inputs"]["width"], echelle[-1]["inputs"]["height"]) == prep.taille[:2]
             or (echelle[-1]["inputs"]["width"], echelle[-1]["inputs"]["height"]) == mi.preparer(doc, sel).taille,
             "recette Kontext : consigne, 2 propositions, rendues à la taille du morceau")
QSettings("Pixane", "Pixane-essais").remove("consigne_derniere")
# ---- traducteur : à télécharger seulement si on le choisit
el = trd.elements()
verifier(len(el) == 7 and sum(e.taille for e in el) == trd.TAILLE and 300e6 < trd.TAILLE < 310e6
         and all(trd.VERSION in e.url and e.licence == "Apache-2.0" and Path(e.dest).parent == trd.dossier()
                 for e in el), f"traducteur : 7 fichiers, {trd.TAILLE / 1e6:.0f} Mo, version fixée, Apache-2.0")
from pixane.installation_traducteur import FenetreTraducteur  # noqa: E402
ft = FenetreTraducteur(f)
verifier("Mo" in ft.b_installer.text() and "28" in ft.b_installer.text() or "29" in ft.b_installer.text(),
         f"fenêtre du traducteur : explication et bouton ({ft.b_installer.text()})")
ft.reject()
from pixane.installation_moteur import FenetreInstallation  # noqa: E402
fi = FenetreInstallation(f, kontext=True)
avec = [e.cle for e in fi.elements()]
verifier(trd.installe() or (fi.c_traducteur.isChecked() and "traducteur_model.safetensors" in avec),
         "Installer le moteur IA : case du traducteur cochée avec Kontext")
fi.c_kontext.setChecked(False)
verifier(not fi.c_traducteur.isChecked() and not any(c.startswith("traducteur_") for c in [e.cle for e in fi.elements()]),
         "sans Kontext : traducteur décoché, rien à télécharger")
fi.close()
for dd in f.documents:
    dd.modifie = False
f.close()

print("ERREURS :", erreurs if erreurs else "aucune")
sys.exit(1 if erreurs else 0)
