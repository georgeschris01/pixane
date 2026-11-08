"""Moteur IA : ComfyUI lancé en arrière-plan, sans fenêtre.

Le programme cherche d'abord un ComfyUI déjà ouvert (port 8188, celui de Comfy Desktop).
Sinon, il lance le ComfyUI installé sur le PC sur le port 8189 et l'arrête à la fermeture.
"""
from __future__ import annotations

import glob
import io
import json
import os
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

DOSSIER_APP = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "RetoucheIA"
FICHIER_CONFIG = DOSSIER_APP / "config.json"
PORT_EXTERNE = 8188   # ComfyUI Desktop, s'il est ouvert
PORT_INTERNE = 8189   # notre moteur caché

NOEUDS_NECESSAIRES = ["InpaintCropImproved", "INPAINT_InpaintWithModel", "UltimateSDUpscale"]


class ErreurMoteur(Exception):
    pass


class Annule(Exception):
    pass


def lire_config() -> dict:
    try:
        return json.loads(FICHIER_CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def trouver_comfyui() -> dict | None:
    """Renvoie {dir, python, chemins_modeles} ou None si ComfyUI n'est pas installé."""
    conf = lire_config()
    candidats = []
    if conf.get("comfyui_dir"):
        candidats.append(Path(conf["comfyui_dir"]))
    candidats.append(Path(r"D:\ComfyUI\ComfyUI\ComfyUI"))
    for d in candidats:
        python = d / ".venv" / "Scripts" / "python.exe"
        if (d / "main.py").is_file() and python.is_file():
            chemins = conf.get("extra_model_paths")
            if not chemins:
                yamls = glob.glob(os.path.join(os.environ.get("APPDATA", ""), "Comfy Desktop",
                                               "instance-model-paths", "*.yaml"))
                yamls.sort(key=os.path.getmtime, reverse=True)
                chemins = yamls[0] if yamls else None
            return {"dir": d, "python": python, "chemins_modeles": chemins}
    return None


def _multipart(champs: dict, fichiers: dict) -> tuple[bytes, str]:
    limite = uuid.uuid4().hex
    corps = io.BytesIO()
    for nom, valeur in champs.items():
        corps.write(f'--{limite}\r\nContent-Disposition: form-data; name="{nom}"\r\n\r\n{valeur}\r\n'.encode())
    for nom, (fichier, donnees, mime) in fichiers.items():
        corps.write(f'--{limite}\r\nContent-Disposition: form-data; name="{nom}"; filename="{fichier}"\r\n'
                    f'Content-Type: {mime}\r\n\r\n'.encode())
        corps.write(donnees)
        corps.write(b"\r\n")
    corps.write(f"--{limite}--\r\n".encode())
    return corps.getvalue(), f"multipart/form-data; boundary={limite}"


class Moteur:
    def __init__(self):
        self.url: str | None = None
        self.processus: subprocess.Popen | None = None
        self.etat = "arrêté"
        self.client_id = uuid.uuid4().hex
        self._verrou = threading.Lock()
        self._arret = threading.Event()   # le programme se ferme

    # ------------------------------------------------------------------ réseau
    def _requete(self, chemin: str, donnees: bytes | None = None, type_contenu: str = "application/json",
                 delai: float = 30) -> bytes:
        req = urllib.request.Request(self.url + chemin, data=donnees,
                                     headers={"Content-Type": type_contenu} if donnees is not None else {})
        with urllib.request.urlopen(req, timeout=delai) as r:
            return r.read()

    def _json(self, chemin: str, objet=None, delai: float = 30):
        donnees = json.dumps(objet).encode() if objet is not None else None
        return json.loads(self._requete(chemin, donnees, delai=delai))

    @staticmethod
    def _repond(url: str) -> bool:
        try:
            with urllib.request.urlopen(url + "/system_stats", timeout=2) as r:
                return r.status == 200
        except (OSError, urllib.error.URLError):
            return False

    # ------------------------------------------------------------ démarrage
    def demarrer(self, signaler=lambda texte: None) -> None:
        """Bloquant (à appeler dans un fil secondaire)."""
        for port in (PORT_EXTERNE, PORT_INTERNE):
            url = f"http://127.0.0.1:{port}"
            if self._repond(url):
                self.url = url
                self._verifier_noeuds()
                self.etat = "prêt"
                signaler("prêt (ComfyUI déjà ouvert)" if port == PORT_EXTERNE else "prêt")
                return

        install = trouver_comfyui()
        if install is None:
            self.etat = "introuvable"
            raise ErreurMoteur("ComfyUI n'est pas installé sur ce PC (ou pas à l'endroit attendu).")

        if self._arret.is_set():
            return
        signaler("démarrage…")
        DOSSIER_APP.mkdir(parents=True, exist_ok=True)
        journal = open(DOSSIER_APP / "moteur.log", "w", encoding="utf-8", errors="replace")
        commande = [str(install["python"]), "main.py", "--listen", "127.0.0.1", "--port", str(PORT_INTERNE),
                    "--disable-auto-launch"]
        if install["chemins_modeles"]:
            commande += ["--extra-model-paths-config", install["chemins_modeles"]]
        self.processus = subprocess.Popen(commande, cwd=install["dir"], stdout=journal, stderr=subprocess.STDOUT,
                                          stdin=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
        self.url = f"http://127.0.0.1:{PORT_INTERNE}"
        debut = time.time()
        while time.time() - debut < 240:
            if self._arret.is_set():
                self.arreter()
                return
            if self.processus.poll() is not None:
                self.etat = "erreur"
                raise ErreurMoteur(f"Le moteur s'est arrêté au démarrage. Détails : {DOSSIER_APP / 'moteur.log'}")
            if self._repond(self.url):
                self._verifier_noeuds()
                self.etat = "prêt"
                signaler("prêt")
                return
            time.sleep(1)
        self.etat = "erreur"
        raise ErreurMoteur("Le moteur ne répond pas après 4 minutes.")

    def _verifier_noeuds(self):
        infos = self._json("/object_info", delai=60)
        manquants = [n for n in NOEUDS_NECESSAIRES if n not in infos]
        if manquants:
            self.etat = "incomplet"
            raise ErreurMoteur("Extensions ComfyUI manquantes : " + ", ".join(manquants))

    def arreter(self):
        self._arret.set()
        if self.processus and self.processus.poll() is None:
            self.processus.terminate()
            try:
                self.processus.wait(10)
            except subprocess.TimeoutExpired:
                self.processus.kill()
        self.processus = None
        self.etat = "arrêté"

    # ------------------------------------------------------------ travail
    def envoyer_image(self, png: bytes) -> str:
        nom = f"{uuid.uuid4().hex}.png"
        corps, type_contenu = _multipart({"subfolder": "retouche-ia", "type": "input", "overwrite": "true"},
                                         {"image": (nom, png, "image/png")})
        rep = json.loads(self._requete("/upload/image", corps, type_contenu, delai=120))
        return f"{rep['subfolder']}/{rep['name']}" if rep.get("subfolder") else rep["name"]

    def executer(self, prompt: dict, sorties: dict[str, str], annuler: threading.Event,
                 progres=lambda secondes: None) -> list[tuple[str, bytes]]:
        """Lance une recette et renvoie [(libellé, png), ...] dans l'ordre de `sorties`."""
        with self._verrou:
            try:
                rep = self._json("/prompt", {"prompt": prompt, "client_id": self.client_id})
            except urllib.error.HTTPError as e:
                raise ErreurMoteur("ComfyUI refuse la recette : " + e.read().decode(errors="replace")[:800])
            pid = rep["prompt_id"]
            debut = time.time()
            while True:
                if annuler.is_set():
                    try:
                        self._json("/queue", {"delete": [pid]})
                        self._requete("/interrupt", b"{}")
                    except OSError:
                        pass
                    raise Annule()
                histo = self._json(f"/history/{pid}")
                if pid in histo:
                    break
                progres(int(time.time() - debut))
                time.sleep(1)
            entree = histo[pid]
            statut = entree.get("status", {})
            if statut.get("status_str") != "success":
                messages = [m for m in statut.get("messages", []) if m[0] == "execution_error"]
                detail = messages[0][1].get("exception_message", "") if messages else ""
                raise ErreurMoteur("Erreur pendant le calcul. " + detail.strip()[:600])
            resultats = []
            for noeud, libelle in sorties.items():
                images = entree["outputs"].get(noeud, {}).get("images", [])
                for i, im in enumerate(images):
                    params = urllib.parse.urlencode({"filename": im["filename"], "subfolder": im["subfolder"],
                                                     "type": im["type"]})
                    donnees = self._requete(f"/view?{params}", delai=120)
                    resultats.append((f"{libelle} {i + 1}" if len(images) > 1 else libelle, donnees))
            return resultats
