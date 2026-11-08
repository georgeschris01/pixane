# Chrypix

Éditeur photo pour Windows avec retouche par IA, sans abonnement :
**Effacer** un objet, **Remplir** une zone, **Agrandir** l'image au-delà de ses bords, **Upscale** (augmenter la définition).

L'IA tourne sur le PC grâce à [ComfyUI](https://github.com/comfyanonymous/ComfyUI), lancé en arrière-plan sans fenêtre.

## Lancer

Double-clic sur `Chrypix.bat` (ou `.venv\Scripts\python -m chrypix photo.jpg`).

## Besoins

- Python 3.11+, puis `uv venv` et `uv pip install -e .`
- ComfyUI installé, avec les extensions `comfyui-inpaint-nodes`, `ComfyUI-Inpaint-CropAndStitch`,
  `ComfyUI_UltimateSDUpscale`, et les modèles Flux Fill, Flux Schnell, LaMa, RealESRGAN x4plus.
- Emplacement de ComfyUI réglable dans `%LOCALAPPDATA%\Chrypix\config.json` (`comfyui_dir`, `extra_model_paths`).

## Licence

Chrypix : **Licence Chrypix 1.1**, © 2026 Georges Christophe (chrypox) — gratuit, code source ouvert, **non
commercial** : utilisable par tous (même au travail), modifiable et partageable (forks permis), à condition de garder
le nom de l'auteur ; ni Chrypix ni une version modifiée ne peuvent être vendus, et les versions modifiées gardent ces
règles (`LICENSE`, seul texte qui fait foi ; traduction anglaise : `LICENSE.en.txt`).

Modèles : Flux.1 Fill dev : usage non commercial. Flux.1 Schnell : Apache-2.0. LaMa : Apache-2.0. RealESRGAN : BSD-3.
Détail de tous les éléments tiers : `docs/LICENCES_TIERS.md`.
