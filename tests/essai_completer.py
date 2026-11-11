"""Compléter un ComfyUI déjà installé : ce qui manque est trouvé d'après /object_info, rangé dans les dossiers de ce
ComfyUI, rien d'autre n'est touché. Faux ComfyUI dans un dossier temporaire, téléchargements simulés.
Usage : essai_completer.py"""
import io
import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from pixane import completer_moteur, installation_moteur
from pixane.completer_moteur import FenetreCompleter, manquants

erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


def combo(*options):
    return ["COMBO", {"options": list(options)}]


def infos_completes():
    return {
        "INPAINT_InpaintWithModel": {}, "InpaintCropImproved": {}, "UltimateSDUpscale": {}, "RemoveBackground": {},
        "SAM3_Detect": {}, "ReferenceLatent": {},
        "UnetLoaderGGUF": {"input": {"required": {"unet_name": combo("flux1-fill-dev-Q8_0.gguf")}}},
        "UNETLoader": {"input": {"required": {"unet_name": combo()}}},
        "DualCLIPLoader": {"input": {"required": {"clip_name1": combo("clip_l.safetensors",
                                                                      "t5xxl_fp8_e4m3fn_scaled.safetensors"),
                                                  "clip_name2": combo("clip_l.safetensors",
                                                                      "t5xxl_fp8_e4m3fn_scaled.safetensors")}}},
        "VAELoader": {"input": {"required": {"vae_name": combo("ae.safetensors")}}},
        "INPAINT_LoadInpaintModel": {"input": {"required": {"model_name": combo("big-lama.pt")}}},
        "LoadBackgroundRemovalModel": {"input": {"required": {"bg_removal_name": combo("birefnet.safetensors")}}},
        "CheckpointLoaderSimple": {"input": {"required": {"ckpt_name": combo("sam3.1_multiplex_fp16.safetensors")}}},
        "UpscaleModelLoader": {"input": {"required": {"model_name": combo("RealESRGAN_x4plus.pth",
                                                                          "scunet_color_real_psnr.pth")}}},
    }


app = QApplication(sys.argv)
tmp = Path(tempfile.mkdtemp())
comfy = tmp / "ComfyUI"
(comfy / "custom_nodes").mkdir(parents=True)
partage = tmp / "Partage" / "models"
dossiers = {g: [str(partage / g)] for g in ("checkpoints", "vae", "text_encoders", "diffusion_models",
                                             "upscale_models", "background_removal")}

# 1. un ComfyUI complet : rien à télécharger
l, notes = manquants(infos_completes(), dossiers, comfy)
verifier(l == [] and notes == [], f"ComfyUI complet : rien à télécharger {[e.cle for e in l]}")

# 2. il manque l'extension Crop and Stitch, Flux Fill, LaMa et RealESRGAN
infos = infos_completes()
del infos["InpaintCropImproved"]
infos["UnetLoaderGGUF"]["input"]["required"]["unet_name"] = combo()
infos["INPAINT_LoadInpaintModel"]["input"]["required"]["model_name"] = combo()
infos["UpscaleModelLoader"]["input"]["required"]["model_name"] = combo("scunet_color_real_psnr.pth")
l, notes = manquants(infos, dossiers, comfy)
cles = {e.cle: e for e in l}
verifier(set(cles) == {"crop", "fill", "lama", "esrgan"}, f"seulement ce qui manque : {sorted(cles)}")
verifier(Path(cles["crop"].dest) == comfy / "custom_nodes" / "ComfyUI-Inpaint-CropAndStitch",
         "l'extension va dans custom_nodes de ce ComfyUI")
verifier(Path(cles["fill"].dest).parent == partage / "diffusion_models",
         f"Flux Fill va dans le dossier de modèles de ComfyUI (même partagé) : {cles['fill'].dest}")
verifier(Path(cles["lama"].dest).parent == partage / "inpaint", "LaMa : dossier « inpaint » à côté des autres")
verifier(Path(cles["esrgan"].dest).parent == partage / "upscale_models", "RealESRGAN : upscale_models")
verifier("gguf" not in cles, "extension GGUF déjà là : pas retéléchargée")

# 3. GGUF absent et Flux Fill à télécharger : l'extension GGUF est ajoutée ; ComfyUI trop ancien : signalé
infos2 = json.loads(json.dumps(infos))
del infos2["UnetLoaderGGUF"]
del infos2["SAM3_Detect"]
infos2["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"] = combo()
l2, notes2 = manquants(infos2, dossiers, comfy)
verifier("gguf" in {e.cle for e in l2}, "Flux Fill en .gguf : l'extension GGUF est ajoutée")
verifier("sam" not in {e.cle for e in l2} and any("trop ancien" in n for n in notes2),
         f"SAM sans le nœud de ComfyUI : pas téléchargé, signalé ({notes2})")

# 4. extension déjà là mais pas chargée (ComfyUI pas relancé) : pas touchée, signalée
(comfy / "custom_nodes" / "ComfyUI-Inpaint-CropAndStitch").mkdir()
l3, notes3 = manquants(infos, dossiers, comfy)
verifier("crop" not in {e.cle for e in l3} and any("pas encore chargé" in n for n in notes3),
         "extension présente mais pas chargée : pas retéléchargée, « ferme et rouvre ComfyUI »")
(comfy / "custom_nodes" / "ComfyUI-Inpaint-CropAndStitch").rmdir()

# 5. installation en mode complément (téléchargements simulés)
avant_reglage = QSettings("Pixane", "Pixane-essais").value("comfyui_dir")
travail = tmp / "complement"


def faux_telecharger(self, e, cible, essais=5):
    cible.parent.mkdir(parents=True, exist_ok=True)
    if e.genre == "zip":
        tampon = io.BytesIO()
        with zipfile.ZipFile(tampon, "w") as z:
            z.writestr("depot-123/__init__.py", "# extension")
        cible.write_bytes(tampon.getvalue())
    else:
        cible.write_bytes(b"modele")
    self.etat.emit(e.cle, "prêt")


installation_moteur.Installation._telecharger = faux_telecharger
pip = []
installation_moteur.Installation._pip = lambda self, r: pip.append(self.python)
inst = {"dir": comfy, "python": tmp / "python.exe"}
f = FenetreCompleter(infos, dossiers, inst, externe=True)
if f.c_traducteur.isEnabled():
    f.c_traducteur.setChecked(False)          # le traducteur a ses propres essais (essai_modifier)
verifier(f.liste.topLevelItemCount() == 4 and not f.c_licence.isHidden() and not f.b_lancer.isEnabled(),
         "fenêtre : 4 lignes ; licence FLUX à accepter avant de télécharger")
f.c_licence.setChecked(True)
verifier(f.b_lancer.isEnabled(), "licence acceptée : bouton Télécharger actif")
completer_moteur.DOSSIER_TRAVAIL = travail
fin = []
f.fini.connect(fin.append)
from PySide6.QtWidgets import QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
f.travail = None
f.commencer()
import time
for _ in range(300):
    app.processEvents()
    if fin:
        break
    time.sleep(0.02)
verifier(fin == [True], "complément terminé")
verifier((comfy / "custom_nodes" / "ComfyUI-Inpaint-CropAndStitch" / "__init__.py").is_file(),
         "extension décompressée dans custom_nodes")
verifier((partage / "diffusion_models" / "flux1-fill-dev-Q8_0.gguf").is_file()
         and (partage / "inpaint" / "big-lama.pt").is_file()
         and (partage / "upscale_models" / "RealESRGAN_x4plus.pth").is_file(), "modèles rangés dans ses dossiers")
verifier(not (comfy / "pixane.json").exists() and not (travail / installation_moteur.MARQUE).exists(),
         "aucune marque « installé par Pixane » sur ce ComfyUI")
verifier(QSettings("Pixane", "Pixane-essais").value("comfyui_dir") == avant_reglage,
         "le dossier de ComfyUI choisi dans les réglages n'a pas changé")
verifier(pip == [], "pas de bibliothèque gguf à installer (extension GGUF déjà là)")

print("ERREURS :", erreurs if erreurs else "aucune")
sys.stdout.flush()
sys.exit(1 if erreurs else 0)
