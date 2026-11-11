"""Vérifie les traductions : chaque texte passé à tr("…") dans le code doit exister dans chaque fichier de langue
(pixane/langues/*.json), avec les mêmes {valeurs}. Signale aussi les traductions qui ne servent plus.
Usage : essai_langues.py [--manquants]   (--manquants : affiche les textes à traduire au format json)"""
import ast
import json
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
CODE = RACINE / "pixane"

# textes traduits « indirectement » (passés à tr() par une variable) : listes dans le code
INDIRECTS = {
    "canevas.py": ["noms"],          # dictionnaire des noms d'outils
    "moteur.py": ["ETAPES"],         # étapes du calcul
    "dialogues.py": ["COTES"],       # noms des côtés
    "calques.py": [],                # bulles d'aide des boutons (relevées dans la boucle)
    "aide.py": ["LIVRES", "TELECHARGES"],   # rôles des éléments tiers : Composant(nom, url, rôle, licence)
}


def textes_du_code() -> set[str]:
    cles = set()
    for f in CODE.glob("*.py"):
        arbre = ast.parse(f.read_text(encoding="utf-8"))
        for n in ast.walk(arbre):
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "tr" and n.args
                    and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str)):
                cles.add(n.args[0].value)
            # dictionnaires / tuples nommés dans INDIRECTS
            if isinstance(n, ast.Assign) and f.name in INDIRECTS:
                noms = [t.id if isinstance(t, ast.Name) else getattr(t, "attr", "") for t in n.targets]
                if any(x in INDIRECTS[f.name] for x in noms):
                    for c in ast.walk(n.value):
                        if (isinstance(c, ast.Call) and getattr(c.func, "id", "") == "Composant"
                                and len(c.args) > 2 and isinstance(c.args[2], ast.Constant)):
                            cles.add(c.args[2].value)
                        if isinstance(c, ast.Dict):
                            for v in c.values:
                                if isinstance(v, ast.Constant) and isinstance(v.value, str):
                                    cles.add(v.value)
                        if isinstance(c, ast.Tuple) and len(c.elts) == 2 and all(
                                isinstance(e, ast.Constant) for e in c.elts):
                            cles.add(c.elts[1].value)
            # consignes de l'IA : exemples (nom, modèle)
            if f.name == "consigne.py" and isinstance(n, ast.Assign) and any(
                    getattr(t, "id", "") == "EXEMPLES" for t in n.targets):
                for c in n.value.elts:
                    cles.update(e.value for e in c.elts)
            # réglages du pinceau : libellés et aides (CHAMPS), onglets, explications (dictionnaire « explication »)
            if f.name == "reglages_pinceau.py" and isinstance(n, ast.Assign):
                noms = [getattr(t, "id", "") for t in n.targets]
                if "CHAMPS" in noms:
                    for c in n.value.elts:
                        cles.update(c.elts[i].value for i in (1, 6) if c.elts[i].value)
                if "ONGLETS" in noms:
                    cles.update(e.value for e in n.value.elts)
                if "explication" in noms:
                    cles.update(v.value for v in n.value.values)
            # styles de calque : noms des effets et des modes, libellés et choix des réglages, styles tout prêts
            if f.name == "styles.py":
                if isinstance(n, ast.Assign) and any(getattr(t, "id", "") in ("TYPES", "MODES", "REGLAGES")
                                                     for t in n.targets):
                    for c in ast.walk(n.value):
                        if isinstance(c, ast.Dict):
                            cles.update(v.value for v in c.values if isinstance(v, ast.Constant))
                        if (isinstance(c, ast.Tuple) and len(c.elts) >= 4 and isinstance(c.elts[1], ast.Constant)
                                and isinstance(c.elts[1].value, str)):
                            cles.add(c.elts[1].value)
                if isinstance(n, ast.FunctionDef) and n.name == "styles_prets":
                    for c in ast.walk(n):
                        if (isinstance(c, ast.Tuple) and len(c.elts) == 2 and isinstance(c.elts[0], ast.Constant)
                                and isinstance(c.elts[1], ast.Call) and getattr(c.elts[1].func, "id", "") == "_s"):
                            cles.add(c.elts[0].value)
            # bulles d'aide des boutons du panneau Calques : for nom, aide, action in ((…, "texte", …), …)
            if isinstance(n, ast.For) and f.name == "calques.py" and isinstance(n.iter, ast.Tuple):
                for e in n.iter.elts:
                    if isinstance(e, ast.Tuple) and len(e.elts) == 3 and isinstance(e.elts[1], ast.Constant):
                        cles.add(e.elts[1].value)
    cles.add("Calcul")                       # étape par défaut (moteur.py)
    return cles


def valeurs(texte: str) -> set[str]:
    return set(re.findall(r"\{(\w+)\}", texte))


def main():
    cles = textes_du_code()
    erreurs = []
    for fichier in sorted((CODE / "langues").glob("*.json")):
        trad = json.loads(fichier.read_text(encoding="utf-8"))
        manquants = sorted(cles - trad.keys())
        inutiles = sorted(trad.keys() - cles)
        mauvais = [k for k in cles & trad.keys() if valeurs(k) != valeurs(trad[k])]
        vides = [k for k in cles & trad.keys() if not trad[k].strip()]
        print(f"{fichier.name} : {len(cles)} textes, {len(manquants)} manquants, {len(inutiles)} inutiles, "
              f"{len(mauvais)} avec des {{valeurs}} différentes, {len(vides)} vides")
        if "--manquants" in sys.argv:
            print(json.dumps({k: "" for k in manquants}, ensure_ascii=False, indent=1))
        for k in manquants[:20]:
            print("  manquant :", repr(k))
        for k in inutiles:
            print("  inutile :", repr(k))
        for k in mauvais:
            print("  {valeurs} :", repr(k))
        erreurs += manquants + mauvais + vides
    print("ERREURS :", len(erreurs) if erreurs else "aucune")
    return 1 if erreurs else 0


if __name__ == "__main__":
    sys.exit(main())
