"""Installation du moteur IA (ComfyUI portable, extensions, modèles) pour un PC qui n'en a pas.

Lancement seul : python -m chrypix.installation_moteur [--dossier D] [--schnell] [--accepte] [--demarrer]
(l'installateur de Chrypix l'ouvre ainsi) ; ou depuis Chrypix, menu IA > Installer le moteur IA.

Chaque fichier est téléchargé dans un fichier « .part » : si on arrête (ou si la connexion coupe), le
téléchargement reprend plus tard là où il s'était arrêté. Chaque fichier est vérifié (taille, empreinte SHA-256).
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, QSettings, Qt, Signal
from PySide6.QtWidgets import (QApplication, QCheckBox, QDialog, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
                               QMessageBox, QProgressBar, QPushButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout)

from .langue import tr

GO = 1024 ** 3
DOSSIER_APP = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Chrypix"
DOSSIER_DEFAUT = DOSSIER_APP / "moteur"
PORTABLE = "ComfyUI_windows_portable"           # dossier créé par l'archive de ComfyUI
# Marque posée dans le dossier choisi dès le début : le désinstalleur de Chrypix ne propose de supprimer
# que ce qu'il trouve à côté d'elle (jamais un ComfyUI installé par quelqu'un d'autre).
MARQUE = "chrypix-moteur.json"
JOURNAL = DOSSIER_APP / "installation_moteur.log"
MARGE_EXTRACTION = 8 * GO                         # ComfyUI décompressé (Python, PyTorch…), en plus de l'archive
LICENCE_FLUX = "https://huggingface.co/black-forest-labs/FLUX.1-dev/blob/main/LICENSE.md"
PILOTE_CUDA13 = 580                               # pilote NVIDIA minimal pour la version « nvidia » (CUDA 13)
GGUF_PIP = "gguf==0.19.0"                         # bibliothèque Python de l'extension ComfyUI-GGUF (MIT)

HF = "https://huggingface.co/{}/resolve/main/{}"
GH = "https://github.com/{}/archive/{}.zip"


@dataclass(frozen=True)
class Element:
    cle: str
    nom: str
    url: str
    taille: int | None            # octets (None : archive GitHub, taille inconnue d'avance, petite)
    sha256: str | None
    licence: str
    genre: str                    # « outil », « 7z », « zip », « modele »
    dest: str = ""                # chemin dans ComfyUI_windows_portable (dossier pour « zip », fichier pour « modele »)
    facultatif: bool = False

    @property
    def fichier(self) -> str:
        return self.url.rsplit("/", 1)[-1]


def _comfyui(pilote_recent: bool) -> Element:
    nom = "ComfyUI_windows_portable_nvidia.7z" if pilote_recent else "ComfyUI_windows_portable_nvidia_cu126.7z"
    taille, sha = ((2054382457, "7170c2db49c182a81adcc051e80234f99dd891656fb200737f87797876348f96") if pilote_recent
                   else (1945636677, "a26cf84f043b3d9fbf0d53296f57d7190482c339caf1b3b5cfda5149d454be9f"))
    return Element("comfyui", tr("ComfyUI portable 0.44 (le moteur)"),
                   f"https://github.com/Comfy-Org/ComfyUI/releases/download/v0.44.0/{nom}", taille, sha,
                   "GPL-3.0", "7z")


def catalogue(pilote_recent: bool = True, schnell: bool = False) -> list[Element]:
    """Tout ce qu'il faut, dans l'ordre d'installation (ComfyUI d'abord : le reste va dedans)."""
    noeuds = "ComfyUI/custom_nodes/"
    modeles = "ComfyUI/models/"
    liste = [
        Element("7zr", tr("7-Zip (pour décompresser ComfyUI)"),
                "https://github.com/ip7z/7zip/releases/download/26.04/7zr.exe", 602624,
                "256feca8e274e5da655e2a284fabafd9f554365eb164862089dacd4e8276d282", "LGPL-2.1", "outil"),
        _comfyui(pilote_recent),
        Element("inpaint", tr("Extension Inpaint nodes (LaMa)"),
                GH.format("Acly/comfyui-inpaint-nodes", "5b7681746fe19e563113d27366ba85236bc1ba5b"), None, None,
                "GPL-3.0", "zip", noeuds + "comfyui-inpaint-nodes"),
        Element("crop", tr("Extension Inpaint Crop and Stitch"),
                GH.format("lquesada/ComfyUI-Inpaint-CropAndStitch", "6005efc02f7745649118edd89cdd084c2b9bd3ae"),
                None, None, "GPL-3.0", "zip", noeuds + "ComfyUI-Inpaint-CropAndStitch"),
        Element("usdu", tr("Extension Ultimate SD Upscale"),
                GH.format("ssitu/ComfyUI_UltimateSDUpscale", "a5547db9e1d07d3318bb21e9e9c474f4c1e9c8df"),
                None, None, "GPL-3.0", "zip", noeuds + "ComfyUI_UltimateSDUpscale"),
        Element("usdu_script", tr("Ultimate SD Upscale (partie commune)"),
                GH.format("Coyote-A/ultimate-upscale-for-automatic1111", "2322caa480535b1011a1f9c18126d85ea444f146"),
                None, None, "GPL-3.0", "zip",
                noeuds + "ComfyUI_UltimateSDUpscale/repositories/ultimate_sd_upscale"),
        Element("gguf", tr("Extension ComfyUI-GGUF"),
                GH.format("city96/ComfyUI-GGUF", "6ea2651e7df66d7585f6ffee804b20e92fb38b8a"), None, None,
                "Apache-2.0", "zip", noeuds + "ComfyUI-GGUF"),
        Element("fill", tr("Flux Fill (effacer, remplir, agrandir)"),
                HF.format("YarvixPA/FLUX.1-Fill-dev-gguf", "flux1-fill-dev-Q8_0.gguf"), 12727035168,
                "345ffd7acf39148e391133ae2a2fa7cc3f85e8dd0dbdb4636e760c3e7fe7952d", "FLUX.1 [dev] (non commerciale)",
                "modele", modeles + "diffusion_models/flux1-fill-dev-Q8_0.gguf"),
        Element("t5", tr("Encodeur de texte T5"),
                HF.format("comfyanonymous/flux_text_encoders", "t5xxl_fp8_e4m3fn_scaled.safetensors"), 5157348688,
                "a498f0485dc9536735258018417c3fd7758dc3bccc0a645feaa472b34955557a", "Apache-2.0", "modele",
                modeles + "text_encoders/t5xxl_fp8_e4m3fn_scaled.safetensors"),
        Element("clip", tr("Encodeur de texte CLIP"),
                HF.format("comfyanonymous/flux_text_encoders", "clip_l.safetensors"), 246144152,
                "660c6f5b1abae9dc498ac2d21e1347d2abdb0cf6c0c0c8576cd796491d9a6cdd", "Apache-2.0", "modele",
                modeles + "text_encoders/clip_l.safetensors"),
        Element("vae", tr("Décodeur d'image (VAE)"),
                HF.format("Comfy-Org/Lumina_Image_2.0_Repackaged", "split_files/vae/ae.safetensors"), 335304388,
                "afc8e28272cd15db3919bacdb6918ce9c1ed22e96cb12c4d5ed0fba823529e38", "Apache-2.0", "modele",
                modeles + "vae/ae.safetensors"),
        Element("lama", tr("LaMa (effacer)"),
                "https://github.com/Sanster/models/releases/download/add_big_lama/big-lama.pt", 205669692,
                "344c77bbcb158f17dd143070d1e789f38a66c04202311ae3a258ef66667a9ea9", "Apache-2.0", "modele",
                modeles + "inpaint/big-lama.pt"),
        Element("birefnet", tr("BiRefNet (sujet, arrière-plan)"),
                HF.format("Comfy-Org/BiRefNet", "background_removal/birefnet.safetensors"), 444473596,
                "9ab37426bf4de0567af6b5d21b16151357149139362e6e8992021b8ce356a154", "MIT", "modele",
                modeles + "background_removal/birefnet.safetensors"),
        Element("esrgan", tr("RealESRGAN x4 (upscale)"),
                "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth", 67040989,
                "4fa0d38905f75ac06eb49a7951b426670021be3018265fd191d2125df9d682f1", "BSD-3-Clause", "modele",
                modeles + "upscale_models/RealESRGAN_x4plus.pth"),
    ]
    if schnell:
        liste.append(Element("schnell", tr("Flux Schnell (Upscale net, facultatif)"),
                             HF.format("city96/FLUX.1-schnell-gguf", "flux1-schnell-Q8_0.gguf"), 12687821728,
                             "f6694941193b10148dbf1f0f498d4ccd3e9875c127fc53946213b68580c66f10", "Apache-2.0",
                             "modele", modeles + "diffusion_models/flux1-schnell-Q8_0.gguf", facultatif=True))
    return liste


def taille_schnell() -> int:
    return 12687821728


def version_pilote() -> float | None:
    """Version du pilote NVIDIA (ex. 610.88), None s'il n'y a pas de carte NVIDIA."""
    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
                           capture_output=True, text=True, timeout=15, creationflags=subprocess.CREATE_NO_WINDOW)
        return float(r.stdout.strip().splitlines()[0])
    except (OSError, ValueError, IndexError, subprocess.SubprocessError):
        return None


def go(octets: float) -> str:
    from .langue import langue
    virgule = "," if langue() == "fr" else "."
    return tr("{n} Go", n=f"{octets / GO:.1f}".replace(".", virgule)) if octets >= GO / 10 else \
        tr("{n} Mo", n=f"{max(1, round(octets / 1024 ** 2))}")


def racine(dossier: Path) -> Path:
    return Path(dossier) / PORTABLE


def deja_installe(dossier: Path) -> bool:
    return (racine(dossier) / "ComfyUI" / "main.py").is_file() and (racine(dossier) / "chrypix.json").is_file()


def comfyui_etranger(dossier: Path) -> bool:
    """Vrai si le dossier contient déjà un ComfyUI portable qui n'a pas été installé par Chrypix."""
    return (racine(dossier) / "ComfyUI" / "main.py").is_file() and not (Path(dossier) / MARQUE).is_file()


def inscriptible(dossier: Path) -> bool:
    """Vrai si Windows laisse écrire dans ce dossier (ou dans son plus proche parent qui existe). Sans droits
    administrateur, un dossier protégé (Program Files…) donne sinon « accès refusé » en plein téléchargement."""
    p = Path(dossier)
    while not p.exists() and p.parent != p:
        p = p.parent
    essai = p / f"chrypix-essai-ecriture-{os.getpid()}.tmp"
    try:
        essai.write_bytes(b"essai")
        essai.unlink()
        return True
    except OSError:
        return False


def taille_restante(dossier: Path, elements: list[Element]) -> int:
    """Place disque encore nécessaire (fichiers pas encore là + ComfyUI décompressé)."""
    total = 0
    r = racine(dossier)
    for e in elements:
        if e.genre == "modele":
            if not _modele_present(r / e.dest, e):
                part = (r / e.dest).with_name(e.fichier + ".part")
                total += e.taille - (part.stat().st_size if part.is_file() else 0)
        elif e.genre == "7z" and not (r / "ComfyUI" / "main.py").is_file():
            total += e.taille + MARGE_EXTRACTION
        elif e.taille:
            total += e.taille
    return max(0, total)


def _modele_present(chemin: Path, e: Element) -> bool:
    return chemin.is_file() and chemin.stat().st_size == e.taille


def _journal(texte: str):
    try:
        DOSSIER_APP.mkdir(parents=True, exist_ok=True)
        with open(JOURNAL, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + texte + "\n")
    except OSError:
        pass


class Arrete(Exception):
    pass


class Installation(QObject):
    """Fait le travail dans un fil secondaire ; les signaux tiennent la fenêtre au courant."""
    etat = Signal(str, str)                      # clé de l'élément, texte d'état
    progres = Signal(float, float, float)        # octets faits, octets au total, vitesse (octets/s)
    message = Signal(str)
    fini = Signal(bool, str)                     # réussi, message

    def __init__(self, dossier: Path, elements: list[Element]):
        super().__init__()
        self.dossier = Path(dossier)
        self.elements = elements
        self.arret = threading.Event()
        self.total = sum(e.taille or 2 * 1024 ** 2 for e in elements)
        self.fait = 0.0
        self._fait_avant: dict[str, float] = {}
        self._debut = 0.0
        self._recu = 0.0                         # octets reçus pendant cette séance (pour la vitesse)

    def lancer(self):
        threading.Thread(target=self._travail, daemon=True).start()

    # ---------------------------------------------------------------- travail
    def _travail(self):
        self._debut = time.time()
        _journal(f"début, dossier {self.dossier}, {len(self.elements)} éléments")
        try:
            self.dossier.mkdir(parents=True, exist_ok=True)
            marque = self.dossier / MARQUE
            if not marque.is_file():
                marque.write_text(json.dumps({"commence_le": time.strftime("%Y-%m-%d %H:%M"),
                                              "contenu": [PORTABLE, "telechargements"]}, indent=1),
                                  encoding="utf-8")
            QSettings("Chrypix", os.environ.get("CHRYPIX_REGLAGES", "Chrypix")).setValue("moteur_dossier",
                                                                                     str(self.dossier))
            telechargements = self.dossier / "telechargements"
            telechargements.mkdir(exist_ok=True)
            r = racine(self.dossier)
            outil = None
            for e in self.elements:
                if self.arret.is_set():
                    raise Arrete()
                self._fait_avant[e.cle] = self.fait
                if e.genre == "outil":
                    outil = telechargements / e.fichier
                    if outil.is_file() and outil.stat().st_size == e.taille:
                        self.etat.emit(e.cle, tr("déjà là"))
                    else:
                        self._telecharger(e, outil)
                elif e.genre == "7z":
                    if (r / "ComfyUI" / "main.py").is_file():
                        self.etat.emit(e.cle, tr("déjà là"))
                    else:
                        archive = telechargements / e.fichier
                        if not (archive.is_file() and archive.stat().st_size == e.taille):
                            self._telecharger(e, archive)
                        self._decompresser(e, outil, archive)
                        archive.unlink(missing_ok=True)
                elif e.genre == "zip":
                    if (r / e.dest / "__init__.py").is_file() or (e.cle == "usdu_script" and
                                                                  (r / e.dest / "scripts").is_dir()):
                        self.etat.emit(e.cle, tr("déjà là"))
                    else:
                        archive = telechargements / f"{e.cle}.zip"
                        self._telecharger(e, archive)
                        self._dezipper(e, archive, r / e.dest)
                        archive.unlink(missing_ok=True)
                    if e.cle == "gguf":
                        self._pip(r)
                else:
                    cible = r / e.dest
                    if _modele_present(cible, e):
                        self.etat.emit(e.cle, tr("déjà là"))
                    else:
                        self._telecharger(e, cible)
                self.fait = self._fait_avant[e.cle] + (e.taille or 2 * 1024 ** 2)
                self.progres.emit(self.fait, self.total, self._vitesse())
            (r / "chrypix.json").write_text(json.dumps({"installe_le": time.strftime("%Y-%m-%d %H:%M"),
                                                        "elements": [e.cle for e in self.elements]}, indent=1),
                                            encoding="utf-8")
            shutil.rmtree(telechargements, ignore_errors=True)
            QSettings("Chrypix", os.environ.get("CHRYPIX_REGLAGES", "Chrypix")).setValue("comfyui_dir", str(r))
            _journal("terminé")
            self.fini.emit(True, tr("Le moteur IA est installé. Chrypix le trouvera tout seul."))
        except Arrete:
            _journal("arrêté par l'utilisateur")
            self.fini.emit(False, tr("Arrêté. Relance l'installation plus tard : elle reprendra où elle s'est "
                                     "arrêtée."))
        except Exception as ex:                  # réseau coupé, disque plein, fichier abîmé…
            _journal(f"échec : {ex!r}")
            self.fini.emit(False, tr("L'installation s'est arrêtée : {erreur}\n\nRelance-la plus tard : elle "
                                     "reprendra où elle s'est arrêtée. Détails : {fichier}", erreur=ex,
                                     fichier=JOURNAL))

    def _vitesse(self) -> float:
        duree = time.time() - self._debut
        return self._recu / duree if duree > 2 else 0.0

    def _telecharger(self, e: Element, cible: Path, essais: int = 5):
        """Télécharge avec reprise ; vérifie taille et empreinte, puis renomme le .part en fichier final."""
        cible.parent.mkdir(parents=True, exist_ok=True)
        part = cible.with_name(cible.name + ".part")
        for essai in range(essais):
            try:
                self._telecharger_une_fois(e, part)
                break
            except (urllib.error.URLError, OSError, TimeoutError) as ex:
                if self.arret.is_set():
                    raise Arrete()
                if isinstance(ex, urllib.error.HTTPError) and ex.code in (403, 404):
                    raise
                if essai == essais - 1:
                    raise
                _journal(f"{e.cle} : coupure ({ex!r}), nouvel essai")
                self.etat.emit(e.cle, tr("coupure, nouvel essai…"))
                time.sleep(5 * (essai + 1))
        if e.sha256:
            self.etat.emit(e.cle, tr("vérification…"))
            h = hashlib.sha256()
            with open(part, "rb") as f:
                while bloc := f.read(8 * 1024 ** 2):
                    if self.arret.is_set():
                        raise Arrete()
                    h.update(bloc)
            if h.hexdigest() != e.sha256:
                part.unlink(missing_ok=True)
                raise ValueError(tr("le fichier {nom} est abîmé (empreinte différente) ; il sera retéléchargé",
                                    nom=e.fichier))
        os.replace(part, cible)
        self.etat.emit(e.cle, tr("prêt"))
        _journal(f"{e.cle} : téléchargé ({cible})")

    def _telecharger_une_fois(self, e: Element, part: Path):
        deja = part.stat().st_size if part.is_file() else 0
        if e.taille and deja > e.taille:
            part.unlink()
            deja = 0
        if e.taille and deja == e.taille:
            return
        if not e.taille:                         # archive GitHub : pas de reprise possible
            deja = 0
        requete = urllib.request.Request(e.url, headers={"User-Agent": "Chrypix"})
        if deja:
            requete.add_header("Range", f"bytes={deja}-")
        with urllib.request.urlopen(requete, timeout=60) as rep:
            if deja and rep.status != 206:       # le serveur ne reprend pas : on recommence
                deja = 0
            mode = "ab" if deja else "wb"
            base = self._fait_avant[e.cle]
            dernier = 0.0
            with open(part, mode) as f:
                recu = deja
                while bloc := rep.read(1024 * 1024):
                    if self.arret.is_set():
                        raise Arrete()
                    f.write(bloc)
                    recu += len(bloc)
                    self._recu += len(bloc)
                    maintenant = time.time()
                    if maintenant - dernier > 0.3:
                        dernier = maintenant
                        self.fait = base + recu
                        self.progres.emit(self.fait, self.total, self._vitesse())
                        if e.taille:
                            self.etat.emit(e.cle, f"{recu * 100 // e.taille} %")
                        else:
                            self.etat.emit(e.cle, go(recu))
        if e.taille and part.stat().st_size != e.taille:
            raise OSError(tr("téléchargement incomplet"))

    def _decompresser(self, e: Element, outil: Path | None, archive: Path):
        self.etat.emit(e.cle, tr("décompression… (quelques minutes)"))
        if outil is None:
            raise OSError("7zr.exe manquant")
        r = subprocess.run([str(outil), "x", str(archive), f"-o{self.dossier}", "-y", "-bso0", "-bsp0"],
                           capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        if r.returncode != 0 or not (racine(self.dossier) / "ComfyUI" / "main.py").is_file():
            _journal(f"7zr : {r.returncode} {r.stderr[-2000:]}")
            raise OSError(tr("la décompression de ComfyUI a échoué"))
        self.etat.emit(e.cle, tr("prêt"))
        _journal("ComfyUI décompressé")

    def _dezipper(self, e: Element, archive: Path, dest: Path):
        """Décompresse une archive GitHub (un dossier « dépôt-commit » au sommet, qu'on enlève)."""
        dest.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive) as z:
            for info in z.infolist():
                parties = info.filename.split("/", 1)
                if len(parties) < 2 or not parties[1]:
                    continue
                chemin = (dest / parties[1]).resolve()
                if not str(chemin).startswith(str(dest.resolve())):     # sécurité : rien hors du dossier
                    continue
                if info.is_dir():
                    chemin.mkdir(parents=True, exist_ok=True)
                else:
                    chemin.parent.mkdir(parents=True, exist_ok=True)
                    with z.open(info) as src, open(chemin, "wb") as dst:
                        shutil.copyfileobj(src, dst)
        self.etat.emit(e.cle, tr("prêt"))

    def _pip(self, r: Path):
        """Bibliothèque « gguf » pour l'extension ComfyUI-GGUF, dans le Python de ComfyUI."""
        python = r / "python_embeded" / "python.exe"
        self.etat.emit("gguf", tr("installation de la bibliothèque gguf…"))
        res = subprocess.run([str(python), "-s", "-m", "pip", "install", "--disable-pip-version-check",
                              GGUF_PIP], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        _journal(f"pip {GGUF_PIP} : {res.returncode}\n{res.stdout[-1500:]}{res.stderr[-1500:]}")
        if res.returncode != 0:
            raise OSError(tr("l'installation de la bibliothèque gguf a échoué"))
        self.etat.emit("gguf", tr("prêt"))


class FenetreInstallation(QDialog):
    """Montre ce qui sera téléchargé (taille, source, licence), fait accepter la licence FLUX.1 [dev], installe."""
    installe = Signal(str)                       # dossier de ComfyUI, une fois tout installé

    def __init__(self, parent=None, dossier: str | None = None, schnell: bool = False, accepte: bool = False):
        super().__init__(parent)
        self.setWindowTitle(tr("Installer le moteur IA"))
        self.setMinimumSize(760, 600)
        self.pilote = version_pilote()
        self.travail: Installation | None = None
        lay = QVBoxLayout(self)

        intro = QLabel(tr("Chrypix utilise ComfyUI comme moteur IA, caché derrière ses boutons. Il n'est pas sur ce "
                          "PC : Chrypix peut l'installer, avec les extensions et les modèles d'IA dont il a besoin. "
                          "Tout est téléchargé depuis les sites officiels (GitHub, Hugging Face)."))
        intro.setWordWrap(True)
        lay.addWidget(intro)
        if self.pilote is None:
            avert = QLabel(tr("Attention : aucune carte graphique NVIDIA trouvée. Le moteur IA a besoin d'une carte "
                              "NVIDIA (8 Go de mémoire graphique conseillés)."))
            avert.setWordWrap(True)
            avert.setStyleSheet("color: #e8366f; font-weight: bold;")
            lay.addWidget(avert)

        ligne = QHBoxLayout()
        ligne.addWidget(QLabel(tr("Dossier :")))
        self.dossier = QLineEdit(dossier or str(DOSSIER_DEFAUT))
        self.dossier.textChanged.connect(self._actualiser)
        ligne.addWidget(self.dossier, 1)
        b = QPushButton(tr("Parcourir…"))
        b.clicked.connect(self._parcourir)
        ligne.addWidget(b)
        lay.addLayout(ligne)

        self.liste = QTreeWidget()
        self.liste.setHeaderLabels([tr("Élément"), tr("Taille"), tr("Licence"), tr("Source"), tr("État")])
        self.liste.setRootIsDecorated(False)
        lay.addWidget(self.liste, 1)

        self.c_schnell = QCheckBox(tr("Ajouter Flux Schnell ({taille}) pour « Upscale net » (facultatif ; "
                                      "l'upscale simple marche sans)", taille=go(taille_schnell())))
        self.c_schnell.setChecked(schnell)
        self.c_schnell.toggled.connect(self._actualiser)
        lay.addWidget(self.c_schnell)

        licence = QLabel(tr("Le modèle Flux Fill est sous licence <b>FLUX.1 [dev] non commerciale</b> : usage "
                            "personnel permis, pas d'usage commercial. <a href=\"{url}\">Lire la licence</a>. "
                            "Les autres éléments sont sous licences libres (GPL, Apache, BSD, LGPL).",
                            url=LICENCE_FLUX))
        licence.setWordWrap(True)
        licence.setTextFormat(Qt.RichText)
        licence.setOpenExternalLinks(True)
        lay.addWidget(licence)
        self.c_licence = QCheckBox(tr("J'accepte la licence FLUX.1 [dev] (usage non commercial)"))
        self.c_licence.setChecked(accepte)
        self.c_licence.toggled.connect(self._actualiser)
        lay.addWidget(self.c_licence)

        self.place = QLabel()
        lay.addWidget(self.place)
        self.barre = QProgressBar()
        self.barre.setRange(0, 1000)
        self.barre.setValue(0)
        lay.addWidget(self.barre)
        self.statut = QLabel(tr("Tu peux arrêter à tout moment : le téléchargement reprendra plus tard où il "
                                "s'est arrêté."))
        self.statut.setWordWrap(True)
        lay.addWidget(self.statut)

        boutons = QHBoxLayout()
        boutons.addStretch(1)
        self.b_lancer = QPushButton(tr("Télécharger et installer"))
        self.b_lancer.setDefault(True)
        self.b_lancer.clicked.connect(self.commencer)
        self.b_arreter = QPushButton(tr("Arrêter"))
        self.b_arreter.clicked.connect(self._arreter)
        self.b_arreter.setEnabled(False)
        self.b_fermer = QPushButton(tr("Fermer"))
        self.b_fermer.clicked.connect(self.close)
        for b in (self.b_lancer, self.b_arreter, self.b_fermer):
            boutons.addWidget(b)
        lay.addLayout(boutons)
        self._actualiser()

    # ------------------------------------------------------------------
    def elements(self) -> list[Element]:
        recent = self.pilote is None or self.pilote >= PILOTE_CUDA13
        return catalogue(recent, self.c_schnell.isChecked())

    def _parcourir(self):
        d = QFileDialog.getExistingDirectory(self, tr("Dossier du moteur IA"), self.dossier.text())
        if d:
            self.dossier.setText(str(Path(d)))

    def _libre(self) -> int | None:
        p = Path(self.dossier.text())
        while not p.exists() and p.parent != p:
            p = p.parent
        try:
            return shutil.disk_usage(p).free
        except OSError:
            return None

    def _actualiser(self):
        if self.travail is not None:
            return
        self.liste.clear()
        self._lignes = {}
        for e in self.elements():
            source = e.url.split("/")[2].replace("www.", "")
            taille = go(e.taille) if e.taille else tr("< 5 Mo")
            ligne = QTreeWidgetItem([e.nom, taille, e.licence, source, ""])
            ligne.setToolTip(0, e.url)
            ligne.setTextAlignment(1, Qt.AlignRight | Qt.AlignVCenter)
            self.liste.addTopLevelItem(ligne)
            self._lignes[e.cle] = ligne
        for i in range(5):
            self.liste.resizeColumnToContents(i)
        besoin = taille_restante(Path(self.dossier.text()), self.elements())
        libre = self._libre()
        assez = libre is None or libre > besoin + GO
        etranger = comfyui_etranger(Path(self.dossier.text()))
        permis = inscriptible(Path(self.dossier.text())) if self.dossier.text().strip() else True
        texte = tr("Place nécessaire : {besoin} ; libre sur ce disque : {libre}", besoin=go(besoin),
                   libre=go(libre) if libre is not None else "?")
        if not assez:
            texte += "  —  " + tr("pas assez de place, choisis un autre dossier")
        if not permis:
            texte = tr("Windows n'autorise pas l'écriture dans ce dossier (dossier protégé, comme Program Files) : "
                       "choisis un autre dossier.")
        if etranger:
            texte = tr("Ce dossier contient déjà un ComfyUI : choisis un dossier vide.")
        self.place.setText(texte)
        ok = assez and permis and not etranger
        self.place.setStyleSheet("" if ok else "color: #e8366f; font-weight: bold;")
        self.b_lancer.setEnabled(self.c_licence.isChecked() and ok
                                 and bool(self.dossier.text().strip()))

    def commencer(self):
        if not self.b_lancer.isEnabled():
            return
        self.travail = Installation(Path(self.dossier.text()), self.elements())
        self.travail.etat.connect(self._etat)
        self.travail.progres.connect(self._progres)
        self.travail.fini.connect(self._fini)
        for w in (self.b_lancer, self.dossier, self.c_schnell, self.c_licence):
            w.setEnabled(False)
        self.b_arreter.setEnabled(True)
        self.statut.setText(tr("Démarrage…"))
        self.travail.lancer()

    def _etat(self, cle: str, texte: str):
        if cle in self._lignes:
            self._lignes[cle].setText(4, texte)
            self.liste.scrollToItem(self._lignes[cle])

    def _progres(self, fait: float, total: float, vitesse: float):
        self.barre.setValue(int(1000 * fait / max(total, 1)))
        texte = tr("{fait} sur {total}", fait=go(fait), total=go(total))
        if vitesse > 0:
            reste = int((total - fait) / vitesse)
            heures, minutes = reste // 3600, (reste % 3600) // 60
            duree = tr("{h} h {min} min", h=heures, min=f"{minutes:02d}") if heures else \
                tr("{min} min", min=max(1, minutes))
            texte += "  —  " + tr("{vitesse}/s, encore environ {duree}", vitesse=go(vitesse), duree=duree)
        self.statut.setText(texte)

    def _arreter(self):
        if self.travail is not None:
            self.b_arreter.setEnabled(False)
            self.statut.setText(tr("Arrêt…"))
            self.travail.arret.set()

    def _fini(self, reussi: bool, message: str):
        self.b_arreter.setEnabled(False)
        self.statut.setText(message)
        dossier = racine(Path(self.dossier.text()))
        self.travail = None
        if reussi:
            self.barre.setValue(1000)
            self.b_lancer.setEnabled(False)
            self.installe.emit(str(dossier))
            QMessageBox.information(self, tr("Installer le moteur IA"), message)
        else:
            for w in (self.dossier, self.c_schnell, self.c_licence):
                w.setEnabled(True)
            self.b_lancer.setText(tr("Reprendre"))
            self._actualiser_bouton()

    def _actualiser_bouton(self):
        self.b_lancer.setEnabled(self.c_licence.isChecked())

    def closeEvent(self, ev):
        if self.travail is not None:
            if QMessageBox.question(self, tr("Installer le moteur IA"),
                                    tr("Arrêter l'installation ? Elle reprendra plus tard où elle s'est arrêtée.")) \
                    != QMessageBox.Yes:
                ev.ignore()
                return
            self.travail.arret.set()
        super().closeEvent(ev)


def main():
    import argparse
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("chrypox.Chrypix")
    a = argparse.ArgumentParser(description="Installe le moteur IA de Chrypix")
    a.add_argument("--dossier")
    a.add_argument("--schnell", action="store_true")
    a.add_argument("--accepte", action="store_true", help="licence FLUX.1 [dev] déjà acceptée (installateur)")
    a.add_argument("--demarrer", action="store_true", help="commencer tout de suite")
    args = a.parse_args()

    from PySide6.QtGui import QIcon
    from . import langue, theme
    from .__main__ import ICONE, traduire_qt
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(str(ICONE)))
    reglages = QSettings("Chrypix", os.environ.get("CHRYPIX_REGLAGES", "Chrypix"))
    traduire_qt(app, langue.choisir(reglages.value("langue", langue.AUTO)))
    theme.appliquer(app, reglages.value("theme", theme.AUTO))
    f = FenetreInstallation(dossier=args.dossier, schnell=args.schnell, accepte=args.accepte)
    f.show()
    if args.demarrer:
        f.commencer()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
