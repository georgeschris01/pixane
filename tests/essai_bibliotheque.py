"""Bibliothèque de pinceaux et de motifs : lecture des formats (.abr Photoshop v1, v2, v6 ; .pat Photoshop ; .gbr,
.gih, .pat GIMP ; .bundle Krita ; images), pinceaux et motifs livrés (Krita, CC-0), ajout / retrait de fichiers,
fenêtre de choix. Les fichiers Photoshop sont fabriqués ici d'après leur description (aucun sur le PC).
Usage : essai_bibliotheque.py"""
import io
import os
import shutil
import struct
import sys
import tempfile
import zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PIL import Image
from PySide6.QtWidgets import QApplication

from pixane import formats_pinceaux as fp
from pixane.bibliotheque import MOTIFS, PINCEAUX, Bibliotheque, Pinceau
from pixane.choix_bibliotheque import ChoixBibliotheque, vignette

erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


def u16(v): return struct.pack(">H", v)
def u32(v): return struct.pack(">I", v)
def i32(v): return struct.pack(">i", v)
def uni(s): return u32(len(s) + 1) + (s + "\x00").encode("utf-16-be")


def packbits(ligne: bytes) -> bytes:
    """Compression simple : répétitions et suites brutes (assez pour l'essai)."""
    out, i = bytearray(), 0
    while i < len(ligne):
        j = i
        while j < len(ligne) and j - i < 128 and ligne[j] == ligne[i]:
            j += 1
        if j - i >= 3:
            out += struct.pack(">b", 1 - (j - i)) + bytes([ligne[i]])
            i = j
        else:
            k = min(len(ligne), i + 128)
            out += struct.pack(">b", k - i - 1) + ligne[i:k]
            i = k
    return bytes(out)


def canal_rle(a: np.ndarray) -> bytes:
    lignes = [packbits(a[y].tobytes()) for y in range(a.shape[0])]
    return b"".join(u16(len(l)) for l in lignes) + b"".join(lignes)


yy, xx = np.mgrid[0:40, 0:30]
forme = ((((xx - 15) / 14) ** 2 + ((yy - 20) / 19) ** 2) < 1).astype(np.uint8) * 200      # ellipse


def abr_v1v2(version: int, comp: int) -> bytes:
    h, w = forme.shape
    donnees = canal_rle(forme) if comp else forme.tobytes()
    corps = u32(0) + u16(30) + (uni("Ellipse") if version == 2 else b"") + b"\x01" + b"\x00" * 8
    corps += i32(0) + i32(0) + i32(h) + i32(w) + u16(8) + bytes([comp]) + donnees
    rond = u32(0) + u16(25) + u16(20) + u16(100) + struct.pack(">h", 0) + u16(50)
    return (u16(version) + u16(2) + u16(1) + u32(len(rond)) + rond + u16(2) + u32(len(corps)) + corps)


def abr_v6() -> bytes:
    h, w = forme.shape
    ech = b"\x00" * 47 + i32(0) + i32(0) + i32(h) + i32(w) + u16(8) + b"\x01" + canal_rle(forme)
    ech_pad = ech + b"\x00" * (-len(ech) % 4)
    samp = u32(len(ech)) + ech_pad
    desc = b"Nm  TEXT" + uni("Ma forme")
    return (u16(6) + u16(1) + b"8BIM" + b"samp" + u32(len(samp)) + samp + b"8BIM" + b"desc" + u32(len(desc)) + desc)


rgb = np.zeros((16, 24, 3), np.uint8)
rgb[..., 0], rgb[..., 1], rgb[..., 2] = 200, np.arange(24)[None, :] * 10, np.arange(16)[:, None] * 15


def pat_photoshop() -> bytes:
    h, w = rgb.shape[:2]
    canaux = b""
    for c in range(3):
        d = canal_rle(np.ascontiguousarray(rgb[..., c]))
        corps = u32(8) + i32(0) + i32(0) + i32(h) + i32(w) + u16(8) + b"\x01" + d
        canaux += u32(1) + u32(len(corps)) + corps
    canaux += u32(0) + u32(0)                                             # 2 canaux non écrits
    vmal = i32(0) + i32(0) + i32(h) + i32(w) + u32(3) + canaux
    motif = u32(1) + u32(3) + u16(h) + u16(w) + uni("Dégradé") + bytes([4]) + b"id01" + u32(3) + u32(len(vmal)) + vmal
    return b"8BPT" + u16(1) + u32(1) + motif


# ---- formats Photoshop (fabriqués)
for v, comp in [(1, 0), (2, 1)]:
    c = fp.lire_octets(abr_v1v2(v, comp), "essai.abr")
    ok = len(c.formes) == 2 and np.array_equal(c.formes[1].image, forme) and c.formes[0].image.shape == (20, 20)
    verifier(ok and abs(c.formes[1].espacement - 0.30) < 1e-6,
             f".abr v{v} ({'PackBits' if comp else 'brut'}) : rond calculé + forme échantillonnée exacte")
verifier(fp.lire_octets(abr_v1v2(2, 1), "essai.abr").formes[1].nom == "Ellipse", ".abr v2 : nom du pinceau lu")
c = fp.lire_octets(abr_v6(), "essai.abr")
verifier(len(c.formes) == 1 and np.array_equal(c.formes[0].image, forme) and c.formes[0].nom == "Ma forme",
         ".abr v6 (Photoshop CS et suivants) : forme et nom lus")
c = fp.lire_octets(pat_photoshop(), "essai.pat")
verifier(len(c.motifs) == 1 and c.motifs[0].nom == "Dégradé" and np.array_equal(c.motifs[0].image[..., :3], rgb)
         and (c.motifs[0].image[..., 3] == 255).all(), ".pat Photoshop (RVB, PackBits) : motif exact")
try:
    fp.lire_octets(b"\x00\x09" + b"\x00" * 20, "x.abr")
    verifier(False, ".abr inconnu refusé")
except ValueError:
    verifier(True, ".abr d'une version inconnue : refusé proprement")

# ---- formats GIMP (fabriqués) et image
g = forme.astype(np.uint8)
nom = b"Ovale\x00"
gbr = u32(28 + len(nom)) + u32(2) + u32(30) + u32(40) + u32(1) + b"GIMP" + u32(40) + nom + g.tobytes()
c = fp.lire_octets(gbr, "x.gbr")
verifier(np.array_equal(c.formes[0].image, g) and c.formes[0].nom == "Ovale" and c.formes[0].espacement == 0.4,
         ".gbr GIMP : forme, nom, espacement")
gih = b"Anime\n2 ncells:2 cellwidth:30 cellheight:40 step:100 dim:1 rank0:2 sel0:incremental\n" + gbr + gbr
c = fp.lire_octets(gih, "x.gih")
verifier(len(c.formes) == 2, ".gih GIMP : ses 2 formes")
png = io.BytesIO()
Image.fromarray(np.dstack([rgb, np.full(rgb.shape[:2], 255, np.uint8)]), "RGBA").save(png, "PNG")
c = fp.lire_octets(png.getvalue(), "papier.png", "motif")
verifier(len(c.motifs) == 1 and c.motifs[0].nom == "papier", "image .png comme motif")
gris = io.BytesIO()
Image.fromarray(255 - g * 1, "L").convert("RGBA").save(gris, "PNG")
c = fp.lire_octets(gris.getvalue(), "tache.png")
verifier(c.formes[0].image.ndim == 2 and c.formes[0].image.max() >= 200,
         "image grise comme pinceau : le noir peint, prend la couleur du pinceau")

# ---- livrés avec Pixane (Krita, CC-0)
tmp = Path(tempfile.mkdtemp(prefix="pixane_biblio_"))
b = Bibliotheque(tmp)
pinceaux, motifs = b.elements(PINCEAUX), b.elements(MOTIFS)
ignores = [x for gr in b.groupes[PINCEAUX] + b.groupes[MOTIFS] for x in gr.ignores]
verifier(len(pinceaux) >= 230 and len(motifs) >= 85 and not ignores,
         f"livrés : {len(pinceaux)} pinceaux, {len(motifs)} motifs, {len(ignores)} illisible(s)")
anime = [p for p in pinceaux if len(p.formes) > 1]
verifier(len(anime) > 50, f"pinceaux animés (.gih) : {len(anime)}, chacun garde ses formes")
verifier(all(p.formes[0].ndim == 2 or p.formes[0].shape[2] == 4 for p in pinceaux)
         and all(m.image.ndim == 3 and m.image.shape[2] == 4 for m in motifs), "formes grises / RGBA, motifs RGBA")
p0 = pinceaux[10]
verifier(b.trouver(PINCEAUX, p0.cle) is p0, f"un pinceau se retrouve par sa clé ({p0.cle})")

# ---- ajout / retrait
dossier = tmp / "fichiers"
dossier.mkdir()
(dossier / "Mes pinceaux.abr").write_bytes(abr_v1v2(2, 1))
(dossier / "Mes motifs.pat").write_bytes(pat_photoshop())
(dossier / "faux.abr").write_bytes(b"pas un pinceau")
z = io.BytesIO()
with zipfile.ZipFile(z, "w") as zz:
    zz.writestr("brushes/ovale.gbr", gbr)
    zz.writestr("patterns/degrade.pat", pat_photoshop())
    zz.writestr("paintoppresets/x.kpp", b"rien")
(dossier / "Paquet.bundle").write_bytes(z.getvalue())
r = b.importer(dossier / "Mes pinceaux.abr")
verifier(r[PINCEAUX] == 2 and any(gr.nom == "Mes pinceaux" for gr in b.groupes[PINCEAUX]),
         ".abr ajouté : un groupe « Mes pinceaux » de 2 pinceaux")
r = b.importer(dossier / "Paquet.bundle")
verifier(r[PINCEAUX] == 1 and r[MOTIFS] == 1, ".bundle ajouté : son pinceau et son motif")
verifier((tmp / PINCEAUX / "Mes pinceaux.abr.pixpaquet").exists()
         and not (tmp / PINCEAUX / "Mes pinceaux.abr").exists(), "rangé en paquet dans la bibliothèque (pas de copie)")
b2 = Bibliotheque(tmp)
verifier(len(b2.elements(PINCEAUX)) == len(pinceaux) + 3 and len(b2.elements(MOTIFS)) == len(motifs) + 1,
         "au redémarrage, les ajouts sont toujours là")
gr = next(gr for gr in b2.groupes[PINCEAUX] if gr.nom == "Mes pinceaux")
b2.retirer(gr)
verifier(not any(gr.nom == "Mes pinceaux" for gr in b2.groupes[PINCEAUX]), "groupe retiré")
# gros fichier (Smoke Brushes, 1,7 Go chez Christophe) : au démarrage, seule la liste du paquet est lue
r = b2.importer(dossier / "Mes pinceaux.abr")
b3 = Bibliotheque(tmp)
cle3 = "Mes pinceaux/Mes pinceaux.abr#0"
g3 = next(gr for gr in b3.groupes[PINCEAUX] if gr.nom == "Mes pinceaux")
verifier(b3.connu(PINCEAUX, cle3) and b3.pret(PINCEAUX, cle3) and all(e._formes is None for e in g3._elements),
         "paquet : pinceau reconnu et prêt sans lire aucune forme")
e3 = b3.trouver(PINCEAUX, cle3)
verifier(e3 is not None and e3._formes is None and e3.formes[0].ndim == 2 and e3._formes is not None
         and all(e._formes is None for e in g3._elements[1:]), "une forme n'est lue que pour le pinceau utilisé")
b2.retirer(next(gr for gr in b2.groupes[PINCEAUX] if gr.nom == "Mes pinceaux"))
# original en lecture seule (cas de Christophe, cruiza_2.abr : « Accès refusé » au retrait)
import stat
seul = dossier / "Protege.abr"
seul.write_bytes((dossier / "Mes pinceaux.abr").read_bytes())
seul.chmod(stat.S_IREAD)
b2.importer(seul)
copie = tmp / PINCEAUX / "Protege.abr.pixpaquet"
verifier(copie.exists() and os.access(copie, os.W_OK), "original en lecture seule : le paquet reste modifiable")
b2.retirer(next(gr for gr in b2.groupes[PINCEAUX] if gr.nom == "Protege"))
copie = tmp / PINCEAUX / "Protege.abr"         # copie faite par une ancienne version (attribut recopié)
copie.write_bytes(seul.read_bytes())
copie.chmod(stat.S_IREAD)
b2.recharger()
gr = next(gr for gr in b2.groupes[PINCEAUX] if gr.nom == "Protege")
try:
    b2.retirer(gr)
    verifier(not copie.exists(), "groupe en lecture seule retiré sans « Accès refusé »")
except PermissionError as ex:
    verifier(False, f"groupe en lecture seule retiré sans « Accès refusé » ({ex})")
seul.chmod(stat.S_IWRITE | stat.S_IREAD)
try:
    b2.retirer(b2.groupes[PINCEAUX][0])
    verifier(False, "un groupe de base ne se retire pas")
except ValueError:
    verifier(True, "un groupe de base ne se retire pas")

# ---- fenêtre
app = QApplication.instance() or QApplication(sys.argv)
d = ChoixBibliotheque(PINCEAUX, biblio=b2)
noms = [d.liste_groupes.item(i).text() for i in range(d.liste_groupes.count())]
verifier(d.grille.count() >= 15 and noms[:4] == ["Styles prêts", "Simples", "Crayon et fusain", "Peinture"]
         and "Nature" in noms and "Effets" in noms, f"fenêtre : styles prêts, simples, puis familles ({noms[:8]})")
from pixane.bibliotheque import STYLES_PRETS  # noqa: E402
st = b2.groupes[PINCEAUX][0].elements
verifier(len(st) == len(STYLES_PRETS) and all(e.reglages for e in st), f"{len(st)} styles prêts, avec leurs réglages")
si = b2.groupes[PINCEAUX][1].elements
verifier([e.nom for e in si][:2] == ["Rond dur", "Rond doux"] and all(e.formes[0].ndim == 2 for e in si),
         "pinceaux simples : rond dur, rond doux…")
verifier(b2.trouver(PINCEAUX, "Krita 4/grass.gih#0") is not None
         and b2.trouver(PINCEAUX, "Krita 4/grass.gih#0").cle == "Nature/grass.gih#0",
         "ancienne clé (« Krita 4/… ») : pinceau retrouvé dans sa famille")
verifier(not any(g.nom == "Divers" for g in b2.groupes[PINCEAUX]), "chaque pinceau de base a sa famille")
d.taille_vignettes.setValue(200)
verifier(d.grille.iconSize().width() == 200 and d.apercu.pixmap() is not None and not d.apercu.pixmap().isNull(),
         "vignettes agrandies (200 px) ; grand aperçu de l'élément choisi")
d.taille_vignettes.setValue(72)
msgs = d.importer([str(dossier / "Mes motifs.pat"), str(dossier / "faux.abr"), str(dossier / "Mes pinceaux.abr")])
verifier(len(msgs) == 3 and "illisible" in msgs[1] and d.groupe().nom == "Mes pinceaux" and d.grille.count() == 2,
         f"fenêtre : ajout (fichier abîmé signalé, nouveau groupe montré) {msgs}")
verifier(d.bouton_retirer.isEnabled(), "fenêtre : groupe ajouté -> bouton Retirer actif")
d.grille.setCurrentRow(1)
d.accept()
verifier(isinstance(d.choisi, Pinceau) and d.choisi.nom == "Ellipse", "fenêtre : pinceau choisi")
cle = d.choisi.cle
d2 = ChoixBibliotheque(PINCEAUX, biblio=b2, cle=cle)
verifier(d2.grille.currentItem().data(0x0100).cle == cle, "fenêtre : rouverte sur le pinceau en cours")
dm = ChoixBibliotheque(MOTIFS, biblio=b2)
verifier(dm.grille.count() > 40 and not vignette(motifs[0]).isNull(), "fenêtre des motifs")

shutil.rmtree(tmp, ignore_errors=True)
print("ERREURS :", erreurs if erreurs else "aucune")
sys.stdout.flush()
sys.exit(1 if erreurs else 0)
