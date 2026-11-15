"""Arrêter un travail IA : un faux ComfyUI répond comme le vrai (corps vide à POST /queue et /interrupt) ;
Moteur.executer doit lever Annule, pas une erreur de lecture (JSONDecodeError, signalée le 15/11/2026).
Usage : python tests/essai_arret_moteur.py"""
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pixane.moteur import Annule, Moteur

recu = []


class FauxComfy(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _repondre(self, corps: bytes = b""):
        self.send_response(200)
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)

    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        recu.append(self.path)
        if self.path == "/prompt":
            self._repondre(json.dumps({"prompt_id": "essai"}).encode())
        else:                                   # /queue, /interrupt : corps vide, comme ComfyUI
            self._repondre()

    def do_GET(self):
        recu.append(self.path)
        self._repondre(b"{}")                   # /history/essai : pas encore fini


serveur = ThreadingHTTPServer(("127.0.0.1", 0), FauxComfy)
threading.Thread(target=serveur.serve_forever, daemon=True).start()
m = Moteur()
m.url = f"http://127.0.0.1:{serveur.server_address[1]}"
annuler = threading.Event()
threading.Timer(0.5, annuler.set).start()

erreurs = []
try:
    m.executer({}, {}, annuler)
    erreurs.append("executer a fini sans être arrêté")
except Annule:
    print("ok  arrêt : Annule, pas d'erreur")
except Exception as e:
    erreurs.append(f"arrêt : {type(e).__name__} : {e}")
for chemin in ("/queue", "/interrupt"):
    if chemin in recu:
        print(f"ok  {chemin} envoyé au moteur")
    else:
        erreurs.append(f"{chemin} pas envoyé")
serveur.shutdown()
print("ERREURS :", erreurs if erreurs else "aucune")
sys.exit(1 if erreurs else 0)
