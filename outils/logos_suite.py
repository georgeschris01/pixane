"""Logos de la Suite Pixane : propositions (même famille que le « P en pixels » de Pixane : fond bleu nuit, trait en
dégradé, pixels qui se détachent). Planche d'aperçu : une ligne par idée, une colonne par logiciel, à 128 et 32 px.
Usage : .venv\\Scripts\\python outils\\logos_suite.py logo\\propositions"""
import sys
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QPainter

sys.path.insert(0, str(Path(__file__).parent))
from logos_pixane import BORD, FOND, NUIT, degrade, etincelle, rendre, svg  # noqa: E402

# couleur de chaque logiciel (début, fin du dégradé)
COULEURS = {
    "Photo": ("#FF8A3D", "#E8366F"),
    "Video": ("#A78BFA", "#4F7CFF"),
    "Vector": ("#B8E04A", "#1FB57A"),
    "Page": ("#FF6FA8", "#C2367F"),
    "Audio": ("#3EE0E8", "#1B8FE0"),
    "Motion": ("#FFC94A", "#F06A2A"),
}
P = '<path d="M90 198 V64 H128 A42 42 0 0 1 164.4 127" fill="none" stroke="url(#r)" stroke-width="30" stroke-linecap="round" stroke-linejoin="round"/>'
LETTRES = {      # lettre du métier, au même trait que le P
    "Photo": P,
    "Video": '<path d="M82 66 L124 194 L166 66" fill="none" stroke="url(#r)" stroke-width="30" stroke-linecap="round" stroke-linejoin="round"/>',
    "Vector": '<path d="M82 66 L124 194 L166 66" fill="none" stroke="url(#r)" stroke-width="30" stroke-linecap="round" stroke-linejoin="round"/>'
              '<rect x="112" y="182" width="24" height="24" rx="3" fill="none" stroke="#FFFFFF" stroke-width="5"/>',
    "Page": '<path d="M90 198 V64 H128 A42 42 0 0 1 164.4 127" fill="none" stroke="url(#r)" stroke-width="30" stroke-linecap="round" stroke-linejoin="round"/>'
            '<path d="M70 222 H186" stroke="#FFFFFF" stroke-opacity=".5" stroke-width="6" stroke-linecap="round"/>',
    "Audio": '<path d="M86 72 L126 194 L166 72" fill="none" stroke="url(#r)" stroke-width="30" stroke-linecap="round" stroke-linejoin="round"/>',
    "Motion": '<path d="M78 196 V66 L128 140 L178 66 V196" fill="none" stroke="url(#r)" stroke-width="28" stroke-linecap="round" stroke-linejoin="round"/>',
}
LETTRES["Audio"] = ('<path d="M80 196 L128 64 L176 196 M98 150 H158" fill="none" stroke="url(#r)" stroke-width="28" '
                    'stroke-linecap="round" stroke-linejoin="round"/>')


def pixels(fin):
    return (f'<rect x="140" y="136" width="18" height="18" rx="3" fill="{fin}"/>'
            f'<rect x="114" y="140" width="14" height="14" rx="2" fill="{fin}" opacity=".75"/>'
            f'<rect x="166" y="152" width="11" height="11" rx="2" fill="{fin}" opacity=".6"/>'
            f'<rect x="186" y="138" width="9" height="9" rx="2" fill="{fin}" opacity=".45"/>')


def symbole(nom, x=184, y=186, c="#FFD27A"):
    """Petit symbole du métier, à la place de l'étincelle."""
    if nom == "Photo":        # montagne et soleil
        return (f'<circle cx="{x + 7}" cy="{y - 9}" r="5" fill="{c}"/>'
                f'<path d="M{x - 17} {y + 14} L{x - 5} {y - 3} L{x + 3} {y + 7} L{x + 9} {y} L{x + 19} {y + 14}Z" fill="{c}"/>')
    if nom == "Video":        # lecture
        return f'<path d="M{x - 11} {y - 15} L{x + 15} {y} L{x - 11} {y + 15}Z" fill="{c}" stroke="{c}" stroke-width="4" stroke-linejoin="round"/>'
    if nom == "Vector":       # courbe et poignées
        return (f'<path d="M{x - 18} {y + 12} C{x - 10} {y - 16} {x + 10} {y - 16} {x + 18} {y + 12}" fill="none" stroke="{c}" stroke-width="5" stroke-linecap="round"/>'
                f'<rect x="{x - 5}" y="{y - 14}" width="10" height="10" rx="2" fill="{c}"/>')
    if nom == "Page":         # lignes de texte
        return "".join(f'<rect x="{x - 17}" y="{y - 14 + 10 * i}" width="{34 - 10 * (i == 2)}" height="6" rx="3" fill="{c}"/>' for i in range(3))
    if nom == "Audio":        # onde
        return "".join(f'<rect x="{x - 18 + 9 * i}" y="{y - h / 2}" width="6" height="{h}" rx="3" fill="{c}"/>'
                       for i, h in enumerate((10, 26, 34, 18, 8)))
    if nom == "Motion":       # trajectoire
        return (f'<path d="M{x - 18} {y + 12} Q{x - 2} {y - 22} {x + 16} {y - 6}" fill="none" stroke="{c}" stroke-width="5" stroke-linecap="round" stroke-dasharray="2 8"/>'
                f'<circle cx="{x + 16}" cy="{y - 6}" r="7" fill="{c}"/>')
    return etincelle(x, y, 15, "#FFD27A")


def logo(idee, nom):
    a, b = COULEURS["Photo"] if idee in ("symbole",) else COULEURS[nom]
    defs = NUIT + degrade("r", a, b)
    if idee == "couleur":         # même P, couleur du logiciel
        corps = P + pixels(b) + etincelle(184, 188, 15, "#FFD27A")
    elif idee == "symbole":       # même P et mêmes couleurs, symbole du métier
        corps = P + pixels(b) + symbole(nom)
    elif idee == "couleur+symbole":
        corps = P + pixels(b) + symbole(nom)
    else:                         # lettre du métier (P, V…) et couleur
        corps = LETTRES[nom] + pixels(b) + etincelle(196, 196, 13, "#FFD27A")
    return svg(defs, FOND + BORD + corps)


TAILLE_SYMBOLE = 2.0          # choisie par Christophe le 15/11/2026 (idée C, symbole 2 fois plus grand)


def logo_final(nom: str, petit: bool = False) -> tuple[str, str]:
    """Logo retenu (idée C) : (defs, corps) du SVG 256 px. petit : version pour 16 à 24 px (trait plus épais,
    un seul pixel)."""
    a, b = COULEURS[nom]
    cx, cy = 186, 190
    sym = f'<g transform="translate({cx} {cy}) scale({TAILLE_SYMBOLE}) translate({-cx} {-cy})">{symbole(nom, cx, cy)}</g>'
    if petit:
        lettre = ('<path d="M88 200 V62 H126 A44 44 0 0 1 166 124" fill="none" stroke="url(#r)" stroke-width="42" '
                  'stroke-linecap="round" stroke-linejoin="round"/>')
        return NUIT + degrade("r", a, b), FOND + BORD + lettre + sym
    return NUIT + degrade("r", a, b), FOND + BORD + P + pixels(b) + sym


IDEES = [
    ("couleur", "A. Même P, une couleur par logiciel"),
    ("symbole", "B. Même P et mêmes couleurs, petit symbole du métier"),
    ("couleur+symbole", "C. Même P, couleur et symbole du métier"),
    ("lettre", "D. Initiale du métier (P, V, …) et couleur"),
]


def planche(sortie: Path, sombre: bool):
    noms = list(COULEURS)
    l_col, h_ligne, marge = 180, 230, 40
    W, H = marge * 2 + 300 + l_col * len(noms), marge * 2 + 50 + h_ligne * len(IDEES)
    img = QImage(W, H, QImage.Format_ARGB32_Premultiplied)
    img.fill(QColor("#1E1F22" if sombre else "#F4F5F7"))
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    texte = QColor("#E6E6E6" if sombre else "#1D2433")
    p.setPen(texte)
    f = QFont("Segoe UI", 13, QFont.Bold)
    p.setFont(f)
    for j, nom in enumerate(noms):
        p.drawText(QRectF(marge + 300 + j * l_col, marge, l_col, 30), Qt.AlignCenter, f"Pixane {nom}")
    for i, (idee, titre) in enumerate(IDEES):
        y = marge + 50 + i * h_ligne
        p.setFont(QFont("Segoe UI", 12, QFont.Bold))
        p.drawText(QRectF(marge, y + 30, 280, 120), Qt.AlignLeft | Qt.TextWordWrap, titre)
        for j, nom in enumerate(noms):
            code = logo(idee, nom)
            x = marge + 300 + j * l_col + (l_col - 128) // 2
            p.drawImage(x, y, rendre(code, 128))
            p.drawImage(x + 20, y + 150, rendre(code, 48))
            p.drawImage(x + 80, y + 158, rendre(code, 32))
    p.end()
    img.save(str(sortie))


if __name__ == "__main__":
    app = QGuiApplication(sys.argv)
    d = Path(sys.argv[1])
    d.mkdir(parents=True, exist_ok=True)
    planche(d / "suite-planche-claire.png", False)
    planche(d / "suite-planche-sombre.png", True)
    print("ok")
