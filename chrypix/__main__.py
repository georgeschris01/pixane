"""Lancement : python -m chrypix [photo]"""
import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from .fenetre import NOM, Fenetre


ICONE = Path(__file__).parent / "ressources" / "chrypix.ico"


def main():
    if sys.platform == "win32":
        # pour que la barre des tâches montre l'icône de Chrypix et non celle de Python
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("chrypox.Chrypix")
    app = QApplication(sys.argv)
    app.setApplicationName(NOM)
    app.setWindowIcon(QIcon(str(ICONE)))
    fenetre = Fenetre()
    fenetre.show()
    if len(sys.argv) > 1:
        fenetre.charger(sys.argv[1])
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
