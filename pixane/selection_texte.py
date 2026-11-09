"""Sélection de texte : un cadre autour d'un texte -> les lettres seules, bords progressifs (traits fins gardés).

Principe (sans IA, numpy seul) :
1. Les couleurs du cadre sont rangées en groupes (k-moyennes en Lab, la couleur comme l'œil la voit).
2. Fond = groupes présents sur au moins deux côtés du cadre (autant que dans le reste), ou surtout collés au bord.
   Un texte coupé par le cadre ne touche qu'un côté : il reste du texte.
3. Un groupe trop proche du fond (flou clair, franges d'une photo) est du fond ; « trop proche » se juge par rapport
   au contraste du texte principal. Les liserés d'anticrénelage (mélange texte / fond) ne sont pas du texte.
4. Les taches aux bords flous et les points isolés sont retirés ; les petits trous dans une lettre (grain du JPEG)
   sont bouchés ; « lettres pleines » bouche tous les trous (motifs, intérieur des O).
5. Bords : démélange local entre la couleur du texte et celle du fond -> sélection progressive (déliés de 1 px).
Corrections : clic sur un morceau (Alt : l'enlever, Maj : l'ajouter), Ctrl en plus : toute cette couleur du cadre.
"""
from __future__ import annotations

import numpy as np

from .selection_auto import etiquettes

GROUPES = 10                 # nombre de groupes de couleurs dans le cadre
ECHANTILLON = 40_000         # pixels tirés pour trouver les groupes (rapide même pour un grand cadre)


# ---------------------------------------------------------------------------------------------- outils numpy
def lab(rgb: np.ndarray) -> np.ndarray:
    """RGB uint8 -> Lab (float32)."""
    c = rgb.astype(np.float32) / 255
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    m = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]], np.float32)
    xyz = c @ m.T / np.array([0.9505, 1.0, 1.089], np.float32)
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def _plus_proche(x: np.ndarray, c: np.ndarray) -> np.ndarray:
    """Numéro du centre le plus proche de chaque point (sans gros tableau intermédiaire)."""
    meilleur = np.full(len(x), np.inf, np.float32)
    e = np.zeros(len(x), np.int32)
    for j in range(len(c)):
        d = ((x - c[j]) ** 2).sum(-1)
        mieux = d < meilleur
        meilleur[mieux], e[mieux] = d[mieux], j
    return e


def _kmeans(x: np.ndarray, k: int, tours: int = 15) -> np.ndarray:
    rng = np.random.default_rng(0)
    k = min(k, len(x))
    c = x[rng.choice(len(x), k, replace=False)].copy()
    for _ in range(tours):
        e = _plus_proche(x, c)
        for j in range(k):
            if (e == j).any():
                c[j] = x[e == j].mean(0)
    return c


def _moyenne(a: np.ndarray, n: int) -> np.ndarray:
    """Moyenne sur un carré n × n (bords répétés)."""
    r = n // 2
    p = np.pad(a.astype(np.float64), r, mode="edge")
    c = np.vstack([np.zeros((1, p.shape[1])), p.cumsum(0)])
    v = c[n:] - c[:-n]
    c = np.hstack([np.zeros((v.shape[0], 1)), v.cumsum(1)])
    return ((c[:, n:] - c[:, :-n]) / (n * n)).astype(np.float32)


def _grossir(m: np.ndarray, fois: int = 1) -> np.ndarray:
    for _ in range(fois):
        z = m.copy()
        z[1:] |= m[:-1]
        z[:-1] |= m[1:]
        z[:, 1:] |= m[:, :-1]
        z[:, :-1] |= m[:, 1:]
        m = z
    return m


def _max3(a: np.ndarray) -> np.ndarray:
    """Maximum sur 3 × 3."""
    p = np.pad(a, 1, mode="edge")
    v = np.maximum(np.maximum(p[:-2], p[1:-1]), p[2:])
    return np.maximum(np.maximum(v[:, :-2], v[:, 1:-1]), v[:, 2:])


def _dist_segment(p, a, b):
    v = b - a
    t = float(np.clip(((p - a) * v).sum() / max(float((v * v).sum()), 1e-6), 0, 1))
    return float(np.linalg.norm(p - (a + t * v))), t


# ---------------------------------------------------------------------------------------------- analyse
class Analyse:
    """Ce qui est calculé une fois par cadre ; les corrections ne refont que la fin (calculer)."""

    def __init__(self, rgb: np.ndarray):
        self.h, self.w = rgb.shape[:2]
        self.L = lab(rgb)
        x = self.L.reshape(-1, 3)
        pas = max(1, len(x) // ECHANTILLON)
        self.c = _kmeans(x[::pas], GROUPES)
        k = len(self.c)
        self.e = _plus_proche(x, self.c).reshape(self.h, self.w)
        self.texte = self._classer(k)
        self.ajouts = np.zeros((self.h, self.w), bool)      # morceaux ajoutés à la main (Maj+clic)
        self.retraits = np.zeros((self.h, self.w), bool)    # morceaux enlevés à la main (Alt+clic)

    def _classer(self, k: int) -> np.ndarray:
        e, c, h, w = self.e, self.c, self.h, self.w
        ep = max(1, min(3, h // 8, w // 8))
        bord = np.zeros((h, w), bool)
        bord[:ep], bord[-ep:], bord[:, :ep], bord[:, -ep:] = True, True, True, True
        pa = np.bincount(e.ravel(), minlength=k) / e.size
        pb = np.bincount(e[bord], minlength=k) / bord.sum()
        cotes = [e[:ep], e[-ep:], e[:, :ep], e[:, -ep:]]
        nb_cotes = np.array([sum((cc == j).mean() >= 0.03 for cc in cotes) for j in range(k)])
        fond = (pb >= 0.35 * pa) & (nb_cotes >= 2)
        fond |= (pb >= 1.5 * pa) & (pb > 0.01)            # surtout collé au bord du cadre : du fond qui dépasse
        fond |= pa < 0.001                                 # groupes minuscules : traités par le démélange
        if fond.all():                                     # cadre sans rien de différent : le moins présent au bord
            fond[np.argmin(pb / np.maximum(pa, 1e-6))] = False
        # contraste avec le fond, jugé par rapport au texte principal
        vrai_fond = fond & (pa > 0.02)
        if vrai_fond.any():
            dist = np.array([min(np.linalg.norm(c[j] - c[i]) for i in np.nonzero(vrai_fond)[0]) for j in range(k)])
            cand = ~fond
            if cand.any():
                ref = dist[np.argmax(np.where(cand, pa * dist, -1))]
                fond |= cand & ((dist < 12) | (dist < 0.5 * ref))
        # liserés : groupe entre un groupe de texte plus présent et un groupe de fond
        texte = ~fond
        for j in np.nonzero(texte)[0]:
            for t_ in np.nonzero(~fond)[0]:
                if t_ == j or pa[t_] <= pa[j]:
                    continue
                if any(d < 5 and 0.1 < t < 0.9 for d, t in (_dist_segment(c[j], c[t_], c[f]) for f in np.nonzero(fond)[0])):
                    texte[j] = False
                    break
        return texte

    # ------------------------------------------------------------------ corrections
    def morceau(self, x: int, y: int) -> np.ndarray:
        """Le morceau d'un seul tenant, de la même couleur (groupe), sous le point."""
        meme = self.e == self.e[y, x]
        lab_, _ = etiquettes(meme)
        n = lab_[y, x]
        return lab_ == n if n >= 0 else np.zeros_like(meme)

    def corriger(self, x: int, y: int, ajouter: bool, toute_couleur: bool):
        if not (0 <= x < self.w and 0 <= y < self.h):
            return
        if toute_couleur:
            j = self.e[y, x]
            self.texte[j] = ajouter
            zone = self.e == j
            self.ajouts &= ~zone
            self.retraits &= ~zone
            return
        if not ajouter and self._dernier is not None and self._dernier[y, x] > 0:
            # enlever : le morceau de la sélection sous le clic (tous groupes confondus)
            lab_, _ = etiquettes(self._dernier > 0)
            zone = lab_ == lab_[y, x]
        else:
            zone = self.morceau(x, y)
        if ajouter:
            self.ajouts |= zone
            self.retraits &= ~zone
        else:
            self.retraits |= zone
            self.ajouts &= ~zone

    _dernier = None

    # ------------------------------------------------------------------ masque
    def calculer(self, pleines: bool = False) -> np.ndarray:
        """Masque 0..255 (taille du cadre)."""
        L, h, w = self.L, self.h, self.w
        coeur = self.texte[self.e]
        coeur = self._nettoyer(coeur)
        coeur = (coeur | self.ajouts) & ~self.retraits
        coeur = self._boucher(coeur, pleines)
        a = self._demelanger(coeur)
        a = np.where(self.retraits, 0, a)
        res = (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)
        self._dernier = res
        return res

    def _nettoyer(self, coeur: np.ndarray) -> np.ndarray:
        """Taches aux bords flous (un fond flou n'est pas du texte) et points isolés : retirés."""
        lab_, tailles = etiquettes(coeur)
        n = len(tailles)
        if not n:
            return coeur
        L = self.L
        g = np.zeros((self.h, self.w), np.float32)
        g[:, 1:-1] = np.linalg.norm(L[:, 2:] - L[:, :-2], axis=-1) / 2
        g[1:-1] = np.maximum(g[1:-1], np.linalg.norm(L[2:] - L[:-2], axis=-1) / 2)
        g = _max3(g)               # mesuré aussi juste à côté : un trait d'1 px n'a pas d'écart sur lui-même
        contour = coeur & _grossir(~coeur)
        if not contour.any():
            return coeur
        idx = lab_[contour]
        moy = np.bincount(idx, weights=g[contour], minlength=n) / np.maximum(np.bincount(idx, minlength=n), 1)
        ref = float(np.median(g[contour])) or 1.0
        garde = ((moy >= 0.35 * ref) | (tailles < 30)) & (tailles >= 4)
        return coeur & (lab_ >= 0) & garde[np.maximum(lab_, 0)]

    def _boucher(self, coeur: np.ndarray, pleines: bool) -> np.ndarray:
        """Trous fermés dans les lettres : les petits (plus petits que l'épaisseur du trait) ou tous (pleines)."""
        lab_, tailles = etiquettes(coeur)
        trous, t_tailles = etiquettes(~coeur)
        if not len(tailles) or not len(t_tailles):
            return coeur
        touche_cadre = np.zeros(len(t_tailles), bool)
        for b in (trous[0], trous[-1], trous[:, 0], trous[:, -1]):
            touche_cadre[b[b >= 0]] = True
        if pleines:
            boucher = ~touche_cadre
        else:
            bordc = coeur & _grossir(~coeur)
            perim = np.bincount(lab_[bordc], minlength=len(tailles))
            epais = 2 * tailles / np.maximum(perim, 1)              # épaisseur moyenne du trait de chaque lettre
            voisin = np.full(len(t_tailles), -1)
            ys, xs = np.nonzero(~coeur)
            for dy, dx in ((0, 1), (1, 0), (0, -1), (-1, 0)):
                l2 = lab_[np.clip(ys + dy, 0, self.h - 1), np.clip(xs + dx, 0, self.w - 1)]
                ok = l2 >= 0
                voisin[trous[ys[ok], xs[ok]]] = l2[ok]
            seuil = np.where(voisin >= 0, 0.8 * epais[np.maximum(voisin, 0)] ** 2, 0)
            boucher = ~touche_cadre & (t_tailles < seuil)
        return coeur | ((trous >= 0) & boucher[np.maximum(trous, 0)])

    def _demelanger(self, coeur: np.ndarray) -> np.ndarray:
        """Bords progressifs : part de texte de chaque pixel, entre la couleur du texte et celle du fond autour."""
        L = self.L
        fm = ~_grossir(coeur, 2)
        n_f = np.maximum(_moyenne(fm, 21), 1e-3)
        n_t = np.maximum(_moyenne(coeur, 9), 1e-3)
        fondL = np.stack([_moyenne(np.where(fm, L[..., i], 0), 21) / n_f for i in range(3)], -1)
        txtL = np.stack([_moyenne(np.where(coeur, L[..., i], 0), 9) / n_t for i in range(3)], -1)
        v = txtL - fondL
        vv = (v * v).sum(-1)
        a = ((L - fondL) * v).sum(-1) / np.maximum(vv, 1)
        pres = (_moyenne(coeur, 9) > 0) & (vv > 100) & _grossir(coeur, 2)
        a = np.where(pres, np.clip(a, 0, 1), 0)
        a = np.where(coeur, np.clip(a, 0.6, 1), a)
        return np.where(coeur & (a > 0.85), 1.0, a)


def a_plat_rgb(rgba: np.ndarray) -> np.ndarray:
    """RGB vu par l'outil : les zones transparentes sur un fond uni contrasté (comme pour l'IA)."""
    from .document import a_plat
    return a_plat(rgba)
