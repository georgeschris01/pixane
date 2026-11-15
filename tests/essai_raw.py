"""Fichiers RAW : un DNG fabriqué ici (16 bits, linéaire) est ouvert (développé par LibRaw), sans remplacer
l'original à l'enregistrement, et traité par le Traitement par lot.
Usage : essai_raw.py dossier_sortie"""
import os
import struct
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PIL import Image
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox
from pixane import raw
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


def fabriquer_dng(chemin: Path, rgb16: np.ndarray):
    """DNG « LinearRaw » minimal (TIFF non compressé, une bande) : de quoi faire lire un vrai RAW à LibRaw."""
    h, w, _c = rgb16.shape
    donnees = rgb16.astype("<u2").tobytes()
    entrees = []          # (tag, type, nombre, valeur octets)
    def t(tag, typ, valeurs):
        fmt = {1: "B", 2: "s", 3: "H", 4: "I", 5: "II", 10: "ii"}[typ]
        if typ == 2:
            b = valeurs.encode() + b"\0"
            entrees.append((tag, typ, len(b), b))
        elif typ in (5, 10):
            b = b"".join(struct.pack("<" + fmt, *v) for v in valeurs)
            entrees.append((tag, typ, len(valeurs), b))
        else:
            entrees.append((tag, typ, len(valeurs), struct.pack("<" + fmt * len(valeurs), *valeurs)))
    xyz_vers_rgb = [[3.2406, -1.5372, -0.4986], [-0.9689, 1.8758, 0.0415], [0.0557, -0.2040, 1.0570]]
    t(254, 4, [0]); t(256, 4, [w]); t(257, 4, [h]); t(258, 3, [16, 16, 16]); t(259, 3, [1]); t(262, 3, [34892])
    t(271, 2, "Pixane"); t(272, 2, "Essai"); t(273, 4, [0]); t(274, 3, [1]); t(277, 3, [3]); t(278, 4, [h])
    t(279, 4, [len(donnees)]); t(284, 3, [1]); t(50706, 1, [1, 4, 0, 0]); t(50707, 1, [1, 1, 0, 0])
    t(50708, 2, "Pixane Essai"); t(50721, 10, [(round(v * 10000), 10000) for l in xyz_vers_rgb for v in l])
    t(50728, 5, [(1, 1)] * 3); t(50778, 3, [21])
    entrees.sort()
    debut_ifd = 8
    taille_ifd = 2 + 12 * len(entrees) + 4
    suite = debut_ifd + taille_ifd
    extra = b""
    champs = []
    for tag, typ, n, b in entrees:
        if len(b) <= 4:
            champs.append(struct.pack("<HHI", tag, typ, n) + b.ljust(4, b"\0"))
        else:
            champs.append(struct.pack("<HHI", tag, typ, n) + struct.pack("<I", suite + len(extra)))
            extra += b + (b"\0" if len(b) % 2 else b"")
    pos_donnees = suite + len(extra)
    # StripOffsets (273) : remplacé par la vraie place des pixels
    champs = [c if struct.unpack("<H", c[:2])[0] != 273 else c[:8] + struct.pack("<I", pos_donnees) for c in champs]
    ifd = struct.pack("<H", len(entrees)) + b"".join(champs) + struct.pack("<I", 0)
    chemin.write_bytes(b"II*\0" + struct.pack("<I", debut_ifd) + ifd + extra + donnees)


H, W = 200, 300
img = np.zeros((H, W, 3), np.float32)
img[:, :150] = (0.6, 0.05, 0.05)          # moitié gauche rouge
img[:, 150:] = (0.05, 0.05, 0.6)          # moitié droite bleue
dng = sortie / "essai.dng"
fabriquer_dng(dng, (img * 65535).astype(np.uint16))

# 1. développement
verifier(raw.est_raw(dng) and raw.est_raw("photo.NEF") and not raw.est_raw("a.jpg"), "extensions RAW reconnues")
rgb, _exif = raw.developper(dng)
verifier(rgb.shape == (H, W, 3), f"DNG développé par LibRaw : {rgb.shape[1]} × {rgb.shape[0]}")
g, d = rgb[:, :140].reshape(-1, 3).mean(0), rgb[:, 160:].reshape(-1, 3).mean(0)
verifier(g[0] > g[2] + 60 and d[2] > d[0] + 60, f"couleurs gardées (gauche {g.round()}, droite {d.round()})")

# 2. dans Pixane
app = QApplication(sys.argv)
from pixane.document import EXTENSIONS_LECTURE
verifier("*.nef" in EXTENSIONS_LECTURE and "*.cr3" in EXTENSIONS_LECTURE and "*.dng" in EXTENSIONS_LECTURE,
         "fenêtre Ouvrir : les RAW sont dans la liste des images")
f = Fenetre()
f.resize(1440, 920)
f.show()
f.charger(str(dng))
app.processEvents()
verifier(f.doc is not None and f.doc.taille() == (W, H), "Fichier > Ouvrir un .dng : la photo s'ouvre")
propose = {}


def faux_enregistrer(parent, titre, chemin, filtres, choisi=""):
    propose["chemin"] = chemin
    return "", ""


QFileDialog.getSaveFileName = staticmethod(faux_enregistrer)
QMessageBox.question = staticmethod(lambda *a, **k: (_ for _ in ()).throw(AssertionError("question posée")))
f.enregistrer()
verifier(propose.get("chemin", "").endswith(".jpg") and "essai" in propose["chemin"],
         f"Enregistrer : le RAW n'est pas remplacé, un .jpg est proposé ({Path(propose.get('chemin', '')).name})")

# 3. traitement par lot
from pixane.export import DialogueLot, traiter_une
lot = sortie / "lot"
lot.mkdir(exist_ok=True)
fabriquer_dng(lot / "photo.dng", (img * 65535).astype(np.uint16))
dl = DialogueLot(f)
dl.source.setText(str(lot))
verifier([p.name for p in dl.photos()] == ["photo.dng"], "Traitement par lot : les RAW du dossier sont pris")
cible = traiter_une(lot / "photo.dng", sortie / "lot_sortie", {"format": "garder", "qualite": 90})
verifier(cible.suffix == ".jpg" and Image.open(cible).size == (W, H), f"lot : RAW -> {cible.name}")

print("ERREURS :", erreurs if erreurs else "aucune")
f.doc.modifie = False
sys.stdout.flush()
QTimer.singleShot(200, f.close)
app.exec()
sys.exit(1 if erreurs else 0)
