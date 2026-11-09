"""Images de l'installateur de Pixane (Inno Setup 7), même présentation que celui de TwinPanel.
À relancer seulement si le logo ou les captures changent (captures : capture.py fr / en d'abord) :
    .venv\\Scripts\\python.exe installateur\\images\\fabrique_images.py
- accueil-<langue>-<l>x<h>.png : bande de gauche des pages d'accueil et de fin (logo, nom, petite capture),
  une taille par réglage d'affichage (100 % à 250 %), proportions 164:314 demandées par Inno Setup ;
- logo-<n>.png : logo carré du bandeau en haut des autres pages (fond transparent).
Couleurs : celles du logo (bleu nuit, dégradé orange -> rose)."""
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

RACINE = Path(__file__).resolve().parents[2]
SORTIE = Path(__file__).resolve().parent
HAUT, BAS = (29, 36, 51), (12, 15, 22)            # bleu nuit du logo (même couleur que dans Pixane.iss)
ORANGE, ROSE = (255, 138, 61), (232, 54, 111)     # dégradé du « C » du logo
TAILLES_ACCUEIL = [(202, 386), (269, 515), (336, 643), (403, 772), (430, 824), (534, 1022)]
TAILLES_LOGO = [58, 77, 97, 116, 124, 143, 159]


def logo_png(taille: int) -> Image.Image:
    """Logo SVG dessiné net à la taille voulue."""
    rendu = QSvgRenderer(QByteArray((RACINE / "logo" / "pixane.svg").read_bytes()))
    img = QImage(taille, taille, QImage.Format_RGBA8888)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    rendu.render(p, QRectF(0, 0, taille, taille))
    p.end()
    return Image.frombuffer("RGBA", (taille, taille), bytes(img.constBits()), "raw", "RGBA", img.bytesPerLine(), 1)


def gras(px: int):
    return ImageFont.truetype(os.path.join(os.environ["WINDIR"], "Fonts", "segoeuib.ttf"), px)


def trait_degrade(largeur: int, epaisseur: int) -> Image.Image:
    t = Image.new("RGBA", (largeur, epaisseur))
    d = ImageDraw.Draw(t)
    for x in range(largeur):
        k = x / max(1, largeur - 1)
        d.line([(x, 0), (x, epaisseur)], fill=tuple(round(ORANGE[i] + (ROSE[i] - ORANGE[i]) * k) for i in range(3)))
    return t


def accueil(capture: Image.Image, logo: Image.Image, w: int, h: int) -> Image.Image:
    im = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(im)
    for y in range(h):
        t = y / (h - 1)
        d.line([(0, y), (w, y)], fill=tuple(round(HAUT[i] + (BAS[i] - HAUT[i]) * t) for i in range(3)))
    u = w / 200                                                   # unité : 1/200 de la largeur
    s = round(110 * u)
    lg = logo.resize((s, s), Image.LANCZOS)
    im.paste(lg, ((w - s) // 2, round(34 * u)), lg)
    f = gras(round(27 * u))
    nom = "Pixane"
    tw = d.textlength(nom, font=f)
    d.text(((w - tw) / 2, round(150 * u)), nom, font=f, fill=(255, 255, 255))
    ligne = trait_degrade(w - 2 * round(60 * u), max(2, round(2 * u)))
    im.paste(ligne, (round(60 * u), round(190 * u)), ligne)
    tw = round(164 * u)
    th = round(tw * capture.height / capture.width)
    c = capture.resize((tw, th), Image.LANCZOS)
    b = max(2, round(2 * u))
    cadre = Image.new("RGBA", (tw + 2 * b, th + 2 * b), (255, 255, 255, 255))
    cadre.paste(c, (b, b))
    m = round(10 * u)
    ombre = Image.new("RGBA", (cadre.width + 2 * m, cadre.height + 2 * m), (0, 0, 0, 0))
    ImageDraw.Draw(ombre).rectangle([m, m + round(2 * u), m + cadre.width, m + cadre.height + round(2 * u)],
                                    fill=(0, 0, 0, 150))
    ombre = ombre.filter(ImageFilter.GaussianBlur(round(5 * u)))
    ombre.alpha_composite(cadre, (m, m))
    im.paste(ombre, ((w - ombre.width) // 2, round(206 * u) - m), ombre)
    return im


def main():
    app = QGuiApplication(sys.argv)
    grand = logo_png(1024)
    for langue in ("fr", "en"):
        capture = Image.open(SORTIE / f"capture-{langue}.png").convert("RGB")
        for w, h in TAILLES_ACCUEIL:
            accueil(capture, grand, w, h).save(SORTIE / f"accueil-{langue}-{w}x{h}.png", optimize=True)
    for n in TAILLES_LOGO:
        logo_png(n * 4).resize((n, n), Image.LANCZOS).save(SORTIE / f"logo-{n}.png", optimize=True)
    print("images faites dans", SORTIE)
    del app


if __name__ == "__main__":
    main()
