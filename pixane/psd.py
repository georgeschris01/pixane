"""Fichiers Photoshop (.psd) : lecture et écriture des calques, sans bibliothèque en plus.

Écrit d'après la description publique du format (« Adobe Photoshop File Formats Specification »).
Lecture : RGB ou niveaux de gris, 8 ou 16 bits ; calques avec nom, visibilité, opacité, verrou, mode de fusion,
masque de calque, groupes et styles de calque (ombre, lueur, contour, biseau, incrustations : voir psd_styles).
Ce que Pixane ne sait pas reproduire (calques de réglage de Photoshop, masques d'écrêtage, mode « traverser » des
groupes) est signalé ; les autres modes de couleur (CMJN…) sont ouverts aplatis, par Pillow.
Écriture : RGB 8 bits, compression RLE (PackBits, comme Photoshop), chaque calque réduit au rectangle de ses pixels
visibles, nom en Unicode, modes de fusion, masques, groupes, image fusionnée pour les visionneuses. Les textes, les
styles et les calques de réglage deviennent des images.
"""
from __future__ import annotations

import struct
import zlib
from pathlib import Path

import numpy as np
from PIL import Image
from PySide6.QtGui import QImage

from .composition import MODE_PSD, MODES, masque_depuis, masque_tableau
from .document import (FORMAT_IMAGE, Calque, avec_image_entiere, image_entiere, image_vide, nouvel_ident,
                       pil_vers_qimage, qimage_rgba, tableau)
from .langue import tr

REGLAGES = {b"levl", b"curv", b"brit", b"blnc", b"hue ", b"hue2", b"selc", b"mixr", b"grdm", b"thrs", b"post",
            b"nvrt", b"expA", b"vibA", b"phfl", b"clrL", b"blwh", b"SoCo", b"GdFl", b"PtFl", b"vmsk"}


class ErreurPsd(ValueError):
    pass


# ------------------------------------------------------------------ lecture
class _Lecteur:
    def __init__(self, donnees: bytes):
        self.d = donnees
        self.p = 0

    def lire(self, n: int) -> bytes:
        if self.p + n > len(self.d):
            raise ErreurPsd(tr("Fichier PSD incomplet ou abîmé."))
        b = self.d[self.p:self.p + n]
        self.p += n
        return b

    def u8(self):
        return self.lire(1)[0]

    def u16(self):
        return struct.unpack(">H", self.lire(2))[0]

    def i16(self):
        return struct.unpack(">h", self.lire(2))[0]

    def u32(self):
        return struct.unpack(">I", self.lire(4))[0]

    def i32(self):
        return struct.unpack(">i", self.lire(4))[0]


def _canal(lec: _Lecteur, fin: int, w: int, h: int, prof: int) -> np.ndarray | None:
    """Un canal d'un calque (compression, puis données) -> tableau (h, w) uint8, ou uint16 pour un PSD 16 bits."""
    comp = lec.u16()
    octets = prof // 8
    if w <= 0 or h <= 0:
        lec.p = fin
        return None
    if comp == 0:
        brut = lec.lire(w * h * octets)
    elif comp == 1:
        lec.lire(2 * h)                                  # longueur de chaque ligne : inutile pour Pillow
        im = Image.frombytes("L", (w * octets, h), lec.d[lec.p:fin], "packbits", "L")
        brut = im.tobytes()
    elif comp in (2, 3):
        brut = zlib.decompress(lec.d[lec.p:fin])
        if comp == 3:                                    # « avec prédiction » : différences ligne par ligne
            if octets == 1:
                a = np.frombuffer(brut, np.uint8).reshape(h, w)
                brut = np.cumsum(a, axis=1, dtype=np.uint8).tobytes()
            else:
                a = np.frombuffer(brut, ">u2").reshape(h, w).astype(np.uint16)
                brut = np.cumsum(a, axis=1, dtype=np.uint16).astype(">u2").tobytes()
    else:
        raise ErreurPsd(tr("Compression PSD inconnue ({n}).", n=comp))
    lec.p = fin
    if octets == 1:
        return np.frombuffer(brut, np.uint8)[:w * h].reshape(h, w)
    return np.frombuffer(brut, ">u2")[:w * h].reshape(h, w).astype(np.uint16)


def _aplati(chemin: Path, raison: str):
    """Repli : l'image fusionnée lue par Pillow, en un seul calque."""
    with Image.open(chemin) as im:
        icc = im.info.get("icc_profile")
        im.load()
        qimg = pil_vers_qimage(im.convert("RGBA"))
    return [Calque.depuis(tr("Arrière-plan"), qimg)], icc, [raison] if raison else []


def lire_psd(chemin: str | Path):
    """-> (calques du bas vers le haut, profil ICC ou None, liste de remarques pour l'utilisateur)."""
    chemin = Path(chemin)
    lec = _Lecteur(chemin.read_bytes())
    if lec.lire(4) != b"8BPS":
        raise ErreurPsd(tr("Ce n'est pas un fichier Photoshop."))
    version = lec.u16()
    if version != 1:
        raise ErreurPsd(tr("Les grands documents Photoshop (.psb) ne sont pas pris en charge."))
    lec.lire(6)
    _nb, H, W, prof, mode = lec.u16(), lec.u32(), lec.u32(), lec.u16(), lec.u16()
    if mode not in (1, 3) or prof not in (8, 16):
        return _aplati(chemin, tr("Ce PSD n'est pas en RVB ou en niveaux de gris 8 / 16 bits : il est ouvert "
                                  "aplati (un seul calque)."))
    lec.lire(lec.u32())                                  # palette de couleurs
    icc = None
    fin = lec.u32() + lec.p                              # ressources : on y prend le profil couleur
    while lec.p + 12 <= fin:
        if lec.lire(4) != b"8BIM":
            break
        ident = lec.u16()
        n = lec.u8()
        lec.lire(n + (1 - n % 2))                        # nom (chaîne Pascal, longueur paire)
        taille = lec.u32()
        donnees = lec.lire(taille)
        if taille % 2:
            lec.lire(1)
        if ident == 1039:
            icc = donnees
    lec.p = fin
    fin_calques_masques = lec.u32() + lec.p
    if fin_calques_masques == lec.p:
        return _aplati(chemin, "")
    fin_infos = lec.u32() + lec.p
    if fin_infos == lec.p:
        return _aplati(chemin, "")
    nb = abs(lec.i16())
    fiches = []
    for _ in range(nb):
        haut, gauche, bas, droite = lec.i32(), lec.i32(), lec.i32(), lec.i32()
        canaux = [(lec.i16(), lec.u32()) for _ in range(lec.u16())]
        lec.lire(4)                                      # « 8BIM »
        fusion = lec.lire(4)
        opacite, ecretage, drapeaux = lec.u8(), lec.u8(), lec.u8()
        lec.u8()
        fin_extra = lec.u32() + lec.p
        masque = None
        t = lec.u32()
        if t >= 18:
            mh, mg, mb, md = lec.i32(), lec.i32(), lec.i32(), lec.i32()
            defaut, mdrap = lec.u8(), lec.u8()
            masque = (mh, mg, mb, md, defaut, mdrap)
            lec.lire(t - 18)
        else:
            lec.lire(t)
        lec.lire(lec.u32())                              # plages de fusion
        n = lec.u8()
        nom = lec.lire(n).decode("mac_roman", "replace")
        lec.lire((4 - (n + 1) % 4) % 4)
        infos = {}
        while lec.p + 12 <= fin_extra:
            sig = lec.lire(4)
            if sig not in (b"8BIM", b"8B64"):
                break
            cle, taille = lec.lire(4), lec.u32()
            infos[cle] = lec.lire(taille)
        lec.p = fin_extra
        if b"luni" in infos and len(infos[b"luni"]) >= 4:
            n = struct.unpack(">I", infos[b"luni"][:4])[0]
            nom = infos[b"luni"][4:4 + 2 * n].decode("utf-16-be", "replace").rstrip("\x00") or nom
        fiches.append(dict(rect=(haut, gauche, bas, droite), canaux=canaux, fusion=fusion, opacite=opacite / 255,
                           ecretage=ecretage, visible=not drapeaux & 2, masque=masque, nom=nom, infos=infos))
    # données des canaux, dans l'ordre des fiches
    for f in fiches:
        haut, gauche, bas, droite = f["rect"]
        w, h = droite - gauche, bas - haut
        f["pixels"] = {}
        for ident, taille in f["canaux"]:
            debut = lec.p
            if ident == -2 and f["masque"]:
                mh, mg, mb, md = f["masque"][:4]
                f["pixels"][ident] = _canal(lec, debut + taille, md - mg, mb - mh, prof)
            elif ident in (-1, 0, 1, 2):
                f["pixels"][ident] = _canal(lec, debut + taille, w, h, prof)
            lec.p = debut + taille

    # groupes (du bas vers le haut : fin de groupe « 3 », ses calques, puis le dossier « 1 » ou « 2 »)
    from .psd_styles import style_depuis_lfx2
    remarques = set()
    resultat, pile = [], []
    for f in fiches:
        sect = f["infos"].get(b"lsct") or f["infos"].get(b"lsdk")
        genre = struct.unpack(">I", sect[:4])[0] if sect and len(sect) >= 4 else 0
        dans = pile[-1] if pile else None
        if genre == 3:
            pile.append(nouvel_ident())
            continue
        if genre in (1, 2):
            ident = pile.pop() if pile else nouvel_ident()
            fusion = f["fusion"]
            if len(sect) >= 12 and sect[4:8] == b"8BIM":
                fusion = sect[8:12]
            if fusion == b"pass":
                fusion = b"norm"                       # « traverser » : dessiné comme un groupe normal
                remarques.add(tr("groupes en mode « traverser »"))
            g = Calque(f["nom"] or tr("Groupe"), image_vide(W, H), visible=f["visible"], opacite=f["opacite"],
                       verrou=_verrou(f["infos"].get(b"lspf")), groupe=True, ident=ident,
                       dans=pile[-1] if pile else None, ouvert=genre == 1, mode=MODE_PSD.get(fusion, "normal"),
                       masque=_masque(f, W, H))
            resultat.append(g)
            continue
        if REGLAGES & set(f["infos"]):
            remarques.add(tr("calques de réglage ou de remplissage"))
            continue
        if f["fusion"] not in MODE_PSD:
            remarques.add(tr("modes de fusion"))
        c = _vers_calque(f, W, H, mode)
        style, manque = None, False
        if b"lfx2" in f["infos"]:
            style, manque = style_depuis_lfx2(f["infos"][b"lfx2"])
        elif b"lrFX" in f["infos"]:
            manque = True
        if manque:
            remarques.add(tr("certains effets de style"))
        from dataclasses import replace
        resultat.append(replace(c, style=style, dans=dans, mode=MODE_PSD.get(f["fusion"], "normal"),
                                ecretage=bool(f["ecretage"])))
    if not resultat or all(c.groupe for c in resultat):
        return _aplati(chemin, "")
    notes = []
    if remarques:
        notes.append(tr("Ce PSD utilise des effets que Pixane Photo ne reproduit pas ({quoi}) : l'aspect peut différer "
                        "de Photoshop.", quoi=", ".join(sorted(remarques))))
    return resultat, icc, notes


def _vers_calque(f, W: int, H: int, mode: int) -> Calque:
    haut, gauche, bas, droite = f["rect"]
    w, h = droite - gauche, bas - haut
    img = image_vide(W, H)
    px = f["pixels"]
    if w > 0 and h > 0 and (0 in px and px[0] is not None):
        if mode == 3:
            r, g, b = px.get(0), px.get(1), px.get(2)
            g = g if g is not None else r
            b = b if b is not None else r
        else:
            r = g = b = px[0]
        a = px.get(-1)
        seize = r.dtype == np.uint16
        a = np.full((h, w), 65535 if seize else 255, r.dtype) if a is None else a.copy()
        if seize:                              # PSD 16 bits : le calque reste en 16 bits
            from .profondeur import qimage16
            morceau = qimage16(np.dstack([r, g, b, a]))
        else:
            morceau = qimage_rgba(np.dstack([r, g, b, a]))
    else:
        morceau = None
    m = _masque(f, W, H)
    c = Calque(f["nom"] or tr("Calque"), img, visible=f["visible"], opacite=f["opacite"],
               verrou=_verrou(f["infos"].get(b"lspf")), masque=m,
               masque_actif=not (f["masque"] and f["masque"][5] & 2))
    if morceau is not None:                    # ce qui dépasse de la feuille est gardé (comme dans Photoshop)
        c = avec_image_entiere(c, morceau, gauche, haut, W, H)
    return c


def _masque(f, W: int, H: int):
    """Masque de calque à la taille du document (ou None)."""
    px = f.get("pixels", {})
    if not f["masque"] or px.get(-2) is None:
        return None
    mh, mg, mb, md, defaut, _ = f["masque"]
    m = np.full((H, W), defaut, np.uint8)
    y0, x0, y1, x1 = max(mh, 0), max(mg, 0), min(mb, H), min(md, W)
    if y1 > y0 and x1 > x0:
        bout = px[-2][y0 - mh:y1 - mh, x0 - mg:x1 - mg]
        m[y0:y1, x0:x1] = (bout >> 8).astype(np.uint8) if bout.dtype == np.uint16 else bout
    return masque_depuis(m)


def _verrou(lspf: bytes | None) -> bool:
    if not lspf or len(lspf) < 4:
        return False
    v = struct.unpack(">I", lspf[:4])[0]
    return bool(v & 0x80000000) or (v & 7) == 7


# ------------------------------------------------------------------ écriture
def _packbits(ligne: np.ndarray) -> bytes:
    """Une ligne (uint8) compressée en PackBits. Les répétitions de 3 octets ou plus sont repérées par numpy ;
    le reste part en blocs littéraux de 128 octets au plus."""
    n = len(ligne)
    if n == 0:
        return b""
    brut = ligne.tobytes()
    debuts = np.concatenate(([0], np.flatnonzero(ligne[1:] != ligne[:-1]) + 1))
    longueurs = np.diff(np.concatenate((debuts, [n])))
    rep = longueurs >= 3
    sortie = bytearray()

    def litteral(a, b):
        while a < b:
            k = min(128, b - a)
            sortie.append(k - 1)
            sortie.extend(brut[a:a + k])
            a += k

    pos = 0
    for d, l in zip(debuts[rep].tolist(), longueurs[rep].tolist()):
        litteral(pos, d)
        v = brut[d]
        pos = d + l
        while l > 0:                                     # répétitions de 2 à 128 octets
            k = min(128, l)
            if l - k == 1:                               # jamais de reste d'un seul octet
                k -= 1
            sortie.append(257 - k)
            sortie.append(v)
            l -= k
    litteral(pos, n)
    return bytes(sortie)


def _canal_rle(plan: np.ndarray) -> tuple[bytes, bytes]:
    """-> (longueurs des lignes, données) d'un plan (h, w) uint8."""
    lignes = [_packbits(plan[y]) for y in range(plan.shape[0])]
    return struct.pack(f">{len(lignes)}H", *(len(l) for l in lignes)), b"".join(lignes)


def _pascal(nom: str, multiple: int) -> bytes:
    b = nom.encode("mac_roman", "replace")[:255]
    b = bytes([len(b)]) + b
    return b + b"\x00" * ((multiple - len(b) % multiple) % multiple)


def _bloc(cle: bytes, donnees: bytes) -> bytes:
    if len(donnees) % 4:
        donnees += b"\x00" * (4 - len(donnees) % 4)
    return b"8BIM" + cle + struct.pack(">I", len(donnees)) + donnees


def _fiche_vide(nom: str, bloc_extra: bytes):
    """Calque sans pixels (fin de groupe)."""
    canaux = [(i, struct.pack(">H", 0)) for i in (-1, 0, 1, 2)]
    extra = struct.pack(">II", 0, 0) + _pascal(nom, 4) + bloc_extra
    fiche = struct.pack(">iiiiH", 0, 0, 0, 0, 4)
    fiche += b"".join(struct.pack(">hI", i, len(b)) for i, b in canaux)
    fiche += b"8BIMnorm" + struct.pack(">BBBB", 255, 0, 0, 0) + struct.pack(">I", len(extra)) + extra
    return fiche, b"".join(b for _i, b in canaux)


def lire_resolution_psd(chemin: str | Path) -> float | None:
    """Résolution (points par pouce) de la ressource 1005 « ResolutionInfo », ou None."""
    try:
        lec = _Lecteur(Path(chemin).read_bytes())
        if lec.lire(4) != b"8BPS":
            return None
        lec.lire(22)
        lec.lire(lec.u32())                              # palette
        fin = lec.u32() + lec.p
        while lec.p + 12 <= fin:
            if lec.lire(4) != b"8BIM":
                break
            ident = lec.u16()
            n = lec.u8()
            lec.lire(n + (1 - n % 2))
            taille = lec.u32()
            donnees = lec.lire(taille)
            if taille % 2:
                lec.lire(1)
            if ident == 1005 and len(donnees) >= 16:
                h, unite = struct.unpack(">IH", donnees[:6])
                v = h / 65536
                if unite == 2:                           # pixels par cm
                    v *= 2.54
                return round(v, 3) if 1 <= v <= 10000 else None
    except Exception:
        return None
    return None


def _plan16(plan: np.ndarray) -> np.ndarray:
    """Plan (h, w) uint16 -> octets gros-boutistes (h, 2w) : la compression RLE travaille octet par octet."""
    return np.ascontiguousarray(plan.astype(">u2")).view(np.uint8).reshape(plan.shape[0], -1)


def ecrire_psd(chemin: str | Path, calques, fusion: QImage, icc: bytes | None = None, dpi: float = 72.0,
               profondeur: int = 8) -> None:
    """profondeur 16 : PSD 16 bits (calques, masques et image fusionnée) ; `fusion` est alors l'image 16 bits."""
    from .profondeur import tab16
    seize = profondeur == 16
    chemin = Path(chemin)
    W, H = fusion.width(), fusion.height()
    if W > 30000 or H > 30000:
        raise ErreurPsd(tr("Image trop grande pour un PSD (30 000 pixels au plus de côté)."))
    fiches, donnees = [], []
    # ordre Photoshop (du bas vers le haut) : fin de groupe, ses calques, puis l'en-tête du groupe
    debuts: dict = {}
    for i, c in enumerate(calques):
        if c.groupe:
            from .composition import descendants
            d = descendants(calques, i)
            debuts.setdefault(min(d) if d else i, []).append(i)
    suite = []
    for i, c in enumerate(calques):
        for g in sorted(debuts.get(i, []), reverse=True):     # le groupe le plus large d'abord
            suite.append(("fin", calques[g]))
        suite.append(("calque", c))
    for genre, c in suite:
        if genre == "fin":
            fiche, bloc = _fiche_vide("</Layer group>", _bloc(b"lsct", struct.pack(">I", 3)))
            fiches.append(fiche)
            donnees.append(bloc)
            continue
        entiere, ox, oy = image_entiere(c)              # ce qui dépasse de la feuille est gardé
        t = tab16(entiere) if seize else tableau(entiere.convertToFormat(FORMAT_IMAGE))
        alpha = t[:, :, 3]
        ys, xs = np.nonzero(alpha)
        if len(ys):
            haut, bas, gauche, droite = int(ys.min()), int(ys.max()) + 1, int(xs.min()), int(xs.max()) + 1
        else:
            haut = bas = gauche = droite = 0
        morceau = t[haut:bas, gauche:droite]
        if bas > haut:
            haut, bas, gauche, droite = haut + oy, bas + oy, gauche + ox, droite + ox
        canaux = []
        for ident, k in ((-1, 3), (0, 0), (1, 1), (2, 2)):
            if bas > haut:
                plan = morceau[:, :, k]
                longueurs, octets = _canal_rle(_plan16(plan) if seize else np.ascontiguousarray(plan))
                bloc = struct.pack(">H", 1) + longueurs + octets
            else:
                bloc = struct.pack(">H", 0)
            canaux.append((ident, bloc))
        donnees_masque = struct.pack(">I", 0)
        if c.masque is not None:
            m = masque_tableau(c.masque)
            longueurs, octets = _canal_rle(_plan16(m.astype(np.uint16) * 257) if seize else np.ascontiguousarray(m))
            canaux.append((-2, struct.pack(">H", 1) + longueurs + octets))
            donnees_masque = struct.pack(">IiiiiBBH", 20, 0, 0, H, W, 255, 0 if c.masque_actif else 2, 0)
        nom = c.nom or "Calque"
        extra = donnees_masque + struct.pack(">I", 0) + _pascal(nom, 4)
        extra += _bloc(b"luni", struct.pack(">I", len(nom)) + nom.encode("utf-16-be"))
        if c.verrou:
            extra += _bloc(b"lspf", struct.pack(">I", 0x80000000))
        cle = MODES.get(c.mode, MODES["normal"])[2]
        if c.groupe:
            extra += _bloc(b"lsct", struct.pack(">I", 1 if c.ouvert else 2) + b"8BIM" + cle)
        fiche = struct.pack(">iiiiH", haut, gauche, bas, droite, len(canaux))
        fiche += b"".join(struct.pack(">hI", ident, len(bloc)) for ident, bloc in canaux)
        fiche += b"8BIM" + cle + struct.pack(">BBBB", round(c.opacite * 255), 1 if getattr(c, "ecretage", False)
                                             else 0, 0 if c.visible else 2, 0)
        fiche += struct.pack(">I", len(extra)) + extra
        fiches.append(fiche)
        donnees.append(b"".join(bloc for _i, bloc in canaux))
    infos = struct.pack(">h", len(fiches)) + b"".join(fiches) + b"".join(donnees)
    if len(infos) % 2:
        infos += b"\x00"
    calques_masques = struct.pack(">I", len(infos)) + infos + struct.pack(">I", 0)

    # résolution (ressource 1005) : points par pouce, en virgule fixe 16.16
    res = struct.pack(">IHHIHH", round(dpi * 65536), 1, 1, round(dpi * 65536), 1, 1)
    ressources = b"8BIM" + struct.pack(">H", 1005) + b"\x00\x00" + struct.pack(">I", len(res)) + res
    if icc:
        r = b"8BIM" + struct.pack(">H", 1039) + b"\x00\x00" + struct.pack(">I", len(icc)) + icc
        ressources += r + (b"\x00" if len(icc) % 2 else b"")

    # image fusionnée (sur fond blanc), pour les visionneuses et les logiciels sans calques
    if seize:
        f = tab16(fusion).astype(np.uint64)
        a = f[:, :, 3:4]
        rgb = ((f[:, :, :3] * a + 65535 * (65535 - a)) // 65535).astype(np.uint16)
    else:
        f = tableau(fusion.convertToFormat(FORMAT_IMAGE)).astype(np.uint16)
        a = f[:, :, 3:4]
        rgb = ((f[:, :, :3] * a + 255 * (255 - a)) // 255).astype(np.uint8)
    longueurs, octets = [], []
    for k in range(3):
        l, o = _canal_rle(_plan16(rgb[:, :, k]) if seize else np.ascontiguousarray(rgb[:, :, k]))
        longueurs.append(l)
        octets.append(o)

    temporaire = chemin.with_name(chemin.name + ".tmp")
    with open(temporaire, "wb") as fic:
        fic.write(b"8BPS" + struct.pack(">H", 1) + b"\x00" * 6 + struct.pack(">HIIHH", 3, H, W, 16 if seize else 8, 3))
        fic.write(struct.pack(">I", 0))
        fic.write(struct.pack(">I", len(ressources)) + ressources)
        fic.write(struct.pack(">I", len(calques_masques)) + calques_masques)
        fic.write(struct.pack(">H", 1) + b"".join(longueurs) + b"".join(octets))
    temporaire.replace(chemin)
