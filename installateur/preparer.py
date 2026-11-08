"""Prépare les fichiers à installer dans publication\\Chrypix (appelé par construire-installateur.bat).

Contenu : une copie de Python (celui du .venv, sans les parties inutiles), les bibliothèques de Chrypix
(PySide6, numpy, Pillow, websocket-client), le programme, le guide, le logo.
Rien de personnel : ni réglages, ni photos, ni modèles, ni journaux.
Écrit aussi publication\\version.txt (version lue dans chrypix\\__init__.py).
"""
import compileall
import re
import shutil
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
SORTIE = RACINE / "publication" / "Chrypix"

# parties de Python inutiles à Chrypix
PYTHON_EXCLUS = {"test", "tests", "idlelib", "tkinter", "turtledemo", "ensurepip", "lib2to3", "__pycache__",
                 "tcl", "include", "libs", "Scripts", "site-packages"}
PAQUETS_EXCLUS = {"tests", "pip", "setuptools", "_distutils_hack", "__pycache__", "_virtualenv.py", "_virtualenv.pth",
                  "distutils-precedence.pth"}


def ignorer(exclus):
    def f(dossier, noms):
        return [n for n in noms if n in exclus or n.endswith((".pyc", ".pdb")) or
                n.startswith(("pip-", "setuptools-"))]
    return f


def main():
    base = None
    for ligne in (RACINE / ".venv" / "pyvenv.cfg").read_text(encoding="utf-8").splitlines():
        if ligne.startswith("home"):
            base = Path(ligne.split("=", 1)[1].strip())
    if base is None or not (base / "python.exe").is_file():
        sys.exit("Python du .venv introuvable (pyvenv.cfg)")
    if SORTIE.exists():
        shutil.rmtree(SORTIE)
    python = SORTIE / "python"
    print("Python :", base)
    shutil.copytree(base, python, ignore=ignorer(PYTHON_EXCLUS))
    paquets = python / "Lib" / "site-packages"
    print("Bibliothèques : .venv\\Lib\\site-packages")
    shutil.copytree(RACINE / ".venv" / "Lib" / "site-packages", paquets, ignore=ignorer(PAQUETS_EXCLUS))
    # Chrypix est trouvé par Python où qu'on le lance (pour « -m chrypix » et l'ouverture des .chr)
    (paquets / "chrypix.pth").write_text("../../..\n", encoding="utf-8")
    shutil.copytree(RACINE / "chrypix", SORTIE / "chrypix", ignore=ignorer(set()))
    (SORTIE / "docs").mkdir()
    for f in ("GUIDE.md", "GUIDE_en.md", "LICENCES_TIERS.md"):
        shutil.copy2(RACINE / "docs" / f, SORTIE / "docs" / f)
    for f in ("LICENSE", "LICENSE.fr.txt"):              # licence MIT : le nom de l'auteur reste avec le programme
        shutil.copy2(RACINE / f, SORTIE / f)
    shutil.copy2(RACINE / "chrypix" / "ressources" / "chrypix.ico", SORTIE / "chrypix.ico")
    # compilé d'avance : Program Files est en lecture seule, Python ne pourrait pas le faire au démarrage
    compileall.compile_dir(SORTIE, quiet=1, workers=0)
    version = re.search(r'__version__ = "([^"]+)"', (RACINE / "chrypix" / "__init__.py").read_text()).group(1)
    (RACINE / "publication" / "version.txt").write_text(version, encoding="ascii")
    # vérification : rien de personnel
    suspects = [p for p in SORTIE.rglob("*") if p.suffix.lower() in (".log", ".jpg", ".jpeg", ".safetensors",
                                                                      ".ckpt", ".pt", ".pth", ".chr", ".ora")
                and p.name not in ("chrypix.pth", "pyside_icon.jpg")]
    taille = sum(p.stat().st_size for p in SORTIE.rglob("*") if p.is_file())
    print(f"Version {version} ; {taille / 1e6:.0f} Mo dans {SORTIE}")
    print("ATTENTION, fichiers suspects :", suspects) if suspects else print("OK, rien de personnel.")


if __name__ == "__main__":
    main()
