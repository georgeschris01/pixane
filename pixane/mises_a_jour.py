"""Rechercher une nouvelle version de Pixane sur GitHub (seulement quand l'utilisateur le demande, ou au démarrage
s'il a coché « Vérifier au démarrage »). Rien n'est envoyé à part la demande elle-même."""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request

from . import __version__
from .langue import tr

API = "https://api.github.com/repos/pixane-suite/photo/releases/latest"
PAGE = "https://github.com/pixane-suite/photo/releases/latest"


def _numeros(v: str) -> tuple[int, ...]:
    return tuple(int(n) for n in re.findall(r"\d+", v)[:3]) or (0,)


def plus_recente(distante: str, locale: str = __version__) -> bool:
    return _numeros(distante) > _numeros(locale)


def derniere_version(delai: float = 10) -> dict:
    """-> {version, page, notes}. Lève OSError avec un message clair si la recherche échoue."""
    req = urllib.request.Request(API, headers={"User-Agent": f"Pixane/{__version__}",
                                               "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=delai) as r:
            d = json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise OSError(tr("Aucune version publiée trouvée sur GitHub (la page n'est peut-être pas encore "
                             "publique).")) from e
        raise OSError(tr("GitHub ne répond pas correctement (erreur {code}).", code=e.code)) from e
    except (urllib.error.URLError, TimeoutError) as e:
        raise OSError(tr("Pas de connexion à Internet, ou GitHub est injoignable.")) from e
    return {"version": str(d.get("tag_name", "")).lstrip("vV"), "page": d.get("html_url") or PAGE,
            "notes": (d.get("body") or "").strip()}


API_LISTE = "https://api.github.com/repos/pixane-suite/photo/releases?per_page=50"


def nouveautes(delai: float = 10, locale: str = __version__) -> dict:
    """Toutes les versions publiées plus récentes que celle-ci, de la plus récente à la plus ancienne :
    -> {version, page, versions: [(version, notes), ...]} (version = la plus récente, ou "" s'il n'y en a pas)."""
    req = urllib.request.Request(API_LISTE, headers={"User-Agent": f"Pixane/{__version__}",
                                                     "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=delai) as r:
            liste = json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise OSError(tr("Aucune version publiée trouvée sur GitHub (la page n'est peut-être pas encore "
                             "publique).")) from e
        raise OSError(tr("GitHub ne répond pas correctement (erreur {code}).", code=e.code)) from e
    except (urllib.error.URLError, TimeoutError) as e:
        raise OSError(tr("Pas de connexion à Internet, ou GitHub est injoignable.")) from e
    return trier_nouveautes(liste, locale)


def trier_nouveautes(liste: list, locale: str = __version__) -> dict:
    versions = []
    for d in liste:
        if d.get("draft"):
            continue
        v = str(d.get("tag_name", "")).lstrip("vV")
        if v and plus_recente(v, locale):
            versions.append((v, (d.get("body") or "").strip(), d.get("html_url") or PAGE))
    versions.sort(key=lambda x: _numeros(x[0]), reverse=True)
    if not versions:
        return {"version": "", "page": PAGE, "versions": []}
    return {"version": versions[0][0], "page": versions[0][2], "versions": [(v, n) for v, n, _p in versions]}


def texte_nouveautes(versions: list) -> str:
    """Notes de plusieurs versions en un seul texte Markdown (titres des notes descendus d'un cran)."""
    morceaux = []
    for v, notes in versions:
        notes = re.sub(r"^(#+)", r"#\1", notes, flags=re.M) if notes else tr("(pas de notes pour cette version)")
        morceaux.append(f"## Pixane Photo {v}\n\n{notes}")
    return "\n\n".join(morceaux)
