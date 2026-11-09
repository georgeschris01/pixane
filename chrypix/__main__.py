"""Lancement : python -m chrypix [photo]"""
import sys
from pathlib import Path

from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from . import langue


ICONE = Path(__file__).parent / "ressources" / "chrypix.ico"


def traduire_qt(app: QApplication, langue: str) -> None:
    """Traduit les textes fournis par Qt (boutons Oui / Non / Annuler, menu clic droit, fenêtres standard)."""
    QLocale.setDefault(QLocale(langue))
    traducteur = QTranslator(app)
    if traducteur.load(f"qtbase_{langue}", QLibraryInfo.path(QLibraryInfo.TranslationsPath)):
        app.installTranslator(traducteur)


def signaler_erreurs() -> None:
    """Une erreur dans un menu ou un bouton ne doit pas passer inaperçue (avec pythonw, rien ne s'affiche) :
    elle est notée dans %LOCALAPPDATA%\\Chrypix\\erreurs.log et montrée à l'écran."""
    import os
    import traceback
    from datetime import datetime
    deja = set()

    def crochet(type_, valeur, tb):
        texte = "".join(traceback.format_exception(type_, valeur, tb))
        try:
            dossier = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Chrypix"
            dossier.mkdir(parents=True, exist_ok=True)
            with open(dossier / "erreurs.log", "a", encoding="utf-8") as f:
                f.write(f"--- {datetime.now():%d/%m/%Y %H:%M:%S}\n{texte}\n")
        except OSError:
            pass
        if sys.stderr is not None:
            sys.stderr.write(texte)
        cle = (type_.__name__, str(valeur))
        if cle in deja or QApplication.instance() is None:
            return
        deja.add(cle)
        from PySide6.QtWidgets import QMessageBox
        from .langue import tr
        QMessageBox.warning(None, "Chrypix", tr("Une erreur s'est produite : l'action n'a pas pu se faire.\n\n"
                                                "{erreur}\n\nDétails dans le fichier erreurs.log "
                                                "(%LOCALAPPDATA%\\Chrypix).", erreur=f"{type_.__name__} : {valeur}"))

    sys.excepthook = crochet


def main():
    signaler_erreurs()
    if sys.platform == "win32":
        # pour que la barre des tâches montre l'icône de Chrypix et non celle de Python
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("chrypox.Chrypix")
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(str(ICONE)))
    # la langue est choisie avant de créer les fenêtres (menu Affichage > Langue ; « auto » = langue de Windows)
    from .fenetre import NOM, Fenetre, reglages
    app.setApplicationName(NOM)
    traduire_qt(app, langue.choisir(reglages().value("langue", langue.AUTO)))
    fenetre = Fenetre()
    fenetre.show()
    if len(sys.argv) > 1:
        fenetre.charger(sys.argv[1])
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
