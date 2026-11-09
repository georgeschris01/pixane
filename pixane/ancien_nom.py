"""Passage de l'ancien nom du programme (Chrypix, jusqu'à la version 0.3.4) à Pixane, fait une seule fois, sans rien perdre :
- le dossier %LOCALAPPDATA%\\Chrypix (journaux, copies de récupération, moteur installé) devient %LOCALAPPDATA%\\Pixane ;
- les réglages (registre HKCU\\Software\\Chrypix\\Chrypix) sont recopiés dans HKCU\\Software\\Pixane\\Pixane ;
- dans un moteur installé par Chrypix, les fichiers repères chrypix.json et chrypix-moteur.json prennent le nouveau nom."""
import os
from pathlib import Path

ANCIEN = "Chrypix"
NOUVEAU = "Pixane"


def _local() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home())))


def _remplacer_chemin(valeur, ancien: str, nouveau: str):
    """Chemins des réglages qui pointaient dans l'ancien dossier (ex. moteur_dossier)."""
    if isinstance(valeur, str) and valeur.lower().startswith(ancien.lower()):
        return nouveau + valeur[len(ancien):]
    if isinstance(valeur, list):
        return [_remplacer_chemin(v, ancien, nouveau) for v in valeur]
    return valeur


def migrer() -> None:
    """À appeler au démarrage, avant de lire les réglages. Rien à faire pour les essais automatiques."""
    if os.environ.get("PIXANE_REGLAGES"):
        return
    ancien, nouveau = _local() / ANCIEN, _local() / NOUVEAU
    deplace = False
    if ancien.is_dir() and not nouveau.exists():
        try:
            ancien.rename(nouveau)
            deplace = True
        except OSError:
            pass                            # fichier ouvert (moteur en marche) : l'ancien dossier reste utilisé
    try:
        from PySide6.QtCore import QSettings
        neuf = QSettings(NOUVEAU, NOUVEAU)
        if neuf.allKeys():
            return
        vieux = QSettings(ANCIEN, ANCIEN)
        for cle in vieux.allKeys():
            v = vieux.value(cle)
            neuf.setValue(cle, _remplacer_chemin(v, str(ancien), str(nouveau)) if deplace else v)
        neuf.sync()
    except Exception:
        pass


def adopter_moteur(dossier) -> None:
    """Moteur installé par Chrypix : ses fichiers repères prennent le nouveau nom (pixane.json, pixane-moteur.json)."""
    d = Path(dossier)
    for parent, vieux, neuf in ((d / "ComfyUI_windows_portable", "chrypix.json", "pixane.json"),
                                (d, "chrypix-moteur.json", "pixane-moteur.json")):
        try:
            if (parent / vieux).is_file() and not (parent / neuf).exists():
                (parent / vieux).rename(parent / neuf)
        except OSError:
            pass
