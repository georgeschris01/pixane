"""Dessine les 6 propositions de logo de Chrypix (SVG) et une planche d'aperçu (PNG, plusieurs tailles)."""
import sys
from pathlib import Path

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

FOND = '<rect x="12" y="12" width="232" height="232" rx="56" fill="url(#f)"/>'
REFLET = '<rect x="12" y="12" width="232" height="116" rx="56" fill="#FFFFFF" opacity="0.10"/>'


def etincelle(x, y, r, couleur="#FFFFFF"):
    """Étoile à 4 branches (symbole de l'IA)."""
    return (f'<path fill="{couleur}" d="M{x} {y - r} C{x + r * .18} {y - r * .18} {x + r * .18} {y - r * .18} {x + r} {y} '
            f'C{x + r * .18} {y + r * .18} {x + r * .18} {y + r * .18} {x} {y + r} '
            f'C{x - r * .18} {y + r * .18} {x - r * .18} {y + r * .18} {x - r} {y} '
            f'C{x - r * .18} {y - r * .18} {x - r * .18} {y - r * .18} {x} {y - r}z"/>')


def degrade(id_, a, b, x1=0, y1=0, x2=1, y2=1):
    return (f'<linearGradient id="{id_}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}">'
            f'<stop offset="0" stop-color="{a}"/><stop offset="1" stop-color="{b}"/></linearGradient>')


LOGOS = {
    # 1. Photo + baguette : un paysage dont une partie est « effacée » par un trait magique
    "1-photo-magique": (
        "Photo magique",
        degrade("f", "#2B6CE6", "#7B3FE4") + degrade("c", "#8FD3FF", "#FFFFFF", 0, 0, 0, 1)
        + degrade("m", "#1E9E6A", "#0E6B4A", 0, 0, 0, 1),
        FOND + REFLET
        + '<rect x="52" y="62" width="152" height="124" rx="16" fill="url(#c)"/>'
        + '<circle cx="164" cy="98" r="14" fill="#FFC83D"/>'
        + '<path d="M52 170 L98 118 L130 152 L150 132 L204 182 V170 a16 16 0 0 1 -16 16 H68 a16 16 0 0 1 -16 -16z" fill="url(#m)"/>'
        + '<path d="M60 206 L196 70" stroke="#FFFFFF" stroke-width="12" stroke-linecap="round"/>'
        + '<path d="M168 98 L196 70" stroke="#FFC83D" stroke-width="12" stroke-linecap="round"/>'
        + etincelle(204, 132, 16) + etincelle(184, 52, 10) + etincelle(90, 210, 8, "#FFC83D")),

    # 2. Un « C » en anneau dégradé, dont l'ouverture se défait en pixels
    "2-c-pixels": (
        "C en pixels",
        degrade("f", "#1D2433", "#0F131B") + degrade("r", "#FF8A3D", "#E8366F"),
        FOND + '<rect x="12" y="12" width="232" height="232" rx="56" fill="none" stroke="#FFFFFF" stroke-opacity=".08" stroke-width="2"/>'
        + '<path d="M170 82 A62 62 0 1 0 170 174" fill="none" stroke="url(#r)" stroke-width="30" stroke-linecap="round"/>'
        + '<rect x="176" y="72" width="18" height="18" rx="4" fill="#FF8A3D"/>'
        + '<rect x="200" y="96" width="14" height="14" rx="3" fill="#F26252" opacity=".85"/>'
        + '<rect x="186" y="118" width="11" height="11" rx="3" fill="#EC4A60" opacity=".7"/>'
        + '<rect x="206" y="138" width="9" height="9" rx="2" fill="#E8366F" opacity=".55"/>'
        + etincelle(200, 186, 15, "#FFD27A")),

    # 3. Clin d'œil au métier d'électricien : un éclair qui retouche la photo
    "3-eclair": (
        "Éclair (volt)",
        degrade("f", "#FFB547", "#FF6A3D") + degrade("e", "#FFFFFF", "#FFF1C2", 0, 0, 0, 1),
        FOND + REFLET
        + '<rect x="46" y="70" width="128" height="104" rx="14" fill="#FFFFFF" opacity=".28"/>'
        + '<circle cx="80" cy="102" r="11" fill="#FFFFFF" opacity=".9"/>'
        + '<path d="M46 160 L84 124 L110 148 L128 132 L174 168 V160 a14 14 0 0 1 -14 14 H60 a14 14 0 0 1 -14 -14z" fill="#FFFFFF" opacity=".75"/>'
        + '<path d="M150 40 L104 132 H140 L118 216 L196 108 H156 L182 40z" fill="url(#e)" stroke="#8A2E0F" stroke-opacity=".25" stroke-width="3" stroke-linejoin="round"/>'
        + etincelle(206, 176, 14) + etincelle(60, 206, 9)),

    # 4. Diaphragme d'appareil photo, avec une étincelle au centre
    "4-diaphragme": (
        "Diaphragme",
        degrade("f", "#11B5A4", "#1769C7"),
        FOND + REFLET
        + '<circle cx="128" cy="128" r="80" fill="#FFFFFF" opacity=".16"/>'
        + "".join(f'<path transform="rotate({i * 60} 128 128)" d="M128 48 A80 80 0 0 1 197 88 L150 115 L128 103z" '
                  f'fill="#FFFFFF" opacity="{0.55 + 0.07 * i:.2f}"/>' for i in range(6))
        + '<circle cx="128" cy="128" r="80" fill="none" stroke="#FFFFFF" stroke-width="8"/>'
        + '<circle cx="128" cy="128" r="26" fill="#0E3D73"/>'
        + etincelle(128, 128, 18, "#FFD966")),

    # 5. Gomme magique qui efface la moitié d'un paysage
    "5-gomme": (
        "Gomme magique",
        degrade("f", "#8E54E9", "#E0457B") + degrade("g", "#FFFFFF", "#FFD6E4", 0, 0, 1, 1),
        FOND + REFLET
        + '<path d="M44 176 L92 124 L122 156 L142 136 L180 176z" fill="#FFFFFF" opacity=".35"/>'
        + '<circle cx="78" cy="84" r="16" fill="#FFFFFF" opacity=".35"/>'
        + '<g transform="rotate(-38 140 140)"><rect x="92" y="112" width="112" height="56" rx="14" fill="url(#g)"/>'
        + '<rect x="92" y="112" width="40" height="56" rx="14" fill="#5B2A86"/>'
        + '<rect x="118" y="112" width="14" height="56" fill="#5B2A86"/></g>'
        + '<path d="M58 206 H150" stroke="#FFFFFF" stroke-width="8" stroke-linecap="round" opacity=".8"/>'
        + etincelle(196, 66, 18) + etincelle(214, 108, 9) + etincelle(170, 44, 7)),

    # 6. Cadre qui s'agrandit (outpaint) : coins tirés vers l'extérieur
    "6-cadre-agrandi": (
        "Cadre agrandi",
        degrade("f", "#0EA5E9", "#6366F1") + degrade("p", "#FDE68A", "#F59E0B", 0, 0, 0, 1),
        FOND + REFLET
        + '<rect x="76" y="76" width="104" height="104" rx="12" fill="#FFFFFF"/>'
        + '<path d="M76 160 L108 128 L130 148 L144 136 L180 168 V168 a12 12 0 0 1 -12 12 H88 a12 12 0 0 1 -12 -12z" fill="#3B82F6"/>'
        + '<circle cx="152" cy="102" r="10" fill="url(#p)"/>'
        + '<path d="M44 84 V52 a8 8 0 0 1 8 -8 H84 M172 44 H204 a8 8 0 0 1 8 8 V84 M212 172 V204 a8 8 0 0 1 -8 8 H172 M84 212 H52 a8 8 0 0 1 -8 -8 V172" '
          'fill="none" stroke="#FFFFFF" stroke-width="10" stroke-linecap="round" stroke-linejoin="round" opacity=".95"/>'
        + etincelle(196, 196, 16, "#FDE68A")),
}


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


if __name__ == "__main__":
    app = QGuiApplication(sys.argv)

if __name__ == "__main__" and len(sys.argv) == 2:
    dossier = Path(sys.argv[1])
    dossier.mkdir(parents=True, exist_ok=True)
    tailles = (256, 64, 32, 16)
    case = 320
    for fond, nom_planche in (("#EEF1F5", "planche-clair.png"), ("#16181D", "planche-sombre.png")):
        planche = QImage(case * 3, case * 2, QImage.Format_ARGB32)
        planche.fill(QColor(fond))
        p = QPainter(planche)
        p.setRenderHint(QPainter.Antialiasing)
        p.setFont(QFont("Segoe UI", 12, QFont.Bold))
        p.setPen(QColor("#1F2328" if fond == "#EEF1F5" else "#E6E8EB"))
        for i, (cle, (titre, defs, corps)) in enumerate(LOGOS.items()):
            code = svg(defs, corps)
            (dossier / f"chrypix-{cle}.svg").write_text(code, encoding="utf-8")
            x, y = (i % 3) * case, (i // 3) * case
            p.drawImage(x + 16, y + 16, rendre(code, 200))
            px = x + 228
            for t in (64, 32, 16):
                p.drawImage(px, y + 28 + {64: 0, 32: 80, 16: 128}[t], rendre(code, t))
            p.drawText(x + 16, y + 240, case - 32, 30, Qt.AlignLeft, f"{i + 1}. {titre}")
        p.end()
        planche.save(str(dossier / nom_planche))
    print("ok", dossier)


# ---------------------------------------------------------------- 2e série : formes libres, sans carré de fond
LOGOS_B = {
    # 7. Coup de pinceau calligraphié en forme de C
    "7-pinceau-c": (
        "Coup de pinceau",
        degrade("b", "#FF5F6D", "#FFC371", 0, 1, 1, 0),
        '<path d="M186 66 C160 40 112 34 78 58 C40 86 34 146 62 182 C90 218 150 226 190 194 '
        'C170 204 128 210 100 186 C74 164 70 118 92 92 C116 64 158 64 178 84 z" fill="url(#b)"/>'
        + '<path d="M190 194 C198 188 204 182 208 176" stroke="#FF8A65" stroke-width="10" stroke-linecap="round" fill="none"/>'
        + etincelle(196, 112, 20, "#FFB300") + etincelle(222, 82, 9, "#FF5F6D")),

    # 8. Prisme : la lumière entre, sort en pixels de couleur
    "8-prisme": (
        "Prisme",
        degrade("v", "#E0E7FF", "#A5B4FC", 0, 0, 1, 1),
        '<path d="M20 140 H92" stroke="#94A3B8" stroke-width="8" stroke-linecap="round"/>'
        + '<path d="M128 44 L196 188 H60z" fill="url(#v)" stroke="#4F46E5" stroke-width="8" stroke-linejoin="round"/>'
        + "".join(f'<rect x="{186 + (i % 2) * 6}" y="{108 + i * 18}" width="{48 - i * 3}" height="12" rx="6" fill="{c}"/>'
                  for i, c in enumerate(("#EF4444", "#F59E0B", "#22C55E", "#3B82F6", "#8B5CF6")))),

    # 9. Œil dont l'iris est un objectif
    "9-oeil-objectif": (
        "Œil objectif",
        degrade("i", "#22D3EE", "#2563EB"),
        '<path d="M16 128 C56 64 200 64 240 128 C200 192 56 192 16 128z" fill="none" stroke="#0F172A" stroke-width="12" stroke-linejoin="round"/>'
        + '<circle cx="128" cy="128" r="46" fill="url(#i)"/>'
        + '<circle cx="128" cy="128" r="46" fill="none" stroke="#0F172A" stroke-width="8"/>'
        + '<circle cx="128" cy="128" r="18" fill="#0F172A"/>'
        + etincelle(146, 110, 13, "#FFFFFF")),

    # 10. Hexagone en pixels qui se détachent
    "10-hexagone": (
        "Hexagone de pixels",
        "",
        '<path d="M128 24 L218 76 V180 L128 232 L38 180 V76z" fill="#0F766E"/>'
        + '<path d="M128 24 L218 76 L128 128 L38 76z" fill="#14B8A6"/>'
        + '<path d="M128 128 L218 76 V180 L128 232z" fill="#0D9488"/>'
        + '<rect x="196" y="40" width="22" height="22" rx="4" fill="#14B8A6"/>'
        + '<rect x="226" y="18" width="14" height="14" rx="3" fill="#5EEAD4"/>'
        + '<rect x="230" y="56" width="10" height="10" rx="2" fill="#99F6E4"/>'
        + etincelle(84, 160, 22, "#FDE68A")),

    # 11. Photo instantanée penchée dont un coin se décolle sur une nouvelle image
    "11-polaroid": (
        "Photo qui se décolle",
        degrade("s", "#FCA5A5", "#FDBA74", 0, 0, 0, 1) + degrade("n", "#93C5FD", "#C4B5FD", 0, 0, 0, 1),
        '<g transform="rotate(-8 128 128)">'
        '<rect x="46" y="36" width="164" height="188" rx="10" fill="#FFFFFF" stroke="#1F2937" stroke-width="6"/>'
        '<rect x="62" y="52" width="132" height="120" rx="4" fill="url(#s)"/>'
        '<path d="M62 150 L104 112 L130 136 L150 120 L194 158 V172 H62z" fill="#B45309" opacity=".7"/>'
        '<path d="M150 52 H194 V104z" fill="url(#n)"/>'
        '<path d="M150 52 L194 104 L160 92z" fill="#FFFFFF" stroke="#1F2937" stroke-width="4" stroke-linejoin="round"/>'
        '</g>' + etincelle(214, 46, 14, "#6366F1")),

    # 12. Monogramme géométrique : C + carré de sélection
    "12-monogramme": (
        "Monogramme C",
        "",
        '<path d="M176 72 A72 72 0 1 0 176 184" fill="none" stroke="#111827" stroke-width="34"/>'
        + '<rect x="146" y="98" width="60" height="60" fill="none" stroke="#F43F5E" stroke-width="7" stroke-dasharray="12 8"/>'
        + '<rect x="166" y="118" width="20" height="20" fill="#F43F5E"/>'),
}

if __name__ == "__main__" and len(sys.argv) > 2 and sys.argv[2] == "B":
    dossier = Path(sys.argv[1])
    case = 320
    for fond, nom_planche in (("#FFFFFF", "planche-B-clair.png"), ("#16181D", "planche-B-sombre.png")):
        planche = QImage(case * 3, case * 2, QImage.Format_ARGB32)
        planche.fill(QColor(fond))
        p = QPainter(planche)
        p.setRenderHint(QPainter.Antialiasing)
        p.setFont(QFont("Segoe UI", 12, QFont.Bold))
        p.setPen(QColor("#1F2328" if fond == "#FFFFFF" else "#E6E8EB"))
        for i, (cle, (titre, defs, corps)) in enumerate(LOGOS_B.items()):
            code = svg(defs, corps)
            (dossier / f"chrypix-{cle}.svg").write_text(code, encoding="utf-8")
            x, y = (i % 3) * case, (i // 3) * case
            p.drawImage(x + 16, y + 16, rendre(code, 200))
            for t, dy in ((64, 0), (32, 80), (16, 128)):
                p.drawImage(x + 228, y + 28 + dy, rendre(code, t))
            p.drawText(x + 16, y + 240, case - 32, 30, Qt.AlignLeft, f"{i + 7}. {titre}")
        p.end()
        planche.save(str(dossier / nom_planche))
    print("série B ok")
