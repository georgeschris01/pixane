"""IA > Retouche portrait : peau lissée (les contours, les cils, les cheveux et le grain de la peau restent), yeux
éclaircis, dents blanchies. SAM 3.1 trouve les parties du visage (recettes.visage) ; le calcul, lui, est fait ici,
avec un aperçu en direct.

Peau : filtre guidé (He et al.), qui lisse les petites variations (boutons, rougeurs, ridules) et garde les grands
contrastes (contours du nez, des yeux, mèches de cheveux) ; puis une partie du grain fin est remise, pour ne pas
avoir une peau « en plastique ».
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageFilter

from .langue import tr

NEUTRES = {"peau": 0, "grain": 60, "yeux": 0, "dents": 0}
DEPART = {"peau": 50, "grain": 60, "yeux": 35, "dents": 35}


def _flou(a: np.ndarray, r: float) -> np.ndarray:
    """Flou gaussien d'un tableau float (h, w) ou (h, w, c), valeurs quelconques."""
    if r <= 0.3:
        return a.copy()
    if a.ndim == 2:
        return _flou(a[..., None], r)[..., 0]
    out = np.empty_like(a)
    for c in range(a.shape[2]):
        lo, hi = float(a[..., c].min()), float(a[..., c].max())
        k = 255 / (hi - lo) if hi > lo else 1.0
        im = Image.fromarray(np.round((a[..., c] - lo) * k).astype(np.uint8)).filter(ImageFilter.GaussianBlur(float(r)))
        out[..., c] = np.asarray(im, np.float32) / k + lo
    return out


def _boite(a: np.ndarray, r: int) -> np.ndarray:
    """Moyenne sur un carré de côté 2r+1 (bords : moyenne de ce qui existe), par sommes cumulées."""
    if r < 1:
        return a.astype(np.float32)
    h, w = a.shape[:2]
    c = np.cumsum(np.cumsum(np.pad(a.astype(np.float64), [(1, 0), (1, 0)] + [(0, 0)] * (a.ndim - 2)), 0), 1)
    y0 = np.clip(np.arange(h) - r, 0, h)
    y1 = np.clip(np.arange(h) + r + 1, 0, h)
    x0 = np.clip(np.arange(w) - r, 0, w)
    x1 = np.clip(np.arange(w) + r + 1, 0, w)
    s = c[y1][:, x1] - c[y0][:, x1] - c[y1][:, x0] + c[y0][:, x0]
    n = ((y1 - y0)[:, None] * (x1 - x0)[None, :]).astype(np.float64)
    if a.ndim == 3:
        n = n[..., None]
    return (s / n).astype(np.float32)


def filtre_guide(rgb: np.ndarray, r: int, eps: float) -> np.ndarray:
    """Filtre guidé (chaque canal guidé par lui-même) : lisse ce qui varie peu, garde les contours. eps en
    (niveaux sur 255)²."""
    i = rgb.astype(np.float32)
    m = _boite(i, r)
    var = _boite(i * i, r) - m * m
    a = var / (var + eps)
    b = m - a * m
    return _boite(a, r) * i + _boite(b, r)


def _taille_visage(visage: np.ndarray) -> float:
    """Côté approximatif d'un visage (px) : pour régler les rayons des filtres."""
    n = float((visage > 0.5).sum())
    return max(40.0, np.sqrt(n)) if n else 200.0


def zones(parties: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Masques 0..1 (h, w) à partir des masques de SAM (0..255) : peau (visage + cou, sans yeux, sourcils, lèvres,
    dents, avec une marge), yeux, dents ; bords adoucis."""
    def m(nom):
        a = parties.get(nom)
        return None if a is None else (a > 127)
    visage = m("visage")
    if visage is None:
        raise ValueError("pas de masque de visage")
    taille = _taille_visage(visage)
    peau = visage | (m("cou") if m("cou") is not None else False)
    exclus = np.zeros_like(visage)
    for nom in ("yeux", "sourcils", "levres", "dents"):
        if m(nom) is not None:
            exclus |= m(nom)
    marge = max(1.5, taille / 60)
    exclus_f = _flou(exclus.astype(np.float32), marge) > 0.05
    doux = max(1.0, taille / 120)
    peau = np.clip(_flou((peau & ~exclus_f).astype(np.float32), doux), 0, 1)
    vide = np.zeros(visage.shape, np.float32)
    yeux = np.clip(_flou(m("yeux").astype(np.float32), doux / 2), 0, 1) if m("yeux") is not None else vide
    dents = np.clip(_flou(m("dents").astype(np.float32), doux / 2), 0, 1) if m("dents") is not None else vide
    return {"peau": peau, "yeux": yeux, "dents": dents, "taille": taille}


def retoucher(rgba: np.ndarray, z: dict, p: dict) -> np.ndarray:
    """rgba (h, w, 4) uint8 -> retouché selon p (0..100 : peau, grain, yeux, dents). Seul le cadre autour du
    visage est calculé."""
    out = rgba.copy()
    zone = np.maximum(np.maximum(z["peau"], z["yeux"]), z["dents"]) > 0.002
    if not zone.any():
        return out
    taille = z["taille"]
    ys, xs = np.nonzero(zone)
    marge = int(taille / 4) + 4
    y0, y1 = max(0, ys.min() - marge), min(rgba.shape[0], ys.max() + 1 + marge)
    x0, x1 = max(0, xs.min() - marge), min(rgba.shape[1], xs.max() + 1 + marge)
    rgb = rgba[y0:y1, x0:x1, :3].astype(np.float32)
    res = rgb.copy()
    peau = z["peau"][y0:y1, x0:x1, None]
    yeux = z["yeux"][y0:y1, x0:x1, None]
    dents = z["dents"][y0:y1, x0:x1, None]
    f = p.get("peau", 0) / 100
    if f > 0 and peau.max() > 0:
        r = max(2, int(round(taille / 45)))
        lisse = filtre_guide(rgb, r, (6 + 20 * f) ** 2)
        lisse = filtre_guide(lisse, max(2, r // 2), (4 + 12 * f) ** 2)
        grain = rgb - _flou(rgb, max(0.6, taille / 300))          # pores, grain fin
        lisse = lisse + grain * (p.get("grain", 60) / 100)
        res = res + (lisse - res) * peau * min(1.0, f * 1.4)
    f = p.get("yeux", 0) / 100
    if f > 0 and yeux.max() > 0:
        net = res + (res - _flou(res, max(0.8, taille / 160))) * 1.2 * f   # plus de netteté, d'éclat
        net = net * (1 + 0.12 * f) + 4 * f
        res = res + (net - res) * yeux
    f = p.get("dents", 0) / 100
    if f > 0 and dents.max() > 0:
        gris = res.mean(axis=2, keepdims=True)
        jaune = np.clip((res[..., :1] + res[..., 1:2]) / 2 - res[..., 2:3], 0, None)   # le jaune : bleu en moins
        blanc = res + (gris - res) * 0.75 * f
        blanc[..., 2:3] += jaune * 0.5 * f
        blanc = blanc * (1 + 0.10 * f) + 3 * f
        res = res + (blanc - res) * dents
    out[y0:y1, x0:x1, :3] = np.clip(np.round(res), 0, 255).astype(np.uint8)
    return out


def panneau_portrait(nb_visages_vus: bool = True):
    """Panneau de la fenêtre de réglage : quatre curseurs."""
    from PySide6.QtWidgets import QLabel, QVBoxLayout
    from .dialogues_reglage import Curseur, _Panneau

    class PanneauPortrait(_Panneau):
        def __init__(self, params, histo):
            super().__init__(params, histo)
            lay = QVBoxLayout(self)
            info = QLabel(tr("L'IA a trouvé le visage, les yeux et les dents. Les contours, les cils et les cheveux "
                             "restent nets."))
            info.setWordWrap(True)
            lay.addWidget(info)
            self.c = {}
            for cle, libelle in (("peau", tr("Lisser la peau")), ("grain", tr("Garder le grain de la peau")),
                                 ("yeux", tr("Éclaircir les yeux")), ("dents", tr("Blanchir les dents"))):
                c = Curseur(libelle, 0, 100, self.p.get(cle, DEPART[cle]), " %")
                c.change.connect(self._lire)
                lay.addWidget(c)
                self.c[cle] = c

        def _lire(self):
            self.p = {k: int(c.valeur()) for k, c in self.c.items()}
            self.change.emit()

    return PanneauPortrait
