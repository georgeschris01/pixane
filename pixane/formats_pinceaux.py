"""Lecture des pinceaux et des motifs d'autres logiciels (fichiers ajoutés par l'utilisateur).

Pinceaux (formes) : Photoshop .abr (versions 1, 2 et 6+ : formes « échantillonnées » ; les formes « calculées »
deviennent un rond), GIMP / Krita .gbr et .gih (pinceau animé : toutes ses formes), image .png / .jpg.
Motifs : Photoshop .pat, GIMP / Krita .pat, image .png / .jpg. Paquets Krita .bundle : leurs formes et leurs motifs.

Une forme est un tableau (h, w) uint8 : 255 = le pinceau peint à fond, 0 = rien ; ou (h, w, 4) RGBA pour une forme en
couleur (pinceau « image »). Un motif est un tableau (h, w, 4) RGBA.
"""
from __future__ import annotations

import io
import struct
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import threading

import numpy as np
from PIL import Image

EXT_PINCEAUX = (".abr", ".gbr", ".gih")
EXT_MOTIFS = (".pat",)
EXT_IMAGES = (".png", ".jpg", ".jpeg", ".bmp", ".webp")
EXT_PAQUETS = (".bundle",)
TAILLE_MAX = 2500             # côté maximal d'une forme ou d'un motif (au-delà : réduit)


@dataclass
class Forme:
    nom: str
    image: np.ndarray                     # (h, w) gris ou (h, w, 4) RGBA
    espacement: float = 0.25              # écart entre deux touches, en part de la taille (0.25 = 25 %)


@dataclass
class Motif:
    nom: str
    image: np.ndarray                     # (h, w, 4) RGBA


@dataclass
class Contenu:
    formes: list = field(default_factory=list)
    motifs: list = field(default_factory=list)
    ignores: list = field(default_factory=list)      # éléments illisibles (nom, raison)


class Lecteur:
    """Lecture big-endian dans des octets."""

    def __init__(self, data: bytes, pos: int = 0):
        self.d, self.p = data, pos

    def octets(self, n: int) -> bytes:
        if n < 0 or self.p + n > len(self.d):
            raise ValueError("fichier tronqué")
        b = self.d[self.p:self.p + n]
        self.p += n
        return b

    def u8(self) -> int:
        return self.octets(1)[0]

    def i8(self) -> int:
        return struct.unpack(">b", self.octets(1))[0]

    def u16(self) -> int:
        return struct.unpack(">H", self.octets(2))[0]

    def i16(self) -> int:
        return struct.unpack(">h", self.octets(2))[0]

    def u32(self) -> int:
        return struct.unpack(">I", self.octets(4))[0]

    def i32(self) -> int:
        return struct.unpack(">i", self.octets(4))[0]

    def unicode(self) -> str:
        """Chaîne Photoshop : nombre de caractères (u32) puis UTF-16 BE."""
        n = self.u32()
        return self.octets(2 * n).decode("utf-16-be", "replace").rstrip("\x00")

    def pascal(self) -> str:
        n = self.u8()
        return self.octets(n).decode("latin-1", "replace")

    def fini(self) -> bool:
        return self.p >= len(self.d)


_lecture = threading.local()       # lecture en pleine taille (rangement en paquet : rien n'est réduit)


def _reduire(a: np.ndarray) -> np.ndarray:
    h, w = a.shape[:2]
    if getattr(_lecture, "pleine", False) or max(h, w) <= TAILLE_MAX:
        return a
    k = TAILLE_MAX / max(h, w)
    mode = "L" if a.ndim == 2 else "RGBA"
    return np.asarray(Image.fromarray(a, mode).resize((max(1, round(w * k)), max(1, round(h * k))), Image.LANCZOS))


def _packbits(lec: Lecteur, largeur: int, hauteur: int, longueurs: list[int]) -> np.ndarray:
    """Lignes compressées en PackBits (Photoshop, RLE)."""
    sortie = np.zeros((hauteur, largeur), np.uint8)
    for y in range(hauteur):
        fin = lec.p + longueurs[y]
        ligne = bytearray()
        while lec.p < fin and len(ligne) < largeur:
            n = lec.i8()
            if n >= 0:
                ligne += lec.octets(n + 1)
            elif n != -128:
                ligne += bytes([lec.u8()]) * (1 - n)
        lec.p = fin
        ligne = ligne[:largeur]
        sortie[y, :len(ligne)] = np.frombuffer(bytes(ligne), np.uint8)
    return sortie


def _canal(lec: Lecteur, largeur: int, hauteur: int, profondeur: int, compression: int) -> np.ndarray:
    """Un canal Photoshop : brut ou PackBits ; 16 bits ramenés à 8."""
    octets = max(1, profondeur // 8)
    if compression == 1:
        longueurs = [lec.u16() for _ in range(hauteur)]
        a = _packbits(lec, largeur * octets, hauteur, longueurs)
    else:
        a = np.frombuffer(lec.octets(largeur * hauteur * octets), np.uint8).reshape(hauteur, largeur * octets)
    if octets == 2:
        a = a.reshape(hauteur, largeur, 2)[:, :, 0]            # octet de poids fort
    elif octets == 4:
        a = (np.clip(a.view(">f4").reshape(hauteur, largeur), 0, 1) * 255).astype(np.uint8)
    return np.ascontiguousarray(a)


# ------------------------------------------------------------------ Photoshop .abr
def _rond(diametre: int, durete: float, rondeur: float = 1.0, angle: float = 0.0) -> np.ndarray:
    """Forme ronde (pinceau « calculé » de Photoshop)."""
    d = max(1, min(int(diametre), TAILLE_MAX))
    yy, xx = np.mgrid[0:d, 0:d].astype(np.float32)
    c = (d - 1) / 2
    a = np.radians(angle)
    x, y = (xx - c), (yy - c)
    xr = x * np.cos(a) + y * np.sin(a)
    yr = (-x * np.sin(a) + y * np.cos(a)) / max(0.01, rondeur)
    r = np.sqrt(xr ** 2 + yr ** 2) / max(0.5, d / 2)
    h = min(0.99, max(0.0, durete))
    v = np.clip((1 - r) / max(0.01, 1 - h), 0, 1)
    return (v * 255 + 0.5).astype(np.uint8)


def lire_abr(data: bytes, nom: str = "Photoshop") -> Contenu:
    lec = Lecteur(data)
    version = lec.u16()
    res = Contenu()
    if version in (1, 2):
        n = lec.u16()
        for i in range(n):
            genre, taille = lec.u16(), lec.u32()
            fin = lec.p + taille
            try:
                if genre == 1:                                   # calculée : rond
                    lec.u32()                                    # divers
                    esp = lec.u16() / 100
                    diam, rondeur, angle, durete = lec.u16(), lec.u16(), lec.i16(), lec.u16()
                    res.formes.append(Forme(f"{nom} {i + 1}", _rond(diam, durete / 100, rondeur / 100, angle),
                                            esp or 0.25))
                elif genre == 2:                                 # échantillonnée
                    lec.u32()
                    esp = lec.u16() / 100
                    nom_b = lec.unicode() if version == 2 else ""
                    lec.u8()                                     # anticrénelage
                    lec.octets(8)                                # bornes courtes
                    haut, gauche, bas, droite = lec.i32(), lec.i32(), lec.i32(), lec.i32()
                    prof, comp = lec.u16(), lec.u8()
                    w, h = droite - gauche, bas - haut
                    if w > 0 and h > 0:
                        img = _canal(lec, w, h, prof, comp)
                        res.formes.append(Forme(nom_b or f"{nom} {i + 1}", _reduire(img), esp or 0.25))
            except (ValueError, struct.error) as e:
                res.ignores.append((f"{nom} {i + 1}", str(e)))
            lec.p = fin
        return res
    if version in (6, 7, 10):
        sous_version = lec.u16()
        noms = _noms_abr6(data)
        while not lec.fini():
            if lec.p + 12 > len(data):
                break
            if lec.octets(4) != b"8BIM":
                break
            cle, longueur = lec.octets(4), lec.u32()
            fin = lec.p + longueur
            if cle == b"samp":
                i = 0
                while lec.p < fin - 4:
                    taille = lec.u32()
                    suivant = lec.p + taille + (-taille % 4)
                    try:
                        lec.octets(47 if sous_version == 1 else 301)
                        haut, gauche, bas, droite = lec.i32(), lec.i32(), lec.i32(), lec.i32()
                        prof, comp = lec.u16(), lec.u8()
                        w, h = droite - gauche, bas - haut
                        if 0 < w <= 10000 and 0 < h <= 10000:
                            img = _canal(lec, w, h, prof, comp)
                            n_ = noms[i] if i < len(noms) else f"{nom} {i + 1}"
                            res.formes.append(Forme(n_, _reduire(img)))
                    except (ValueError, struct.error) as e:
                        res.ignores.append((f"{nom} {i + 1}", str(e)))
                    i += 1
                    lec.p = suivant
            lec.p = fin + (longueur % 2 if cle != b"samp" else 0)
        return res
    raise ValueError(f"version de .abr inconnue ({version})")


def _noms_abr6(data: bytes) -> list[str]:
    """Noms des pinceaux (section « desc » : clés « Nm  » TEXT)."""
    noms = []
    i = data.find(b"8BIMdesc")
    if i < 0:
        return noms
    j = i
    while True:
        j = data.find(b"Nm  TEXT", j)
        if j < 0:
            break
        try:
            lec = Lecteur(data, j + 8)
            noms.append(lec.unicode())
        except (ValueError, struct.error):
            pass
        j += 8
    return noms


# ------------------------------------------------------------------ GIMP / Krita .gbr, .gih
def _gbr(lec: Lecteur) -> Forme:
    debut = lec.p
    taille_entete, version = lec.u32(), lec.u32()
    w, h, octets = lec.u32(), lec.u32(), lec.u32()
    esp = 0.25
    if version == 1:
        nom_long = taille_entete - 20
    else:
        if lec.octets(4) != b"GIMP":
            raise ValueError("pas un pinceau GIMP")
        esp = lec.u32() / 100
        nom_long = taille_entete - 28
    nom = lec.octets(max(0, nom_long)).split(b"\x00")[0].decode("utf-8", "replace")
    lec.p = debut + taille_entete
    if not (0 < w <= 10000 and 0 < h <= 10000 and octets in (1, 2, 4)):
        raise ValueError("taille de pinceau impossible")
    a = np.frombuffer(lec.octets(w * h * octets), np.uint8).reshape(h, w, octets) if octets > 1 else \
        np.frombuffer(lec.octets(w * h), np.uint8).reshape(h, w)
    if octets == 2:
        a = a[:, :, 0]                                   # 16 bits : poids fort
    elif octets == 4:
        a = _rgba_ou_gris(a)
    return Forme(nom or "GIMP", _reduire(np.ascontiguousarray(a)), esp or 0.25)


def _rgba_ou_gris(a: np.ndarray) -> np.ndarray:
    """Une forme RGBA sans couleur (gris) devient une forme grise (elle prend la couleur du pinceau)."""
    rgb = a[:, :, :3].astype(np.int16)
    if (np.abs(rgb[:, :, 0] - rgb[:, :, 1]) < 8).all() and (np.abs(rgb[:, :, 1] - rgb[:, :, 2]) < 8).all():
        alpha = a[:, :, 3].astype(np.float32)
        if alpha.min() >= 250:                           # opaque : le noir peint
            return (255 - rgb[:, :, 0]).astype(np.uint8)
        return (alpha * (255 - rgb[:, :, 0]) / 255 + 0.5).astype(np.uint8) if rgb.mean() > 8 else a[:, :, 3].copy()
    return np.ascontiguousarray(a)


def lire_gbr(data: bytes) -> Contenu:
    return Contenu(formes=[_gbr(Lecteur(data))])


def lire_gih(data: bytes) -> Contenu:
    """Pinceau animé GIMP : 2 lignes de texte (nom, nombre de formes et réglages), puis les formes .gbr."""
    lignes = data.split(b"\n", 2)
    if len(lignes) < 3:
        raise ValueError("pinceau animé illisible")
    nom = lignes[0].decode("utf-8", "replace").strip() or "GIMP"
    n = int(lignes[1].split()[0])
    lec = Lecteur(data, len(lignes[0]) + len(lignes[1]) + 2)
    res = Contenu()
    for i in range(n):
        if lec.fini():
            break
        f = _gbr(lec)
        f.nom = f"{nom} {i + 1}" if n > 1 else nom
        res.formes.append(f)
    return res


# ------------------------------------------------------------------ motifs
def lire_pat_gimp(data: bytes) -> Contenu:
    lec = Lecteur(data)
    taille_entete, _version, w, h, octets = lec.u32(), lec.u32(), lec.u32(), lec.u32(), lec.u32()
    if lec.octets(4) != b"GPAT":
        raise ValueError("pas un motif GIMP")
    nom = lec.octets(max(0, taille_entete - 24)).split(b"\x00")[0].decode("utf-8", "replace")
    lec.p = taille_entete
    a = np.frombuffer(lec.octets(w * h * octets), np.uint8).reshape(h, w, octets)
    return Contenu(motifs=[Motif(nom or "GIMP", _reduire(_vers_rgba(a)))])


def _vers_rgba(a: np.ndarray) -> np.ndarray:
    h, w = a.shape[:2]
    if a.ndim == 2:
        a = a[:, :, None]
    n = a.shape[2]
    sortie = np.empty((h, w, 4), np.uint8)
    if n in (1, 2):
        sortie[:, :, :3] = a[:, :, :1]
        sortie[:, :, 3] = a[:, :, 1] if n == 2 else 255
    else:
        sortie[:, :, :3] = a[:, :, :3]
        sortie[:, :, 3] = a[:, :, 3] if n >= 4 else 255
    return sortie


def lire_pat_photoshop(data: bytes) -> Contenu:
    """Motifs Photoshop (8BPT) : RVB, gris ou couleurs indexées, 8 ou 16 bits, transparence si présente."""
    lec = Lecteur(data)
    if lec.octets(4) != b"8BPT":
        raise ValueError("pas un motif Photoshop")
    lec.u16()
    n = lec.u32()
    res = Contenu()
    for i in range(n):
        try:
            lec.u32()                                     # version
            mode = lec.u32()
            h, w = lec.u16(), lec.u16()
            nom = lec.unicode() or f"Motif {i + 1}"
            lec.pascal()                                  # identifiant
            palette = None
            if mode == 2:
                palette = np.frombuffer(lec.octets(768), np.uint8).reshape(256, 3)
            lec.u32()                                     # version de la liste (3)
            longueur = lec.u32()
            fin = lec.p + longueur
            haut, gauche, bas, droite = lec.i32(), lec.i32(), lec.i32(), lec.i32()
            nb = lec.u32()
            canaux = []
            for _ in range(nb + 2):
                if lec.p >= fin:
                    break
                if not lec.u32():                         # canal non écrit
                    continue
                long_c = lec.u32()
                if not long_c:
                    continue
                fin_c = lec.p + long_c
                prof = lec.u32()
                ch, cg, cb, cd = lec.i32(), lec.i32(), lec.i32(), lec.i32()
                prof2, comp = lec.u16(), lec.u8()
                cw, chh = cd - cg, cb - ch
                if cw > 0 and chh > 0:
                    canaux.append(_canal(lec, cw, chh, prof2 or prof, comp))
                lec.p = fin_c
            lec.p = fin
            if not canaux:
                continue
            h0, w0 = canaux[0].shape
            canaux = [c for c in canaux if c.shape == (h0, w0)]
            if mode == 2 and palette is not None:
                rgb = palette[canaux[0]]
                a = np.dstack([rgb, canaux[1]]) if len(canaux) > 1 else rgb
            elif mode in (3, 4):                          # RVB (CMJN : on prend les 3 premiers, approximatif)
                a = np.dstack(canaux[:4]) if len(canaux) >= 4 and mode == 3 else np.dstack(canaux[:3])
            else:                                         # gris
                a = np.dstack(canaux[:2]) if len(canaux) > 1 else canaux[0]
            res.motifs.append(Motif(nom, _reduire(_vers_rgba(np.ascontiguousarray(a)))))
        except (ValueError, struct.error) as e:
            res.ignores.append((f"Motif {i + 1}", str(e)))
            break
    return res


def lire_pat(data: bytes) -> Contenu:
    return lire_pat_photoshop(data) if data[:4] == b"8BPT" else lire_pat_gimp(data)


# ------------------------------------------------------------------ images, paquets
def lire_image(data: bytes, nom: str, comme: str) -> Contenu:
    """Une image : comme forme de pinceau (comme = « forme ») ou comme motif (« motif »)."""
    with Image.open(io.BytesIO(data)) as im:
        im.load()
        a = np.asarray(im.convert("RGBA"))
    if comme == "motif":
        return Contenu(motifs=[Motif(nom, _reduire(a))])
    return Contenu(formes=[Forme(nom, _reduire(_rgba_ou_gris(a)))])


def lire_paquet(data: bytes) -> Contenu:
    """Paquet Krita (.bundle, un zip) : formes (brushes/) et motifs (patterns/)."""
    res = Contenu()
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for n in z.namelist():
            if n.endswith("/"):
                continue
            dossier, _, fichier = n.partition("/")
            ext = Path(fichier).suffix.lower()
            if dossier not in ("brushes", "patterns") or ext not in EXT_PINCEAUX + EXT_MOTIFS + EXT_IMAGES:
                continue
            try:
                c = lire_octets(z.read(n), fichier, "motif" if dossier == "patterns" else "forme")
            except Exception as e:                       # un élément illisible n'arrête pas le reste
                res.ignores.append((fichier, str(e)))
                continue
            res.formes += c.formes
            res.motifs += c.motifs
            res.ignores += c.ignores
    return res


def lire_octets(data: bytes, nom_fichier: str, comme: str = "forme") -> Contenu:
    ext = Path(nom_fichier).suffix.lower()
    base = Path(nom_fichier).stem.replace("_", " ")
    if ext == ".abr":
        return lire_abr(data, base)
    if ext == ".gbr":
        c = lire_gbr(data)
    elif ext == ".gih":
        c = lire_gih(data)
    elif ext == ".pat":
        c = lire_pat(data)
    elif ext in EXT_IMAGES:
        return lire_image(data, base, comme)
    elif ext in EXT_PAQUETS:
        return lire_paquet(data)
    else:
        raise ValueError("format de fichier inconnu")
    for o in c.formes + c.motifs:
        if not o.nom or o.nom in ("GIMP", "Untitled"):
            o.nom = base
    return c


def lire_fichier(chemin: str | Path, comme: str = "forme", pleine_taille: bool = False) -> Contenu:
    """pleine_taille : les formes et motifs gardent leur taille d'origine (sinon : réduits à TAILLE_MAX)."""
    chemin = Path(chemin)
    _lecture.pleine = pleine_taille
    try:
        return lire_octets(chemin.read_bytes(), chemin.name, comme)
    finally:
        _lecture.pleine = False
