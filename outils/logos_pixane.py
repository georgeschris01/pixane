"""Logo de Pixane : propositions (la n° 1, « P en pixels », a été choisie le 09/11/2026) : fond bleu nuit, dégradé
orange-rose, pixels qui se détachent, étincelle de l'IA. Écrit les SVG et deux planches d'aperçu (fond clair et
fond sombre, à 256, 64, 32 et 16 px).
Usage : .venv\\Scripts\\python outils\\logos_pixane.py logo\\propositions"""
import sys
from pathlib import Path

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

FOND = '<rect x="12" y="12" width="232" height="232" rx="56" fill="url(#f)"/>'


def etincelle(x, y, r, couleur="#FFFFFF"):
    """Étoile à 4 branches (symbole de l'IA)."""
    return (f'<path fill="{couleur}" d="M{x} {y - r} C{x + r * .18} {y - r * .18} {x + r * .18} {y - r * .18} {x + r} {y} '
            f'C{x + r * .18} {y + r * .18} {x + r * .18} {y + r * .18} {x} {y + r} '
            f'C{x - r * .18} {y + r * .18} {x - r * .18} {y + r * .18} {x - r} {y} '
            f'C{x - r * .18} {y - r * .18} {x - r * .18} {y - r * .18} {x} {y - r}z"/>')


def degrade(id_, a, b, x1=0, y1=0, x2=1, y2=1):
    return (f'<linearGradient id="{id_}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}">'
            f'<stop offset="0" stop-color="{a}"/><stop offset="1" stop-color="{b}"/></linearGradient>')


def svg(defs, corps):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256">'
            f'<defs>{defs}</defs>{corps}</svg>')


def rendre(code, taille):
    img = QImage(taille, taille, QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    QSvgRenderer(QByteArray(code.encode())).render(p, QRectF(0, 0, taille, taille))
    p.end()
    return img

BORD = '<rect x="12" y="12" width="232" height="232" rx="56" fill="none" stroke="#FFFFFF" stroke-opacity=".08" stroke-width="2"/>'
NUIT = degrade("f", "#1D2433", "#0F131B")
ORANGE = degrade("r", "#FF8A3D", "#E8366F")


def pixels(liste):
    """Petits carrés arrondis : (x, y, côté, couleur, opacité)."""
    return "".join(f'<rect x="{x}" y="{y}" width="{c}" height="{c}" rx="{max(2, c // 5)}" fill="{coul}" opacity="{o}"/>'
                   for x, y, c, coul, o in liste)


# grille du P en carrés (proposition 2) : 1 = carré plein ; les carrés de la boucle se détachent vers la droite
GRILLE = ["1111.",
          "1...1",
          "1...1",
          "1111.",
          "1....",
          "1...."]

LOGOS = {
    # 1. Un « P » d'un seul trait dégradé ; le bas de sa boucle se défait en pixels (choisi)
    "1-p-pixels": (
        "P en pixels",
        NUIT + ORANGE,
        FOND + BORD
        + '<path d="M90 198 V64 H128 A42 42 0 0 1 164.4 127" fill="none" stroke="url(#r)" stroke-width="30" '
          'stroke-linecap="round" stroke-linejoin="round"/>'
        + pixels([(140, 136, 18, "#EC4A60", 1), (114, 140, 14, "#E8366F", .75), (166, 152, 11, "#E8366F", .6),
                  (186, 138, 9, "#E8366F", .45)])
        + etincelle(184, 188, 15, "#FFD27A")),

    # 2. Un « P » en gros pixels (carrés), qui se dispersent à droite
    "2-p-carres": (
        "P en carrés",
        NUIT + ORANGE,
        FOND + BORD
        + "".join(f'<rect x="{62 + 26 * c}" y="{50 + 26 * l}" width="22" height="22" rx="5" fill="url(#r)"/>'
                  for l, ligne in enumerate(GRILLE) for c, v in enumerate(ligne) if v == "1")
        + pixels([(196, 58, 15, "#F26252", .8), (214, 84, 11, "#EC4A60", .6), (200, 108, 8, "#E8366F", .45)])
        + etincelle(178, 190, 15, "#FFD27A")),

    # 3. Un « P » dont la boucle est un objectif (anneau), avec l'étincelle au centre
    "3-p-objectif": (
        "P objectif",
        NUIT + ORANGE,
        FOND + BORD
        + '<path d="M84 200 V108" stroke="url(#r)" stroke-width="30" stroke-linecap="round"/>'
        + '<circle cx="128" cy="104" r="46" fill="none" stroke="url(#r)" stroke-width="28"/>'
        + etincelle(128, 104, 17, "#FFD27A")
        + pixels([(180, 160, 16, "#EC4A60", .85), (198, 184, 11, "#E8366F", .6), (172, 196, 8, "#E8366F", .45)])),

    # 4. Le même P qu'en 1, en blanc sur le dégradé orange-rose (plus lumineux)
    "4-p-lumineux": (
        "P lumineux",
        degrade("f", "#FF8A3D", "#E8366F"),
        FOND + '<rect x="12" y="12" width="232" height="116" rx="56" fill="#FFFFFF" opacity="0.10"/>'
        + '<path d="M90 198 V64 H128 A42 42 0 0 1 164.4 127" fill="none" stroke="#FFFFFF" stroke-width="30" '
          'stroke-linecap="round" stroke-linejoin="round"/>'
        + pixels([(140, 136, 18, "#FFFFFF", .95), (114, 140, 14, "#FFFFFF", .75), (166, 152, 11, "#FFFFFF", .55),
                  (186, 138, 9, "#FFFFFF", .4)])
        + etincelle(184, 188, 15, "#FFF3C4")),
}

if __name__ == "__main__" and len(sys.argv) == 2:
    app = QGuiApplication(sys.argv)
    dossier = Path(sys.argv[1])
    dossier.mkdir(parents=True, exist_ok=True)
    case = 320
    for fond, nom_planche in (("#EEF1F5", "pixane-planche-clair.png"), ("#16181D", "pixane-planche-sombre.png")):
        planche = QImage(case * len(LOGOS), case, QImage.Format_ARGB32)
        planche.fill(QColor(fond))
        p = QPainter(planche)
        p.setRenderHint(QPainter.Antialiasing)
        p.setFont(QFont("Segoe UI", 12, QFont.Bold))
        p.setPen(QColor("#1F2328" if fond == "#EEF1F5" else "#E6E8EB"))
        for i, (cle, (titre, defs, corps)) in enumerate(LOGOS.items()):
            code = svg(defs, corps)
            (dossier / f"pixane-{cle}.svg").write_text(code, encoding="utf-8")
            x = i * case
            p.drawImage(x + 16, 16, rendre(code, 200))
            for t in (64, 32, 16):
                p.drawImage(x + 228, 28 + {64: 0, 32: 80, 16: 128}[t], rendre(code, t))
            p.drawText(x + 16, 240, case - 32, 30, Qt.AlignLeft, f"{i + 1}. {titre}")
        p.end()
        planche.save(str(dossier / nom_planche))
    print("ok")
