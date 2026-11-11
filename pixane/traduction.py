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
import subprocess
import sys
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


def dossier() -> Path:
    """Dossier du modèle : <dossier choisi>/opus-mt-fr-en."""
    return dossier_choisi() / NOM


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


def traduire(texte: str, delai: float = 120) -> str:
    """Traduit en anglais (les textes entre guillemets restent tels quels). Lève RuntimeError si impossible."""
    protege, morceaux = proteger(texte)
    if not re.search(r"[A-Za-zÀ-ÿ]{2,}", re.sub(r"Q\d+Q", "", protege)):
        return remettre(protege, morceaux)          # rien à traduire (seulement des guillemets)
    python = python_traducteur()
    if python is None:
        raise RuntimeError("Python de ComfyUI introuvable")
    lignes = [l for l in protege.splitlines()]
    entree = json.dumps({"dossier": str(dossier()), "textes": lignes})
    drapeaux = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    r = subprocess.run([str(python), "-I", str(SCRIPT)], input=entree, capture_output=True, text=True,
                       encoding="utf-8", timeout=delai, creationflags=drapeaux)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or "").strip().splitlines()[-1] if r.stderr.strip() else "erreur")
    sortie = json.loads(r.stdout.strip().splitlines()[-1])
    return remettre("\n".join(sortie), morceaux)
