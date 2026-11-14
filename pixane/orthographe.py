"""Orthographe et césure des textes.

- Orthographe : dictionnaires Hunspell de LibreOffice (pixane\\dictionnaires : français Grammalecte « Classique »,
  MPL 2.0 ; anglais SCOWL en_US), lus par spylls (MIT). Les suggestions sont calculées ici (une faute de frappe :
  lettre en trop, en moins, inversée, remplacée, accent) : celles de spylls prennent jusqu'à 30 s.
- Césure : pyphen (règles de LibreOffice, LGPL / MPL).
Option « Orthographe et césure » (installateur, Affichage) : réglage `orthographe` ; décochée, rien n'est chargé.
"""
from __future__ import annotations

import re
import atexit
import threading
import time
import unicodedata
from functools import lru_cache
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent / "dictionnaires"      # installés avec Pixane (case de l'installateur)
FICHIERS = {"fr": "fr", "en": "en_US"}            # langue -> nom des fichiers .aff / .dic
NOMS = {"fr": "Français", "en": "English"}
CESURE = {"fr": "fr", "en": "en_US"}
ALPHABET = {"fr": "abcdefghijklmnopqrstuvwxyzàâäçéèêëîïôöùûüÿœæ", "en": "abcdefghijklmnopqrstuvwxyz"}
# dictionnaires de LibreOffice (github.com/LibreOffice/dictionaries) : pour ajouter une langue après l'installation
_GITHUB = "https://raw.githubusercontent.com/LibreOffice/dictionaries/master/"
SOURCES = {
    "fr": dict(fichiers=[("fr_FR/dictionaries/fr.aff", "fr.aff"), ("fr_FR/dictionaries/fr.dic", "fr.dic"),
                         ("fr_FR/dictionaries/README_dict_fr.txt", "README_dict_fr.txt")],
               taille="1,4 Mo", licence="MPL 2.0", auteur="Grammalecte (Olivier R.)"),
    "en": dict(fichiers=[("en/en_US.aff", "en_US.aff"), ("en/en_US.dic", "en_US.dic"),
                         ("en/README_en_US.txt", "README_en_US.txt")],
               taille="0,6 Mo", licence="SCOWL (libre)", auteur="Kevin Atkinson (SCOWL)"),
}
APOSTROPHES = "'’"
# un mot : lettres, avec apostrophes ou traits d'union à l'intérieur (l'éléphant, aujourd'hui, peut-être)
MOT = re.compile(r"[^\W\d_]+(?:[’'\-][^\W\d_]+)*")
TEMPS_SUGGESTIONS = 1.5                            # secondes au plus pour chercher des suggestions

_dicos: dict = {}
_verrou = threading.Lock()
_mots_perso: set[str] = set()
_ignores: set[str] = set()


def _reglages():
    from .fenetre import reglages
    return reglages()


def active() -> bool:
    """Option « Orthographe et césure » cochée (réglage `orthographe`, choisi à l'installation, vrai par défaut)."""
    return str(_reglages().value("orthographe", "true")).lower() != "false"


def dossier_perso() -> Path:
    """Dictionnaires ajoutés depuis Pixane (Program Files est en lecture seule)."""
    import os
    base = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Pixane"
    nom = "dictionnaires"
    if os.environ.get("PIXANE_REGLAGES"):                 # essais : à part
        nom += "-" + os.environ["PIXANE_REGLAGES"]
    return base / nom


def fichiers_langue(langue: str) -> Path | None:
    """Chemin (sans extension) du dictionnaire de la langue, s'il est là (installé ou ajouté)."""
    for dossier in (dossier_perso(), DOSSIER):
        base = dossier / FICHIERS[langue]
        if base.with_suffix(".dic").is_file() and base.with_suffix(".aff").is_file():
            return base
    return None


def langues_presentes() -> list[str]:
    return [l for l in FICHIERS if fichiers_langue(l) is not None]


def langues_actives() -> list[str]:
    """Langues cochées (installateur ou Pixane) dont le dictionnaire est là."""
    v = _reglages().value("orthographe_langues", None)
    choisies = list(FICHIERS) if v is None else [l for l in str(v).split(",") if l in FICHIERS]
    return [l for l in choisies if fichiers_langue(l) is not None]


def choisir_langues(langues: list[str]):
    _reglages().setValue("orthographe_langues", ",".join(l for l in FICHIERS if l in langues))


def installer_langue(langue: str, progression=None) -> None:
    """Télécharge le dictionnaire de la langue (LibreOffice) dans le dossier perso. Exception si échec."""
    import urllib.request
    dossier = dossier_perso()
    dossier.mkdir(parents=True, exist_ok=True)
    fichiers = SOURCES[langue]["fichiers"]
    temporaires = []
    try:
        for n, (chemin, nom) in enumerate(fichiers):
            if progression:
                progression(n, len(fichiers))
            tmp = dossier / (nom + ".tmp")
            req = urllib.request.Request(_GITHUB + chemin, headers={"User-Agent": "Pixane"})
            with urllib.request.urlopen(req, timeout=60) as r, open(tmp, "wb") as f:
                f.write(r.read())
            temporaires.append((tmp, dossier / nom))
        for tmp, final in temporaires:
            if final.suffix in (".dic", ".aff") and tmp.stat().st_size < 1000:
                raise OSError(f"fichier incomplet : {final.name}")
        for tmp, final in temporaires:
            tmp.replace(final)
    finally:
        for tmp, _final in temporaires:
            tmp.unlink(missing_ok=True)
    _dicos.pop(langue, None)


def retirer_langue(langue: str) -> None:
    """Décoche la langue ; un dictionnaire ajouté depuis Pixane est effacé (celui de l'installation reste, il part
    avec la désinstallation)."""
    base = dossier_perso() / FICHIERS[langue]
    for ext in (".dic", ".aff"):
        base.with_suffix(ext).unlink(missing_ok=True)
    _dicos.pop(langue, None)


def langue_texte(langue: str) -> str:
    """Langue d'un texte : la sienne, sinon celle de Pixane."""
    if langue in FICHIERS:
        return langue
    from .langue import langue as langue_pixane
    l = langue_pixane()
    return l if l in FICHIERS else "fr"


def disponible() -> bool:
    """Bibliothèques présentes (pyphen pour la césure, spylls pour l'orthographe)."""
    try:
        import pyphen  # noqa: F401
        import spylls  # noqa: F401
    except ImportError:
        return False
    return True


def verifiable(langue: str) -> bool:
    """L'orthographe de ce texte peut être vérifiée (option cochée, langue cochée et présente)."""
    return active() and disponible() and langue_texte(langue) in langues_actives()


def _charger(langue: str, base):
    """Lecture des fichiers par spylls (pur Python : rien de Qt, peut tourner dans un fil)."""
    with _verrou:
        d = _dicos.get(langue)
        if d is None:
            from spylls.hunspell import Dictionary
            d = _dicos[langue] = Dictionary.from_files(str(base))
        return d


def dictionnaire(langue: str):
    """Dictionnaire de la langue (chargé une fois, environ 1 s pour le français)."""
    langue = langue_texte(langue)
    d = _dicos.get(langue)
    if d is not None:
        return d
    base = fichiers_langue(langue)
    if base is None:
        raise FileNotFoundError(f"dictionnaire absent : {langue}")
    return _charger(langue, base)


_fils: list = []


def precharger(langue: str = ""):
    """Charge le dictionnaire en arrière-plan (pour que le premier soulignement ne fige pas Pixane).
    La langue et le fichier sont trouvés ici (réglages Qt : seulement dans le fil principal) ; le fil ne fait que
    lire le fichier, et Pixane l'attend en quittant (un fil encore actif à la fermeture de Python peut planter)."""
    langue = langue_texte(langue)
    if langue in _dicos:
        return
    base = fichiers_langue(langue)
    if base is None:
        return
    fil = threading.Thread(target=_charger, args=(langue, base), daemon=True)
    _fils.append(fil)
    fil.start()


def _attendre_fils():
    for fil in _fils:
        fil.join(30)


atexit.register(_attendre_fils)


def pret(langue: str) -> bool:
    return langue_texte(langue) in _dicos


# ------------------------------------------------------------------ mots ajoutés / ignorés
def charger_mots_perso():
    import json
    try:
        mots = json.loads(_reglages().value("mots_perso", "[]"))
    except ValueError:
        mots = []
    _mots_perso.clear()
    _mots_perso.update(m for m in mots if isinstance(m, str))


def ajouter_mot(mot: str):
    """« Ajouter au dictionnaire » : le mot n'est plus souligné, dans aucun texte (gardé dans les réglages)."""
    import json
    _mots_perso.add(mot)
    _reglages().setValue("mots_perso", json.dumps(sorted(_mots_perso), ensure_ascii=False))


def ignorer_mot(mot: str):
    """« Ignorer » : le mot n'est plus souligné jusqu'à la fermeture de Pixane."""
    _ignores.add(mot)


# ------------------------------------------------------------------ vérification
def _normal(mot: str) -> str:
    return mot.replace("’", "'")


def correct(mot: str, langue: str) -> bool:
    if mot in _mots_perso or mot in _ignores or len(mot) < 2:
        return True
    d = dictionnaire(langue)
    if d.lookup(mot) or d.lookup(_normal(mot)):
        return True
    if "-" in mot:                                    # mots composés : chaque partie
        return all(correct(m, langue) for m in mot.split("-") if m)
    return False


def fautes(texte: str, langue: str) -> list[tuple[int, int]]:
    """Mots mal orthographiés du texte : (début, fin)."""
    if not verifiable(langue):
        return []
    return [(m.start(), m.end()) for m in MOT.finditer(texte) if not correct(m.group(), langue)]


def mot_a(texte: str, pos: int) -> tuple[int, int] | None:
    """Le mot du texte qui contient la position (ou finit juste avant)."""
    for m in MOT.finditer(texte):
        if m.start() <= pos <= m.end():
            return m.start(), m.end()
    return None


def _sans_accents(mot: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", mot) if unicodedata.category(c) != "Mn")


def _variantes_accents(m: str, lettres: str, maximum: int = 400) -> list[str]:
    """Le mot avec d'autres accents, sur une ou plusieurs lettres (eleve -> élève)."""
    from itertools import product
    choix = []
    for ch in m:
        nu = _sans_accents(ch)
        options = [ch] + [x for x in lettres if x != ch and _sans_accents(x) == nu]
        choix.append(options)
    res = []
    for combi in product(*choix):
        c = "".join(combi)
        if c != m:
            res.append(c)
        if len(res) >= maximum:
            break
    return res


def suggestions(mot: str, langue: str, nombre: int = 6) -> list[str]:
    """Mots proches qui existent : accents, lettres inversées, en trop, oubliées (apostrophe et trait d'union
    compris), remplacées, ou deux mots collés ; dans cet ordre (le plus probable d'abord)."""
    langue = langue_texte(langue)
    d = dictionnaire(langue)
    debut = time.monotonic()
    majuscule = mot[:1].isupper() and not mot.isupper()
    tout_maj = mot.isupper() and len(mot) > 1
    m = mot.lower()
    lettres = ALPHABET[langue]
    familles = [
        _variantes_accents(m, lettres),
        [m[:i] + m[i + 1] + m[i] + m[i + 2:] for i in range(len(m) - 1)],
        [m[:i] + m[i + 1:] for i in range(len(m))],
        [m[:i] + "'" + m[i:] for i in range(1, len(m))]                    # apostrophe (aujourd'hui)
        + [m[:i] + x + m[i:] for i in range(len(m) + 1) for x in lettres],
        [m[:i] + x + m[i + 1:] for i in range(len(m)) for x in lettres],
    ]
    res: list[str] = []
    vus = {m}
    for famille in familles:
        for c in famille:
            if c in vus:
                continue
            vus.add(c)
            if d.lookup(c) or ("'" in c and d.lookup(c.replace("'", "’"))):
                res.append(c)
            if time.monotonic() - debut > TEMPS_SUGGESTIONS:
                break
        if len(res) >= nombre or time.monotonic() - debut > TEMPS_SUGGESTIONS:
            break
    if len(res) < nombre:
        for i in range(1, len(m)):                                                            # deux mots collés
            if min(i, len(m) - i) >= 2 and d.lookup(m[:i]) and d.lookup(m[i:]):
                res.append(m[:i] + " " + m[i:])
    if tout_maj:
        res = [c.upper() for c in res]
    elif majuscule:
        res = [c[:1].upper() + c[1:] for c in res]
    return res[:nombre]


# ------------------------------------------------------------------ césure
@lru_cache(maxsize=8)
def _coupeur(langue: str):
    import pyphen
    return pyphen.Pyphen(lang=CESURE[langue], left=2, right=3)


@lru_cache(maxsize=512)
def couper(texte: str, langue: str = "") -> str:
    """Texte avec les coupures possibles des mots longs (tiret conditionnel U+00AD)."""
    coupeur = _coupeur(langue_texte(langue))
    return MOT.sub(lambda m: m.group() if len(m.group()) < 6 else coupeur.inserted(m.group(), hyphen="­"),
                   texte)
