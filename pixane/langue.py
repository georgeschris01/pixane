"""Langues de Pixane.

Le texte français écrit dans le code sert de clé : tr("Ouvrir…") renvoie « Open… » en anglais.
Les traductions sont dans pixane/langues/<code>.json ({"texte français": "traduction"}).
Un texte absent du fichier reste en français (l'essai tests/essai_langues.py signale les oublis).
Ajouter une langue = ajouter un fichier json et une ligne dans LANGUES.
Un même mot français avec deux sens se distingue par « |précision » : tr("Annuler|édition") affiche « Annuler »
en français et « Undo » en anglais, alors que tr("Annuler") donne « Cancel ».
"""
from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QLocale

AUTO = "auto"
LANGUES = {"fr": "Français", "en": "English"}     # nom de chaque langue écrit dans cette langue
DOSSIER = Path(__file__).parent / "langues"

_langue = "fr"
_textes: dict[str, str] = {}


def langue_systeme() -> str:
    """Langue de Windows si Pixane la connaît, sinon l'anglais."""
    code = QLocale.system().name().split("_")[0].lower()
    return code if code in LANGUES else "en"


def choisir(reglage: str | None) -> str:
    """reglage : « auto » (langue de Windows), « fr » ou « en ». Renvoie la langue retenue."""
    global _langue, _textes
    code = langue_systeme() if reglage in (None, "", AUTO) or reglage not in LANGUES else reglage
    _langue = code
    _textes = {}
    fichier = DOSSIER / f"{code}.json"
    if code != "fr" and fichier.exists():
        _textes = json.loads(fichier.read_text(encoding="utf-8"))
    return code


def langue() -> str:
    return _langue


def tr(texte: str, **valeurs) -> str:
    """Traduit un texte écrit en français ; {nom} est remplacé par les valeurs données."""
    t = _textes.get(texte)
    if t is None:
        t = texte.split("|")[0]          # français (sans la précision éventuelle)
    return t.format(**valeurs) if valeurs else t
