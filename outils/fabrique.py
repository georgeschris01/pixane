# Fabrique les 4 recettes ComfyUI (format "workflow" pour l'interface + format "API" pour les tests).
import json, sys, os

OI = json.load(open(os.path.join(os.path.dirname(__file__), "object_info.json"), encoding="utf-8"))
WIDGET_TYPES = {"INT", "FLOAT", "STRING", "BOOLEAN", "COMBO"}


def is_widget(spec):
    t = spec[0]
    return isinstance(t, list) or t in WIDGET_TYPES


def input_specs(ntype):
    inp = OI[ntype]["input"]
    out = []
    for sect in ("required", "optional"):
        for name, spec in inp.get(sect, {}).items():
            out.append((name, spec))
    return out


class Recette:
    def __init__(self, nom):
        self.nom = nom
        self.nodes = []

    def add(self, nid, ntype, title=None, w=None, links=None, col=0, row=0, size=None, color=None):
        self.nodes.append(dict(id=nid, type=ntype, title=title, w=w or {}, links=links or {},
                               col=col, row=row, size=size, color=color))
        return nid

    def note(self, nid, texte, col, row, size=(420, 300)):
        self.nodes.append(dict(id=nid, type="Note", title="Mode d'emploi", w={"text": texte}, links={},
                               col=col, row=row, size=size, color="#432", note=True))

    # ---------- format API (tests) ----------
    def api(self):
        p = {}
        for n in self.nodes:
            if n.get("note"):
                continue
            inputs = {}
            for name, spec in input_specs(n["type"]):
                if name in n["links"]:
                    src, idx = n["links"][name]
                    inputs[name] = [str(src), idx]
                elif is_widget(spec) and name in n["w"]:
                    inputs[name] = n["w"][name]
            p[str(n["id"])] = {"class_type": n["type"], "inputs": inputs}
        return p

    # ---------- format interface ----------
    def ui(self):
        links = []
        lid = 0
        out_links = {}
        nodes = []
        COLW, ROWH = 380, 260
        for order, n in enumerate(self.nodes):
            x, y = 40 + n["col"] * COLW, 40 + n["row"] * ROWH
            if n.get("note"):
                nodes.append({"id": n["id"], "type": "Note", "pos": [x, y], "size": list(n["size"]),
                              "flags": {}, "order": order, "mode": 0, "inputs": [], "outputs": [],
                              "title": n["title"], "properties": {}, "widgets_values": [n["w"]["text"]],
                              "color": "#432", "bgcolor": "#653"})
                continue
            ins, wv = [], []
            for name, spec in input_specs(n["type"]):
                widget = is_widget(spec)
                if name in n["links"]:
                    src, idx = n["links"][name]
                    lid += 1
                    t = OI[[m for m in self.nodes if m["id"] == src][0]["type"]]["output"][idx]
                    links.append([lid, src, idx, n["id"], len(ins), t])
                    out_links.setdefault((src, idx), []).append(lid)
                    d = {"name": name, "type": t if not widget else (spec[0] if isinstance(spec[0], str) else "COMBO"), "link": lid}
                    if widget:
                        d["widget"] = {"name": name}
                    ins.append(d)
                    if widget:
                        wv.append(n["w"].get(name, 0))
                elif widget:
                    if name not in n["w"]:
                        raise SystemExit(f"{self.nom}: réglage manquant {n['type']}.{name}")
                    wv.append(n["w"][name])
                    if name in ("seed", "noise_seed"):
                        wv.append("randomize")
                else:
                    ins.append({"name": name, "type": spec[0], "link": None})
            if n["type"] == "LoadImage":
                wv = [n["w"]["image"], "image"]
            node = {"id": n["id"], "type": n["type"], "pos": [x, y], "size": list(n["size"] or (340, 120)),
                    "flags": {}, "order": order, "mode": 0, "inputs": ins, "outputs": [],
                    "properties": {"Node name for S&R": n["type"]}, "widgets_values": wv}
            if n["title"]:
                node["title"] = n["title"]
            if n["color"]:
                node["color"], node["bgcolor"] = n["color"]
            nodes.append(node)
        for node in nodes:
            if node["type"] == "Note":
                continue
            o = OI[node["type"]]
            names = o.get("output_name") or o["output"]
            node["outputs"] = [{"name": names[i], "type": o["output"][i],
                                "links": out_links.get((node["id"], i), []), "slot_index": i}
                               for i in range(len(o["output"]))]
        return {"last_node_id": max(n["id"] for n in nodes), "last_link_id": lid, "nodes": nodes,
                "links": links, "groups": [], "config": {}, "extra": {"ds": {"scale": 0.75, "offset": [0, 0]}},
                "version": 0.4}


# ---------------------------------------------------------------- pièces communes
VERT = ("#232", "#353")      # ce que Christophe touche
BLEU = ("#223", "#335")      # résultats

def flux_commun(r, col, nb_images, texte="", denoise=1.0, steps=24):
    """Chargement Flux Fill + conditionnement. Attend les nœuds 10 (image découpée) via r.crop_img / r.crop_mask."""
    r.add(20, "UNETLoader", "Flux Fill", {"unet_name": "flux1-fill-dev.safetensors", "weight_dtype": "fp8_e4m3fn"}, col=col, row=0)
    r.add(21, "DualCLIPLoader", None, {"clip_name1": "clip_l.safetensors", "clip_name2": "t5xxl_fp8_e4m3fn_scaled.safetensors",
                                       "type": "flux", "device": "default"}, col=col, row=1)
    r.add(22, "VAELoader", None, {"vae_name": "ae.safetensors"}, col=col, row=2)
    r.add(23, "DifferentialDiffusion", None, {"strength": 1.0}, {"model": (20, 0)}, col=col + 1, row=0)
    r.add(24, "CLIPTextEncode", "Texte (facultatif, laisser vide)", {"text": texte}, {"clip": (21, 0)}, col=col + 1, row=1,
          size=(340, 140), color=VERT)
    r.add(25, "FluxGuidance", None, {"guidance": 30.0}, {"conditioning": (24, 0)}, col=col + 2, row=1)
    r.add(26, "ConditioningZeroOut", None, {}, {"conditioning": (24, 0)}, col=col + 2, row=2)
    r.add(27, "InpaintModelConditioning", None, {"noise_mask": True},
          {"positive": (25, 0), "negative": (26, 0), "vae": (22, 0), "pixels": r.pixels, "mask": r.crop_mask}, col=col + 3, row=1)
    r.add(28, "RepeatLatentBatch", "Nombre de propositions", {"amount": nb_images}, {"samples": (27, 2)}, col=col + 3, row=2,
          color=VERT)
    r.add(29, "KSampler", None, {"seed": 1, "steps": steps, "cfg": 1.0, "sampler_name": "euler", "scheduler": "simple",
                                  "denoise": denoise},
          {"model": (23, 0), "positive": (27, 0), "negative": (27, 1), "latent_image": (28, 0)}, col=col + 4, row=1, size=(320, 270))
    r.add(30, "VAEDecode", None, {}, {"samples": (29, 0), "vae": (22, 0)}, col=col + 5, row=1)
    r.add(31, "InpaintStitchImproved", None, {}, {"stitcher": r.stitcher, "inpainted_image": (30, 0)}, col=col + 5, row=2)


def crop(r, nid, col, row, **reglages):
    w = {"downscale_algorithm": "bilinear", "upscale_algorithm": "bicubic", "preresize": False,
         "preresize_mode": "ensure minimum resolution", "preresize_min_width": 1024, "preresize_min_height": 1024,
         "preresize_max_width": 16384, "preresize_max_height": 16384, "mask_fill_holes": True, "mask_expand_pixels": 16,
         "mask_invert": False, "mask_blend_pixels": 32, "mask_hipass_filter": 0.1, "extend_for_outpainting": False,
         "extend_up_factor": 1.0, "extend_down_factor": 1.0, "extend_left_factor": 1.0, "extend_right_factor": 1.0,
         "context_from_mask_extend_factor": 1.6, "output_resize_to_target_size": True, "output_target_width": 1024,
         "output_target_height": 1024, "output_padding": "32", "device_mode": "gpu (much faster)"}
    w.update(reglages)
    return w


NOTE_MASQUE = ("1. Clic droit sur « Ta photo » > Open Image (ou glisse ta photo dessus).\n"
               "2. Clic droit > « Open in MaskEditor » : peins la zone, puis Save.\n")


def effacer(nb, img="exemple.png"):
    r = Recette("Effacer test")
    r.note(1, "EFFACER TEST\n\n" + NOTE_MASQUE +
           "3. Bouton « Exécuter » (Run).\n\n"
           "Résultats (dossier output\\Effacer test) :\n"
           "- « lama » : LaMa seul (rapide).\n"
           "- « flux » : LaMa + finition Flux, plusieurs propositions.\n\n"
           "Réglage utile : « Finition Flux » > denoise (0,4 = léger, 0,8 = fort).", col=0, row=0, size=(340, 330))
    r.add(10, "LoadImage", "Ta photo", {"image": img}, col=0, row=1.4, size=(340, 360), color=VERT)
    r.add(11, "InpaintCropImproved", "Découpe autour de la zone", crop(r, 11, 1, 0), {"image": (10, 0), "mask": (10, 1)},
          col=1, row=0, size=(340, 640))
    r.add(12, "INPAINT_LoadInpaintModel", None, {"model_name": "big-lama.pt"}, col=2, row=0)
    r.add(13, "INPAINT_InpaintWithModel", "LaMa efface", {"seed": 1}, {"inpaint_model": (12, 0), "image": (11, 1), "mask": (11, 2)},
          col=2, row=1)
    r.add(14, "InpaintStitchImproved", None, {}, {"stitcher": (11, 0), "inpainted_image": (13, 0)}, col=2, row=2)
    r.add(15, "SaveImage", "Résultat LaMa seul", {"filename_prefix": "Effacer test/lama"}, {"images": (14, 0)}, col=2, row=3,
          size=(340, 340), color=BLEU)
    r.crop_mask, r.stitcher, r.pixels = (11, 2), (11, 0), (13, 0)
    flux_commun(r, 3, nb, denoise=0.6, steps=20)
    for n in r.nodes:
        if n["id"] == 29:
            n["title"], n["color"] = "Finition Flux", VERT
    r.add(32, "SaveImage", "Résultats LaMa + Flux", {"filename_prefix": "Effacer test/flux"}, {"images": (31, 0)}, col=8, row=0,
          size=(520, 560), color=BLEU)
    return r


def remplir(nb, img="exemple.png"):
    r = Recette("Remplir test")
    r.note(1, "REMPLIR TEST\n\n" + NOTE_MASQUE +
           "3. Bouton « Exécuter » (Run).\n\n"
           "Sans texte : Flux remplit d'après le reste de la photo.\n"
           "Le texte est facultatif (ex. « un arbre »).\n\n"
           "Résultats : dossier output\\Remplir test.", col=0, row=0, size=(340, 330))
    r.add(10, "LoadImage", "Ta photo", {"image": img}, col=0, row=1.4, size=(340, 360), color=VERT)
    r.add(11, "InpaintCropImproved", "Découpe autour de la zone", crop(r, 11, 1, 0), {"image": (10, 0), "mask": (10, 1)},
          col=1, row=0, size=(340, 640))
    r.crop_mask, r.stitcher, r.pixels = (11, 2), (11, 0), (11, 1)
    flux_commun(r, 2, nb, denoise=1.0)
    r.add(32, "SaveImage", "Résultats", {"filename_prefix": "Remplir test/flux"}, {"images": (31, 0)}, col=7, row=0,
          size=(520, 560), color=BLEU)
    return r


def agrandir(nb, img="exemple.png"):
    r = Recette("Agrandir test")
    r.note(1, "AGRANDIR TEST\n\n"
           "1. Clic droit sur « Ta photo » > Open Image (ou glisse ta photo dessus).\n"
           "2. Dans « De combien agrandir » : extend_..._factor\n"
           "   1,00 = rien ; 1,25 = +25 % de ce côté.\n"
           "   up = haut, down = bas, left = gauche, right = droite.\n"
           "3. Bouton « Exécuter » (Run).\n\n"
           "Résultats : dossier output\\Agrandir test.", col=0, row=0, size=(340, 330))
    r.add(10, "LoadImage", "Ta photo", {"image": img}, col=0, row=1.4, size=(340, 360), color=VERT)
    r.add(9, "SolidMask", "Contexte = toute la photo", {"value": 1.0, "width": 64, "height": 64}, col=0, row=3)
    r.add(11, "InpaintCropImproved", "De combien agrandir",
          crop(r, 11, 1, 0, extend_for_outpainting=True, extend_left_factor=1.25, extend_right_factor=1.25,
               mask_expand_pixels=48, mask_blend_pixels=96, context_from_mask_extend_factor=1.2),
          {"image": (10, 0), "mask": (10, 1), "optional_context_mask": (9, 0)}, col=1, row=0, size=(340, 640), color=VERT)
    r.crop_mask, r.stitcher, r.pixels = (11, 2), (11, 0), (11, 1)
    flux_commun(r, 2, nb, denoise=1.0)
    r.add(32, "SaveImage", "Résultats", {"filename_prefix": "Agrandir test/flux"}, {"images": (31, 0)}, col=7, row=0,
          size=(520, 560), color=BLEU)
    return r


def upscale(img="exemple.png"):
    r = Recette("Upscale test")
    r.note(1, "UPSCALE TEST\n\n"
           "1. Clic droit sur « Ta photo » > Open Image (ou glisse ta photo dessus).\n"
           "2. « Taille finale » : 0,5 = photo x2 ; 1,0 = photo x4.\n"
           "3. Bouton « Exécuter » (Run).\n\n"
           "Résultat : dossier output\\Upscale test.", col=0, row=0, size=(340, 300))
    r.add(10, "LoadImage", "Ta photo", {"image": img}, col=0, row=1.3, size=(340, 360), color=VERT)
    r.add(11, "UpscaleModelLoader", None, {"model_name": "RealESRGAN_x4plus.pth"}, col=1, row=0)
    r.add(12, "ImageUpscaleWithModel", "RealESRGAN (x4)", {}, {"upscale_model": (11, 0), "image": (10, 0)}, col=1, row=1)
    r.add(13, "ImageScaleBy", "Taille finale", {"upscale_method": "lanczos", "scale_by": 0.5}, {"image": (12, 0)}, col=2, row=1,
          color=VERT)
    r.add(14, "SaveImage", "Résultat", {"filename_prefix": "Upscale test/upscale"}, {"images": (13, 0)}, col=3, row=0,
          size=(520, 560), color=BLEU)
    return r


TEXTE_DETAIL = "high quality photo, sharp focus, fine details, natural texture"


def upscale_net(img="exemple.png", force=0.35):
    r = Recette("Upscale net test")
    r.note(1, "UPSCALE NET TEST\n\n"
           "Agrandit avec RealESRGAN puis Flux redessine les détails\n"
           "(peau, cheveux, cils), morceau par morceau.\n\n"
           "1. Clic droit sur « Ta photo » > Open Image (ou glisse ta photo dessus).\n"
           "2. « Agrandir et redessiner » :\n"
           "   upscale_by = x2 (mettre 1,5 / 3 / 4 si besoin)\n"
           "   denoise = force : 0,25 léger, 0,35 normal, 0,45 fort\n"
           "   (trop fort = le visage peut changer).\n"
           "3. Bouton « Exécuter » (Run).\n\n"
           "Résultat : dossier output\\Upscale net test.", col=0, row=0, size=(360, 380))
    r.add(10, "LoadImage", "Ta photo", {"image": img}, col=0, row=1.6, size=(340, 360), color=VERT)
    r.add(11, "UpscaleModelLoader", None, {"model_name": "RealESRGAN_x4plus.pth"}, col=1, row=0)
    r.add(20, "UNETLoader", "Flux Schnell", {"unet_name": "flux1-schnell.safetensors", "weight_dtype": "fp8_e4m3fn"}, col=1, row=1)
    r.add(21, "DualCLIPLoader", None, {"clip_name1": "clip_l.safetensors", "clip_name2": "t5xxl_fp8_e4m3fn_scaled.safetensors",
                                       "type": "flux", "device": "default"}, col=1, row=2)
    r.add(22, "VAELoader", None, {"vae_name": "ae.safetensors"}, col=1, row=3)
    r.add(24, "CLIPTextEncode", "Description automatique (ne pas toucher)", {"text": TEXTE_DETAIL}, {"clip": (21, 0)},
          col=2, row=1, size=(340, 140))
    r.add(26, "ConditioningZeroOut", None, {}, {"conditioning": (24, 0)}, col=2, row=2)
    r.add(30, "UltimateSDUpscale", "Agrandir et redessiner",
          {"upscale_by": 2.0, "seed": 1, "steps": 6, "cfg": 1.0, "sampler_name": "euler", "scheduler": "simple",
           "denoise": force, "mode_type": "Chess", "tile_width": 1024, "tile_height": 1024, "mask_blur": 16,
           "tile_padding": 64, "seam_fix_mode": "None", "seam_fix_denoise": 1.0, "seam_fix_width": 64,
           "seam_fix_mask_blur": 8, "seam_fix_padding": 16, "force_uniform_tiles": True, "tiled_decode": False,
           "batch_size": 1},
          {"image": (10, 0), "model": (20, 0), "positive": (24, 0), "negative": (26, 0), "vae": (22, 0),
           "upscale_model": (11, 0)}, col=3, row=0, size=(360, 820), color=VERT)
    r.add(31, "SaveImage", "Résultat", {"filename_prefix": "Upscale net test/upscale"}, {"images": (30, 0)}, col=4, row=0,
          size=(520, 560), color=BLEU)
    return r


CONSIGNE_ALPHABET = ("Replace the text 'TEXTE' with the text 'LETTRES'. Keep exactly the same font, the same lettering "
                     "style, the same stroke thickness, the same color and the same size. Keep everything else "
                     "unchanged.")
# majuscules accompagnées de leur minuscule : seules, Kontext les écrivait dans une autre police (essai du 10/11)
PASSES_ALPHABET = ["abcdef", "ghijkl", "mnopqr", "stuvwx", "yz",
                   "Aa Bb Cc Dd", "Ee Ff Gg Hh", "Ii Jj Kk Ll", "Mm Nn Oo Pp", "Qq Rr Ss Tt", "Uu Vv Ww Xx", "Yy Zz",
                   "a1 b2 c3 d4 e5", "f6 g7 h8 i9 j0", "éèêàçù", "âîôûœë"]


def alphabet(nb, img="exemple.png"):
    """Flux Kontext : le texte de l'image est remplacé par d'autres lettres, même style, passe par passe."""
    r = Recette("Alphabet test")
    r.note(1, "ALPHABET TEST\n\n"
           "Refait l'alphabet dans le style d'un texte de l'image\n"
           "(Flux Kontext, usage personnel seulement).\n\n"
           "1. Clic droit sur « Ton image » > Open Image : une image où\n"
           "   le texte se voit bien (recadrée autour du texte, c'est mieux).\n"
           "2. « Texte écrit sur l'image » : recopie exactement le texte\n"
           "   à imiter (ex. Oublie-moi).\n"
           "3. « Nombre de propositions » : 3 conseillé (Kontext se trompe\n"
           "   parfois de lettre : on garde les meilleures).\n"
           "4. Bouton « Exécuter » (Run). Environ 2 à 3 min par proposition :\n"
           "   13 passes x 3 = environ 1 h 30. Pour sauter une passe :\n"
           "   clic sur son bloc « Lettres … », puis Ctrl+B.\n\n"
           "Résultats : dossier output\\Alphabet test, un sous-dossier\n"
           "par passe (abcdef, ghijkl…).", col=0, row=0, size=(400, 420))
    r.add(10, "LoadImage", "Ton image", {"image": img}, col=0, row=1.8, size=(340, 360), color=VERT)
    r.add(11, "PrimitiveStringMultiline", "Texte écrit sur l'image", {"value": "Oublie-moi"}, col=1, row=0,
          size=(340, 110), color=VERT)
    r.add(20, "UNETLoader", "Flux Kontext", {"unet_name": "flux1-dev-kontext_fp8_scaled.safetensors",
                                             "weight_dtype": "default"}, col=1, row=1)
    r.add(21, "DualCLIPLoader", None, {"clip_name1": "clip_l.safetensors",
                                       "clip_name2": "t5xxl_fp8_e4m3fn_scaled.safetensors", "type": "flux",
                                       "device": "default"}, col=1, row=2)
    r.add(22, "VAELoader", None, {"vae_name": "ae.safetensors"}, col=1, row=3)
    r.add(13, "FluxKontextImageScale", None, {}, {"image": (10, 0)}, col=2, row=0)
    r.add(14, "VAEEncode", None, {}, {"pixels": (13, 0), "vae": (22, 0)}, col=2, row=1)
    r.add(12, "RepeatLatentBatch", "Nombre de propositions", {"amount": nb}, {"samples": (14, 0)}, col=2, row=2,
          color=VERT)
    r.add(15, "StringReplace", "Consigne (ne pas toucher)", {"string": CONSIGNE_ALPHABET, "find": "TEXTE",
                                                             "replace": ""}, {"replace": (11, 0)}, col=2, row=3,
          size=(340, 200))
    for i, lettres in enumerate(PASSES_ALPHABET):
        b = 100 + 10 * i
        col = 3 + (i % 6) * 1.0
        row = 4 * (i // 6) / 1.0
        r.add(b, "StringReplace", f"Lettres {lettres}", {"string": "", "find": "LETTRES", "replace": lettres},
              {"string": (15, 0)}, col=col, row=row, size=(340, 150))
        r.add(b + 1, "CLIPTextEncode", None, {"text": ""}, {"clip": (21, 0), "text": (b, 0)}, col=col, row=row + 0.7)
        r.add(b + 2, "ReferenceLatent", None, {}, {"conditioning": (b + 1, 0), "latent": (14, 0)}, col=col,
              row=row + 1.2)
        r.add(b + 3, "FluxGuidance", None, {"guidance": 2.5}, {"conditioning": (b + 2, 0)}, col=col, row=row + 1.7)
        r.add(b + 4, "ConditioningZeroOut", None, {}, {"conditioning": (b + 1, 0)}, col=col, row=row + 2.2)
        r.add(b + 5, "KSampler", None, {"seed": 1, "steps": 20, "cfg": 1.0, "sampler_name": "euler",
                                         "scheduler": "simple", "denoise": 1.0},
              {"model": (20, 0), "positive": (b + 3, 0), "negative": (b + 4, 0), "latent_image": (12, 0)},
              col=col, row=row + 2.7, size=(320, 270))
        r.add(b + 6, "VAEDecode", None, {}, {"samples": (b + 5, 0), "vae": (22, 0)}, col=col, row=row + 3.3)
        r.add(b + 7, "SaveImage", f"Résultat {lettres}", {"filename_prefix": f"Alphabet test/{lettres.replace(' ', '')}/lettres"},
              {"images": (b + 6, 0)}, col=col, row=row + 3.6, size=(340, 300), color=BLEU)
    return r


if __name__ == "__main__":
    mode, dest = sys.argv[1], sys.argv[2]
    nb = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    img = sys.argv[4] if len(sys.argv) > 4 else "exemple.png"
    seules = sys.argv[5].split(",") if len(sys.argv) > 5 else None
    os.makedirs(dest, exist_ok=True)
    for r in (effacer(2, img), remplir(3, img), agrandir(3, img), upscale(img), upscale_net(img), alphabet(3, img)):
        if seules and r.nom not in seules:
            continue
        data = r.ui() if mode == "ui" else r.api()
        with open(os.path.join(dest, r.nom + ".json"), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        print("écrit", r.nom)
