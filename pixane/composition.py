"""Comment les calques se posent les uns sur les autres : masque de calque, style, mode de fusion, opacité,
calques de réglage et groupes.

La liste des calques reste plate (du bas vers le haut). Un groupe est un calque « en-tête » (`groupe=True`, un
identifiant `ident`) posé juste au-dessus de ses calques ; chaque calque d'un groupe porte l'identifiant de son
groupe (`dans`). Un groupe se dessine à part (ses calques entre eux), puis se pose comme un seul calque, avec son
masque, son opacité et son mode.
Un calque de réglage (`reglage` = {"type", "params"}) n'a pas de pixels : il change tout ce qui est dessous (dans
son groupe), à travers son masque et avec son opacité.
"""
from __future__ import annotations

import weakref

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter

FORMAT_MASQUE = QImage.Format_Grayscale8

# clé : (nom affiché, mode QPainter ou None si calcul maison, clé PSD, opération OpenRaster)
MODES = {
    "normal": ("Normal", QPainter.CompositionMode_SourceOver, b"norm", "svg:src-over"),
    "obscurcir": ("Obscurcir", QPainter.CompositionMode_Darken, b"dark", "svg:darken"),
    "produit": ("Produit", QPainter.CompositionMode_Multiply, b"mul ", "svg:multiply"),
    "densite_plus": ("Densité couleur +", QPainter.CompositionMode_ColorBurn, b"idiv", "svg:color-burn"),
    "eclaircir": ("Éclaircir", QPainter.CompositionMode_Lighten, b"lite", "svg:lighten"),
    "ecran": ("Superposition", QPainter.CompositionMode_Screen, b"scrn", "svg:screen"),
    "densite_moins": ("Densité couleur −", QPainter.CompositionMode_ColorDodge, b"div ", "svg:color-dodge"),
    "addition": ("Densité linéaire − (Ajout)", QPainter.CompositionMode_Plus, b"lddg", "svg:plus"),
    "incrustation": ("Incrustation", QPainter.CompositionMode_Overlay, b"over", "svg:overlay"),
    "lumiere_tamisee": ("Lumière tamisée", QPainter.CompositionMode_SoftLight, b"sLit", "svg:soft-light"),
    "lumiere_crue": ("Lumière crue", QPainter.CompositionMode_HardLight, b"hLit", "svg:hard-light"),
    "difference": ("Différence", QPainter.CompositionMode_Difference, b"diff", "svg:difference"),
    "exclusion": ("Exclusion", QPainter.CompositionMode_Exclusion, b"smud", "svg:exclusion"),
    "teinte": ("Teinte", None, b"hue ", "svg:hue"),
    "saturation": ("Saturation", None, b"sat ", "svg:saturation"),
    "couleur": ("Couleur", None, b"colr", "svg:color"),
    "luminosite": ("Luminosité", None, b"lum ", "svg:luminosity"),
}
GROUPES_MODES = (("normal",), ("obscurcir", "produit", "densite_plus"), ("eclaircir", "ecran", "densite_moins",
                 "addition"), ("incrustation", "lumiere_tamisee", "lumiere_crue"), ("difference", "exclusion"),
                 ("teinte", "saturation", "couleur", "luminosite"))
MODE_PSD = {v[2]: k for k, v in MODES.items()}
MODE_ORA = {v[3]: k for k, v in MODES.items()}


def noms_modes() -> dict:
    """Noms affichés (écrits en entier pour la traduction)."""
    from .langue import tr
    return {"normal": tr("Normal"), "obscurcir": tr("Obscurcir"), "produit": tr("Produit"),
            "densite_plus": tr("Densité couleur +"), "eclaircir": tr("Éclaircir"), "ecran": tr("Superposition"),
            "densite_moins": tr("Densité couleur −"), "addition": tr("Densité linéaire − (Ajout)"),
            "incrustation": tr("Incrustation"), "lumiere_tamisee": tr("Lumière tamisée"),
            "lumiere_crue": tr("Lumière crue"), "difference": tr("Différence"), "exclusion": tr("Exclusion"),
            "teinte": tr("Teinte"), "saturation": tr("Saturation"), "couleur": tr("Couleur"),
            "luminosite": tr("Luminosité")}


# ------------------------------------------------------------------ masques
def masque_plein(w: int, h: int, valeur: int = 255) -> QImage:
    m = QImage(w, h, FORMAT_MASQUE)
    m.fill(valeur)
    return m


def masque_tableau(m: QImage) -> np.ndarray:
    """Masque (h, w) uint8 (copie)."""
    h, w, ligne = m.height(), m.width(), m.bytesPerLine()
    return np.frombuffer(m.constBits(), np.uint8, count=h * ligne).reshape(h, ligne)[:, :w].copy()


def masque_depuis(a: np.ndarray) -> QImage:
    a = np.ascontiguousarray(a.astype(np.uint8))
    h, w = a.shape
    return QImage(a.data, w, h, w, FORMAT_MASQUE).copy()


def masque_vers_argb(m: QImage) -> QImage:
    """Masque -> image gris opaque (pour y peindre avec les outils des calques)."""
    return m.convertToFormat(QImage.Format_ARGB32_Premultiplied)


def argb_vers_masque(img: QImage) -> QImage:
    return img.convertToFormat(FORMAT_MASQUE)


def masque_transforme(m: QImage, fonction) -> QImage:
    """Applique à un masque une transformation écrite pour les calques (QImage ARGB -> QImage ARGB).
    Ce qui sort de l'image reste visible (blanc)."""
    img = masque_vers_argb(m)
    res = fonction(img)
    fond = QImage(res.size(), QImage.Format_ARGB32_Premultiplied)
    fond.fill(Qt.white)
    p = QPainter(fond)
    p.drawImage(0, 0, res)
    p.end()
    return argb_vers_masque(fond)


def _alpha(m: QImage) -> QImage:
    return QImage(m.constBits(), m.width(), m.height(), m.bytesPerLine(), QImage.Format_Alpha8).copy()


def _format_de(img: QImage):
    """Format de travail : prémultiplié, de même profondeur que l'image (8, 16 ou 32 bits)."""
    from .profondeur import format_de
    return format_de(img)


def avec_masque(img: QImage, m: QImage) -> QImage:
    res = img.convertToFormat(_format_de(img)).copy()
    p = QPainter(res)
    p.setCompositionMode(QPainter.CompositionMode_DestinationIn)
    p.drawImage(0, 0, _alpha(m))
    p.end()
    return res


# ------------------------------------------------------------------ rendu d'un calque
_cache: "weakref.WeakKeyDictionary" = weakref.WeakKeyDictionary()


def masque_utile(c) -> bool:
    return getattr(c, "masque", None) is not None and getattr(c, "masque_actif", True)


def rendre_calque(c) -> QImage:
    """Pixels du calque, masqués puis avec leur style (gardé en mémoire tant que le calque existe)."""
    from .styles import rendre_style
    style = getattr(c, "style", None)
    a_style = style is not None and not style.vide()
    if not a_style and not masque_utile(c):
        return c.image
    r = _cache.get(c)
    if r is None:
        r = avec_masque(c.image, c.masque) if masque_utile(c) else c.image
        if a_style:
            r = rendre_style(r, style)
        _cache[c] = r
    return r


# ------------------------------------------------------------------ arbre des groupes
class Noeud:
    __slots__ = ("calque", "enfants")

    def __init__(self, calque, enfants=None):
        self.calque = calque
        self.enfants = enfants          # None : calque ordinaire ; liste (du bas vers le haut) : groupe


def arbre(calques) -> list[Noeud]:
    """Liste plate (du bas vers le haut) -> arbre. Un calque dont le groupe manque reste à la racine."""
    attente: dict = {}
    racine: list[Noeud] = []
    for c in calques:
        if getattr(c, "groupe", False):
            n = Noeud(c, attente.pop(c.ident, []))
        else:
            n = Noeud(c)
        dans = getattr(c, "dans", None)
        (attente.setdefault(dans, []) if dans is not None else racine).append(n)
    for reste in attente.values():          # calques d'un groupe absent (fichier abîmé) : à la racine
        racine.extend(reste)
    return racine


def a_plat(noeuds, dans=None) -> list:
    """Arbre -> liste plate ; corrige `dans` de chaque calque d'après sa place."""
    from dataclasses import replace
    res = []
    for n in noeuds:
        c = n.calque if getattr(n.calque, "dans", None) == dans else replace(n.calque, dans=dans)
        if n.enfants is not None:
            res.extend(a_plat(n.enfants, c.ident))
        res.append(c)
    return res


def descendants(calques, index: int) -> list[int]:
    """Index des calques contenus (à toute profondeur) dans le groupe d'index donné."""
    c = calques[index]
    if not getattr(c, "groupe", False):
        return []
    ids, res = {c.ident}, []
    for i in range(index - 1, -1, -1):
        d = getattr(calques[i], "dans", None)
        if d in ids:
            res.append(i)
            if getattr(calques[i], "groupe", False):
                ids.add(calques[i].ident)
        else:
            break
    return sorted(res)


def parents(calques, index: int) -> list:
    """Groupes qui contiennent le calque, du plus proche au plus lointain."""
    par_id = {c.ident: c for c in calques if getattr(c, "groupe", False)}
    res, d = [], getattr(calques[index], "dans", None)
    while d is not None and d in par_id and len(res) < 64:
        res.append(par_id[d])
        d = getattr(par_id[d], "dans", None)
    return res


def visible_en_vrai(calques, index: int) -> bool:
    return calques[index].visible and all(g.visible for g in parents(calques, index))


# ------------------------------------------------------------------ fusion
def fusionner(calques, largeur: int, hauteur: int, seulement_visibles: bool = True) -> QImage:
    """Image fusionnée (ARGB32 prémultiplié) des calques, du bas vers le haut."""
    return _composer(arbre(calques), largeur, hauteur, seulement_visibles)


def ecreter(img: QImage, base: QImage) -> QImage:
    """Masque d'écrêtage : img gardée seulement là où la base a des pixels (son alpha)."""
    r = img.convertToFormat(_format_de(img))
    if r is img:
        r = img.copy()
    p = QPainter(r)
    p.setCompositionMode(QPainter.CompositionMode_DestinationIn)
    p.drawImage(0, 0, base)
    p.end()
    return r


def _bits(noeuds) -> int:
    """Plus grande profondeur (8, 16, 32) des calques."""
    from .profondeur import bits
    return max([8] + [max(bits(n.calque.image), _bits(n.enfants) if n.enfants is not None else 8) for n in noeuds])


def _composer(noeuds, w: int, h: int, seulement_visibles: bool) -> QImage:
    from .profondeur import FORMATS
    res = QImage(w, h, FORMATS[_bits(noeuds)])
    res.fill(Qt.transparent)
    # base des masques d'écrêtage : (image, opacité) du dernier calque non écrêté ; False : base cachée (les calques
    # écrêtés le sont aussi) ; None : pas de base (un calque écrêté tout en bas se voit normalement)
    base = None
    for n in noeuds:
        c = n.calque
        reglage = getattr(c, "reglage", None)
        ecrete = getattr(c, "ecretage", False) and n.enfants is None and reglage is None and base is not None
        if not ecrete and reglage is None:
            base = False                              # (remplacée plus bas si le calque se voit)
        if seulement_visibles and not c.visible:
            continue
        if reglage is not None:
            base = None
            res = appliquer_reglage(res, c)
            continue
        if ecrete:
            if base is False:
                continue
            img = ecreter(rendre_calque(c), base[0])
            poser(res, img, c.opacite * base[1], getattr(c, "mode", "normal"))
            continue
        if n.enfants is not None:
            img = _composer(n.enfants, w, h, seulement_visibles)
            if masque_utile(c):
                img = avec_masque(img, c.masque)
        else:
            img = rendre_calque(c)
        base = (img, c.opacite)
        poser(res, img, c.opacite, getattr(c, "mode", "normal"))
    return res


def poser(dest: QImage, img: QImage, opacite: float, mode: str = "normal") -> None:
    """Pose img sur dest (même taille), avec l'opacité et le mode de fusion."""
    if opacite <= 0:
        return
    qmode = MODES.get(mode, MODES["normal"])[1]
    if qmode is not None:
        p = QPainter(dest)
        p.setCompositionMode(qmode)
        p.setOpacity(opacite)
        p.drawImage(0, 0, img)
        p.end()
        return
    _poser_numpy(dest, img, opacite, mode)


def _tab(img: QImage) -> np.ndarray:
    """ARGB32 prémultiplié -> vue numpy (h, w, 4) B, G, R, A (Windows : petit-boutiste)."""
    h, w, ligne = img.height(), img.width(), img.bytesPerLine()
    return np.frombuffer(img.bits(), np.uint8, count=h * ligne).reshape(h, ligne)[:, :w * 4].reshape(h, w, 4)


def _lum(c):
    return c[..., 0] * 0.3 + c[..., 1] * 0.59 + c[..., 2] * 0.11


def _clip_couleur(c):
    l = _lum(c)[..., None]
    n = c.min(axis=-1, keepdims=True)
    x = c.max(axis=-1, keepdims=True)
    c = np.where(n < 0, l + (c - l) * l / np.maximum(l - n, 1e-6), c)
    c = np.where(x > 1, l + (c - l) * (1 - l) / np.maximum(x - l, 1e-6), c)
    return c


def _set_lum(c, l):
    return _clip_couleur(c + (l - _lum(c))[..., None])


def _sat(c):
    return c.max(axis=-1) - c.min(axis=-1)


def _set_sat(c, s):
    mx, mn = c.max(axis=-1, keepdims=True), c.min(axis=-1, keepdims=True)
    etendue = mx - mn
    return np.where(etendue > 1e-6, (c - mn) * s[..., None] / np.maximum(etendue, 1e-6), 0.0)


def _vue(img: QImage):
    """Vue numpy modifiable (h, w, 4) d'une image ARGB32, RGBA64 ou RGBA32FPx4 prémultipliée, ordre des couches
    R, V, B, A (index), valeur maximale (1.0 en 32 bits : les valeurs peuvent la dépasser)."""
    from .profondeur import FORMAT_16, FORMAT_32
    if img.format() == FORMAT_32:
        h, w, ligne = img.height(), img.width(), img.bytesPerLine()
        v = np.frombuffer(img.bits(), np.float32, count=h * ligne // 4).reshape(h, ligne // 4)[:, :w * 4]
        return v.reshape(h, w, 4), [0, 1, 2], 1.0
    if img.format() == FORMAT_16:
        h, w, ligne = img.height(), img.width(), img.bytesPerLine()
        v = np.frombuffer(img.bits(), np.uint16, count=h * ligne // 2).reshape(h, ligne // 2)[:, :w * 4]
        return v.reshape(h, w, 4), [0, 1, 2], 65535
    return _tab(img), [2, 1, 0], 255


def _poser_numpy(dest: QImage, img: QImage, opacite: float, mode: str) -> None:
    """Modes Teinte, Saturation, Couleur, Luminosité (formules du W3C, comme Photoshop)."""
    if img.format() != dest.format():
        from .profondeur import convertir
        img = convertir(img, dest.format())
    s, _o, _m = _vue(img)
    a_s = s[..., 3]
    ys, xs = np.nonzero(a_s)
    if not len(ys):
        return
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    d, ordre, maxi = _vue(dest)
    D = d[y0:y1, x0:x1].astype(np.float32) / maxi
    S = s[y0:y1, x0:x1].astype(np.float32) / maxi
    ad, as_ = D[..., 3:4], S[..., 3:4] * opacite
    cd = np.where(ad > 0, D[..., ordre] / np.maximum(ad, 1e-6), 0)        # R, G, B non prémultipliés
    cs = np.where(S[..., 3:4] > 0, S[..., ordre] / np.maximum(S[..., 3:4], 1e-6), 0)
    flottant = d.dtype == np.float32
    if flottant:                                    # 32 bits : couleurs au-dessus du blanc ramenées pour le calcul
        hd = np.maximum(1.0, np.maximum(cd.max(axis=-1, keepdims=True), cs.max(axis=-1, keepdims=True)))
        cd, cs = cd / hd, cs / hd
    if mode == "teinte":
        b = _set_lum(_set_sat(cs, _sat(cd)), _lum(cd))
    elif mode == "saturation":
        b = _set_lum(_set_sat(cd, _sat(cs)), _lum(cd))
    elif mode == "couleur":
        b = _set_lum(cs, _lum(cd))
    else:
        b = _set_lum(cd, _lum(cs))
    b = np.clip(b, 0, 1)
    if flottant:
        b, cs, cd = b * hd, cs * hd, cd * hd
    # W3C : couleur posée = (1 − ad)·cs + ad·B ; puis « source over »
    cm = (1 - ad) * cs + ad * b
    ao = as_ + ad * (1 - as_)
    co = cm * as_ + cd * ad * (1 - as_)                                    # prémultiplié
    out = np.empty_like(D)
    out[..., ordre] = co
    out[..., 3:4] = ao
    if flottant:
        d[y0:y1, x0:x1] = np.maximum(out, 0)
    else:
        d[y0:y1, x0:x1] = np.clip(np.round(out * maxi), 0, maxi).astype(d.dtype)


def appliquer_reglage(res: QImage, c) -> QImage:
    """Calque de réglage : change l'image `res` (ce qui est dessous) à travers son masque, avec son opacité."""
    from . import ajustements
    r = c.reglage
    if c.opacite <= 0:
        return res
    from .profondeur import FORMAT_16, FORMAT_32
    if res.format() == FORMAT_32:
        return _reglage32(res, c)
    if res.format() == FORMAT_16:
        return _reglage16(res, c)
    t = _tab(res)
    a = t[..., 3].astype(np.float32)
    rgb = np.where(a[..., None] > 0, t[..., 2::-1].astype(np.float32) * 255 / np.maximum(a[..., None], 1), 0)
    rgb8 = np.clip(np.round(rgb), 0, 255).astype(np.uint8)
    nouv = ajustements.appliquer(np.ascontiguousarray(rgb8), r["type"], r["params"]).astype(np.float32)
    poids = np.full(a.shape, float(c.opacite), np.float32)
    if masque_utile(c):
        poids *= masque_tableau(c.masque).astype(np.float32) / 255
    rgb = rgb8 + (nouv - rgb8) * poids[..., None]
    pre = rgb * a[..., None] / 255
    sortie = QImage(res.size(), QImage.Format_ARGB32_Premultiplied)
    o = _tab(sortie)
    o[..., 2::-1] = np.clip(np.round(pre), 0, 255).astype(np.uint8)
    o[..., 3] = t[..., 3]
    return sortie


def _reglage16(res: QImage, c) -> QImage:
    """Calque de réglage sur une image 16 bits : calcul en 16 bits (ajustements.appliquer_16)."""
    from . import ajustements
    from .profondeur import FORMAT_16
    t, _o, _m = _vue(res)
    a = t[..., 3].astype(np.float32)
    rgb = np.where(a[..., None] > 0, t[..., :3].astype(np.float32) * 65535 / np.maximum(a[..., None], 1), 0)
    rgb16 = np.clip(np.round(rgb), 0, 65535).astype(np.uint16)
    nouv = ajustements.appliquer_16(rgb16, c.reglage["type"], c.reglage["params"]).astype(np.float32)
    poids = np.full(a.shape, float(c.opacite), np.float32)
    if masque_utile(c):
        poids *= masque_tableau(c.masque).astype(np.float32) / 255
    rgb = rgb16 + (nouv - rgb16) * poids[..., None]
    sortie = QImage(res.size(), FORMAT_16)
    o, _o, _m = _vue(sortie)
    o[..., :3] = np.clip(np.round(rgb * a[..., None] / 65535), 0, 65535).astype(np.uint16)
    o[..., 3] = t[..., 3]
    return sortie


def _reglage32(res: QImage, c) -> QImage:
    """Calque de réglage sur une image 32 bits (ajustements.appliquer_32 : les couleurs au-dessus du blanc gardent
    leur éclat)."""
    from . import ajustements
    from .profondeur import FORMAT_32
    t, _o, _m = _vue(res)
    a = t[..., 3:4]
    rgb = np.where(a > 0, t[..., :3] / np.maximum(a, 1e-6), 0).astype(np.float32)
    nouv = ajustements.appliquer_32(rgb, c.reglage["type"], c.reglage["params"])
    poids = np.full(a.shape[:2], float(c.opacite), np.float32)
    if masque_utile(c):
        poids *= masque_tableau(c.masque).astype(np.float32) / 255
    rgb = rgb + (nouv - rgb) * poids[..., None]
    sortie = QImage(res.size(), FORMAT_32)
    o, _o, _m = _vue(sortie)
    o[..., :3] = np.maximum(rgb, 0) * a
    o[..., 3] = t[..., 3]
    return sortie
