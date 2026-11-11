"""Lancé avec le Python de ComfyUI (pas importé par Pixane) : traduit des lignes du français vers l'anglais avec le
modèle Opus-MT fr-en. Entrée (stdin, JSON) : {"dossier": ..., "textes": [...]} ; sortie (dernière ligne de stdout,
JSON) : la liste des traductions (une ligne vide reste vide)."""
import json
import sys


def main():
    d = json.loads(sys.stdin.read())
    import torch
    from transformers import MarianMTModel, MarianTokenizer
    torch.set_num_threads(max(1, min(4, torch.get_num_threads())))
    tok = MarianTokenizer.from_pretrained(d["dossier"])
    modele = MarianMTModel.from_pretrained(d["dossier"])
    modele.eval()
    textes = d["textes"]
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
    print(json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    main()
