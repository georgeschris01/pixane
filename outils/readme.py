"""Recopie le guide (docs/GUIDE.md, docs/GUIDE_en.md) dans README.md et README.en.md, entre les repères
<!-- guide --> et <!-- /guide --> (comme le README de TwinPanel). À relancer après chaque mise à jour du guide.
Usage : .venv\\Scripts\\python outils\\readme.py"""
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
DEBUT, FIN = "<!-- guide -->", "<!-- /guide -->"


def corps_du_guide(texte: str) -> str:
    """Le guide sans son titre ni son introduction : à partir du premier chapitre (« ## 1. »)."""
    i = texte.index("\n## 1.")
    return texte[i + 1:].strip() + "\n"


def recopier(readme: Path, guide: Path) -> bool:
    s = readme.read_text(encoding="utf-8")
    a, b = s.index(DEBUT) + len(DEBUT), s.index(FIN)
    nouveau = s[:a] + "\n" + corps_du_guide(guide.read_text(encoding="utf-8")) + s[b:]
    if nouveau == s:
        return False
    readme.write_text(nouveau, encoding="utf-8")
    return True


if __name__ == "__main__":
    for readme, guide in (("README.md", "docs/GUIDE.md"), ("README.en.md", "docs/GUIDE_en.md")):
        change = recopier(RACINE / readme, RACINE / guide)
        print(f"{readme} : {'mis à jour' if change else 'déjà à jour'}")
