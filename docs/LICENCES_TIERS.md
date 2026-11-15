# Licences des éléments tiers / Third-party licences

Pixane lui-même : Licence Pixane 1.2 (gratuit, code source disponible, non commercial), © 2026 Georges Christophe (chrypox) —
voir `LICENSE` (seul texte qui fait foi).
Pixane itself: Pixane Licence 1.2 (free of charge, source-available, non-commercial) — see `LICENSE.en.txt`
(courtesy translation).

## Inclus dans l'installateur / Included in the installer

| Élément / Item | Licence |
|---|---|
| Python 3.11 | PSF License (`python\LICENSE.txt`) |
| PySide6 / Qt 6.12, shiboken6 | LGPL-3.0 (bibliothèques non modifiées / unmodified libraries) |
| numpy | BSD-3-Clause (et composants 0BSD, MIT, Zlib, CC0) |
| Pillow | MIT-CMU |
| websocket-client | Apache-2.0 |
| pyphen 0.18 (césure / hyphenation) | au choix / either GPL-2.0+, LGPL-2.1+ ou / or MPL-1.1 |
| spylls 0.1.7 (lecture des dictionnaires Hunspell / Hunspell dictionary reader) | MIT |
| Dictionnaire français / French dictionary (Grammalecte « Classique » 7.7, Olivier R. — `pixane\dictionnaires\README_dict_fr.txt`), si la case est cochée / if ticked | MPL-2.0 |
| Dictionnaire anglais / English dictionary (SCOWL en_US, Kevin Atkinson et al. — `pixane\dictionnaires\README_en_US.txt`), si la case est cochée / if ticked | licence SCOWL (libre, notice à garder / permissive, notice kept) |
| Pinceaux et motifs de base / Built-in brushes and patterns (`pixane\ressources\base`) : paquets « Krita 3 Default Resources » et « Krita 4 Default Resources » de Krita (krita.org), par / by David Revoy (Deevad), Ramon Miranda, Timothée Giet, Razvanc, Radian, Wolthera van Hövell, Storm, Scottyp et d'autres / and others | CC0 1.0 (domaine public / public domain), déclaré dans chaque paquet / stated in each bundle |

## Téléchargé seulement si l'utilisateur le choisit / Downloaded only if the user chooses

| Élément / Item | Licence |
|---|---|
| ComfyUI portable | GPL-3.0 |
| comfyui-inpaint-nodes, ComfyUI-Inpaint-CropAndStitch, ComfyUI_UltimateSDUpscale | GPL-3.0 |
| ComfyUI-GGUF | Apache-2.0 ; bibliothèque gguf : MIT |
| 7-Zip (7zr.exe) | LGPL-2.1 |
| FLUX.1 Fill [dev] (GGUF Q8) | **FLUX.1 [dev] Non-Commercial License** — https://huggingface.co/black-forest-labs/FLUX.1-dev/blob/main/LICENSE.md |
| FLUX.1 [schnell] (GGUF Q8, facultatif / optional) | Apache-2.0 |
| FLUX.1 Kontext [dev] (fp8, facultatif / optional) | **FLUX.1 [dev] Non-Commercial License** |
| Opus-MT fr-en (Helsinki-NLP, traducteur facultatif / optional translator) | Apache-2.0 |
| Dictionnaires d'orthographe ajoutés depuis Pixane / spelling dictionaries added from Pixane (LibreOffice dictionaries, github.com/LibreOffice/dictionaries) | voir ci-dessus / see above |
| Encodeurs T5 et CLIP / T5 and CLIP encoders, VAE | Apache-2.0 |
| LaMa | Apache-2.0 |
| RealESRGAN x4plus | BSD-3-Clause |
| SCUNet (réduire le bruit / noise reduction) | Apache-2.0 |
| BiRefNet (détourage / background removal) | MIT |
| SAM 3.1 (sélection d'objet / object selection) | SAM License (Meta) — https://huggingface.co/Comfy-Org/sam3.1/blob/main/LICENSE |
| Depth Anything 3 Small (flou selon la profondeur, facultatif / depth blur, optional) | Apache-2.0 — https://huggingface.co/Comfy-Org/Depth-Anything-3 |

Pixane lance ComfyUI comme un programme séparé (aucun code de ComfyUI n'est inclus dans Pixane).
Pixane runs ComfyUI as a separate program (no ComfyUI code is included in Pixane).
