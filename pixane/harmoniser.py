"""Calque > Harmoniser avec l'arrière-plan : un objet collé (calque avec de la transparence) prend la lumière de la
photo en dessous : mêmes noirs et mêmes blancs, même couleur de lumière, bord adouci.

Couleur de la lumière : estimée sur les parties claires (là où la lumière se voit le mieux), pas sur la moyenne :
une chemise rouge posée sur de l'herbe ne doit pas devenir verte.
Référence : la photo en dessous, autour de l'objet (anneau de la taille de l'objet), ou toute la photo si l'objet
couvre presque tout.
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageFilter

from .langue import tr

NEUTRES = {"lumiere": 0, "couleur": 0, "bord": 0}
DEPART = {"lumiere": 70, "couleur": 70, "bord": 1}

_M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]], np.float32)
_BLANC = np.array([0.9505, 1.0, 1.089], np.float32)


def lab(rgb: np.ndarray) -> np.ndarray:
    c = rgb.astype(np.float32) / 255
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    xyz = c @ _M.T / _BLANC
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def rgb(lab_: np.ndarray) -> np.ndarray:
    """Lab -> RGB float 0..255 (non borné)."""
    fy = (lab_[..., 0] + 16) / 116
    fx = fy + lab_[..., 1] / 500
    fz = fy - lab_[..., 2] / 200
    f = np.stack([fx, fy, fz], -1)
    xyz = np.where(f > 0.2069, f ** 3, (f - 16 / 116) / 7.787) * _BLANC
    c = xyz @ np.linalg.inv(_M).T.astype(np.float32)
    c = np.clip(c, 0, None)
    c = np.where(c > 0.0031308, 1.055 * c ** (1 / 2.4) - 0.055, 12.92 * c)
    return c * 255


def reference(fond: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    """Masque booléen de la photo à imiter : un anneau autour de l'objet (alpha 0..255), sinon toute la photo."""
    objet = alpha > 127
    n = int(objet.sum())
    if n == 0:
        return np.ones(alpha.shape, bool)
    r = float(max(8.0, np.sqrt(n) / 2))
    autour = np.asarray(Image.fromarray(np.where(objet, 255, 0).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(r / 2)), np.uint8) > 3
    anneau = autour & (alpha < 20) & (fond[..., 3] > 127)
    if anneau.sum() < 200:
        anneau = (alpha < 20) & (fond[..., 3] > 127)
    if anneau.sum() < 200:
        anneau = fond[..., 3] > 127
    return anneau


def mesures(lab_px: np.ndarray) -> dict:
    """Noirs, blancs (L) et couleur de la lumière (a, b des parties claires) d'un lot de pixels Lab (n, 3)."""
    if len(lab_px) > 200_000:
        lab_px = lab_px[np.random.default_rng(0).choice(len(lab_px), 200_000, replace=False)]
    L = lab_px[:, 0]
    bas, haut = np.percentile(L, 3), np.percentile(L, 97)
    clairs = lab_px[L >= np.percentile(L, 85)]
    return {"bas": float(bas), "haut": float(haut), "a": float(clairs[:, 1].mean()), "b": float(clairs[:, 2].mean())}


def harmoniser(calque: np.ndarray, ref: dict, p: dict) -> np.ndarray:
    """calque RGBA uint8 (l'objet) ; ref : mesures de la photo autour ; p (0..100 : lumiere, couleur ; bord en px)."""
    out = calque.copy()
    alpha = calque[..., 3]
    vis = alpha > 127
    if not vis.any():
        return out
    lo = lab(calque[..., :3])
    obj = mesures(lo[vis])
    l = p.get("lumiere", 0) / 100
    c = p.get("couleur", 0) / 100
    res = lo.copy()
    if l > 0:
        k = (ref["haut"] - ref["bas"]) / max(5.0, obj["haut"] - obj["bas"])
        k = float(np.clip(k, 0.5, 2.0))
        cible = (lo[..., 0] - obj["bas"]) * k + ref["bas"]
        res[..., 0] = lo[..., 0] + (cible - lo[..., 0]) * l
    if c > 0:
        # la teinte de la lumière passe, en entier sur les parties claires, à moitié sur les sombres
        poids = 0.5 + 0.5 * np.clip(lo[..., 0] / 100, 0, 1)
        res[..., 1] += (ref["a"] - obj["a"]) * c * poids
        res[..., 2] += (ref["b"] - obj["b"]) * c * poids
    if l > 0 or c > 0:
        out[..., :3] = np.where(vis[..., None] | (alpha[..., None] > 0),
                                np.clip(np.round(rgb(res)), 0, 255), calque[..., :3]).astype(np.uint8)
    b = float(p.get("bord", 0))
    if b > 0:
        flou = np.asarray(Image.fromarray(alpha).filter(ImageFilter.GaussianBlur(b)), np.float32)
        # le bord s'adoucit vers l'intérieur : l'objet ne déborde pas
        out[..., 3] = np.minimum(alpha.astype(np.float32), np.clip((flou - 127.5) * 2, 0, 255)).astype(np.uint8)
    return out


def panneau_harmoniser():
    from PySide6.QtWidgets import QLabel, QVBoxLayout
    from .dialogues_reglage import Curseur, _Panneau

    class PanneauHarmoniser(_Panneau):
        def __init__(self, params, histo):
            super().__init__(params, histo)
            lay = QVBoxLayout(self)
            info = QLabel(tr("L'objet du calque choisi prend la lumière de la photo qui l'entoure."))
            info.setWordWrap(True)
            lay.addWidget(info)
            self.c = {}
            for cle, libelle, maxi, unite in (("lumiere", tr("Lumière (noirs et blancs)"), 100, " %"),
                                              ("couleur", tr("Couleur de la lumière"), 100, " %"),
                                              ("bord", tr("Adoucir le bord"), 20, " px")):
                c = Curseur(libelle, 0, maxi, self.p.get(cle, DEPART[cle]), unite)
                c.change.connect(self._lire)
                lay.addWidget(c)
                self.c[cle] = c

        def _lire(self):
            self.p = {k: int(c.valeur()) for k, c in self.c.items()}
            self.change.emit()

    return PanneauHarmoniser
