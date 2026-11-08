"""Rechercher une nouvelle version de Chrypix sur GitHub (seulement quand l'utilisateur le demande, ou au démarrage
s'il a coché « Vérifier au démarrage »). Rien n'est envoyé à part la demande elle-même."""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request

from . import __version__
from .langue import tr

API = "https://api.github.com/repos/georgeschris01/chrypix/releases/latest"
PAGE = "https://github.com/georgeschris01/chrypix/releases/latest"


def _numeros(v: str) -> tuple[int, ...]:
    return tuple(int(n) for n in re.findall(r"\d+", v)[:3]) or (0,)


def plus_recente(distante: str, locale: str = __version__) -> bool:
    return _numeros(distante) > _numeros(locale)


def derniere_version(delai: float = 10) -> dict:
    """-> {version, page, notes}. Lève OSError avec un message clair si la recherche échoue."""
    req = urllib.request.Request(API, headers={"User-Agent": f"Chrypix/{__version__}",
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
