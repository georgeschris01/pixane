"""32 bits par couche (HDR) et outils dans la profondeur de l'image : ouverture / enregistrement EXR, HDR, TIFF 32,
.piximg ; fusion, calques de réglage, réglages, filtres, taille en 32 bits ; pinceaux, gomme, tampon, retouche en 16
et 32 bits ; Virage HDR, exposition de l'aperçu ; Image > Mode > 32 bits dans la fenêtre.
Usage : python tests/essai_32bits.py DOSSIER_SORTIE"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("PIXANE_REGLAGES", "Pixane-essais")

import numpy as np
from PySide6.QtCore import QPointF, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QMessageBox

from pixane import ajustements, filtres, hdr
from pixane import profondeur as P
from pixane.document import Calque, Document
from pixane.retouche import Trait

sortie = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(os.environ["TEMP"]) / "essai_32bits"
sortie.mkdir(parents=True, exist_ok=True)
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ERREUR  ") + texte)
    if not cond:
        erreurs.append(texte)


app = QApplication(sys.argv)
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.Ok)
QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.Ok)
W, H = 300, 40

# image HDR : un ciel qui monte jusqu'à 6 fois le blanc (linéaire, comme dans un EXR)
lin = np.zeros((H, W, 4), np.float32)
lin[..., 0] = np.linspace(0.01, 6.0, W)[None]
lin[..., 1] = lin[..., 0] * 0.8
lin[..., 2] = lin[..., 0] * 0.6
lin[..., 3] = 1
srvb = lin.copy()
srvb[..., :3] = P.lineaire_vers_srvb(lin[..., :3])

# ---- fichiers
for ext, tol in ((".exr", 2e-3), (".tif", 1e-5), (".hdr", 1e-2)):
    chemin = sortie / ("ciel" + ext)
    hdr.ecrire(chemin, srvb)
    doc = Document.ouvrir(chemin)
    t = P.tab32(doc.calques[0].image)
    ecart = float(np.max(np.abs(t[..., :3] - srvb[..., :3]) / np.maximum(srvb[..., :3], 0.05)))
    verifier(doc.profondeur == 32 and P.est_32(doc.calques[0].image) and ecart < tol and t[..., 0].max() > 1.5,
             f"{ext} ouvert en 32 bits, au-dessus du blanc gardé (écart {ecart:.1e})")
doc = Document.ouvrir(sortie / "ciel.exr")
doc.enregistrer(sortie / "ciel.piximg")
d2 = Document.ouvrir(sortie / "ciel.piximg")
verifier(d2.profondeur == 32 and np.array_equal(P.tab32(d2.calques[0].image), P.tab32(doc.calques[0].image)),
         ".piximg 32 bits : relu à l'identique")
doc.exporter(sortie / "ciel.jpg")
doc.exporter(sortie / "ciel16.png")
doc.enregistrer(sortie / "ciel.psd")
d3 = Document.ouvrir(sortie / "ciel.psd")
verifier((sortie / "ciel.jpg").stat().st_size > 0 and d3.profondeur == 16, "export JPG, PNG ; PSD en 16 bits")
d8 = Document.ouvrir(sortie / "ciel.jpg")
doc8 = Document.ouvrir(sortie / "ciel.jpg")
doc8.exporter(sortie / "depuis8.exr")
verifier(Document.ouvrir(sortie / "depuis8.exr").profondeur == 32, "image 8 bits exportée en EXR")

# ---- fusion des calques, modes, calque de réglage en 32 bits
img = doc.calques[0].image
moitie = P.qimage32(np.dstack([np.full((H, W, 3), 0.5, np.float32), np.full((H, W), 0.5, np.float32)]))
for mode in ("normal", "produit", "ecran", "addition", "teinte", "luminosite"):
    doc.appliquer_etat(doc.etat_avec((doc.calques[0], Calque("dessus", moitie, mode=mode))))
    f = P.tab32(doc.image_profonde())
    verifier(P.est_32(doc.calques[1].image) and np.isfinite(f).all() and f[..., 0].max() > 1.0,
             f"fusion « {mode} » en 32 bits (au-dessus du blanc : {f[..., 0].max():.2f})")
doc.appliquer_etat(doc.etat_avec((doc.calques[0],)))
doc.appliquer_etat(doc.etat_nouveau_calque())
verifier(P.tab32(doc.calques[1].image, premul=True)[..., 3].max() == 0
         and P.tab32(doc.image_profonde())[20, -1, 0] > 1.5,
         "nouveau calque en 32 bits : transparent (défaut de conversion de Qt contourné)")
from pixane.document import image_vide as _vide
verifier(P.tab32(P.en_32(_vide(4, 4)), premul=True)[..., 3].max() == 0, "conversion 8 → 32 bits : transparence gardée")
doc.appliquer_etat(doc.etat_avec((doc.calques[0],)))
for nom, etat in (("pivoter", lambda d_: d_.etat_pivote(1)), ("miroir", lambda d_: d_.etat_miroir(True)),
                  ("redresser", lambda d_: d_.etat_redresse(5)), ("dupliquer", lambda d_: d_.etat_dupliquer()),
                  ("zone de travail", lambda d_: d_.etat_zone_travail(320, 50, 10, 5, None))):
    d_ = Document.ouvrir(sortie / "ciel.exr")
    d_.appliquer_etat(etat(d_))
    verifier(all(P.est_32(c.image) for c in d_.calques) and P.tab32(d_.image_profonde())[..., 0].max() > 1.5,
             f"{nom} en 32 bits")
for type_ in ajustements.TYPES:
    try:
        r = ajustements.appliquer_rgba(P.tab32(img), type_, ajustements.defaut(type_))
        ok = r.dtype == np.float32 and np.isfinite(r).all()
    except Exception as e:
        ok = False
        print("   ", type_, e)
    verifier(ok, f"réglage « {type_} » en 32 bits")
p = ajustements.defaut("base")
r = ajustements.appliquer_rgba(P.tab32(img), "base", p)
verifier(np.allclose(r, P.tab32(img), atol=1e-4), "réglage neutre : image 32 bits inchangée (blanc dépassé gardé)")
for type_, fonction in filtres.FONCTIONS.items():
    try:
        r = filtres.appliquer_calque(img, lambda a: fonction(a, filtres.defauts(type_)), None, "flottant")
        ok = P.est_32(r) and np.isfinite(P.tab32(r)).all()
    except Exception as e:
        ok = False
        print("   ", type_, e)
    verifier(ok, f"filtre « {type_} » en 32 bits")
flou = filtres.appliquer_calque(img, lambda a: filtres.flou_gaussien(a, {"rayon": 3}), None, "flottant")
verifier(P.tab32(flou)[20, -10, 0] > 1.5, "flou en 32 bits : le ciel reste plus clair que le blanc")
from pixane.transformation import redimensionner
r = redimensionner(img, 150, 20)
verifier(P.est_32(r) and P.tab32(r)[..., 0].max() > 1.5, "taille de l'image en 32 bits")

# ---- pont 8 bits : seuls les pixels changés perdent le 32 bits
from pixane.document import qimage_rgba, tableau
from pixane.document import FORMAT_IMAGE
t8 = tableau(img.convertToFormat(FORMAT_IMAGE))
t8[:5, :5] = [255, 0, 0, 255]
doc.appliquer_etat(doc.etat_calque_modifie(0, image=qimage_rgba(t8)))
f = P.tab32(doc.calques[0].image)
verifier(P.est_32(doc.calques[0].image) and f[20, -1, 0] > 1.5 and f[0, 0, 1] < 0.01,
         "pont 8 bits : zone changée en 8 bits, le reste garde ses 32 bits")

# ---- outils dans la profondeur de l'image
for b in (16, 32):
    base = P.en_bits(img, b)
    for mode, kw in (("peinture", dict(couleur=QColor(255, 0, 0))), ("gomme", {}),
                     ("tampon", dict(source=base, decalage=QPointF(150, 0))), ("eclaircir", {}), ("assombrir", {}),
                     ("goutte", {}), ("nettete", {}), ("eponge", {}), ("doigt", {})):
        tr_ = Trait(mode, base, 12, 0.8, 0.6, **kw)
        tr_.ajouter(QPointF(20, 20))
        tr_.ajouter(QPointF(60, 20))
        res = tr_.image
        a, avant = P.tab32(res), P.tab32(base)
        verifier(P.bits(res) == b and np.array_equal(a[2, 200:], avant[2, 200:]) and np.isfinite(a).all(),
                 f"{mode} en {b} bits : même profondeur, reste intact")
    tr_ = Trait("tampon", P.en_32(img), 12, 1.0, 1.0, source=P.en_32(img), decalage=QPointF(200, 0))
    tr_.ajouter(QPointF(30, 20))
    if b == 32:
        verifier(P.tab32(tr_.image)[20, 30, 0] > 1.5, "tampon en 32 bits : recopie le ciel plus clair que le blanc")
# 16 bits : un coup de pinceau léger garde des nuances plus fines que le 8 bits
deg = np.tile(np.linspace(0, 1500, W).round().astype(np.uint16), (H, 1))
base16 = P.qimage16(np.dstack([deg, deg, deg, np.full((H, W), 65535, np.uint16)]))
tr_ = Trait("goutte", base16, 30, 0.5, 0.5)
tr_.ajouter(QPointF(100, 20))
tr_.ajouter(QPointF(200, 20))
v = P.tab16(tr_.image)[20, 100:200, 0]
verifier(len(np.unique(v)) > 40 and np.any(v % 257 != 0), "goutte d'eau en 16 bits : nuances fines gardées")

# ---- Virage HDR et exposition de l'aperçu
v = P.virage(P.qimage32(srvb), exposition=-2.6)
verifier(P.tab32(v)[..., :3].max() <= 1.0 and P.tab32(v)[20, -1, 0] < 0.999, "virage : exposition −2,6 retrouve le ciel")
v = P.virage(P.qimage32(srvb), compression=True)
c = P.tab32(v)[20, -60:, 0]
verifier(c.max() <= 1.0 and np.all(np.diff(c[:-1]) > 0), "virage : compression sans coupure au blanc")
doc = Document.ouvrir(sortie / "ciel.exr")
e = doc.etat_profondeur(16, {"exposition": -2.6, "gamma": 1.0, "compression": False})
doc.appliquer_etat(e)
doc.profondeur = 16
verifier(P.tab16(doc.calques[0].image)[20, -1, 0] < 65535, "Image > Mode > 16 bits avec virage : ciel retrouvé")
doc = Document.ouvrir(sortie / "ciel.exr")
P.tramage = False
a0 = doc.image_tramee()
P.exposition_ecran = -3.0
a1 = doc._image_ecran()
P.exposition_ecran = 0.0
verifier(tableau(a1)[20, -1, 0] < 255 and tableau(a0)[20, -1, 0] == 255,
         "exposition de l'aperçu : le ciel se voit à −3 diaphs, l'image ne change pas")
P.tramage = True

# ---- fenêtre : Image > Mode > 32 bits, titre, Virage HDR, Annuler
from pixane.fenetre import Fenetre
from pixane import dialogue_hdr
f = Fenetre()
f.resize(1200, 800)
f.show()
f.charger(str(sortie / "ciel.jpg"))
app.processEvents()
action = next(a for a in f._actions_bits.actions() if a.data() == 32)
action.trigger()
app.processEvents()
verifier(f.doc.profondeur == 32 and P.est_32(f.doc.calques[0].image) and "32 bits" in f.windowTitle()
         and f.a_exposition.isEnabled(), "Image > Mode > 32 bits : calques convertis, « (32 bits) » dans le titre")
f.historique.undo()
app.processEvents()
verifier(f.doc.profondeur == 8 and not f.a_exposition.isEnabled(), "Ctrl+Z : revient en 8 bits")
f.doc.modifie = False
f.charger(str(sortie / "ciel.exr"))
app.processEvents()
vu = []
dialogue_hdr.DialogueVirage.exec = lambda self: (vu.append(self.valeurs()), self._expo.setValue(-2.6),
                                                 dialogue_hdr.QDialog.Accepted)[-1]
next(a for a in f._actions_bits.actions() if a.data() == 8).trigger()
app.processEvents()
verifier(vu and f.doc.profondeur == 8 and tableau(f.doc.calques[0].image)[20, -1, 0] < 255,
         "32 → 8 bits : la fenêtre Virage HDR s'ouvre et son exposition est appliquée")
f.doc.modifie = False

print("ERREURS :", erreurs if erreurs else "aucune")
sys.stdout.flush()
QTimer.singleShot(200, f.close)
app.exec()
sys.exit(1 if erreurs else 0)
