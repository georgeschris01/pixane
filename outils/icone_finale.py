"""Fabrique l'icône finale de Pixane (logo « P en pixels ») : SVG, ICO multi-tailles, PNG 256."""
import io
import sys
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtGui import QGuiApplication

sys.path.insert(0, str(Path(__file__).parent))
from logos_pixane import BORD, FOND, LOGOS, rendre, svg  # noqa: E402

titre, defs, corps = LOGOS["1-p-pixels"]
complet = svg(defs, corps)
# version simplifiée pour 16 à 24 px : trait plus épais, un seul pixel, pas d'étincelle
simple = svg(defs, FOND + BORD
             + '<path d="M88 200 V62 H126 A44 44 0 0 1 166 124" fill="none" stroke="url(#r)" stroke-width="42" '
               'stroke-linecap="round" stroke-linejoin="round"/>'
             + '<rect x="128" y="138" width="34" height="34" rx="7" fill="#EC4A60"/>')

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
