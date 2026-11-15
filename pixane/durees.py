"""Durées des propositions de l'IA mesurées sur ce PC (elles changent beaucoup d'une carte graphique à l'autre).

Chaque calcul note sa durée par proposition (moyenne glissante, gardée dans les réglages) ; les fenêtres affichent
alors « environ X chacune (mesuré sur ce PC) ». Tant que rien n'est mesuré, elles donnent la durée observée sur une
RTX 3060 Ti (8 Go), en prévenant que ça dépend du PC.

Clés (indépendantes de la langue) : « creer » (Flux Schnell), « kontext » (Modifier avec une consigne, Restaurer).
"""
from __future__ import annotations

import os

from .langue import tr

# durée par proposition sur une RTX 3060 Ti 8 Go (secondes)
REFERENCE = {"creer": 30, "kontext": 150}
_POIDS = 0.4                     # part de la nouvelle mesure dans la moyenne


def _reglages():
    from PySide6.QtCore import QSettings
    return QSettings("Pixane", os.environ.get("PIXANE_REGLAGES", "Pixane"))


def noter(cle: str, secondes: float):
    """Retient la durée d'une proposition (moyenne glissante). Mesures absurdes ignorées."""
    if not 0.5 <= secondes <= 3600:
        return
    r = _reglages()
    ancienne = mesure(cle)
    nouvelle = secondes if ancienne is None else ancienne * (1 - _POIDS) + secondes * _POIDS
    r.setValue(f"duree_{cle}", round(nouvelle, 1))


def mesure(cle: str) -> float | None:
    try:
        v = float(_reglages().value(f"duree_{cle}", 0) or 0)
    except (TypeError, ValueError):
        return None
    return v if v > 0 else None


def lisible(secondes: float) -> str:
    """« 25 secondes », « 1 minute », « 2 minutes 30 »… (arrondi : c'est une estimation)."""
    s = int(round(secondes))
    if s < 55:
        return tr("{n} secondes", n=max(5, int(round(s / 5)) * 5))
    m, s = divmod(int(round(s / 30)) * 30, 60)
    if s == 0:
        return tr("1 minute") if m == 1 else tr("{n} minutes", n=m)
    return tr("{m} minute {s}", m=m, s=f"{s:02d}") if m == 1 else tr("{m} minutes {s}", m=m, s=f"{s:02d}")


def texte(cle: str) -> str:
    """Texte à afficher à côté du nombre de propositions."""
    m = mesure(cle)
    if m is not None:
        return tr("(environ {duree} chacune, mesuré sur ce PC)", duree=lisible(m))
    return tr("(environ {duree} chacune sur une carte comme la RTX 3060 Ti ; plus ou moins selon le PC)",
              duree=lisible(REFERENCE.get(cle, 60)))


def phrase(cle: str) -> str:
    """Phrase entière : « Compte environ X par proposition (mesuré sur ce PC). »"""
    m = mesure(cle)
    if m is not None:
        return tr("Compte environ {duree} par proposition (mesuré sur ce PC).", duree=lisible(m))
    return tr("Compte environ {duree} par proposition sur une carte comme la RTX 3060 Ti ; plus ou moins selon le "
              "PC.", duree=lisible(REFERENCE.get(cle, 60)))
