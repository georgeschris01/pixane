"""Lancement : python -m chrypix [photo]"""
import sys
from pathlib import Path

from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from .fenetre import NOM, Fenetre


ICONE = Path(__file__).parent / "ressources" / "chrypix.ico"
LANGUE = "fr"   # Chrypix n'existe qu'en français pour l'instant (version anglaise prévue)


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
    app.setApplicationName(NOM)
    app.setWindowIcon(QIcon(str(ICONE)))
    traduire_qt(app, LANGUE)
    fenetre = Fenetre()
    fenetre.show()
    if len(sys.argv) > 1:
        fenetre.charger(sys.argv[1])
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
