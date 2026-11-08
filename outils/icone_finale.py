"""Fabrique l'icône finale de Chrypix (logo « C en pixels ») : SVG, ICO multi-tailles, PNG 256."""
import io, sys
from pathlib import Path
from PIL import Image
from PySide6.QtGui import QGuiApplication
sys.path.insert(0, str(Path(__file__).parent))
from logos import LOGOS, degrade, etincelle, rendre, svg

titre, defs, corps = LOGOS["2-c-pixels"]
complet = svg(defs, corps)
# version simplifiée pour 16 et 24 px : anneau plus épais, un seul pixel, pas d'étincelle
simple = svg(defs, '<rect x="12" y="12" width="232" height="232" rx="56" fill="url(#f)"/>'
             '<path d="M168 80 A62 62 0 1 0 168 176" fill="none" stroke="url(#r)" stroke-width="40" stroke-linecap="round"/>'
             '<rect x="178" y="66" width="34" height="34" rx="6" fill="#FF8A3D"/>')

app = QGuiApplication(sys.argv)
racine = Path(__file__).resolve().parents[1]
def pil(code, t):
    q = rendre(code, t); b = io.BytesIO()
    from PySide6.QtCore import QBuffer, QIODevice
    buf = QBuffer(); buf.open(QIODevice.WriteOnly); q.save(buf, "PNG")
    return Image.open(io.BytesIO(bytes(buf.data()))).convert("RGBA")
tailles = [16, 20, 24, 32, 40, 48, 64, 128, 256]
images = [pil(simple if t <= 24 else complet, t) for t in tailles]
for dossier in (racine / "logo", racine / "chrypix" / "ressources"):
    dossier.mkdir(exist_ok=True)
    (dossier / "chrypix.svg").write_text(complet, encoding="utf-8")
    images[-1].save(dossier / "chrypix.ico", format="ICO", sizes=[(t, t) for t in tailles], append_images=images[:-1])
(racine / "logo" / "chrypix-petit.svg").write_text(simple, encoding="utf-8")
images[-1].save(racine / "logo" / "chrypix-256.png")
apercu = Image.new("RGBA", (420, 120), (238, 241, 245, 255)); x = 10
for im in images:
    apercu.alpha_composite(im if im.width <= 100 else im.resize((100, 100), Image.LANCZOS), (x, 10)); x += min(im.width, 100) + 10
apercu.save(racine / "logo" / "apercu-tailles.png"); print("ok")
