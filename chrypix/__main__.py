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


def main():
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
