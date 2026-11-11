"""Bibliothèque de pinceaux et de motifs : ceux livrés avec Pixane (paquets de Krita, licence CC-0) et ceux que
l'utilisateur ajoute (.abr, .gbr, .gih, .pat, .bundle, images).

Les fichiers ajoutés sont copiés tels quels dans %LOCALAPPDATA%\\Pixane\\bibliotheque\\{pinceaux,motifs} : chaque
fichier devient un « groupe » (un .abr de 50 pinceaux = un groupe de 50). Rien n'est converti : on relit le fichier
d'origine (rapide), ce qui garde tout ce qu'il contient.

Un pinceau d'un .gih (pinceau animé de GIMP / Krita) garde toutes ses formes : elles alternent pendant le trait.
"""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .formats_pinceaux import (EXT_IMAGES, EXT_MOTIFS, EXT_PAQUETS, EXT_PINCEAUX, Contenu, lire_fichier)

BASE = Path(__file__).resolve().parent / "ressources" / "base"
GROUPES_BASE = [("krita4", "Krita 4"), ("krita3", "Krita 3")]
PINCEAUX, MOTIFS = "pinceaux", "motifs"
SIMPLES = "Simples"                     # premier groupe de pinceaux : les formes de base, dessinées par Pixane


def _formes_simples() -> list:
    """Les pinceaux de tous les jours (comme les premiers de Photoshop) : rond dur, rond doux, aérographe, carré,
    plat, biseau. Formes en gris (blanc = peint), 256 px."""
    from .pointe import forme_ronde
    t = 256
    yy, xx = np.mgrid[0:t, 0:t].astype(np.float32)
    c = (t - 1) / 2
    u, v = (xx - c) / (t / 2), (yy - c) / (t / 2)

    def bord(d):                                       # 1 dedans, 0 dehors, bord adouci de ~2 px
        return (np.clip(0.5 - d * t / 4, 0, 1) * 255 + 0.5).astype(np.uint8)

    r = np.hypot(u, v)
    plat = bord(np.hypot(u, v / 0.3) - 1)
    a = np.radians(45)
    ub, vb = u * np.cos(a) + v * np.sin(a), -u * np.sin(a) + v * np.cos(a)
    biseau = bord(np.hypot(ub, vb / 0.14) - 1)
    return [
        ("rond_dur", "Rond dur", forme_ronde(0.92, t), 0.08),
        ("rond_doux", "Rond doux", forme_ronde(0.0, t), 0.1),
        ("aerographe", "Aérographe", (np.exp(-2.5 * r ** 2) * np.clip(1 - r, 0, 1) ** 0.5 * 255 + 0.5).astype(np.uint8), 0.06),
        ("carre", "Carré", bord(np.maximum(np.abs(u), np.abs(v)) * 1.02 - 1), 0.08),
        ("plat", "Plat", plat, 0.06),
        ("biseau", "Biseau (calligraphie)", biseau, 0.04),
    ]


def groupe_simples() -> "Groupe":
    from .langue import tr
    g = Groupe(SIMPLES, PINCEAUX, True, [])
    g._elements = [Pinceau(tr(nom), [forme], esp, f"{SIMPLES}/{cle}#0") for cle, nom, forme, esp in _formes_simples()]
    return g


@dataclass
class Pinceau:
    """Forme(s) d'un pinceau ; une forme : (h, w) gris (prend la couleur du pinceau) ou (h, w, 4) en couleur."""
    nom: str
    formes: list
    espacement: float = 0.25
    cle: str = ""                       # identifiant stable : « groupe/fichier#n »
    reglages: dict | None = None        # style prêt : réglages appliqués en le choisissant

    @property
    def en_couleur(self) -> bool:
        return self.formes[0].ndim == 3


@dataclass
class Motif:
    nom: str
    image: np.ndarray                   # (h, w, 4) RGBA
    cle: str = ""


@dataclass
class Groupe:
    nom: str
    genre: str                          # PINCEAUX ou MOTIFS
    de_base: bool
    fichiers: list                      # chemins (Path)
    _elements: list | None = field(default=None, repr=False)
    ignores: list = field(default_factory=list)
    fabrique: object = field(default=None, repr=False)     # fonction qui donne les éléments (groupes calculés)

    @property
    def elements(self) -> list:
        """Pinceaux ou motifs du groupe (lus à la première demande)."""
        if self._elements is None and self.fabrique is not None:
            self._elements = self.fabrique()
        if self._elements is None:
            self._elements = []
            for f in self.fichiers:
                try:
                    c = lire_fichier(f, "motif" if self.genre == MOTIFS else "forme")
                except Exception as e:               # fichier abîmé : on le signale, on continue
                    self.ignores.append((f.name, str(e)))
                    continue
                self.ignores += c.ignores
                self._elements += elements_de(c, self.genre, f, self.nom)
        return self._elements


def elements_de(c: Contenu, genre: str, fichier: Path, groupe: str) -> list:
    if genre == MOTIFS:
        return [Motif(m.nom, m.image, f"{groupe}/{fichier.name}#{i}") for i, m in enumerate(c.motifs)]
    if fichier.suffix.lower() == ".gih" and c.formes:     # pinceau animé : un seul pinceau à plusieurs formes
        nom = c.formes[0].nom.rsplit(" ", 1)[0] if len(c.formes) > 1 else c.formes[0].nom
        return [Pinceau(nom, [f.image for f in c.formes], c.formes[0].espacement, f"{groupe}/{fichier.name}#0")]
    return [Pinceau(f.nom, [f.image], f.espacement, f"{groupe}/{fichier.name}#{i}") for i, f in enumerate(c.formes)]


def dossier_utilisateur() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Pixane"
    nom = "bibliotheque"
    if os.environ.get("PIXANE_REGLAGES"):            # essais : à part
        nom += "-" + os.environ["PIXANE_REGLAGES"]
    return base / nom


def _accepte(f: Path, genre: str) -> bool:
    ext = f.suffix.lower()
    return ext in (EXT_PINCEAUX if genre == PINCEAUX else EXT_MOTIFS) + EXT_IMAGES


class Bibliotheque:
    def __init__(self, dossier: Path | None = None):
        self.dossier = Path(dossier) if dossier else dossier_utilisateur()
        self.groupes: dict[str, list[Groupe]] = {}
        self.recharger()

    def recharger(self) -> None:
        for genre in (PINCEAUX, MOTIFS):
            liste = []
            if genre == PINCEAUX:                 # styles prêts, simples, puis les pinceaux de Krita par familles
                liste.append(Groupe(STYLES, PINCEAUX, True, [], fabrique=lambda: styles_prets(self)))
                liste.append(groupe_simples())
                fichiers = [f for court, _n in GROUPES_BASE if (BASE / court / genre).is_dir()
                            for f in (BASE / court / genre).iterdir() if _accepte(f, genre)]
                par_famille: dict[str, list] = {}
                for f in fichiers:
                    par_famille.setdefault(famille(f.name), []).append(f)
                for nom, _mots in FAMILLES + [(DIVERS, ())]:
                    if par_famille.get(nom):
                        liste.append(Groupe(nom, genre, True, sorted(par_famille[nom], key=lambda p: p.name.lower())))
            else:
                for court, nom in GROUPES_BASE:
                    d = BASE / court / genre
                    if d.is_dir():
                        liste.append(Groupe(nom, genre, True, sorted(f for f in d.iterdir() if _accepte(f, genre))))
            d = self.dossier / genre
            if d.is_dir():
                for f in sorted(d.iterdir(), key=lambda p: p.name.lower()):
                    if f.is_file():
                        liste.append(Groupe(f.stem, genre, False, [f]))
            self.groupes[genre] = liste

    def elements(self, genre: str) -> list:
        return [e for g in self.groupes[genre] for e in g.elements]

    def trouver(self, genre: str, cle: str):
        groupe, _, reste = cle.partition("/")
        for g in self.groupes[genre]:
            if g.nom == groupe:
                for e in g.elements:
                    if e.cle == cle:
                        return e
        if groupe in ANCIENS_GROUPES and genre == PINCEAUX:     # clé d'avant le classement par familles
            return self.par_fichier(reste)
        return None

    def par_fichier(self, nom: str):
        """Pinceau de base d'après « fichier#n » (quelle que soit sa famille)."""
        fichier = nom.split("#", 1)[0]
        g = next((g for g in self.groupes[PINCEAUX] if g.de_base and g.fabrique is None
                  and any(f.name == fichier for f in g.fichiers)), None)
        return next((e for e in g.elements if e.cle.endswith("/" + nom)), None) if g else None

    def importer(self, chemin: str | Path, image_comme: str = PINCEAUX) -> dict:
        """Ajoute un fichier : copié dans la bibliothèque (pinceaux et/ou motifs selon ce qu'il contient ; une
        image devient un pinceau ou un motif selon image_comme). Renvoie {"pinceaux": n, "motifs": n, "ignores": [...]}; ValueError si le fichier n'apporte rien."""
        chemin = Path(chemin)
        ext = chemin.suffix.lower()
        if ext not in EXT_PINCEAUX + EXT_MOTIFS + EXT_IMAGES + EXT_PAQUETS:
            raise ValueError("format de fichier inconnu")
        comme = "motif" if ext in EXT_MOTIFS or (ext in EXT_IMAGES and image_comme == MOTIFS) else "forme"
        c = lire_fichier(chemin, comme)
        if not c.formes and not c.motifs:
            raise ValueError("aucun pinceau ni motif lisible dans ce fichier")
        bilan = {PINCEAUX: 0, MOTIFS: 0, "ignores": list(c.ignores)}
        if ext in EXT_PAQUETS:                   # paquet : on en tire ses fichiers de pinceaux et de motifs
            import zipfile
            with zipfile.ZipFile(chemin) as z:
                for n in z.namelist():
                    d, _, f = n.partition("/")
                    genre = {"brushes": PINCEAUX, "patterns": MOTIFS}.get(d)
                    if genre and f and "/" not in f and _accepte(Path(f), genre):
                        cible = self._cible(genre, f"{chemin.stem} - {f}")
                        cible.write_bytes(z.read(n))
            bilan[PINCEAUX], bilan[MOTIFS] = len(c.formes), len(c.motifs)
        else:
            genre = MOTIFS if c.motifs else PINCEAUX
            shutil.copy2(chemin, self._cible(genre, chemin.name))
            bilan[genre] = len(c.motifs) if c.motifs else len(c.formes)
        self.recharger()
        return bilan

    def _cible(self, genre: str, nom: str) -> Path:
        d = self.dossier / genre
        d.mkdir(parents=True, exist_ok=True)
        cible, k = d / nom, 2
        while cible.exists():
            cible = d / f"{Path(nom).stem} ({k}){Path(nom).suffix}"
            k += 1
        return cible

    def retirer(self, groupe: Groupe) -> None:
        """Retire un groupe ajouté par l'utilisateur (les groupes de base restent)."""
        if groupe.de_base:
            raise ValueError("groupe de base")
        for f in groupe.fichiers:
            f.unlink(missing_ok=True)
        self.recharger()


# ---- familles (comme les dossiers de pinceaux de Photoshop) : d'après le nom du fichier
STYLES = "Styles prêts"
DIVERS = "Divers"
ANCIENS_GROUPES = ("Krita 4", "Krita 3")
FAMILLES = [
    ("Crayon et fusain", ("pencil", "graphite", "crayon", "sketch", "study", "chalk", "charcoal")),
    ("Peinture", ("oil", "bristle", "rake", "brush", "smear", "knife", "chisel", "watercolor", "flat_textured",
                  "impressionism", "smudge", "eroded", "dynamic", "3_dotted", "3_splat", "rect_textured", "fibers")),
    ("Nature", ("grass", "leaves", "leaf", "vegetal", "bamboo", "foliage", "herbs", "flowers", "trees", "rock",
                "mountain", "water", "snow", "smoke", "cloud", "floor", "fur", "hair", "scales", "reptile",
                "mineral", "provencal", "coroballs", "spines")),
    ("Effets", ("sparkle", "star", "fairy", "bokey", "splat", "hearts", "dust", "particles", "debris", "sparks",
                "freckles", "lucky", "snowman")),
    ("Textures", ("texture", "noise", "concrete", "wall", "brick", "abstract", "rough", "scratch", "crackle",
                  "dirty", "spike", "square", "gradient", "scribbles", "circle_hard")),
    ("Formes", ("shape", "m_0", "u_circle", "z_", "te_", "pipe", "triangle", "arrow", "chain", "braids", "church",
                "cage", "bulb", "pin.", "a_pin", "techno")),
]


def famille(nom_fichier: str) -> str:
    n = nom_fichier.lower()
    for nom, mots in FAMILLES:
        if any(m in n for m in mots):
            return nom
    return DIVERS


# ---- styles prêts : une forme et ses réglages, en un clic (comme les préréglages d'outils de Photoshop)
_PAPIER = "Krita 4/04_paper-C-grain.png#0"
_TOILE = "Krita 4/02_rough-canvas.png#0"
_AQUARELLE = "Krita 4/03_default-paper.png#0"
STYLES_PRETS = [
    ("crayon", "Crayon", "Simples/rond_dur#0",
     dict(espacement=0.06, texture=_PAPIER, texture_force=0.7, texture_echelle=0.6, flux=0.85, pression_opacite=True)),
    ("fusain", "Fusain", "graphite_grain.gih#0",
     dict(espacement=0.06, texture=_PAPIER, texture_force=0.5, var_angle=0.1)),
    ("craie", "Craie", "chalk_round_hard.png#0",
     dict(espacement=0.08, texture=_PAPIER, texture_force=0.75, texture_echelle=1.5, var_angle=0.15,
          var_taille=0.1)),
    ("encre", "Encre (plume)", "Simples/rond_dur#0", dict(espacement=0.04, pression_taille=True, taille_min=0.15)),
    ("feutre", "Feutre", "Simples/rond_dur#0", dict(espacement=0.05, rondeur=0.75, angle=30, flux=0.6)),
    ("calligraphie", "Calligraphie", "Simples/biseau#0", dict(espacement=0.03)),
    ("aquarelle", "Aquarelle", "watercolor.gih#0",
     dict(espacement=0.12, flux=0.3, texture=_AQUARELLE, texture_force=0.45, var_luminosite=0.04,
          var_angle=0.3)),
    ("huile", "Peinture à l'huile", "oil_bristle.png#0",
     dict(espacement=0.08, suivre=True, var_luminosite=0.05)),
    ("couteau", "Couteau à peindre", "oil_knife.png#0", dict(espacement=0.06, suivre=True, var_luminosite=0.04)),
    ("sec", "Pinceau sec", "bristles_circle_sparse.png#0",
     dict(espacement=0.06, suivre=True, texture=_TOILE, texture_force=0.5)),
    ("aerographe", "Aérographe", "Simples/aerographe#0", dict(espacement=0.05, flux=0.15)),
    ("bombe", "Bombe (spray)", "random_particles.png#0",
     dict(espacement=0.25, dispersion=0.3, deux_axes=True, var_angle=1.0, flux=0.8)),
    ("feuillage", "Feuillage", "leaves.png#0",
     dict(espacement=0.45, dispersion=1.0, deux_axes=True, nombre=2, var_taille=0.5, var_angle=1.0,
          var_teinte=0.04, var_luminosite=0.25, melange_fond=0.3)),
    ("herbe", "Herbe", "grass.gih#0",
     dict(espacement=0.3, dispersion=0.4, var_taille=0.4, var_luminosite=0.15, var_teinte=0.03)),
    ("etoiles", "Étoiles et paillettes", "sparkle.png#0",
     dict(espacement=0.6, dispersion=1.0, deux_axes=True, nombre=2, var_taille=0.6, taille_min=0.4, var_angle=1.0)),
    ("fumee", "Nuages et fumée", "smoke.png#0",
     dict(espacement=0.3, flux=0.3, dispersion=0.3, var_taille=0.5, var_angle=1.0)),
    ("eclaboussures", "Éclaboussures", "splats_large.gih#0",
     dict(espacement=0.7, dispersion=0.6, deux_axes=True, var_taille=0.5, taille_min=0.4, var_angle=1.0)),
]


def styles_prets(biblio: "Bibliotheque") -> list:
    from .langue import tr
    liste = []
    for cle, nom, base, reglages in STYLES_PRETS:
        e = biblio.trouver(PINCEAUX, base) if base.startswith(SIMPLES + "/") else biblio.par_fichier(base)
        if e is not None:
            liste.append(Pinceau(tr(nom), e.formes, e.espacement, f"{STYLES}/{cle}#0", dict(reglages)))
    return liste


_unique: Bibliotheque | None = None


def bibliotheque() -> Bibliotheque:
    """La bibliothèque de Pixane (une seule, créée à la première demande)."""
    global _unique
    if _unique is None:
        _unique = Bibliotheque()
    return _unique
