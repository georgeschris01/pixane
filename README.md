# Retouche IA

Éditeur photo pour Windows avec retouche par IA, sans abonnement :
**Effacer** un objet, **Remplir** une zone, **Agrandir** l'image au-delà de ses bords, **Upscale** (augmenter la définition).

L'IA tourne sur le PC grâce à [ComfyUI](https://github.com/comfyanonymous/ComfyUI), lancé en arrière-plan sans fenêtre.

## Lancer

Double-clic sur `Retouche IA.bat` (ou `.venv\Scripts\python -m retouche_ia photo.jpg`).

## Besoins

- Python 3.11+, puis `uv venv` et `uv pip install -e .`
- ComfyUI installé, avec les extensions `comfyui-inpaint-nodes`, `ComfyUI-Inpaint-CropAndStitch`,
  `ComfyUI_UltimateSDUpscale`, et les modèles Flux Fill, Flux Schnell, LaMa, RealESRGAN x4plus.
- Emplacement de ComfyUI réglable dans `%LOCALAPPDATA%\RetoucheIA\config.json` (`comfyui_dir`, `extra_model_paths`).

## Licences des modèles

Flux.1 Fill dev : usage non commercial. Flux.1 Schnell : Apache-2.0. LaMa : Apache-2.0. RealESRGAN : BSD-3.
