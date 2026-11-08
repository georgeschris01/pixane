"""Les recettes ComfyUI (format API), avec les réglages validés à l'étape 1.

Chaque fonction renvoie (prompt, sorties) : sorties = {numéro de nœud: libellé affiché}.
"""
from __future__ import annotations

import math
import random

NB_EFFACER = 2      # propositions Flux (plus la version LaMa seule)
NB_REMPLIR = 3
NB_AGRANDIR = 3


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
               steps: int = 24) -> None:
    """Ajoute la chaîne Flux Fill (nœuds 20 à 31) au prompt p."""
    p["20"] = _n("UNETLoader", unet_name="flux1-fill-dev.safetensors", weight_dtype="fp8_e4m3fn")
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
    p["29"] = _n("KSampler", model=["23", 0], seed=_graine(), steps=steps, cfg=1.0, sampler_name="euler",
                 scheduler="simple", positive=["27", 0], negative=["27", 1], latent_image=["28", 0], denoise=denoise)
    p["30"] = _n("VAEDecode", samples=["29", 0], vae=["22", 0])
    if assembleur is None:   # pas de découpe : on garde l'image entière
        p["32"] = _n("PreviewImage", images=["30", 0])
    else:
        p["31"] = _n("InpaintStitchImproved", stitcher=assembleur, inpainted_image=["30", 0])
        p["32"] = _n("PreviewImage", images=["31", 0])


def effacer(image: str, nb: int = NB_EFFACER):
    p = {"10": _n("LoadImage", image=image),
         "11": _n("InpaintCropImproved", image=["10", 0], mask=["10", 1], **_decoupe()),
         "12": _n("INPAINT_LoadInpaintModel", model_name="big-lama.pt"),
         "13": _n("INPAINT_InpaintWithModel", inpaint_model=["12", 0], image=["11", 1], mask=["11", 2], seed=_graine()),
         "14": _n("InpaintStitchImproved", stitcher=["11", 0], inpainted_image=["13", 0]),
         "15": _n("PreviewImage", images=["14", 0])}
    _flux_fill(p, ["13", 0], ["11", 2], ["11", 0], nb, denoise=0.6, steps=20)
    return p, {"32": "Flux", "15": "LaMa seul"}


def remplir(image: str, texte: str = "", nb: int = NB_REMPLIR):
    p = {"10": _n("LoadImage", image=image),
         "11": _n("InpaintCropImproved", image=["10", 0], mask=["10", 1], **_decoupe())}
    _flux_fill(p, ["11", 1], ["11", 2], ["11", 0], nb, texte=texte, denoise=1.0)
    return p, {"32": "Proposition"}


def agrandir(image: str, nb: int = NB_AGRANDIR):
    """image : toile déjà préparée par Chrypix (raccord.preparer), zone à peindre en transparent."""
    p = {"10": _n("LoadImage", image=image)}
    _flux_fill(p, ["10", 0], ["10", 1], None, nb, denoise=1.0)
    return p, {"32": "Proposition"}


def upscale_rapide(image: str, facteur: float = 2.0):
    p = {"10": _n("LoadImage", image=image),
         "11": _n("UpscaleModelLoader", model_name="RealESRGAN_x4plus.pth"),
         "12": _n("ImageUpscaleWithModel", upscale_model=["11", 0], image=["10", 0]),
         "13": _n("ImageScaleBy", image=["12", 0], upscale_method="lanczos", scale_by=facteur / 4),
         "14": _n("PreviewImage", images=["13", 0])}
    return p, {"14": "Upscale rapide"}


def nb_morceaux(largeur: int, hauteur: int, facteur: float, tuile: int = 1024) -> int:
    """Nombre de morceaux de 1024 px que Flux redessine (pour la barre de progression)."""
    return math.ceil(largeur * facteur / tuile) * math.ceil(hauteur * facteur / tuile)


def upscale_net(image: str, facteur: float = 2.0, force: float = 0.35, taille: tuple[int, int] | None = None):
    p = {"10": _n("LoadImage", image=image),
         "11": _n("UpscaleModelLoader", model_name="RealESRGAN_x4plus.pth"),
         "20": _n("UNETLoader", unet_name="flux1-schnell.safetensors", weight_dtype="fp8_e4m3fn"),
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
        return p, {"31": "Upscale net"}, nb_morceaux(*taille, facteur)
    return p, {"31": "Upscale net"}
