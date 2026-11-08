"""Lancement : python -m chrypix [photo]"""
import sys

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from .fenetre import NOM, Fenetre


def theme_sombre(app: QApplication):
    app.setStyle("Fusion")
    p = QPalette()
    for role, couleur in ((QPalette.Window, "#353535"), (QPalette.WindowText, "#e0e0e0"),
                          (QPalette.Base, "#2a2a2a"), (QPalette.AlternateBase, "#353535"),
                          (QPalette.Text, "#e0e0e0"), (QPalette.Button, "#454545"),
                          (QPalette.ButtonText, "#e0e0e0"), (QPalette.Highlight, "#2f6fd0"),
                          (QPalette.HighlightedText, "#ffffff"), (QPalette.ToolTipBase, "#202020"),
                          (QPalette.ToolTipText, "#e0e0e0")):
        p.setColor(role, QColor(couleur))
    p.setColor(QPalette.Disabled, QPalette.ButtonText, QColor("#808080"))
    p.setColor(QPalette.Disabled, QPalette.WindowText, QColor("#808080"))
    app.setPalette(p)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(NOM)
    theme_sombre(app)
    fenetre = Fenetre()
    fenetre.show()
    if len(sys.argv) > 1:
        fenetre.charger(sys.argv[1])
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
