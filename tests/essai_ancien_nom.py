"""Ancien nom (Chrypix) : les réglages et le dossier %LOCALAPPDATA%
sont repris, les fichiers repères du moteur prennent le nouveau nom. Usage : essai_ancien_nom.py"""
import os
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from pixane import ancien_nom

erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


app = QApplication(sys.argv)

# 1. réglages et dossier de travail repris (noms d'essai, jamais les vrais)
base = Path(tempfile.mkdtemp())
os.environ["LOCALAPPDATA"] = str(base)
ancien_nom.ANCIEN, ancien_nom.NOUVEAU = "Chrypix-essai-migration", "Pixane-essai-migration"
for nom in (ancien_nom.ANCIEN, ancien_nom.NOUVEAU):
    QSettings(nom, nom).clear()
vieux = QSettings(ancien_nom.ANCIEN, ancien_nom.ANCIEN)
vieux.setValue("theme", "sombre")
vieux.setValue("moteur_dossier", str(base / ancien_nom.ANCIEN / "moteur"))
vieux.setValue("recents", ["C:/a.chr", "C:/b.jpg"])
vieux.sync()
(base / ancien_nom.ANCIEN / "recuperation").mkdir(parents=True)
(base / ancien_nom.ANCIEN / "erreurs.log").write_text("x")
del os.environ["PIXANE_REGLAGES"]
ancien_nom.migrer()
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
neuf_r = QSettings(ancien_nom.NOUVEAU, ancien_nom.NOUVEAU)
verifier(neuf_r.value("theme") == "sombre" and neuf_r.value("recents") == ["C:/a.chr", "C:/b.jpg"], "réglages recopiés")
verifier(neuf_r.value("moteur_dossier") == str(base / ancien_nom.NOUVEAU / "moteur"),
         f"chemin vers l'ancien dossier corrigé ({neuf_r.value('moteur_dossier')})")
verifier((base / ancien_nom.NOUVEAU / "erreurs.log").is_file() and not (base / ancien_nom.ANCIEN).exists(),
         "dossier %LOCALAPPDATA% renommé")
neuf_r.setValue("theme", "clair")
neuf_r.sync()
del os.environ["PIXANE_REGLAGES"]
ancien_nom.migrer()
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
verifier(QSettings(ancien_nom.NOUVEAU, ancien_nom.NOUVEAU).value("theme") == "clair",
         "deuxième démarrage : rien n'est recopié par-dessus")
for nom in (ancien_nom.ANCIEN, ancien_nom.NOUVEAU):     # clés d'essai retirées du registre
    QSettings(nom, nom).clear()
    QSettings(nom, nom).sync()
    import winreg
    for cle in (rf"Software\{nom}\{nom}", rf"Software\{nom}"):
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, cle)
        except OSError:
            pass

# 2. moteur installé par Chrypix : fichiers repères renommés, toujours reconnu comme « le nôtre »
from pixane import installation_moteur as im  # noqa: E402
m = base / "moteur"
(m / im.PORTABLE / "ComfyUI").mkdir(parents=True)
(m / im.PORTABLE / "ComfyUI" / "main.py").write_text("")
(m / im.PORTABLE / "chrypix.json").write_text('{"elements": []}')
(m / "chrypix-moteur.json").write_text("{}")
verifier(im.deja_installe(m) and not im.comfyui_etranger(m), "moteur de Chrypix reconnu")
verifier((m / im.PORTABLE / im.INFOS).is_file() and (m / im.MARQUE).is_file(), "repères renommés (pixane…)")

print("ERREURS :", erreurs if erreurs else "aucune")
sys.exit(1 if erreurs else 0)
