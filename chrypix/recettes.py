"""Les recettes ComfyUI (format API), avec les réglages validés à l'étape 1.

Chaque fonction renvoie (prompt, sorties) : sorties = {numéro de nœud: libellé affiché}.
"""
from __future__ import annotations

import math
import random

from .langue import tr

NB_EFFACER = 2      # propositions Flux (plus la version LaMa seule)
NB_REMPLIR = 3
NB_AGRANDIR = 3

# Modèle Flux Fill utilisé : version complète (.safetensors, réduite à 8 bits au chargement) ou version GGUF
# (même modèle, compressé ; extension ComfyUI-GGUF). Choisi par configurer() selon ce qui est installé.
FILL_COMPLET = "flux1-fill-dev.safetensors"
FILL_GGUF = "flux1-fill-dev-Q8_0.gguf"
PREFERENCE_FILL = ("complet", "gguf")    # ordre de préférence quand les deux sont présents
_fill = {"type": "complet", "fichier": FILL_COMPLET}
# Flux Schnell (Upscale net) : version complète si elle est là, sinon GGUF (installée par Chrypix, facultative)
SCHNELL_COMPLET = "flux1-schnell.safetensors"
_schnell: dict = {"type": "complet", "fichier": SCHNELL_COMPLET}
# Détourage (sujet / arrière-plan) : nœuds intégrés à ComfyUI + modèle BiRefNet (MIT)
BIREFNET = "birefnet.safetensors"
_detourage = {"ok": False}


class ModeleManquant(Exception):
    pass


def _options(infos: dict, noeud: str, entree: str) -> list:
    """Choix possibles d'une entrée : ancien format [[...], {...}] ou nouveau ["COMBO", {"options": [...]}]."""
    try:
        d = infos[noeud]["input"]["required"][entree]
    except (KeyError, IndexError, TypeError):
        return []
    if d and isinstance(d[0], list):
        return list(d[0])
    if len(d) > 1 and isinstance(d[1], dict):
        return list(d[1].get("options") or [])
    return []


def configurer(infos: dict) -> str | None:
    """Choisit le modèle Flux Fill d'après /object_info de ComfyUI. Renvoie le fichier choisi (None si aucun)."""
    trouves = {}
    if FILL_COMPLET in _options(infos, "UNETLoader", "unet_name"):
        trouves["complet"] = FILL_COMPLET
    ggufs = [f for f in _options(infos, "UnetLoaderGGUF", "unet_name") if "fill" in f.lower()]
    if ggufs:
        trouves["gguf"] = FILL_GGUF if FILL_GGUF in ggufs else sorted(ggufs)[-1]
    if SCHNELL_COMPLET in _options(infos, "UNETLoader", "unet_name"):
        _schnell.update(type="complet", fichier=SCHNELL_COMPLET)
    else:
        schnells = sorted(f for f in _options(infos, "UnetLoaderGGUF", "unet_name") if "schnell" in f.lower())
        _schnell.update(type="gguf" if schnells else None, fichier=schnells[-1] if schnells else None)
    _detourage["ok"] = ("RemoveBackground" in infos
                        and BIREFNET in _options(infos, "LoadBackgroundRemovalModel", "bg_removal_name"))
    for t in PREFERENCE_FILL:
        if t in trouves:
            _fill.update(type=t, fichier=trouves[t])
            return trouves[t]
    return None


def detourage_disponible() -> bool:
    return _detourage["ok"]


def detourer(image: str):
    """Masque du sujet principal (blanc = sujet, noir = arrière-plan), de la taille de l'image."""
    p = {"10": _n("LoadImage", image=image),
         "11": _n("LoadBackgroundRemovalModel", bg_removal_name=BIREFNET),
         "12": _n("RemoveBackground", bg_removal_model=["11", 0], image=["10", 0]),
         "13": _n("MaskToImage", mask=["12", 0]),
         "14": _n("PreviewImage", images=["13", 0])}
    return p, {"14": tr("Sujet")}


def schnell_disponible() -> bool:
    return _schnell["type"] is not None


def chargeur_schnell() -> dict:
    if _schnell["type"] is None:
        raise ModeleManquant(tr("« Upscale net » a besoin du modèle Flux Schnell, qui n'est pas installé. "
                                "Menu IA > Installer le moteur IA permet de l'ajouter ; l'upscale simple marche "
                                "sans."))
    if _schnell["type"] == "gguf":
        return _n("UnetLoaderGGUF", unet_name=_schnell["fichier"])
    return _n("UNETLoader", unet_name=_schnell["fichier"], weight_dtype="fp8_e4m3fn")


def chargeur_fill(type_: str | None = None, fichier: str | None = None) -> dict:
    """Nœud qui charge Flux Fill (type_ et fichier : pour forcer un choix, ex. comparaison)."""
    type_ = type_ or _fill["type"]
    fichier = fichier or _fill["fichier"]
    if type_ == "gguf":
        return _n("UnetLoaderGGUF", unet_name=fichier)
    return _n("UNETLoader", unet_name=fichier, weight_dtype="fp8_e4m3fn")


def _graine() -> int:
    return random.randint(1, 2**48)


def _decoupe(**reglages) -> dict:
    r = {"downscale_algorithm": "bilinear", "upscale_algorithm": "bicubic", "preresize": False,
         "preresize_mode": "ensure minimum resolution", "preresize_min_width": 1024, "preresize_min_height": 1024,
         "preresize_max_width": 16384, "preresize_max_height": 16384, "mask_fill_holes": True,
         "mask_expand_pixels": 16, "mask_invert": False, "mask_blend_pixels": 32, "mask_hipass_filter": 0.1,
         "extend_for_outpainting": False, "extend_up_factor": 1.0, "extend_down_factor": 1.0,
         "extend_left_factor": 1.0, "extend_right_factor": 1.0, "context_from_mask_extend_factor": 1.6,
         "output_resize_to_target_size": True, "output_target_width": 1024, "output_target_height": 1024,
         "output_padding": "32", "device_mode": "gpu (much faster)"}
    r.update(reglages)
    return r


def _n(classe: str, **entrees) -> dict:
    return {"class_type": classe, "inputs": entrees}


def _flux_fill(p: dict, pixels, masque, assembleur, nb: int, texte: str = "", denoise: float = 1.0,
               steps: int = 24, graine: int | None = None, chargeur: dict | None = None) -> None:
    """Ajoute la chaîne Flux Fill (nœuds 20 à 31) au prompt p."""
    p["20"] = chargeur or chargeur_fill()
    p["21"] = _n("DualCLIPLoader", clip_name1="clip_l.safetensors", clip_name2="t5xxl_fp8_e4m3fn_scaled.safetensors",
                 type="flux", device="default")
    p["22"] = _n("VAELoader", vae_name="ae.safetensors")
    p["23"] = _n("DifferentialDiffusion", model=["20", 0], strength=1.0)
    p["24"] = _n("CLIPTextEncode", text=texte, clip=["21", 0])
    p["25"] = _n("FluxGuidance", conditioning=["24", 0], guidance=30.0)
    p["26"] = _n("ConditioningZeroOut", conditioning=["24", 0])
    p["27"] = _n("InpaintModelConditioning", positive=["25", 0], negative=["26", 0], vae=["22", 0],
                 pixels=pixels, mask=masque, noise_mask=True)
    p["28"] = _n("RepeatLatentBatch", samples=["27", 2], amount=nb)
    p["29"] = _n("KSampler", model=["23", 0], seed=graine or _graine(), steps=steps, cfg=1.0, sampler_name="euler",
                 scheduler="simple", positive=["27", 0], negative=["27", 1], latent_image=["28", 0], denoise=denoise)
    p["30"] = _n("VAEDecode", samples=["29", 0], vae=["22", 0])
    if assembleur is None:   # pas de découpe : on garde l'image entière
        p["32"] = _n("PreviewImage", images=["30", 0])
    else:
        p["31"] = _n("InpaintStitchImproved", stitcher=assembleur, inpainted_image=["30", 0])
        p["32"] = _n("PreviewImage", images=["31", 0])


def effacer(image: str, nb: int = NB_EFFACER, graine: int | None = None, chargeur: dict | None = None):
    p = {"10": _n("LoadImage", image=image),
         "11": _n("InpaintCropImproved", image=["10", 0], mask=["10", 1], **_decoupe()),
         "12": _n("INPAINT_LoadInpaintModel", model_name="big-lama.pt"),
         "13": _n("INPAINT_InpaintWithModel", inpaint_model=["12", 0], image=["11", 1], mask=["11", 2],
                  seed=graine or _graine()),
         "14": _n("InpaintStitchImproved", stitcher=["11", 0], inpainted_image=["13", 0]),
         "15": _n("PreviewImage", images=["14", 0])}
    _flux_fill(p, ["13", 0], ["11", 2], ["11", 0], nb, denoise=0.6, steps=20, graine=graine, chargeur=chargeur)
    return p, {"32": "Flux", "15": tr("LaMa seul")}


def remplir(image: str, texte: str = "", nb: int = NB_REMPLIR, graine: int | None = None,
            chargeur: dict | None = None):
    p = {"10": _n("LoadImage", image=image),
         "11": _n("InpaintCropImproved", image=["10", 0], mask=["10", 1], **_decoupe())}
    _flux_fill(p, ["11", 1], ["11", 2], ["11", 0], nb, texte=texte, denoise=1.0, graine=graine, chargeur=chargeur)
    return p, {"32": tr("Proposition")}


def agrandir(image: str, nb: int = NB_AGRANDIR, graine: int | None = None, chargeur: dict | None = None):
    """image : toile déjà préparée par Chrypix (raccord.preparer), zone à peindre en transparent."""
    p = {"10": _n("LoadImage", image=image)}
    _flux_fill(p, ["10", 0], ["10", 1], None, nb, denoise=1.0, graine=graine, chargeur=chargeur)
    return p, {"32": tr("Proposition")}


def upscale_rapide(image: str, facteur: float = 2.0):
    p = {"10": _n("LoadImage", image=image),
         "11": _n("UpscaleModelLoader", model_name="RealESRGAN_x4plus.pth"),
         "12": _n("ImageUpscaleWithModel", upscale_model=["11", 0], image=["10", 0]),
         "13": _n("ImageScaleBy", image=["12", 0], upscale_method="lanczos", scale_by=facteur / 4),
         "14": _n("PreviewImage", images=["13", 0])}
    return p, {"14": tr("Upscale rapide")}


def nb_morceaux(largeur: int, hauteur: int, facteur: float, tuile: int = 1024) -> int:
    """Nombre de morceaux de 1024 px que Flux redessine (pour la barre de progression)."""
    return math.ceil(largeur * facteur / tuile) * math.ceil(hauteur * facteur / tuile)


def upscale_net(image: str, facteur: float = 2.0, force: float = 0.35, taille: tuple[int, int] | None = None):
    p = {"10": _n("LoadImage", image=image),
         "11": _n("UpscaleModelLoader", model_name="RealESRGAN_x4plus.pth"),
         "20": chargeur_schnell(),
         "21": _n("DualCLIPLoader", clip_name1="clip_l.safetensors",
                  clip_name2="t5xxl_fp8_e4m3fn_scaled.safetensors", type="flux", device="default"),
         "22": _n("VAELoader", vae_name="ae.safetensors"),
         "24": _n("CLIPTextEncode", clip=["21", 0],
                  text="high quality photo, sharp focus, fine details, natural texture"),
         "26": _n("ConditioningZeroOut", conditioning=["24", 0]),
         "30": _n("UltimateSDUpscale", image=["10", 0], model=["20", 0], positive=["24", 0], negative=["26", 0],
                  vae=["22", 0], upscale_model=["11", 0], upscale_by=facteur, seed=_graine(), steps=6, cfg=1.0,
                  sampler_name="euler", scheduler="simple", denoise=force, mode_type="Chess", tile_width=1024,
                  tile_height=1024, mask_blur=16, tile_padding=64, seam_fix_mode="None", seam_fix_denoise=1.0,
                  seam_fix_width=64, seam_fix_mask_blur=8, seam_fix_padding=16, force_uniform_tiles=True,
                  tiled_decode=False, batch_size=1),
         "31": _n("PreviewImage", images=["30", 0])}
    if taille:
        return p, {"31": tr("Upscale net")}, nb_morceaux(*taille, facteur)
    return p, {"31": tr("Upscale net")}
