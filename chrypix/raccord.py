"""Agrandir (outpaint) : préparation de l'image pour Flux et raccord final, faits par Chrypix.

Pourquoi pas l'extension « Crop and Stitch » : son recollage mélangeait l'ajout avec des pixels de bord étirés
(effet fantôme) et laissait apparaître le liseré clair que beaucoup d'images ont sur leurs bords.

Étapes :
1. preparer() : enlève le liseré éventuel des bords à agrandir, réduit l'image agrandie à ~1 mégapixel
   (taille de travail de Flux), et marque la zone à peindre : l'ajout + une bande de raccord dans l'original.
2. Flux peint toute cette zone (recette « agrandir »).
3. finaliser() : remet le résultat à la taille réelle, accorde les couleurs de l'ajout sur l'original (mesurées
   dans la bande de raccord) puis fond la photo d'origine intacte avec la bande peinte par Flux.
"""
from __future__ import annotations

import io
import math
from dataclasses import dataclass

import numpy as np
from PIL import Image

PIXELS_TRAVAIL = 1024 * 1024   # taille de travail de Flux
BANDE_TRAVAIL = 24             # bande de raccord peinte dans l'original (px de travail)
LISERE_MAX = 8                 # liseré de bord maximal détecté (px)
SEUIL_LISERE = 3.0             # écart de luminosité moyen qui signale un liseré
ECART_MAX = 20.0               # correction de teinte maximale (niveaux sur 255)
LISSAGE = 40                   # lissage de l'écart de couleur le long du bord (px réels)


@dataclass
class Geometrie:
    coupe: tuple[int, int, int, int]      # liseré enlevé : haut, bas, gauche, droite
    marges: tuple[int, int, int, int]     # ajout en px réels : haut, bas, gauche, droite
    taille: tuple[int, int]               # taille finale (l, h)
    travail: tuple[int, int]              # taille de travail (l, h)
    bande: tuple[float, float]            # largeur réelle de la bande de raccord (x, y)


def _lisere(lignes: np.ndarray) -> int:
    """lignes : luminosité moyenne des lignes depuis le bord vers l'intérieur. Renvoie le nombre à enlever."""
    if len(lignes) <= LISERE_MAX + 2:
        return 0
    reference = lignes[LISERE_MAX:LISERE_MAX + 3].mean()
    n = 0
    for i in range(LISERE_MAX):
        if abs(lignes[i] - reference) > SEUIL_LISERE:
            n = i + 1
    return n


def _lumi(rgb: np.ndarray) -> np.ndarray:
    return rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114


def lisere_auto(original: np.ndarray) -> tuple[int, int, int, int]:
    """Liseré clair ou foncé détecté sur chaque bord (haut, bas, gauche, droite), en px."""
    lum = _lumi(original.astype(np.float32))
    lignes, colonnes = lum.mean(axis=1), lum.mean(axis=0)
    return _lisere(lignes), _lisere(lignes[::-1]), _lisere(colonnes), _lisere(colonnes[::-1])


def preparer(original: np.ndarray, haut: float, bas: float, gauche: float, droite: float,
             enlever_lisere: bool = True):
    """original : (h, w, 3) uint8. Renvoie (png RGBA pour ComfyUI, géométrie, original sans liseré).
    enlever_lisere=False quand le bord abîmé a déjà été choisi (et retiré) dans Chrypix."""
    lum = _lumi(original.astype(np.float32))
    auto = enlever_lisere
    ch = _lisere(lum.mean(axis=1)) if auto and haut > 0 else 0
    cb = _lisere(lum.mean(axis=1)[::-1]) if auto and bas > 0 else 0
    cg = _lisere(lum.mean(axis=0)) if auto and gauche > 0 else 0
    cd = _lisere(lum.mean(axis=0)[::-1]) if auto and droite > 0 else 0
    h0, w0 = original.shape[:2]
    orig = original[ch:h0 - cb, cg:w0 - cd]
    h, w = orig.shape[:2]

    mh, mb = round(h * haut / 100), round(h * bas / 100)
    mg, md = round(w * gauche / 100), round(w * droite / 100)
    W, H = w + mg + md, h + mh + mb
    echelle = min(1.0, math.sqrt(PIXELS_TRAVAIL / (W * H)))
    Wt, Ht = max(64, round(W * echelle / 16) * 16), max(64, round(H * echelle / 16) * 16)
    sx, sy = Wt / W, Ht / H

    # l'original réduit, posé sur la toile de travail ; l'ajout est rempli en prolongeant les bords
    x0, y0 = round(mg * sx), round(mh * sy)
    wt, ht = max(1, round((w + mg) * sx) - x0), max(1, round((h + mh) * sy) - y0)
    petit = np.asarray(Image.fromarray(orig).resize((wt, ht), Image.LANCZOS))
    toile = np.pad(petit, ((y0, Ht - y0 - ht), (x0, Wt - x0 - wt), (0, 0)), mode="edge")

    # zone à peindre : tout sauf l'original rétréci de la bande de raccord, côtés agrandis seulement
    masque = np.ones((Ht, Wt), np.uint8)
    b = BANDE_TRAVAIL
    ya = y0 + (b if mh > 0 else 0)
    yb = y0 + ht - (b if mb > 0 else 0)
    xa = x0 + (b if mg > 0 else 0)
    xb = x0 + wt - (b if md > 0 else 0)
    masque[max(ya, 0):max(yb, ya), max(xa, 0):max(xb, xa)] = 0

    rgba = np.dstack([toile, (1 - masque) * 255]).astype(np.uint8)  # transparent = à peindre
    tampon = io.BytesIO()
    Image.fromarray(rgba, "RGBA").save(tampon, "PNG", compress_level=1)
    geo = Geometrie(coupe=(ch, cb, cg, cd), marges=(mh, mb, mg, md), taille=(W, H), travail=(Wt, Ht),
                    bande=(b / sx, b / sy))
    return tampon.getvalue(), geo, orig


def _lisser(profil: np.ndarray, sigma: float) -> np.ndarray:
    r = int(sigma * 2.5)
    if r < 1 or len(profil) < 3:
        return profil
    x = np.arange(-r, r + 1)
    noyau = np.exp(-(x ** 2) / (2 * sigma ** 2))
    noyau /= noyau.sum()
    bord = np.pad(profil, ((r, r), (0, 0)), mode="edge")
    return np.stack([np.convolve(bord[:, c], noyau, mode="valid") for c in range(profil.shape[1])], axis=1)


def _flou(a: np.ndarray, sigma: float) -> np.ndarray:
    """Flou gaussien séparable sur un tableau (h, w, c)."""
    for axe in (0, 1):
        b = np.moveaxis(a, axe, 0)
        forme = b.shape
        b = _lisser(b.reshape(forme[0], -1), sigma).reshape(forme)
        a = np.moveaxis(b, 0, axe)
    return a


def _champ_correction(ecart: np.ndarray, bande: tuple[int, int], marges, taille) -> np.ndarray:
    """ecart : (h, w, 3) original - Flux sur la zone de l'original. Renvoie la correction (H, W, 3)."""
    W, H = taille
    mh, mb, mg, md = marges
    h, w = ecart.shape[:2]
    k = 8                                                   # calcul en basse résolution
    hp, wp = max(2, h // k), max(2, w // k)
    petit = lambda x: np.dstack([np.asarray(Image.fromarray(x[:, :, c]).resize((wp, hp), Image.BOX))
                                 for c in range(x.shape[2])])
    # poids : 1 dans la bande de raccord des côtés agrandis, 0 ailleurs
    m = np.zeros((h, w), np.float32)
    bx, by = max(2, bande[0]), max(2, bande[1])
    if mh > 0: m[:by] = 1
    if mb > 0: m[-by:] = 1
    if mg > 0: m[:, :bx] = 1
    if md > 0: m[:, -bx:] = 1
    # les pixels où Flux a dessiné autre chose (une feuille décalée…) ne comptent presque pas :
    # on ne cherche qu'un petit écart de teinte, pas les différences de dessin
    ecart = ecart.astype(np.float32)
    m = m / (1 + (np.abs(ecart).mean(axis=2) / 6) ** 2)
    e = petit(ecart * m[:, :, None])
    p = petit(m[:, :, None])
    s = LISSAGE / k
    e, p = _flou(e, s), _flou(p, s)
    champ = np.clip(e / np.maximum(p, 1e-3), -ECART_MAX, ECART_MAX)
    # agrandi aux marges (en prolongeant les bords), puis remis à la taille réelle
    ph, pb, pg, pd = (round(v / k) + 2 for v in (mh, mb, mg, md))
    champ = np.pad(champ, ((ph, pb), (pg, pd), (0, 0)), mode="edge")
    champ = _flou(champ, s)
    champ = np.dstack([np.asarray(Image.fromarray(champ[:, :, c].astype(np.float32)).resize(
        (w + pg * k + pd * k, h + ph * k + pb * k), Image.BILINEAR)) for c in range(3)])
    champ = champ[ph * k - mh: ph * k - mh + H, pg * k - mg: pg * k - mg + W]
    # extinction vers les bords extérieurs
    def rampe(n_avant, n, n_apres):
        return np.concatenate([np.linspace(0, 1, n_avant, dtype=np.float32), np.ones(n, np.float32),
                               np.linspace(1, 0, n_apres, dtype=np.float32)])
    poids = rampe(mh, h, mb)[:, None] * rampe(mg, w, md)[None, :]
    return champ * poids[:, :, None]


def finaliser(orig: np.ndarray, flux: np.ndarray, geo: Geometrie) -> np.ndarray:
    """orig : original sans liseré (h, w, 3) ; flux : résultat de Flux à la taille de travail. -> (H, W, 3) uint8."""
    W, H = geo.taille
    mh, mb, mg, md = geo.marges
    h, w = orig.shape[:2]
    R = np.asarray(Image.fromarray(flux).resize((W, H), Image.LANCZOS)).astype(np.float32)
    O = orig.astype(np.float32)
    y0, x0 = mh, mg
    zone = R[y0:y0 + h, x0:x0 + w]                       # la version de Flux de la bande de raccord
    bx, by = int(geo.bande[0] * 0.8), int(geo.bande[1] * 0.8)
    mx, my = max(2, min(bx, w // 4)), max(2, min(by, h // 4))

    # 1. accorder les couleurs de l'ajout sur l'original : l'écart (original - Flux) mesuré dans la bande de
    #    raccord devient un champ lisse, prolongé vers l'extérieur et qui s'éteint jusqu'au bord (pas de marche)
    R += _champ_correction(O - zone, (mx, my), geo.marges, (W, H))

    # 2. fondre l'original intact dans la bande de raccord (0 au bord -> 1 au fond de la bande)
    ys = np.arange(h, dtype=np.float32)[:, None]
    xs = np.arange(w, dtype=np.float32)[None, :]
    alpha = np.ones((h, w), np.float32)
    if mh > 0:
        alpha = np.minimum(alpha, np.clip(ys / max(1, by), 0, 1))
    if mb > 0:
        alpha = np.minimum(alpha, np.clip((h - 1 - ys) / max(1, by), 0, 1))
    if mg > 0:
        alpha = np.minimum(alpha, np.clip(xs / max(1, bx), 0, 1))
    if md > 0:
        alpha = np.minimum(alpha, np.clip((w - 1 - xs) / max(1, bx), 0, 1))
    alpha = (alpha * alpha * (3 - 2 * alpha))[:, :, None]   # transition douce
    R[y0:y0 + h, x0:x0 + w] = alpha * O + (1 - alpha) * R[y0:y0 + h, x0:x0 + w]
    return np.clip(R + 0.5, 0, 255).astype(np.uint8)
