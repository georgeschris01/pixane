"""Temps écoulé / restant affiché pendant un calcul : un nombre à virgule (Agrandir en pleine définition) ne doit
pas provoquer d'erreur (« Unknown format code 'd' for object of type 'float' », signalé par Christophe).
Usage : essai_duree.py"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pixane.dialogues import duree, texte_progression

erreurs = []
for valeur, attendu in [(75.6, "1 min 16 s"), (12.4, "12 s"), (0, "0 s"), (None, "0 s"), (600, "10 min 00 s")]:
    ok = duree(valeur) == attendu
    print(("ok  " if ok else "ÉCHEC ") + f"duree({valeur}) = {duree(valeur)}")
    if not ok:
        erreurs.append(valeur)
t = texte_progression({"secondes": 61.2, "restant": 143.7})
print("ok  " + t)
print("ERREURS :", erreurs if erreurs else "aucune")
sys.exit(1 if erreurs else 0)
