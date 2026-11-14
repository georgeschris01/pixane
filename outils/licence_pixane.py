"""Image de la licence de Pixane pour le README (comme celle de TwinPanel) : logo, trois pastilles (gratuit, non
commercial, code ouvert), « LICENCE PIXANE ». Écrit logo\\licence\\licence-pixane(-en).svg et .png (2 ×).
Usage (depuis la racine du projet) : .venv\\Scripts\\python.exe outils\\licence_pixane.py"""
import re
import sys
from pathlib import Path

from PySide6.QtCore import QByteArray, QRectF
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

RACINE = Path(__file__).resolve().parents[1]
DOSSIER = RACINE / "logo" / "licence"
W, H = 610, 160


def logo(x: float, y: float, cote: float) -> str:
    """Le logo de Pixane (logo\\pixane.svg) placé dans l'image, identifiants renommés pour ne pas se mêler."""
    s = (RACINE / "logo" / "pixane.svg").read_text(encoding="utf-8")
    s = s.replace('id="f"', 'id="logo_f"').replace('id="r"', 'id="logo_r"')
    s = s.replace("url(#f)", "url(#logo_f)").replace("url(#r)", "url(#logo_r)")
    s = re.sub(r'^<svg [^>]*>', "", s).replace("</svg>", "")       # un <svg> dans un <svg> n'est pas lu par Qt
    return f'<g transform="translate({x} {y}) scale({cote / 256})">{s}</g>'


def cadeau(cx, cy):          # gratuit
    c = "#3DBB8A"
    return (f'<circle cx="{cx}" cy="{cy}" r="34" fill="none" stroke="{c}" stroke-width="5"/>'
            f'<rect x="{cx - 17}" y="{cy - 4}" width="34" height="22" rx="3" fill="{c}"/>'
            f'<rect x="{cx - 20}" y="{cy - 13}" width="40" height="10" rx="2.5" fill="{c}"/>'
            f'<rect x="{cx - 3}" y="{cy - 13}" width="6" height="31" fill="#1E222B"/>'
            f'<path d="M{cx} {cy - 13} C{cx - 6} {cy - 26} {cx - 19} {cy - 22} {cx - 12} {cy - 15} Z '
            f'M{cx} {cy - 13} C{cx + 6} {cy - 26} {cx + 19} {cy - 22} {cx + 12} {cy - 15} Z" fill="{c}"/>')


def euro_barre(cx, cy):      # non commercial
    c = "#E5534B"
    return (f'<circle cx="{cx}" cy="{cy}" r="34" fill="none" stroke="{c}" stroke-width="5"/>'
            f'<text x="{cx}" y="{cy + 14}" text-anchor="middle" font-family="Segoe UI, Inter, Arial, sans-serif" '
            f'font-size="40" font-weight="700" fill="{c}">€</text>'
            f'<line x1="{cx - 24}" y1="{cy - 24}" x2="{cx + 24}" y2="{cy + 24}" stroke="{c}" stroke-width="5" '
            f'stroke-linecap="round"/>')


def code_ouvert(cx, cy):     # code ouvert : on peut le modifier et le partager (même licence)
    c = "#4AA3F0"
    return (f'<circle cx="{cx}" cy="{cy}" r="34" fill="none" stroke="{c}" stroke-width="5"/>'
            f'<path d="M{cx - 9} {cy - 13} L{cx - 20} {cy} L{cx - 9} {cy + 13}" fill="none" stroke="{c}" '
            f'stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<path d="M{cx + 9} {cy - 13} L{cx + 20} {cy} L{cx + 9} {cy + 13}" fill="none" stroke="{c}" '
            f'stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<line x1="{cx + 4}" y1="{cy - 17}" x2="{cx - 4}" y2="{cy + 17}" stroke="{c}" stroke-width="5" '
            f'stroke-linecap="round"/>')


def image(sous_titre: str) -> str:
    police = 'font-family="Segoe UI, Inter, Arial, sans-serif"'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
            '<defs><linearGradient id="bord" x1="0" y1="0" x2="1" y2="1">'
            '<stop offset="0" stop-color="#FF8A3D"/><stop offset="1" stop-color="#E8366F"/></linearGradient></defs>'
            f'<rect x="3" y="3" width="{W - 6}" height="{H - 6}" rx="24" fill="#1E222B" stroke="url(#bord)" '
            'stroke-width="5"/>'
            '<circle cx="80" cy="80" r="60" fill="#2A2E38"/>'
            + logo(28, 28, 104)
            + cadeau(206, 66) + euro_barre(298, 66) + code_ouvert(390, 66)
            + f'<text x="458" y="72" {police} font-size="27" font-weight="700" fill="#FFFFFF">LICENCE</text>'
            f'<text x="458" y="102" {police} font-size="27" font-weight="700" fill="url(#bord)">PIXANE</text>'
            f'<text x="375" y="138" text-anchor="middle" {police} font-size="15" font-weight="600" '
            f'letter-spacing="1.5" fill="#C3C8D4">{sous_titre}</text>'
            '</svg>')


app = QGuiApplication(sys.argv)
DOSSIER.mkdir(parents=True, exist_ok=True)
for suffixe, sous_titre in (("", "GRATUIT · NON COMMERCIAL · CODE OUVERT"), ("-en", "FREE · NON-COMMERCIAL · OPEN SOURCE")):
    code = image(sous_titre)
    (DOSSIER / f"licence-pixane{suffixe}.svg").write_text(code, encoding="utf-8")
    img = QImage(W * 2, H * 2, QImage.Format_ARGB32_Premultiplied)
    img.fill(0)
    p = QPainter(img)
    p.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)
    QSvgRenderer(QByteArray(code.encode("utf-8"))).render(p, QRectF(0, 0, W * 2, H * 2))
    p.end()
    img.save(str(DOSSIER / f"licence-pixane{suffixe}.png"))
    print("écrit", f"licence-pixane{suffixe}")
