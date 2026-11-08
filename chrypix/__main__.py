"""Lancement : python -m chrypix [photo]"""
import sys

from PySide6.QtWidgets import QApplication

from .fenetre import NOM, Fenetre


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(NOM)
    fenetre = Fenetre()
    fenetre.show()
    if len(sys.argv) > 1:
        fenetre.charger(sys.argv[1])
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
