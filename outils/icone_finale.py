"""Fabrique l'icône finale de Pixane Photo (logo de la Suite Pixane, idée C : « P en pixels » orange-rose et symbole
photo) : SVG, ICO multi-tailles, PNG 256. L'emblème de la suite (P sans symbole) est dans logo\suite-pixane.svg."""
import io
import sys
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtGui import QGuiApplication

sys.path.insert(0, str(Path(__file__).parent))
from logos_pixane import rendre, svg  # noqa: E402
from logos_suite import logo_final  # noqa: E402

defs, corps = logo_final("Photo")
defs_p, corps_p = logo_final("Photo", petit=True)


def plein(c):
    """Le dessin agrandi pour remplir l'icône (le carré arrondi touche presque les bords, comme les icônes de
    Windows ; avant, il laissait 12 px de vide sur 256 et paraissait plus petit que les autres)."""
    return f'<g transform="translate(128 128) scale(1.085) translate(-128 -128)">{c}</g>'


complet = svg(defs, plein(corps))
# version simplifiée pour 16 à 24 px : trait plus épais, sans les petits pixels
simple = svg(defs_p, plein(corps_p))

app = QGuiApplication(sys.argv)
racine = Path(__file__).resolve().parents[1]


def pil(code, t):
    q = rendre(code, t)
    buf = QBuffer()
    buf.open(QIODevice.WriteOnly)
    q.save(buf, "PNG")
    return Image.open(io.BytesIO(bytes(buf.data()))).convert("RGBA")


tailles = [16, 20, 24, 32, 40, 48, 64, 128, 256]
images = [pil(simple if t <= 24 else complet, t) for t in tailles]
for dossier in (racine / "logo", racine / "pixane" / "ressources"):
    dossier.mkdir(exist_ok=True)
    (dossier / "pixane.svg").write_text(complet, encoding="utf-8")
    images[-1].save(dossier / "pixane.ico", format="ICO", sizes=[(t, t) for t in tailles], append_images=images[:-1])
(racine / "logo" / "pixane-petit.svg").write_text(simple, encoding="utf-8")
images[-1].save(racine / "logo" / "pixane-256.png")
apercu = Image.new("RGBA", (420, 120), (238, 241, 245, 255))
x = 10
for im in images:
    apercu.alpha_composite(im if im.width <= 100 else im.resize((100, 100), Image.LANCZOS), (x, 10))
    x += min(im.width, 100) + 10
apercu.save(racine / "logo" / "apercu-tailles.png")
print("ok")
