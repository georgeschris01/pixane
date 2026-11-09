"""Sélections automatiques : baguette magique (sans IA), et calculs communs à la sélection rapide et à la sélection
d'objet (IA SAM 3.1) : zones d'un seul tenant, nettoyage des miettes, combinaison avec la sélection existante.

Tout est en numpy, sans bibliothèque en plus. Les zones d'un seul tenant sont trouvées par « segments » : chaque ligne
de l'image est découpée en segments, puis les segments qui se touchent d'une ligne à l'autre reçoivent le même numéro
(propagation du plus petit numéro avec saut de pointeurs, entièrement vectorisée).

Baguette magique, mieux que celle de Photoshop :
- couleurs comparées comme l'œil les voit (écart « redmean », bien plus proche de la vision que l'écart canal par
  canal de Photoshop), couleur de départ prise en moyenne sur 3 × 3 pixels (le bruit compte moins) ;
- bord doux proportionnel à l'écart de couleur (pas d'escalier, pas de liseré) ;
- tolérance réglable en glissant après le clic, avec aperçu en direct ;
- trous bouchés si on le demande (oiseaux dans un ciel, reflets sur un objet…).
"""
from __future__ import annotations

import numpy as np

PIXELS_CONNEXITE = 1_500_000      # les zones d'un seul tenant sont cherchées sur une image d'au plus ~1,5 Mpx
PIXELS_APERCU = 350_000           # aperçu pendant le glisser : encore plus petit, pour suivre la souris


# ---------------------------------------------------------------------------- zones d'un seul tenant
def _segments(m: np.ndarray):
    """Segments de pixels vrais, ligne par ligne : (ligne, début, fin exclue), triés par ligne puis début."""
    h, w = m.shape
    bord = np.zeros((h, w + 2), np.int8)
    bord[:, 1:-1] = m
    d = np.diff(bord, axis=1)
    ys, xs = np.nonzero(d)
    v = d[ys, xs]
    return ys[v == 1], xs[v == 1], xs[v == -1]


def etiquettes(m: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Numéro de zone de chaque pixel (-1 hors zone, 8 voisins) et taille de chaque zone."""
    h, w = m.shape
    lignes, debuts, fins = _segments(m)
    n = len(lignes)
    if n == 0:
        return np.full((h, w), -1, np.int32), np.zeros(0, np.int64)
    # liens entre segments de deux lignes voisines qui se touchent (8 voisins : un pixel de décalage permis)
    premier = np.searchsorted(lignes, np.arange(h + 1))
    a_l, b_l = [], []
    for y in range(h - 1):
        i0, i1, j0, j1 = premier[y], premier[y + 1], premier[y + 1], premier[y + 2]
        if i0 == i1 or j0 == j1:
            continue
        sd, sf = debuts[j0:j1], fins[j0:j1]
        bas = np.searchsorted(sf, debuts[i0:i1], "left")          # premier segment du dessous qui finit après
        haut = np.searchsorted(sd, fins[i0:i1] + 1, "left")       # jusqu'au premier qui commence trop loin
        nb = np.maximum(haut - bas, 0)
        if nb.sum() == 0:
            continue
        a = np.repeat(np.arange(i0, i1), nb)
        decal = np.arange(nb.sum()) - np.repeat(np.cumsum(nb) - nb, nb)
        b = j0 + np.repeat(bas, nb) + decal
        a_l.append(a)
        b_l.append(b)
    lab = np.arange(n)
    if a_l:
        a = np.concatenate(a_l)
        b = np.concatenate(b_l)
        while True:
            m_ab = np.minimum(lab[a], lab[b])
            nouveau = lab.copy()
            np.minimum.at(nouveau, a, m_ab)
            np.minimum.at(nouveau, b, m_ab)
            nouveau = nouveau[nouveau]                             # saut de pointeurs
            nouveau = nouveau[nouveau]
            if np.array_equal(nouveau, lab):
                break
            lab = nouveau
    _, lab = np.unique(lab, return_inverse=True)
    longueurs = fins - debuts
    tailles = np.bincount(lab, weights=longueurs).astype(np.int64)
    img = np.full(h * w, -1, np.int32)
    depart = lignes * w + debuts
    idx = np.repeat(depart, longueurs) + (np.arange(longueurs.sum()) - np.repeat(np.cumsum(longueurs) - longueurs,
                                                                               longueurs))
    img[idx] = np.repeat(lab, longueurs)
    return img.reshape(h, w), tailles


def zone_de(m: np.ndarray, graines: list[tuple[int, int]]) -> np.ndarray:
    """Pixels vrais d'un seul tenant avec au moins une des graines (x, y)."""
    lab, _ = etiquettes(m)
    h, w = m.shape
    choisis = {int(lab[min(max(y, 0), h - 1), min(max(x, 0), w - 1)]) for x, y in graines}
    choisis.discard(-1)
    if not choisis:
        return np.zeros_like(m, bool)
    return np.isin(lab, list(choisis))


def boucher_trous(m: np.ndarray) -> np.ndarray:
    """Remplit les trous entièrement entourés par la zone."""
    lab, _ = etiquettes(~m)
    bord = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    bord = bord[bord >= 0]
    dehors = np.isin(lab, bord)
    return m | (~m & ~dehors)


def nettoyer(m: np.ndarray, points: list[tuple[int, int]] = (), part_min: float = 0.03) -> np.ndarray:
    """Résultat de l'IA : enlève les miettes (zones de moins de part_min de la plus grande), sauf celles qui
    contiennent un point demandé ; bouche aussi les tout petits trous (moins de 0,2 % de la zone)."""
    lab, tailles = etiquettes(m)
    if len(tailles) == 0:
        return m
    garder = tailles >= part_min * tailles.max()
    h, w = m.shape
    for x, y in points:
        n = lab[min(max(y, 0), h - 1), min(max(x, 0), w - 1)]
        if n >= 0:
            garder[n] = True
    m = garder[lab] & (lab >= 0)
    lab_t, tailles_t = etiquettes(~m)
    bord = set(np.unique(np.concatenate([lab_t[0], lab_t[-1], lab_t[:, 0], lab_t[:, -1]])).tolist())
    petits = [i for i, t in enumerate(tailles_t) if i not in bord and t < 0.002 * m.sum()]
    if petits:
        m = m | np.isin(lab_t, petits)
    return m


# ---------------------------------------------------------------------------- baguette magique
def _reduction(h: int, w: int, pixels: int) -> int:
    return max(1, int(np.ceil(np.sqrt(h * w / pixels))))


def ecart(rgba: np.ndarray, couleur: np.ndarray) -> np.ndarray:
    """Écart de couleur perçu (0 à ~255) entre chaque pixel et la couleur de départ (r, g, b, a)."""
    t = rgba.astype(np.float32)
    dr, dg, db = t[..., 0] - couleur[0], t[..., 1] - couleur[1], t[..., 2] - couleur[2]
    rm = (t[..., 0] + couleur[0]) / 2
    d = np.sqrt((2 + rm / 256) * dr * dr + 4 * dg * dg + (2 + (255 - rm) / 256) * db * db) / 3
    return np.maximum(d, np.abs(t[..., 3] - couleur[3]))       # transparent / opaque : très différents


def couleur_depart(rgba: np.ndarray, x: int, y: int) -> np.ndarray:
    h, w = rgba.shape[:2]
    x, y = min(max(x, 0), w - 1), min(max(y, 0), h - 1)
    # médiane 3 × 3 : le bruit compte moins, et un clic au bord d'une zone ne mélange pas les deux couleurs
    return np.median(rgba[max(0, y - 1):y + 2, max(0, x - 1):x + 2].reshape(-1, 4).astype(np.float32), axis=0)


def baguette(rgba: np.ndarray, x: int, y: int, tolerance: float, contigu: bool = True, doux: bool = True,
             trous: bool = False, couleur: np.ndarray | None = None) -> np.ndarray:
    """Masque 0..255 (taille de rgba) de la zone de couleur proche du point (x, y)."""
    h, w = rgba.shape[:2]
    if couleur is None:
        couleur = couleur_depart(rgba, x, y)
    bande = max(3.0, tolerance * 0.3) if doux else 0.0
    limite = tolerance + bande
    d = ecart(rgba, couleur)
    if bande:
        a = np.clip((limite - d) / bande, 0, 1)
    else:
        a = (d <= tolerance).astype(np.float32)
    if contigu or trous:
        f = _reduction(h, w, PIXELS_CONNEXITE)
        d_p = d[::f, ::f] if f > 1 else d
        dedans = d_p <= max(limite, 0.5)
        zone = zone_de(dedans, [(x // f, y // f)]) if contigu else dedans
        if trous:
            zone = boucher_trous(zone)
        if f > 1:
            # retour à la taille réelle, élargi d'un pas pour ne pas rogner les bords fins
            z = zone.copy()
            z[1:] |= zone[:-1]
            z[:-1] |= zone[1:]
            z[:, 1:] |= zone[:, :-1]
            z[:, :-1] |= zone[:, 1:]
            grand = np.repeat(np.repeat(z, f, axis=0), f, axis=1)[:h, :w]
            a = a * grand
            if trous:
                tr_ = np.repeat(np.repeat(zone & ~(d_p <= limite), f, axis=0), f, axis=1)[:h, :w]
                a = np.maximum(a, tr_)
        else:
            a = a * zone
            if trous:
                a = np.maximum(a, zone & ~dedans)
    if doux:                                   # lissage d'un pixel : pas d'escalier sur les bords nets
        a = _flou3(a.astype(np.float32))
    return (a * 255 + 0.5).astype(np.uint8)


def _flou3(a: np.ndarray) -> np.ndarray:
    """Moyenne 3 × 3 (bords répétés)."""
    p = np.pad(a, 1, mode="edge")
    v = p[:-2] + p[1:-1] + p[2:]
    return (v[:, :-2] + v[:, 1:-1] + v[:, 2:]) / 9


def apercu_baguette(rgba: np.ndarray, x: int, y: int, tolerance: float, **options) -> tuple[np.ndarray, int]:
    """Version rapide (image réduite) pour suivre la souris : (masque réduit, facteur de réduction)."""
    h, w = rgba.shape[:2]
    f = _reduction(h, w, PIXELS_APERCU)
    petit = rgba[::f, ::f] if f > 1 else rgba
    couleur = couleur_depart(rgba, x, y)
    return baguette(petit, x // f, y // f, tolerance, couleur=couleur, **options), f


# ---------------------------------------------------------------------------- combiner avec la sélection
def combiner(base: np.ndarray | None, a: np.ndarray, mode: str) -> np.ndarray:
    """mode : « nouvelle » (remplace), « ajouter » ou « retirer »."""
    if mode == "nouvelle" or base is None:
        return a
    if mode == "ajouter":
        return np.maximum(base, a)
    return (base.astype(np.uint16) * (255 - a.astype(np.uint16)) // 255).astype(np.uint8)


def points_du_trait(points: list[tuple[float, float]], pas: float, maximum: int = 12) -> list[tuple[int, int]]:
    """Points régulièrement espacés le long d'un trait (pour l'IA), au plus `maximum`."""
    if not points:
        return []
    choisis = [points[0]]
    reste = 0.0
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        lg = float(np.hypot(x1 - x0, y1 - y0))
        t = pas - reste
        while t <= lg:
            choisis.append((x0 + (x1 - x0) * t / lg, y0 + (y1 - y0) * t / lg))
            t += pas
        reste = (reste + lg) % pas if lg else reste
    if len(choisis) > maximum:
        idx = np.linspace(0, len(choisis) - 1, maximum).round().astype(int)
        choisis = [choisis[i] for i in idx]
    return [(int(round(x)), int(round(y))) for x, y in choisis]
