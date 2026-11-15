"""Réglages de couleur, en calcul pur (numpy) : servent aux fenêtres de réglage (appliqués dans les pixels) et aux
calques de réglage (appliqués à l'affichage sur tout ce qui est dessous, modifiables à tout moment).

Chaque réglage = un type et un dictionnaire de paramètres (enregistrable en JSON) :
- « base » : luminosité, contraste, saturation, teinte, température, netteté (les Réglages de l'image) ;
- « niveaux » : point noir, gris (gamma), point blanc, sortie, par canal (rvb, r, v, b) ;
- « courbes » : points [[entrée, sortie], …] de 0 à 255 par canal, courbe douce qui passe par les points ;
- « balance » : cyan–rouge, magenta–vert, jaune–bleu pour les ombres, les tons moyens et les hautes lumières ;
- « noir_blanc » : part de chaque couleur (rouges, jaunes, verts, cyans, bleus, magentas) dans le gris, virage ;
- « vibrance » : vibrance (ravive surtout les couleurs ternes) et saturation ;
- « seuil » : noir ou blanc selon la clarté ; « posterisation » : nombre de niveaux par couleur ; « negatif » ;
- « mappe » : courbe de transfert de dégradé (la clarté de chaque point choisit sa couleur dans un dégradé) ;
- « filtre_photo » : filtre de couleur posé devant l'objectif (densité, clarté gardée) ;
- « melangeur » : mélangeur de couches (chaque couleur de sortie = part du rouge, du vert, du bleu + constante).
"""
from __future__ import annotations

import numpy as np

from .langue import tr

TYPES = {"base": "Réglages de l'image", "niveaux": "Niveaux", "courbes": "Courbes",
         "balance": "Balance des couleurs", "noir_blanc": "Noir et blanc", "vibrance": "Vibrance",
         "filtre_photo": "Filtre photo", "melangeur": "Mélangeur de couches", "mappe": "Courbe de transfert de dégradé",
         "seuil": "Seuil", "posterisation": "Postérisation", "negatif": "Négatif"}
SORTIES = ("rouge", "vert", "bleu")
CANAUX = ("rvb", "r", "v", "b")
TONS = ("ombres", "moyens", "lumieres")
COULEURS_NB = ("rouges", "jaunes", "verts", "cyans", "bleus", "magentas")
LUM = np.array([0.2126, 0.7152, 0.0722], np.float32)


def nom(type_: str) -> str:
    """Nom affiché d'un type (écrit en entier pour la traduction)."""
    return {"base": tr("Réglages de l'image"), "niveaux": tr("Niveaux"), "courbes": tr("Courbes"),
            "balance": tr("Balance des couleurs"), "noir_blanc": tr("Noir et blanc"),
            "vibrance": tr("Vibrance"), "filtre_photo": tr("Filtre photo"),
            "melangeur": tr("Mélangeur de couches"), "mappe": tr("Courbe de transfert de dégradé"),
            "seuil": tr("Seuil"), "posterisation": tr("Postérisation"), "negatif": tr("Négatif")}.get(type_, type_)


def defaut(type_: str) -> dict:
    if type_ == "base":
        return {"luminosite": 0, "contraste": 0, "saturation": 0, "teinte": 0, "temperature": 0, "nettete": 0}
    if type_ == "niveaux":
        return {k: [0, 1.0, 255, 0, 255] for k in CANAUX}
    if type_ == "courbes":
        return {k: [[0, 0], [255, 255]] for k in CANAUX}
    if type_ == "balance":
        return {"ombres": [0, 0, 0], "moyens": [0, 0, 0], "lumieres": [0, 0, 0], "luminosite": True}
    if type_ == "noir_blanc":
        return {"rouges": 40, "jaunes": 60, "verts": 40, "cyans": 60, "bleus": 20, "magentas": 80,
                "virage": False, "couleur": "#c8a878", "force": 50}
    if type_ == "vibrance":
        return {"vibrance": 0, "saturation": 0}
    if type_ == "seuil":
        return {"seuil": 128}
    if type_ == "posterisation":
        return {"niveaux": 4}
    if type_ == "negatif":
        return {}
    if type_ == "mappe":
        return {"degrade": {"couleurs": [{"pos": 0.0, "couleur": "#000000", "milieu": 0.5},
                                         {"pos": 1.0, "couleur": "#ffffff", "milieu": 0.5}],
                            "opacites": [{"pos": 0.0, "opacite": 1.0, "milieu": 0.5},
                                         {"pos": 1.0, "opacite": 1.0, "milieu": 0.5}]},
                "inverser": False}
    if type_ == "filtre_photo":
        return {"couleur": "#ec8a00", "densite": 25, "luminosite": True}
    if type_ == "melangeur":
        return {"rouge": [100, 0, 0, 0], "vert": [0, 100, 0, 0], "bleu": [0, 0, 100, 0], "gris": [40, 40, 20, 0],
                "monochrome": False}
    raise ValueError(type_)


def neutre(type_: str, p: dict) -> bool:
    if type_ in ("noir_blanc", "seuil", "posterisation", "negatif", "mappe"):
        return False
    if type_ == "filtre_photo":
        return p.get("densite", 0) == 0
    if type_ == "melangeur":
        d = defaut("melangeur")
        return not p.get("monochrome") and all(p.get(k) == d[k] for k in SORTIES)
    return p == defaut(type_)


# ------------------------------------------------------------------ tables (courbes par canal)
def table_niveaux(n) -> np.ndarray:
    noir, gamma, blanc, s_noir, s_blanc = n
    x = np.arange(256, dtype=np.float32)
    v = np.clip((x - noir) / max(1.0, float(blanc - noir)), 0, 1) ** (1 / max(0.05, float(gamma)))
    return np.clip(np.round(s_noir + v * (s_blanc - s_noir)), 0, 255).astype(np.uint8)


def table_courbe(points) -> np.ndarray:
    """Courbe douce (monotone par morceaux, sans dépassement) qui passe par les points ; plate au-delà."""
    pts = sorted((float(x), float(y)) for x, y in points)
    xs = np.array([p[0] for p in pts], np.float64)
    ys = np.array([p[1] for p in pts], np.float64)
    keep = np.concatenate(([True], np.diff(xs) > 0))
    xs, ys = xs[keep], ys[keep]
    x = np.arange(256, dtype=np.float64)
    if len(xs) == 1:
        return np.full(256, np.clip(round(ys[0]), 0, 255), np.uint8)
    d = np.diff(ys) / np.diff(xs)
    m = np.empty(len(xs))
    m[0], m[-1] = d[0], d[-1]
    for i in range(1, len(xs) - 1):                       # tangentes de Fritsch–Carlson
        m[i] = 0.0 if d[i - 1] * d[i] <= 0 else 2 / (1 / d[i - 1] + 1 / d[i])
    k = np.clip(np.searchsorted(xs, x) - 1, 0, len(xs) - 2)
    h = xs[k + 1] - xs[k]
    t = np.clip((x - xs[k]) / h, 0, 1)
    t2, t3 = t * t, t * t * t
    v = ((2 * t3 - 3 * t2 + 1) * ys[k] + (t3 - 2 * t2 + t) * h * m[k] + (-2 * t3 + 3 * t2) * ys[k + 1]
         + (t3 - t2) * h * m[k + 1])
    v = np.where(x < xs[0], ys[0], np.where(x > xs[-1], ys[-1], v))
    return np.clip(np.round(v), 0, 255).astype(np.uint8)


def _par_tables(rgb: np.ndarray, maitre: np.ndarray, canaux) -> np.ndarray:
    out = np.empty_like(rgb)
    for k in range(3):
        out[..., k] = canaux[k][maitre[rgb[..., k]]]
    return out


def _balance_tables(p: dict) -> list[np.ndarray]:
    """Balance des couleurs (méthode de GIMP) : chaque ton a son poids selon la clarté du pixel."""
    x = np.arange(256, dtype=np.float32) / 255
    a, b, k = 0.25, 0.333, 0.7
    ombres = np.clip((x - b) / -a + 0.5, 0, 1) * k
    moyens = np.clip((x - b) / a + 0.5, 0, 1) * np.clip((x + b - 1) / -a + 0.5, 0, 1) * k
    lumieres = np.clip((x + b - 1) / a + 0.5, 0, 1) * k
    tables = []
    for c in range(3):
        v = x + (p["ombres"][c] * ombres + p["moyens"][c] * moyens + p["lumieres"][c] * lumieres) / 100
        tables.append(np.clip(np.round(v * 255), 0, 255).astype(np.uint8))
    return tables


# ------------------------------------------------------------------ calcul
def appliquer(rgb: np.ndarray, type_: str, p: dict) -> np.ndarray:
    """rgb : tableau (..., 3) uint8 -> nouveau tableau (..., 3) uint8."""
    if type_ == "base":
        from .reglages_image import appliquer_rgb
        return appliquer_rgb(rgb, p)
    if type_ == "niveaux":
        maitre = table_niveaux(p["rvb"])
        return _par_tables(rgb, maitre, [table_niveaux(p[c]) for c in ("r", "v", "b")])
    if type_ == "courbes":
        maitre = table_courbe(p["rvb"])
        return _par_tables(rgb, maitre, [table_courbe(p[c]) for c in ("r", "v", "b")])
    if type_ == "balance":
        t = _balance_tables(p)
        out = np.stack([t[k][rgb[..., k]] for k in range(3)], axis=-1)
        if p.get("luminosite", True):
            f0 = rgb.astype(np.float32) @ LUM
            f1 = out.astype(np.float32) @ LUM
            out = np.clip(np.round(out + (f0 - f1)[..., None]), 0, 255).astype(np.uint8)
        return out
    if type_ == "noir_blanc":
        return _noir_blanc(rgb, p)
    if type_ == "vibrance":
        return _vibrance(rgb, p)
    if type_ == "seuil":
        g = (rgb.astype(np.float32) @ LUM) >= p.get("seuil", 128) - 0.5
        v = np.where(g, 255, 0).astype(np.uint8)
        return np.stack([v, v, v], axis=-1)
    if type_ == "posterisation":
        n = int(np.clip(p.get("niveaux", 4), 2, 255))
        x = np.arange(256)
        tab = np.clip(np.round(np.minimum(x * n // 256, n - 1) * 255 / (n - 1)), 0, 255).astype(np.uint8)
        return tab[rgb]
    if type_ == "negatif":
        return 255 - rgb
    if type_ == "mappe":
        return _mappe(rgb, p)
    if type_ == "filtre_photo":
        return _filtre_photo(rgb, p)
    if type_ == "melangeur":
        return _melangeur(rgb, p)
    raise ValueError(type_)


def _mappe(rgb: np.ndarray, p: dict) -> np.ndarray:
    """Courbe de transfert de dégradé : la clarté (0 à 255) de chaque point donne sa place dans le dégradé."""
    from . import degrades
    tab = degrades.table(p.get("degrade") or defaut("mappe")["degrade"])         # (256, 4) 0..1
    if p.get("inverser"):
        tab = tab[::-1]
    f = rgb.astype(np.float32)
    y = np.clip(np.round(f @ LUM), 0, 255).astype(np.intp)
    c = tab[y]
    out = f + (c[..., :3] * 255 - f) * c[..., 3:4]                  # parties transparentes du dégradé : photo gardée
    return np.clip(np.round(out), 0, 255).astype(np.uint8)


def _filtre_photo(rgb: np.ndarray, p: dict) -> np.ndarray:
    """Comme un filtre de couleur devant l'objectif : la photo est teintée (produit par la couleur) selon la densité ;
    « garder la luminosité » rend à chaque point sa clarté d'origine (seule la teinte change)."""
    from PySide6.QtGui import QColor
    c = QColor(p.get("couleur", "#ec8a00"))
    coul = np.array([c.red(), c.green(), c.blue()], np.float32) / 255
    d = p.get("densite", 25) / 100
    f = rgb.astype(np.float32)
    out = f + (f * coul - f) * d
    if p.get("luminosite", True):
        out = out + ((f @ LUM) - (out @ LUM))[..., None]
    return np.clip(np.round(out), 0, 255).astype(np.uint8)


def _melangeur(rgb: np.ndarray, p: dict) -> np.ndarray:
    """Chaque couleur de sortie = rouge × a % + vert × b % + bleu × c % + constante (en % de 255) ; monochrome :
    la même formule (ligne « gris ») pour les trois, la photo devient grise."""
    f = rgb.astype(np.float32)
    lignes = [p.get("gris", [40, 40, 20, 0])] * 3 if p.get("monochrome") else [p[k] for k in SORTIES]
    out = np.stack([f @ (np.array(l[:3], np.float32) / 100) + l[3] * 2.55 for l in lignes], axis=-1)
    return np.clip(np.round(out), 0, 255).astype(np.uint8)


def _noir_blanc(rgb: np.ndarray, p: dict) -> np.ndarray:
    """Gris = min + (moyen − min) × part de la couleur secondaire + (max − moyen) × part de la primaire
    (comme le réglage Noir et blanc de Photoshop)."""
    f = rgb.astype(np.float32)
    ordre = np.argsort(f, axis=-1)
    bas = np.take_along_axis(f, ordre[..., :1], -1)[..., 0]
    mil = np.take_along_axis(f, ordre[..., 1:2], -1)[..., 0]
    haut = np.take_along_axis(f, ordre[..., 2:], -1)[..., 0]
    i_haut, i_mil = ordre[..., 2], ordre[..., 1]
    prim = np.array([p["rouges"], p["verts"], p["bleus"]], np.float32) / 100
    # secondaire : rouge+vert = jaunes, vert+bleu = cyans, rouge+bleu = magentas
    sec = np.zeros((3, 3), np.float32)
    sec[0, 1] = sec[1, 0] = p["jaunes"] / 100
    sec[1, 2] = sec[2, 1] = p["cyans"] / 100
    sec[0, 2] = sec[2, 0] = p["magentas"] / 100
    gris = bas + (mil - bas) * sec[i_haut, i_mil] + (haut - mil) * prim[i_haut]
    gris = np.clip(gris, 0, 255)
    if p.get("virage"):
        from PySide6.QtGui import QColor
        c = QColor(p.get("couleur", "#c8a878"))
        teinte = np.array([c.red(), c.green(), c.blue()], np.float32)
        decal = teinte - float(teinte @ LUM)
        g = gris / 255
        force = p.get("force", 50) / 100 * 4 * g * (1 - g)       # rien dans le noir pur et le blanc pur
        out = gris[..., None] + decal * force[..., None]
        return np.clip(np.round(out), 0, 255).astype(np.uint8)
    g = np.round(gris).astype(np.uint8)
    return np.stack([g, g, g], axis=-1)


def _vibrance(rgb: np.ndarray, p: dict) -> np.ndarray:
    f = rgb.astype(np.float32)
    y = (f @ LUM)[..., None]
    mx, mn = f.max(axis=-1, keepdims=True), f.min(axis=-1, keepdims=True)
    sat = (mx - mn) / np.maximum(mx, 1)
    v = p.get("vibrance", 0) / 100
    gain = 1 + (v * (1 - sat) * 1.6 if v > 0 else v * 1.0)          # les couleurs ternes bougent le plus
    f = y + (f - y) * gain
    s = 1 + p.get("saturation", 0) / 100
    y = (f @ LUM)[..., None]
    f = y + (f - y) * s
    return np.clip(np.round(f), 0, 255).astype(np.uint8)


def appliquer_rgba(t: np.ndarray, type_: str, p: dict, poids: np.ndarray | None = None) -> np.ndarray:
    """Tableau RGBA (h, w, 4) uint8 (couleurs non prémultipliées) -> nouveau tableau ; poids (h, w) 0..1 :
    mélange avec l'original (sélection, masque, opacité)."""
    out = t.copy()
    res = appliquer(np.ascontiguousarray(t[..., :3]), type_, p)
    if poids is None:
        out[..., :3] = res
    else:
        w = poids.astype(np.float32)[..., None]
        out[..., :3] = np.round(t[..., :3] + (res.astype(np.float32) - t[..., :3]) * w).astype(np.uint8)
    return out
