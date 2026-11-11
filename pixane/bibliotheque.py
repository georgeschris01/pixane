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


@dataclass
class Pinceau:
    """Forme(s) d'un pinceau ; une forme : (h, w) gris (prend la couleur du pinceau) ou (h, w, 4) en couleur."""
    nom: str
    formes: list
    espacement: float = 0.25
    cle: str = ""                       # identifiant stable : « groupe/fichier#n »

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

    @property
    def elements(self) -> list:
        """Pinceaux ou motifs du groupe (lus à la première demande)."""
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
        groupe = cle.split("/", 1)[0]
        for g in self.groupes[genre]:
            if g.nom == groupe:
                for e in g.elements:
                    if e.cle == cle:
                        return e
        return None

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


_unique: Bibliotheque | None = None


def bibliotheque() -> Bibliotheque:
    """La bibliothèque de Pixane (une seule, créée à la première demande)."""
    global _unique
    if _unique is None:
        _unique = Bibliotheque()
    return _unique
