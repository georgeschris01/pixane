"""Agrandir, sans moteur : détection des bords abîmés (cadre, liseré, bord flou, bandes unies ; pas de fausse
alerte sur un ciel en dégradé ou une photo saine) et raccord (bandes plus claires de Flux retirées dans les fonds
unis, dessins de Flux gardés, original intact), tourbillons de Flux lissés, proposition « Fond prolongé »
(sans IA). Usage : essai_raccord.py"""
import io
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from PIL import Image, ImageFilter

from pixane.raccord import finaliser, fond_prolonge, lisere_auto, lisser_tourbillons, preparer, retirer_bandes

erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


rng = np.random.default_rng(1)
H, W = 600, 800
yy, xx = np.mgrid[0:H, 0:W]
base = (np.sin(xx / 9) * np.cos(yy / 13) * 40 + 120 + rng.normal(0, 6, (H, W))).clip(0, 255)


def rgb(a):
    return np.dstack([a, a * 0.9, a * 0.8]).clip(0, 255).astype(np.uint8)


# ------------------------------------------------------------ détection
verifier(lisere_auto(rgb(base)) == (0, 0, 0, 0), "photo saine : aucun bord")
f = base.copy()
f[:12], f[-12:], f[:, :12], f[:, -12:] = 20, 20, 20, 20
verifier(lisere_auto(rgb(f)) == (12, 12, 12, 12), f"cadre foncé de 12 px ({lisere_auto(rgb(f))})")
f = base.copy()
f[:3] = 250
verifier(lisere_auto(rgb(f)) == (3, 0, 0, 0), "liseré clair de 3 px")
verifier(lisere_auto(rgb(base * 0.3 + yy / H * 160)) == (0, 0, 0, 0), "ciel en dégradé : pas un bord")
im = Image.fromarray(rgb(base))
flou = np.asarray(im.filter(ImageFilter.GaussianBlur(4)))
g = np.asarray(im).copy()
g[:15], g[:, -15:] = flou[:15], flou[:, -15:]
verifier(lisere_auto(g) == (15, 0, 0, 15), f"bord flou de 15 px ({lisere_auto(g)})")
f = base.copy()
f[-15:] = 188
verifier(lisere_auto(rgb(f))[1] == 15, "barre blanche unie en bas (miniature YouTube)")
b = io.BytesIO()
Image.fromarray(rgb(base)).resize((400, 300)).save(b, "JPEG", quality=60)
verifier(lisere_auto(np.asarray(Image.open(b).convert("RGB"))) == (0, 0, 0, 0), "JPEG réduit : pas de fausse alerte")

# ------------------------------------------------------------ raccord : fond uni + bandes claires de Flux
h, w = 400, 400
fond = np.dstack([np.full((h, w), 10.0), np.full((h, w), 20.0), 40 + np.arange(h)[:, None] * 0.3 * np.ones((1, w))])
orig = (fond + rng.normal(0, 1.5, fond.shape)).clip(0, 255).astype(np.uint8)
png, geo, o2 = preparer(orig, 0, 0, 50, 50, enlever_lisere=False)
Wt, Ht = geo.travail
mh, mb, mg, md = geo.marges
# faux Flux : l'original prolongé, plus clair de 4 niveaux et avec des bandes verticales, et un objet net à gauche
toile = np.asarray(Image.fromarray(orig).resize((Wt, round(Wt * h / (w + mg + md))))).astype(np.float32)
pad = np.pad(toile, ((0, 0), (round(mg * Wt / geo.taille[0]),) * 2, (0, 0)), mode="edge")
flux = np.asarray(Image.fromarray(pad.clip(0, 255).astype(np.uint8)).resize((Wt, Ht))).astype(np.float32)
xs = np.arange(Wt)[None, :, None]
dehors = (xs < mg * Wt / geo.taille[0]) | (xs > (mg + w) * Wt / geo.taille[0])
flux = flux + dehors * (4 + 3 * np.sin(xs / 30.0))
flux[10:50, 20:60] = [220, 180, 40]                                # objet dessiné par Flux (net)
flux = flux.clip(0, 255).astype(np.uint8)
R = finaliser(o2, flux, geo).astype(np.float32)
verifier(np.abs(R[:, mg + 30:mg + w - 30] - orig[:, 30:w - 30]).max() < 1, "l'original reste intact")
gauche = R[200:380, 5:mg - 10, 2].mean(axis=0)
droite = R[200:380, mg + w + 10:-5, 2].mean(axis=0)
bord = orig[200:380, :20, 2].mean()
verifier(abs(gauche.mean() - bord) < 1.5 and abs(droite.mean() - bord) < 1.5,
         f"fond ajouté au niveau de l'original ({gauche.mean():.1f} / {droite.mean():.1f} pour {bord:.1f})")
# bandes de Flux : 6 niveaux d'écart ; il en reste moins de la moitié (le grain de l'original vaut déjà ~1)
verifier(np.ptp(gauche) < 3 and np.ptp(droite) < 3,
         f"bandes réduites de plus de moitié (écart {np.ptp(gauche):.1f} / {np.ptp(droite):.1f}, au lieu de 6)")
k = geo.taille[0] / Wt
objet = R[int(18 * k):int(42 * k), int(28 * k):int(52 * k)].mean(axis=(0, 1))
verifier(objet[0] > 180 and objet[2] < 90, f"l'objet dessiné par Flux est gardé ({objet.round(0)})")

# ------------------------------------------------------------ tourbillons de Flux (fond uni ajouté)
rt = np.random.default_rng(3)
Ht2, Wt2 = 300, 900
yy2, xx2 = np.mgrid[0:Ht2, 0:Wt2].astype(np.float32)
fond2 = 30 + yy2 * 0.15                                             # dégradé de haut en bas
tourb = 2.0 * np.sin(xx2 / 23) * np.cos(yy2 / 17)                  # tourbillons de 2 niveaux
grain = rt.normal(0, 1.0, (Ht2, Wt2))
I = np.repeat((fond2 + grain)[:, :, None], 3, axis=2).astype(np.float32)
I[:, :300] += tourb[:, :300, None]
I[:, 600:] += tourb[:, 600:, None]
I[100:130, 100:130] += 60                                           # une étoile nette dans l'ajout : gardée
L = lisser_tourbillons(I.copy(), (0, 0, 300, 300), (300, 0, 300, Ht2), 20)
mi = lambda a: float((a - fond2[150:290, 20:260, None]).std())
avant, apres = mi(I[150:290, 20:260]), mi(L[150:290, 20:260])
verifier(apres < avant * 0.75, f"tourbillons atténués ({avant:.2f} -> {apres:.2f}, grain gardé)")
verifier(abs(L[150:290, 20:260, 0].mean() - I[150:290, 20:260, 0].mean()) < 0.5, "dégradé gardé")
verifier(L[105:125, 105:125].mean() > fond2[105:125, 105:125].mean() + 50, "l'étoile nette est gardée")
verifier(np.abs(L[:, 300:600] - I[:, 300:600]).max() < 1e-3, "la photo n'est pas touchée")

# ------------------------------------------------------------ « Fond prolongé » (sans IA)
_png, geo2, o3 = preparer(orig, 0, 0, 50, 50, enlever_lisere=False)
F = fond_prolonge(o3, geo2)
verifier(F is not None and F.shape == (geo2.taille[1], geo2.taille[0], 3), "fond uni : Fond prolongé proposé")
if F is not None:
    mh2, mb2, mg2, md2 = geo2.marges
    verifier(np.array_equal(F[:, mg2:mg2 + w], o3), "l'original reste intact")
    g2 = F[:, 5:mg2 - 5].astype(np.float32)
    ligne = o3[:, :10].astype(np.float32).mean(axis=1)            # niveau de chaque ligne au bord
    verifier(np.abs(g2.mean(axis=1) - ligne).max() < 2.5, "le dégradé continue, ligne par ligne")
    verifier(0.5 < float(g2[:, :, 2].std(axis=1).mean()) < 3.0, "grain présent, du même ordre que la photo")
objet = orig.copy()
objet[150:250, :60] = [230, 200, 30]                                # un objet touche le bord gauche
_png, geo3, o4 = preparer(objet, 0, 0, 50, 50, enlever_lisere=False)
verifier(fond_prolonge(o4, geo3) is None, "objet au bord : pas de Fond prolongé (il serait étiré)")

print()
print("ÉCHECS :" if erreurs else "Tout est bon.", *erreurs, sep="\n  ")
sys.exit(1 if erreurs else 0)
