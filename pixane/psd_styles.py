"""Styles de calque d'un PSD (bloc « lfx2 ») -> Style de Pixane.

Le bloc est un « descripteur » Photoshop (arbre de clés typées), décrit dans la spécification publique du format.
Effets repris : ombre portée, ombre interne, lueur externe et interne, contour (couleur unie), biseau et estampage,
incrustation de couleur, incrustation de dégradé (deux couleurs, linéaire ou radial). Le satin, les motifs et les
contours en dégradé ne sont pas repris (signalé à l'ouverture).
"""
from __future__ import annotations

import struct

from .styles import Effet, Style


class _Desc:
    def __init__(self, d: bytes):
        self.d, self.p = d, 0

    def lire(self, n):
        b = self.d[self.p:self.p + n]
        if len(b) < n:
            raise ValueError("descripteur incomplet")
        self.p += n
        return b

    def u32(self):
        return struct.unpack(">I", self.lire(4))[0]

    def i32(self):
        return struct.unpack(">i", self.lire(4))[0]

    def double(self):
        return struct.unpack(">d", self.lire(8))[0]

    def unicode(self):
        n = self.u32()
        return self.lire(2 * n).decode("utf-16-be", "replace").rstrip("\x00")

    def cle(self):
        n = self.u32()
        return self.lire(4 if n == 0 else n).decode("latin-1")

    def descripteur(self) -> dict:
        self.unicode()
        classe = self.cle()
        res = {"_classe": classe}
        for _ in range(self.u32()):
            k = self.cle()
            res[k] = self.valeur(self.lire(4))
        return res

    def valeur(self, t: bytes):
        if t in (b"Objc", b"GlbO"):
            return self.descripteur()
        if t == b"VlLs":
            return [self.valeur(self.lire(4)) for _ in range(self.u32())]
        if t == b"doub":
            return self.double()
        if t == b"UntF":
            unite = self.lire(4).decode("latin-1")
            return (unite, self.double())
        if t == b"UnFl":
            unite = self.lire(4).decode("latin-1")
            return (unite, [self.double() for _ in range(self.u32())])
        if t == b"TEXT":
            return self.unicode()
        if t == b"enum":
            self.cle()
            return self.cle()
        if t == b"long":
            return self.i32()
        if t == b"comp":
            return struct.unpack(">q", self.lire(8))[0]
        if t == b"bool":
            return bool(self.lire(1)[0])
        if t in (b"type", b"GlbC"):
            self.unicode()
            return self.cle()
        if t in (b"alis", b"tdta", b"Pth "):
            return self.lire(self.u32())
        if t == b"obj ":
            for _ in range(self.u32()):
                genre = self.lire(4)
                if genre == b"prop":
                    self.unicode(); self.cle(); self.cle()
                elif genre == b"Clss":
                    self.unicode(); self.cle()
                elif genre == b"Enmr":
                    self.unicode(); self.cle(); self.cle(); self.cle()
                elif genre == b"rele":
                    self.unicode(); self.cle(); self.i32()
                elif genre == b"Idnt" or genre == b"indx":
                    self.i32()
                elif genre == b"name":
                    self.unicode(); self.cle(); self.unicode()
                else:
                    raise ValueError("référence inconnue")
            return None
        raise ValueError(f"type inconnu {t!r}")


MODES_PS = {"Nrml": "normal", "Mltp": "produit", "Scrn": "ecran", "Ovrl": "incrustation"}


def _couleur(d) -> str:
    if not isinstance(d, dict):
        return "#000000"
    if d.get("_classe") == "RGBC" or "Rd  " in d:
        r, g, b = d.get("Rd  ", 0), d.get("Grn ", 0), d.get("Bl  ", d.get("Bl  ", 0))
    elif "Gry " in d:
        r = g = b = 255 - d["Gry "] * 2.55
    else:
        return "#000000"
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(v))) for v in (r, g, b))


def _n(v, defaut=0.0) -> float:
    if isinstance(v, tuple):
        return float(v[1])
    if isinstance(v, (int, float)):
        return float(v)
    return defaut


def _commun(d, angle_global):
    r = {"opacite": round(_n(d.get("Opct"), 100)), "mode": MODES_PS.get(d.get("Md  "), "normal")}
    if "Clr " in d:
        r["couleur"] = _couleur(d["Clr "])
    if "lagl" in d:
        glob = bool(d.get("uglg", False))
        r["angle"] = round(angle_global if glob else _n(d["lagl"], 120))
        r["global"] = glob
    return r


def _effet(cle: str, d: dict, angle_global: float):
    if not isinstance(d, dict):
        return None, False
    actif = bool(d.get("enab", True))
    c = _commun(d, angle_global)
    if cle in ("DrSh", "IrSh"):
        typ = "ombre" if cle == "DrSh" else "ombre_interne"
        reg = dict(c, distance=round(_n(d.get("Dstn"), 5)), taille=round(_n(d.get("blur"), 5)),
                   etendue=round(_n(d.get("Ckmt"), 0)))
        return Effet(typ, {**Effet.nouveau(typ).reglages, **reg}, actif), False
    if cle in ("OrGl", "IrGl"):
        typ = "lueur" if cle == "OrGl" else "lueur_interne"
        reg = dict(c, taille=max(1, round(_n(d.get("blur"), 10))), etendue=round(_n(d.get("Ckmt"), 0)))
        if typ == "lueur_interne":
            reg["source"] = "centre" if d.get("glwS") == "SrcC" else "bord"
        approx = isinstance(d.get("Grad"), dict) and "Clr " not in d
        return Effet(typ, {**Effet.nouveau(typ).reglages, **reg}, actif), approx
    if cle == "FrFX":
        pos = {"OutF": "exterieur", "InsF": "interieur", "CtrF": "centre"}.get(d.get("Styl"), "exterieur")
        reg = dict(c, taille=max(1, round(_n(d.get("Sz  "), 3))), position=pos)
        reg.pop("mode", None)
        approx = d.get("PntT") not in (None, "SClr")
        return Effet("contour", {**Effet.nouveau("contour").reglages, **reg}, actif), approx
    if cle == "SoFi":
        return Effet("couleur", {**Effet.nouveau("couleur").reglages, **c}, actif), False
    if cle == "GrFl":
        g = d.get("Grad") if isinstance(d.get("Grad"), dict) else {}
        couleurs = [x for x in g.get("Clrs", []) if isinstance(x, dict)]
        c1 = _couleur(couleurs[0].get("Clr ")) if couleurs else "#000000"
        c2 = _couleur(couleurs[-1].get("Clr ")) if couleurs else "#ffffff"
        transp = [x for x in g.get("Trns", []) if isinstance(x, dict)]
        points = None
        if couleurs:                    # tous les points de couleur et d'opacité (Lctn : 0..4096, Mdpn : 0..100)
            points = {"couleurs": [{"pos": _n(x.get("Lctn"), 0) / 4096, "couleur": _couleur(x.get("Clr ")),
                                    "milieu": _n(x.get("Mdpn"), 50) / 100} for x in couleurs],
                      "opacites": [{"pos": _n(x.get("Lctn"), 0) / 4096, "opacite": _n(x.get("Opct"), 100) / 100,
                                    "milieu": _n(x.get("Mdpn"), 50) / 100} for x in transp]}
        reg = dict(c, couleur1=c1, couleur2=c2, degrade=points, angle=round(_n(d.get("Angl"), 90)),
                   forme="radial" if d.get("Type") == "Rdl " else "lineaire",
                   echelle=max(10, min(150, round(_n(d.get("Scl "), 100)))), inverser=bool(d.get("Rvrs", False)))
        reg.pop("couleur", None)
        reg.pop("global", None)
        return Effet("degrade", {**Effet.nouveau("degrade").reglages, **reg}, actif), False
    if cle == "ebbl":
        forme = {"InrB": "interne", "OtrB": "externe", "Embs": "estampage", "PlEb": "estampage"}.get(
            d.get("bvlS"), "interne")
        glob = bool(d.get("uglg", False))
        reg = dict(forme=forme, profondeur=max(1, min(500, round(_n(d.get("srgR"), 100)))),
                   direction="bas" if d.get("bvlD") == "Out " else "haut", taille=max(1, round(_n(d.get("blur"), 5))),
                   adoucir=round(_n(d.get("Sftn"), 0)), angle=round(angle_global if glob else _n(d.get("lagl"), 120)),
                   global_=glob, altitude=round(_n(d.get("Lald"), 30)), clair=_couleur(d.get("hglC")),
                   opacite_clair=round(_n(d.get("hglO"), 75)), sombre=_couleur(d.get("sdwC")),
                   opacite_sombre=round(_n(d.get("sdwO"), 75)))
        reg["global"] = reg.pop("global_")
        return Effet("biseau", {**Effet.nouveau("biseau").reglages, **reg}, actif), False
    return None, cle in ("ChFX", "patternFill")


MULTI = {"dropShadowMulti": "DrSh", "innerShadowMulti": "IrSh", "frameFXMulti": "FrFX", "solidFillMulti": "SoFi",
         "gradientFillMulti": "GrFl"}
ORDRE_PS = ("DrSh", "IrSh", "OrGl", "IrGl", "ebbl", "SoFi", "GrFl", "FrFX", "ChFX", "patternFill")


def style_depuis_lfx2(donnees: bytes, angle_global: float = 120.0):
    """-> (Style ou None, True si un effet n'a pas pu être repris tel quel)."""
    try:
        lec = _Desc(donnees)
        lec.u32()
        lec.u32()
        d = lec.descripteur()
    except (ValueError, struct.error, UnicodeDecodeError):
        return None, True
    if d.get("masterFXSwitch") is False:
        return None, False
    effets, manque = [], False
    vus = []
    for k, v in d.items():
        if k in MULTI and isinstance(v, list):
            vus.extend((MULTI[k], x) for x in v)
    deja = {c for c, _ in vus}
    for k in ORDRE_PS:
        if k in d and k not in deja:
            vus.append((k, d[k]))
    for cle, valeur in vus:
        e, approx = _effet(cle, valeur, angle_global)
        manque = manque or approx
        if e is not None:
            effets.append(e)
    if not effets:
        return None, manque
    return Style(tuple(effets)), manque
