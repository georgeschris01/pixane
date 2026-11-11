"""Garde-fou des aplats de l'Upscale net : ce que Flux invente dans les aplats (taches, gribouillis) disparaît ; son
travail est gardé là où l'origine a du détail (traits, texte, matière de photo). Usage : essai_garde_fou.py"""
import io
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PIL import Image, ImageFilter
from PySide6.QtWidgets import QApplication

import pixane.fenetre as fen
from pixane.document import FORMAT_IMAGE, Calque, Document, qimage_rgb, qimage_rgba, tableau
from pixane.fenetre import Fenetre
from pixane.garde_fou import garder_aplats, part_aplats, poids_detail
from pixane.moteur import Moteur

Moteur.demarrer = lambda self, signaler=None: None
Fenetre._moteur_en_echec = lambda self, *a: None
fen.recettes.schnell_disponible = lambda: True
lances = []
Fenetre._lancer = lambda self, titre, sel, fab, apres=None, png=None, placer=None, **kw: lances.append(
    dict(apres=apres, png=png, placer=placer))
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


app = QApplication(sys.argv)

# pochette : aplat rouge, cadre noir, petit dessin
poch = np.zeros((200, 200, 3), np.uint8)
poch[:] = [225, 60, 50]
poch[20:22, 20:180] = 0
poch[178:180, 20:180] = 0
poch[20:180, 20:22] = 0
poch[20:180, 178:180] = 0
for k in range(10):
    poch[100 + k * 3, 80:120] = 0                   # traits du dessin


def faux_flux(rgb, taches=True, dessin=True):
    """Upscale ×2 « net » simulé : agrandi, avec des taches inventées dans l'aplat, des traits plus nets et une teinte
    ajoutée au dessin."""
    im = Image.fromarray(rgb).resize((rgb.shape[1] * 2, rgb.shape[0] * 2), Image.LANCZOS)
    a = np.asarray(im).astype(int)
    if dessin:
        net = np.asarray(im.filter(ImageFilter.UnsharpMask(2, 150, 0))).astype(int)
        a[200:260, 160:240] = net[200:260, 160:240] + [30, 0, 0]          # plus net, et teinté de rouge
    if taches:
        a[80:120, 60:100] += 40                        # tache dans l'aplat (loin des traits)
        a[300:310, 200:300] -= 60                      # « gribouillis »
    return np.clip(a, 0, 255).astype(np.uint8)


flux = faux_flux(poch)
res = tableau(garder_aplats(poch, qimage_rgb(flux)).convertToFormat(FORMAT_IMAGE)).astype(int)
lanczos = np.asarray(Image.fromarray(poch).resize((400, 400), Image.LANCZOS)).astype(int)
verifier(np.abs(res[80:120, 60:100, :3] - lanczos[80:120, 60:100]).max() <= 2, "tache inventée dans l'aplat : enlevée")
verifier(np.abs(res[300:310, 200:300, :3] - lanczos[300:310, 200:300]).max() <= 2, "gribouillis dans l'aplat : enlevé")


def nettete(a):
    a = a[..., :3].astype(float).mean(2)
    return np.abs(4 * a[1:-1, 1:-1] - a[:-2, 1:-1] - a[2:, 1:-1] - a[1:-1, :-2] - a[1:-1, 2:]).mean()


z = (slice(204, 256), slice(164, 236))
verifier(nettete(res[z]) > 0.9 * nettete(flux[z]) > nettete(lanczos[z]),
         f"dessin : la netteté de Flux est gardée ({nettete(res[z]):.1f} / Flux {nettete(flux[z]):.1f} "
         f"/ simple agrandi {nettete(lanczos[z]):.1f})")
verifier(abs(res[z][..., 0].mean() - lanczos[z][..., 0].mean()) < 4,
         "dessin : la teinte ajoutée par Flux est enlevée (couleurs de l'origine)")
verifier(res.shape[:2] == (400, 400) and (res[..., 3] == 255).all(), "taille ×2, opaque")
# photo (matière partout) : Flux gardé presque partout
rng = np.random.default_rng(1)
photo = np.clip(rng.normal(120, 35, (200, 200, 3)), 0, 255).astype(np.uint8)
p = poids_detail(photo)
verifier(p.mean() > 0.95, f"photo pleine de détails : travail de Flux gardé ({p.mean():.0%})")
verifier(part_aplats(poch) > 0.5 and part_aplats(photo) < 0.2,
         f"pochette reconnue comme image graphique ({part_aplats(poch):.0%} d'aplats), pas la photo")
from pixane.dialogues import ReglagesUpscale as RU
d_g, d_p = RU(200, 200, None, graphique=True), RU(200, 200, None)
verifier(d_g.force.value() == 0.25 and d_p.force.value() == 0.35 and "graphique" in d_g.aide_force.text(),
         "image graphique : force 0,25 proposée d'office ; photo : 0,35")
# vraie pochette de Christophe (s'il l'a mise dans « image de test\upscal ») : origine + résultat de l'Upscale net
dossier = Path(__file__).resolve().parents[1] / "image de test" / "upscal"
o_ = dossier / "ab67616d0000b273d5e9572024d0068b9d8b8759.jpg"
r_ = dossier / "ab67616d0000b273d5e9572024d0068b9d8b8759_retouche.jpg"
if o_.is_file() and r_.is_file():
    o = np.asarray(Image.open(o_).convert("RGB"))
    r = np.asarray(Image.open(r_).convert("RGB"))
    g = tableau(garder_aplats(o, qimage_rgb(np.ascontiguousarray(r))).convertToFormat(FORMAT_IMAGE)).astype(int)
    zone = (slice(520, 590), slice(60, 300))         # aplat rouge du bas, plein de taches inventées
    avant, apres_ = np.abs(r[zone].astype(int) - o[zone]).mean(), np.abs(g[zone][..., :3] - o[zone]).mean()
    verifier(apres_ < avant / 3, f"pochette réelle : taches de l'aplat enlevées (écart {avant:.1f} -> {apres_:.1f})")

# dans Pixane : Upscale net (toute l'image, et calque seul) passe par le garde-fou
f = Fenetre()
f.show()
f.a_ia_nouveau_calque.setChecked(False)
fen.ReglagesUpscale.exec = lambda self: 1
for cible in ("image", "net", "agrandi"):
    fen.ReglagesUpscale.valeurs = lambda self, c=cible: {"net": True, "facteur": 2.0, "force": 0.35, "cible": c}
    rgba = np.dstack([poch, np.full((200, 200), 255, np.uint8)])
    doc = Document(calques=[Calque("Pochette", qimage_rgba(rgba))])
    f._installer_document(doc)
    f.ia_upscale()
    l = lances[-1]
    entree = poch if l["png"] is None else np.asarray(Image.open(io.BytesIO(l["png"])).convert("RGB"))
    sortie = tableau(l["apres"](qimage_rgb(faux_flux(entree))).convertToFormat(FORMAT_IMAGE)).astype(int)
    verifier(np.abs(sortie[80:120, 60:100, :3] - lanczos[80:120, 60:100]).max() <= 2,
             f"Upscale net « {cible} » : la tache inventée est enlevée")
fen.ReglagesUpscale.valeurs = lambda self: {"net": False, "facteur": 2.0, "force": 0.35, "cible": "image"}
f.ia_upscale()
verifier(lances[-1]["apres"] is None, "Upscale rapide : pas de garde-fou (RealESRGAN n'invente pas)")

print("ERREURS :", erreurs if erreurs else "aucune")
sys.stdout.flush()
for dd in f.documents:
    dd.modifie = False
f.close()
sys.exit(1 if erreurs else 0)
