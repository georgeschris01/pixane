"""Prépare les fichiers à installer dans publication\\Pixane (appelé par construire-installateur.bat).

Contenu : une copie de Python (celui du .venv, sans les parties inutiles), les bibliothèques de Pixane
(PySide6, numpy, Pillow, websocket-client), le programme, le guide, le logo.
Rien de personnel : ni réglages, ni photos, ni modèles, ni journaux.
Écrit aussi publication\\version.txt (version lue dans pixane\\__init__.py).
"""
import compileall
import re
import shutil
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
SORTIE = RACINE / "publication" / "Pixane"

# parties de Python inutiles à Pixane
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
    # Pixane est trouvé par Python où qu'on le lance (pour « -m pixane » et l'ouverture des .pixane)
    (paquets / "pixane.pth").write_text("../../..\n", encoding="utf-8")
    shutil.copytree(RACINE / "pixane", SORTIE / "pixane", ignore=ignorer(set()))
    (SORTIE / "docs").mkdir()
    for f in ("GUIDE.md", "GUIDE_en.md", "LICENCES_TIERS.md"):
        shutil.copy2(RACINE / "docs" / f, SORTIE / "docs" / f)
    for f in ("LICENSE", "LICENSE.en.txt"):              # licence MIT : le nom de l'auteur reste avec le programme
        shutil.copy2(RACINE / f, SORTIE / f)
    shutil.copy2(RACINE / "pixane" / "ressources" / "pixane.ico", SORTIE / "pixane.ico")
    version = re.search(r'__version__ = "([^"]+)"', (RACINE / "pixane" / "__init__.py").read_text()).group(1)
    # python\Pixane.exe : pythonw.exe nommé « Pixane » (Gestionnaire des tâches, pare-feu) avec l'icône
    from lanceur import fabriquer
    fabriquer(python / "pythonw.exe", SORTIE / "pixane.ico", python / "Pixane.exe", version)
    # compilé d'avance : Program Files est en lecture seule, Python ne pourrait pas le faire au démarrage
    compileall.compile_dir(SORTIE, quiet=1, workers=0)
    (RACINE / "publication" / "version.txt").write_text(version, encoding="ascii")
    # vérification : rien de personnel
    suspects = [p for p in SORTIE.rglob("*") if p.suffix.lower() in (".log", ".jpg", ".jpeg", ".safetensors",
                                                                      ".ckpt", ".pt", ".pth", ".pixane", ".ora")
                and p.name not in ("pixane.pth", "pyside_icon.jpg")]
    taille = sum(p.stat().st_size for p in SORTIE.rglob("*") if p.is_file())
    print(f"Version {version} ; {taille / 1e6:.0f} Mo dans {SORTIE}")
    print("ATTENTION, fichiers suspects :", suspects) if suspects else print("OK, rien de personnel.")


if __name__ == "__main__":
    main()
