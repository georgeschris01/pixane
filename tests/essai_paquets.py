"""Pinceaux et motifs rangés en paquets (.pixpaquet) : conversion des anciennes copies (en arrière-plan, copie
effacée seulement après vérification), qualité identique au pixel près et à la taille d'origine (pas de réduction),
mêmes clés qu'avant, lecture à la demande (un seul pinceau ouvert), vignettes rangées, paquet abîmé sauté.
Usage : essai_paquets.py"""
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PIL import Image
from PySide6.QtWidgets import QApplication

from pixane import bibliotheque as bm
from pixane.bibliotheque import MOTIFS, PAQUET, PINCEAUX, Bibliotheque, elements_de
from pixane.choix_bibliotheque import vignette
from pixane.formats_pinceaux import TAILLE_MAX, lire_fichier

erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


app = QApplication(sys.argv)
tmp = Path(tempfile.mkdtemp(prefix="pixane_paquets_"))
base = Path(bm.__file__).parent / "ressources" / "base" / "krita4"
(tmp / PINCEAUX).mkdir(parents=True)
(tmp / MOTIFS).mkdir(parents=True)
# anciennes copies telles quelles : un .gih (plusieurs formes), un .gbr, une très grande forme, des motifs
gih = next(f for f in sorted((base / PINCEAUX).glob("*.gih")) if len(lire_fichier(f).formes) > 1)
gbr = next(iter(sorted((base / PINCEAUX).glob("*.gbr"))))
shutil.copyfile(gih, tmp / PINCEAUX / gih.name)
shutil.copyfile(gbr, tmp / PINCEAUX / gbr.name)
yy, xx = np.mgrid[0:3000, 0:4000]
grande = ((np.sin(xx / 7.0) * np.cos(yy / 11.0) + 1) * 127).astype(np.uint8)       # détails fins partout
Image.fromarray(grande).save(tmp / PINCEAUX / "Grande forme.png")
motif = np.dstack([(xx[:2800, :2800] * 7 % 256), (yy[:2800, :2800] * 3 % 256),
                   ((xx[:2800, :2800] ^ yy[:2800, :2800]) % 256), np.full((2800, 2800), 255)]).astype(np.uint8)
Image.fromarray(motif, "RGBA").save(tmp / MOTIFS / "Grand motif.png")
shutil.copyfile(next(iter(sorted((base / MOTIFS).glob("*.png")))), tmp / MOTIFS / "Papier.png")

b = Bibliotheque(tmp)
avant = {g: {e.cle: e for gr in b.groupes[g] if not gr.de_base for e in gr.elements} for g in (PINCEAUX, MOTIFS)}
verifier(len(b.anciens()) == 5, f"5 anciennes copies à convertir ({len(b.anciens())})")
# référence : lecture à la taille d'origine
ref = {}
for genre in (PINCEAUX, MOTIFS):
    for f in (tmp / genre).iterdir():
        c = lire_fichier(f, "motif" if genre == MOTIFS else "forme", pleine_taille=True)
        for e in elements_de(c, genre, f, f.stem):
            ref[e.cle] = e.image if genre == MOTIFS else e.formes
verifier(max(grande.shape) > TAILLE_MAX and ref["Grande forme/Grande forme.png#0"][0].shape == grande.shape,
         f"lecture pleine taille : {grande.shape[1]} × {grande.shape[0]} gardé (réduction habituelle : {TAILLE_MAX})")

fini = []
t0 = time.time()
b.convertir_anciens(lambda n: fini.append(n))
bloque = time.time() - t0
fin = time.time() + 120
while not fini and time.time() < fin:
    app.processEvents()
    time.sleep(0.05)
verifier(bloque < 0.5, f"conversion en arrière-plan (Pixane libre : {bloque * 1000:.0f} ms)")
verifier(fini == [5], f"5 copies converties ({fini})")
restes = sorted(f.name for g in (PINCEAUX, MOTIFS) for f in (tmp / g).iterdir())
verifier(all(n.endswith(PAQUET) for n in restes) and len(restes) == 5, f"copies effacées, paquets seuls : {restes}")
verifier(not b.anciens(), "plus rien à convertir")
taille_avant = sum((gih.stat().st_size, gbr.stat().st_size))
print("    tailles :", ", ".join(f"{f.name} {f.stat().st_size // 1024} Ko" for g in (PINCEAUX, MOTIFS)
                                  for f in (tmp / g).iterdir()))

b2 = Bibliotheque(tmp)
apres = {g: {e.cle: e for gr in b2.groupes[g] if not gr.de_base for e in gr.elements} for g in (PINCEAUX, MOTIFS)}
verifier(all(set(avant[g]) == set(apres[g]) for g in avant), "mêmes groupes et mêmes clés qu'avant")
verifier(all(e._formes is None for e in apres[PINCEAUX].values())
         and all(e._image is None for e in apres[MOTIFS].values()), "au démarrage : aucune forme lue")
identiques = all(len(e.formes) == len(ref[k]) and all(a.dtype == r.dtype and np.array_equal(a, r)
                                                      for a, r in zip(e.formes, ref[k]))
                 for k, e in apres[PINCEAUX].items())
identiques &= all(e.image.dtype == ref[k].dtype and np.array_equal(e.image, ref[k]) for k, e in apres[MOTIFS].items())
verifier(identiques, "toutes les formes et motifs identiques au pixel près, à leur taille d'origine")
e = apres[PINCEAUX]["Grande forme/Grande forme.png#0"]
verifier(e.formes[0].shape == (3000, 4000), f"grande forme gardée en {e.formes[0].shape[1]} × {e.formes[0].shape[0]}")
k = next(c for c in apres[PINCEAUX] if c.endswith(gih.name + "#0"))
verifier(apres[PINCEAUX][k].en_couleur == (ref[k][0].ndim == 3), "en couleur ou non : d'après la liste")

# lecture à la demande : un pinceau seul, rapide
b3 = Bibliotheque(tmp)
t0 = time.time()
e = b3.trouver(PINCEAUX, "Grande forme/Grande forme.png#0")
t_trouver = time.time() - t0
t0 = time.time()
e.formes
t_lire = time.time() - t0
verifier(t_trouver < 0.05, f"trouver un pinceau (ouverture des réglages) : {t_trouver * 1000:.1f} ms")
autres = [x for gr in b3.groupes[PINCEAUX] if not gr.de_base for x in gr.elements if x is not e]
verifier(all(x._formes is None for x in autres), f"seul le pinceau utilisé est lu ({t_lire * 1000:.0f} ms pour 4000 px)")
v = vignette(e, 64)
verifier(not v.isNull() and v.width() <= 64 and e.apercu.shape[:2] == (192, 256),
         f"vignette d'après l'aperçu rangé ({e.apercu.shape[1]} × {e.apercu.shape[0]})")
m = b3.trouver(MOTIFS, "Grand motif/Grand motif.png#0")
vignette(m, 64)
verifier(m._image is None, "vignette d'un motif sans lire le motif entier")
vignette(m, 256, detail=True)
verifier(m._image is not None, "détail : le motif entier est lu")

# paquet abîmé : sauté sans tout bloquer
(tmp / PINCEAUX / ("Abîmé.abr" + PAQUET)).write_bytes(b"pas un zip")
b4 = Bibliotheque(tmp)
verifier(not any(g.nom == "Abîmé" for g in b4.groupes[PINCEAUX]) and b4.trouver(PINCEAUX, k) is not None,
         "paquet abîmé sauté, les autres restent")
(tmp / PINCEAUX / ("Abîmé.abr" + PAQUET)).unlink()
# copie illisible : laissée telle quelle
(tmp / PINCEAUX / "faux.abr").write_bytes(b"pas un pinceau")
b5 = Bibliotheque(tmp)
fini.clear()
b5.convertir_anciens(lambda n: fini.append(n))
fin = time.time() + 30
while not fini and time.time() < fin:
    app.processEvents()
    time.sleep(0.05)
verifier(fini == [0] and (tmp / PINCEAUX / "faux.abr").exists()
         and not (tmp / PINCEAUX / ("faux.abr" + PAQUET)).exists(), "copie illisible : gardée, pas de paquet")
# retirer un groupe converti
gr = next(g for g in b5.groupes[PINCEAUX] if g.nom == "Grande forme")
b5.retirer(gr)
verifier(not (tmp / PINCEAUX / ("Grande forme.png" + PAQUET)).exists()
         and not any(g.nom == "Grande forme" for g in b5.groupes[PINCEAUX]), "groupe en paquet retiré")

shutil.rmtree(tmp, ignore_errors=True)
print()
print("ÉCHECS :" if erreurs else "Tout est bon.", *erreurs, sep="\n  ")
sys.exit(1 if erreurs else 0)
