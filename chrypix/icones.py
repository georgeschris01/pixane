"""Icônes vectorielles dessinées pour Chrypix (traits arrondis, couleur du thème)."""
from __future__ import annotations

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

# Tracés sur une grille de 24 × 24, trait de 1,8 ; « C » = couleur du texte, « A » = couleur d'accent.
DESSINS = {
    "main": '<path d="M8 12V6.5a1.5 1.5 0 0 1 3 0V11M11 10V4.5a1.5 1.5 0 0 1 3 0V11M14 10.5V6a1.5 1.5 0 0 1 3 0v6.5'
            'M8 11.5V9.5a1.5 1.5 0 0 0-3 0V14c0 4 2.8 7 6.5 7h1c3.3 0 5.5-2.7 5.5-6V12a1.5 1.5 0 0 0-3 0"/>',
    "rectangle": '<rect x="4" y="5" width="16" height="14" rx="1.5" stroke-dasharray="3 2.4"/>',
    "lasso": '<path d="M7.5 16.5C4.5 15.3 3 13.4 3 11c0-4.1 4-7 9-7s9 2.9 9 7-4 7-9 7c-1 0-2-.1-2.9-.3"/>'
             '<path d="M8.5 15.5a2 2 0 1 0 1.2 2.6M8.2 19.8 7 21.5"/>',
    "pinceau": '<path d="M14.5 4.5l5 5-7.8 7.8-5-5z"/><path d="M6.7 12.3l5 5" />'
               '<path d="M6.5 13.5C4 14 3.2 16 3.5 18.5c.2 1.4-.6 2-1 2.5 3.5.5 6.5-.5 7.5-3.5"/>',
    "gomme": '<path d="M8.5 20 3.6 15.1a1.6 1.6 0 0 1 0-2.3L13 3.4a1.6 1.6 0 0 1 2.3 0l5.3 5.3a1.6 1.6 0 0 1 0 2.3'
             'L11.2 20z"/><path d="M8.5 20H21M8 9l7 7"/>',
    "effacer": '<path d="M7.5 19.5 3.6 15.6a1.5 1.5 0 0 1 0-2.1l7.3-7.3a1.5 1.5 0 0 1 2.1 0l3.9 3.9a1.5 1.5 0 0 1 0 2.1'
               'L10 19.5z"/><path d="M7.5 19.5H14"/>'
               '<path stroke="A" d="M18.5 3v4M16.5 5h4M20.5 13.5v3M19 15h3"/>',
    "remplir": '<path d="M5 13 11.5 6.5l6 6L11 19a1.5 1.5 0 0 1-2.1 0L5 15.1a1.5 1.5 0 0 1 0-2.1z"/>'
               '<path d="M9 4l3.5 3.5M5 13h12.5"/>'
               '<path stroke="A" d="M20 15.5c0 1.4-.9 2.5-2 2.5s-2-1.1-2-2.5 2-4 2-4 2 2.6 2 4z"/>',
    "agrandir": '<rect x="8" y="8" width="8" height="8" rx="1"/>'
                '<path stroke="A" d="M3 8V3h5M16 3h5v5M21 16v5h-5M8 21H3v-5"/>',
    "upscale": '<rect x="3" y="11" width="10" height="10" rx="1.5"/>'
               '<path stroke="A" d="M10 14 20 4M14 4h6v6"/>',
    "ouvrir": '<path d="M3.5 18.5V6a1.5 1.5 0 0 1 1.5-1.5h4l2 2.5h7.5A1.5 1.5 0 0 1 20 8.5V10"/>'
              '<path d="M3.5 18.5 6 11.5a1.5 1.5 0 0 1 1.4-1h13a1 1 0 0 1 1 1.3l-2.2 6.4a1.5 1.5 0 0 1-1.4 1H5'
              'a1.5 1.5 0 0 1-1.5-1.2z"/>',
    "enregistrer": '<path d="M5 3.5h11l4 4V19a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 3.5 19V5A1.5 1.5 0 0 1 5 3.5z"/>'
                   '<path d="M7.5 3.5V8h7V3.5M7 20.5v-6.5h10v6.5"/>',
    "annuler": '<path d="M9 14 4 9l5-5"/><path d="M4 9h10.5a5.5 5.5 0 0 1 0 11H11"/>',
    "retablir": '<path d="M15 14l5-5-5-5"/><path d="M20 9H9.5a5.5 5.5 0 0 0 0 11H13"/>',
    "zoom_plus": '<circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.5 15.5 21 21M10.5 7.5v6M7.5 10.5h6"/>',
    "zoom_moins": '<circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.5 15.5 21 21M7.5 10.5h6"/>',
    "ajuster": '<path d="M4 9V5a1 1 0 0 1 1-1h4M15 4h4a1 1 0 0 1 1 1v4M20 15v4a1 1 0 0 1-1 1h-4M9 20H5a1 1 0 0 1-1-1v-4"/>'
               '<rect x="8" y="8" width="8" height="8" rx="1"/>',
    "soleil": '<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2M12 19.5v2M4.6 4.6 6 6M18 18l1.4 1.4M2.5 12h2'
              'M19.5 12h2M4.6 19.4 6 18M18 6l1.4-1.4"/>',
    "lune": '<path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/>',
    "ajouter": '<circle cx="12" cy="12" r="8.5"/><path d="M12 8v8M8 12h8"/>',
    "retirer": '<circle cx="12" cy="12" r="8.5"/><path d="M8 12h8"/>',
    # calques
    "calque_nouveau": '<path d="M12 4 3 8.5l9 4.5 9-4.5z"/><path d="M3 13l9 4.5 3-1.5"/>'
                      '<path stroke="A" d="M19 14v6M16 17h6"/>',
    "dupliquer": '<rect x="8" y="8" width="12" height="12" rx="1.5"/>'
                 '<path d="M16 8V5.5A1.5 1.5 0 0 0 14.5 4h-9A1.5 1.5 0 0 0 4 5.5v9A1.5 1.5 0 0 0 5.5 16H8"/>',
    "supprimer": '<path d="M4 7h16M9.5 7V4.5h5V7M6 7l1 12.5a1.5 1.5 0 0 0 1.5 1.5h7a1.5 1.5 0 0 0 1.5-1.5L18 7"/>'
                 '<path d="M10 11v6M14 11v6"/>',
    "monter": '<path d="M12 19V5M6 11l6-6 6 6"/>',
    "descendre": '<path d="M12 5v14M6 13l6 6 6-6"/>',
    "fusionner": '<path d="M12 3 3 7.5 12 12l9-4.5z"/><path stroke="A" d="M12 14.5v6.5M9 18l3 3 3-3"/>',
    "aplatir": '<path d="M12 4 3 8.5l9 4.5 9-4.5z"/><path d="M3 12.5l9 4.5 9-4.5M3 16.5l9 4.5 9-4.5"/>',
    "oeil": '<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"/>'
            '<circle cx="12" cy="12" r="3"/>',
    "oeil_ferme": '<path d="M4 9.5c2 2.2 4.8 3.5 8 3.5s6-1.3 8-3.5M6.5 12.2 5 14.5M12 13v2.8M17.5 12.2l1.5 2.3"/>',
    "cadenas": '<rect x="5" y="10.5" width="14" height="10" rx="2"/><path d="M8 10.5V7.5a4 4 0 0 1 8 0v3"/>'
               '<path stroke="A" d="M12 14.5v2"/>',
    "cadenas_ouvert": '<rect x="5" y="10.5" width="14" height="10" rx="2"/><path d="M8 10.5V7.5a4 4 0 0 1 7.6-1.7"/>',
    "gomme_calque": '<path d="M8.5 20 3.6 15.1a1.6 1.6 0 0 1 0-2.3L13 3.4a1.6 1.6 0 0 1 2.3 0l5.3 5.3a1.6 1.6 0 0 1 '
                    '0 2.3L11.2 20z"/><path d="M8.5 20H14"/><path stroke="A" d="M16.5 15.5l4 4M20.5 15.5l-4 4"/>',
    "deplacer": '<path d="M12 3v18M3 12h18M12 3 9.5 5.5M12 3l2.5 2.5M12 21l-2.5-2.5M12 21l2.5-2.5'
                'M3 12l2.5-2.5M3 12l2.5 2.5M21 12l-2.5-2.5M21 12l-2.5 2.5"/>',
    # texte
    "texte": '<path d="M5 6.5V4.5h14v2M12 4.5v15M9 19.5h6"/>',
    "aligner_gauche": '<path d="M4 6h16M4 10h10M4 14h16M4 18h10"/>',
    "aligner_centre": '<path d="M4 6h16M7 10h10M4 14h16M7 18h10"/>',
    "aligner_droite": '<path d="M4 6h16M10 10h10M4 14h16M10 18h10"/>',
}


def svg(nom: str, couleur: str, accent: str) -> bytes:
    corps = DESSINS[nom].replace('stroke="A"', f'stroke="{accent}"')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{couleur}" '
            f'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{corps}</svg>').encode()


def icone(nom: str, couleur: str, accent: str, taille: int = 24) -> QIcon:
    rendu = QSvgRenderer(QByteArray(svg(nom, couleur, accent)))
    ic = QIcon()
    for echelle in (1, 2):
        pm = QPixmap(taille * echelle, taille * echelle)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        rendu.render(p, QRectF(0, 0, taille * echelle, taille * echelle))
        p.end()
        pm.setDevicePixelRatio(echelle)
        ic.addPixmap(pm)
    return ic
