"""Traduction des consignes de l'IA, du français vers l'anglais (Flux Kontext comprend mal le français).

Modèle Opus-MT fr-en (Helsinki-NLP, licence Apache-2.0), installé sur demande dans le dossier de Pixane ; il tourne
sur le PC (rien n'est envoyé sur Internet), avec le Python de ComfyUI (qui a déjà transformers et sentencepiece).

Les textes entre guillemets (« … », "…", “…”) ne sont pas traduits : ils sont remplacés par des repères avant la
traduction, puis remis tels quels (entre guillemets droits, ce que l'IA comprend).
"""
from __future__ import annotations

import json
import os
import re
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path

MODELE = "Helsinki-NLP/opus-mt-fr-en"
VERSION = "c4aed37b318c763fd177aa449b44e3b783cc6c02"      # version précise du dépôt (fichiers vérifiés)
LICENCE = "Apache-2.0"
# fichier : (taille en octets, empreinte SHA-256 ou None pour les petits fichiers : taille vérifiée)
CONTENU = {
    "config.json": (1416, None),
    "generation_config.json": (293, None),
    "model.safetensors": (300803608, "6e3837f34b903802c3d0d670362b997cee6e87584a1108eb3fa89e4625e4424a"),
    "source.spm": (802397, None),
    "target.spm": (778395, None),
    "tokenizer_config.json": (42, None),
    "vocab.json": (1339166, None),
}
FICHIERS = list(CONTENU)
TAILLE = sum(t for t, _ in CONTENU.values())
SCRIPT = Path(__file__).resolve().parent / "traduire_script.py"
_GUILLEMETS = re.compile(r"«\s*(.*?)\s*»|\"(.*?)\"|“(.*?)”|„(.*?)“")


NOM = "opus-mt-fr-en"


def dossier_par_defaut() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Pixane" / "traducteur"


def _reglages():
    from PySide6.QtCore import QSettings
    return QSettings("Pixane", os.environ.get("PIXANE_REGLAGES", "Pixane"))


def dossier_choisi() -> Path:
    """Dossier où l'on range le traducteur (choisi par l'utilisateur, sinon celui de Pixane)."""
    v = _reglages().value("traducteur_dossier", "")
    return Path(v) if v else dossier_par_defaut()


def choisir_dossier(d: Path | str | None):
    """Retient le dossier choisi (None : celui de Pixane)."""
    r = _reglages()
    if d is None or Path(d) == dossier_par_defaut():
        r.remove("traducteur_dossier")
    else:
        r.setValue("traducteur_dossier", str(Path(d)))


def dossier_programme() -> Path:
    """Dossier où Pixane est installé (D:\\Programmes\\Pixane…) : remplacé en entier à chaque mise à jour."""
    return Path(__file__).resolve().parents[1]


def dans_le_programme(d: Path | str) -> bool:
    """Vrai si d est dans le dossier du programme : ce qu'on y range est effacé à la mise à jour suivante (arrivé
    au traducteur de Christophe le 11/11/2026)."""
    try:
        return Path(d).resolve().is_relative_to(dossier_programme())
    except (OSError, ValueError):
        return False


def refuser_dossier(parent, d: Path | str, quoi: str) -> bool:
    """Message et True si le dossier d est dans celui du programme."""
    if not dans_le_programme(d):
        return False
    from PySide6.QtWidgets import QMessageBox
    from .langue import tr
    QMessageBox.warning(parent, quoi, tr(
        "« {dossier} » est dans le dossier où Pixane est installé ({programme}). Ce dossier est remplacé en entier à "
        "chaque mise à jour : ce qu'on y range serait effacé.\n\nChoisis un dossier ailleurs, par exemple "
        "D:\\Pixane-traducteur.", dossier=str(Path(d)), programme=str(dossier_programme())))
    return True


def dossier() -> Path:
    """Dossier du modèle : <dossier choisi>/opus-mt-fr-en."""
    return dossier_choisi() / NOM


_MOTS_ANGLAIS = set("""a an the and or of to in on at by for with from into as is are be it its this that these those
make change replace remove add keep put turn give same style text color colour word words line lines background
while without but not only all whole into onto your my his her their of very more less same exactly""".split())
# petits mots très courants d'autres langues (français, allemand, espagnol, italien, néerlandais, polonais…)
_MOTS_AUTRES = set("""le la les un une des du de en et par pour dans avec sur au aux ce cette ces est sont qui que
mets remplace enlève change rends der die das und mit ein eine einen ist zu den dem el los las y con por para del
il lo gli di da che una het een van op na w z i jest oraz się""".split())


def semble_anglais(texte: str) -> bool:
    """La consigne a-t-elle l'air d'être en anglais ? (textes entre guillemets mis à part : ils restent tels quels).
    Simple indice : pas de lettres accentuées, et assez de petits mots anglais courants."""
    hors = _GUILLEMETS.sub(" ", texte)
    mots = re.findall(r"[^\W\d_]+", hors.lower())
    if not mots:
        return True
    if any(ord(c) > 127 for m in mots for c in m):
        return False
    anglais = sum(m in _MOTS_ANGLAIS for m in mots)
    autres = sum(m in _MOTS_AUTRES for m in mots)
    return anglais > autres and anglais >= max(1, len(mots) // 5)


def installe() -> bool:
    d = dossier()
    return all((d / f).is_file() and (d / f).stat().st_size == t for f, (t, _) in CONTENU.items())


def elements() -> list:
    """Fichiers à télécharger (éléments de installation_moteur : chemin complet, vérifiés)."""
    from .installation_moteur import Element
    from .langue import tr
    return [Element(f"traducteur_{f}", tr("Traducteur des consignes : {fichier}", fichier=f),
                    f"https://huggingface.co/{MODELE}/resolve/{VERSION}/{f}", t, sha, LICENCE, "modele",
                    str(dossier() / f)) for f, (t, sha) in CONTENU.items()]


def guillemets_droits(texte: str) -> str:
    return _GUILLEMETS.sub(lambda m: '"' + next(g for g in m.groups() if g is not None) + '"', texte)


def proteger(texte: str) -> tuple[str, list[str]]:
    """Remplace les textes entre guillemets par des repères (Q0, Q1…) ; renvoie le texte et les morceaux."""
    morceaux: list[str] = []

    def rep(m):
        morceaux.append(next(g for g in m.groups() if g is not None))
        return f"Q{len(morceaux) - 1}Q"
    return _GUILLEMETS.sub(rep, texte), morceaux


def remettre(texte: str, morceaux: list[str]) -> str:
    for i, m in enumerate(morceaux):
        texte, n = re.subn(rf"(?:[\"“”«»']\s*)?Q\s*{i}\s*Q(?:\s*[\"“”«»'])?", '"' + m.replace("\\", "\\\\") + '"', texte, 1)
        if not n:                                    # repère perdu par le traducteur : on l'ajoute à la fin
            texte += f' "{m}"'
    return texte


def python_traducteur() -> Path | None:
    """Python de ComfyUI (il a transformers, sentencepiece, torch)."""
    from .moteur import trouver_comfyui
    i = trouver_comfyui()
    p = i.get("python") if i else None
    return Path(p) if p and Path(p).is_file() else None


_DRAPEAUX = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

# Traducteur gardé ouvert : lancer Python et charger le modèle prend environ 10 s, la traduction elle-même un quart
# de seconde. Le traducteur est donc lancé une fois (en avance, à l'ouverture de la fenêtre de consigne), puis
# réutilisé jusqu'à la fermeture de Pixane.
_verrou = threading.Lock()
_serveur: dict | None = None


def _lire(proc, file):
    try:
        for ligne in proc.stdout:
            file.put(ligne.rstrip("\r\n"))
    except (OSError, ValueError):
        pass
    file.put(None)                                  # fin : le traducteur s'est arrêté


def _fermer(s: dict):
    p = s["proc"]
    try:
        p.stdin.close()                             # le traducteur s'arrête de lui-même
        p.wait(timeout=3)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        try:
            p.kill()
        except OSError:
            pass


def _lancer_serveur() -> dict | None:
    """Lance le traducteur gardé ouvert (sans attendre qu'il soit prêt). À appeler avec _verrou."""
    global _serveur
    d = str(dossier())
    if _serveur is not None:
        if _serveur["proc"].poll() is None and _serveur["dossier"] == d:
            return _serveur
        _fermer(_serveur)
        _serveur = None
    python = python_traducteur()
    if python is None or not installe():
        return None
    try:
        proc = subprocess.Popen([str(python), "-I", str(SCRIPT), "--serveur", d], stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8",
                                creationflags=_DRAPEAUX)
    except OSError:
        return None
    file: queue.Queue = queue.Queue()
    threading.Thread(target=_lire, args=(proc, file), daemon=True).start()
    _serveur = {"proc": proc, "file": file, "dossier": d, "pret": False}
    return _serveur


def prechauffer():
    """Lance le traducteur en arrière-plan s'il est installé (rend la main tout de suite)."""
    with _verrou:
        _lancer_serveur()


def arreter():
    """Arrête le traducteur gardé ouvert (fermeture de Pixane)."""
    global _serveur
    with _verrou:
        if _serveur is not None:
            _fermer(_serveur)
            _serveur = None


def _ligne(s: dict, fin: float) -> str:
    try:
        ligne = s["file"].get(timeout=max(0.1, fin - time.monotonic()))
    except queue.Empty:
        raise TimeoutError("traducteur trop lent")
    if ligne is None:
        raise RuntimeError("traducteur arrêté")
    return ligne


def _par_serveur(lignes: list[str], delai: float) -> list[str] | None:
    """Traduction par le traducteur gardé ouvert ; None s'il ne marche pas (on essaie alors l'ancienne façon)."""
    global _serveur
    with _verrou:
        s = _lancer_serveur()
        if s is None:
            return None
        fin = time.monotonic() + delai
        try:
            while not s["pret"]:
                if _ligne(s, fin) == "PRET":
                    s["pret"] = True
            s["proc"].stdin.write(json.dumps({"textes": lignes}, ensure_ascii=False) + "\n")
            s["proc"].stdin.flush()
            ligne = _ligne(s, fin)
            while not ligne.startswith(("[", "{")):
                ligne = _ligne(s, fin)
            rep = json.loads(ligne)
        except (OSError, ValueError, RuntimeError, TimeoutError):
            _fermer(s)
            _serveur = None
            return None
    if isinstance(rep, dict):
        raise RuntimeError(rep.get("erreur") or "erreur")
    return rep


def _une_fois(lignes: list[str], delai: float) -> list[str]:
    """Ancienne façon : un Python lancé pour une seule traduction."""
    python = python_traducteur()
    if python is None:
        raise RuntimeError("Python de ComfyUI introuvable")
    entree = json.dumps({"dossier": str(dossier()), "textes": lignes})
    r = subprocess.run([str(python), "-I", str(SCRIPT)], input=entree, capture_output=True, text=True,
                       encoding="utf-8", timeout=delai, creationflags=_DRAPEAUX)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or "").strip().splitlines()[-1] if r.stderr.strip() else "erreur")
    return json.loads(r.stdout.strip().splitlines()[-1])


def traduire(texte: str, delai: float = 120) -> str:
    """Traduit en anglais (les textes entre guillemets restent tels quels). Lève RuntimeError si impossible."""
    protege, morceaux = proteger(texte)
    if not re.search(r"[A-Za-zÀ-ÿ]{2,}", re.sub(r"Q\d+Q", "", protege)):
        return remettre(protege, morceaux)          # rien à traduire (seulement des guillemets)
    lignes = [l for l in protege.splitlines()]
    sortie = _par_serveur(lignes, delai)
    if sortie is None:
        sortie = _une_fois(lignes, delai)
    return remettre("\n".join(sortie), morceaux)
