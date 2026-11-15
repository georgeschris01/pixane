"""Lancé avec le Python de ComfyUI (pas importé par Pixane) : traduit des lignes du français vers l'anglais avec le
modèle Opus-MT fr-en.

- Mode simple : entrée (stdin, JSON) {"dossier": ..., "textes": [...]} ; sortie (dernière ligne de stdout, JSON) : la
  liste des traductions (une ligne vide reste vide).
- Mode « --serveur DOSSIER » : le modèle est chargé une seule fois (le plus long : environ 10 s), puis le programme
  écrit « PRET » et attend des demandes, une par ligne ({"textes": [...]}) ; il répond une ligne JSON par demande
  (la liste des traductions, ou {"erreur": ...}). Il s'arrête quand son entrée se ferme (Pixane fermé).
"""
import json
import sys


def charger(dossier):
    import torch
    from transformers import MarianMTModel, MarianTokenizer
    torch.set_num_threads(max(1, min(4, torch.get_num_threads())))
    tok = MarianTokenizer.from_pretrained(dossier)
    modele = MarianMTModel.from_pretrained(dossier)
    modele.eval()
    return torch, tok, modele


def traduire(torch, tok, modele, textes):
    a_traduire = [t for t in textes if t.strip()]
    sorties = []
    if a_traduire:
        with torch.no_grad():
            lot = tok(a_traduire, return_tensors="pt", padding=True, truncation=True, max_length=400)
            gen = modele.generate(**lot, max_new_tokens=400, num_beams=4)
        sorties = tok.batch_decode(gen, skip_special_tokens=True)
    res, k = [], 0
    for t in textes:
        if t.strip():
            res.append(sorties[k])
            k += 1
        else:
            res.append("")
    return res


def serveur(dossier):
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    torch, tok, modele = charger(dossier)
    print("PRET", flush=True)
    for ligne in sys.stdin:
        if not ligne.strip():
            continue
        try:
            rep = traduire(torch, tok, modele, json.loads(ligne)["textes"])
        except Exception as e:                       # la demande suivante doit encore marcher
            rep = {"erreur": str(e) or type(e).__name__}
        print(json.dumps(rep, ensure_ascii=False), flush=True)


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--serveur":
        serveur(sys.argv[2])
        return
    d = json.loads(sys.stdin.read())
    torch, tok, modele = charger(d["dossier"])
    print(json.dumps(traduire(torch, tok, modele, d["textes"]), ensure_ascii=False))


if __name__ == "__main__":
    main()
