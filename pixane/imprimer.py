"""Fichier > Imprimer : choix de l'imprimante, du papier, de la taille de l'image sur la feuille, avec un aperçu
de la page. L'image imprimée est l'image visible (tous les calques).

Tailles : « Remplir la page » (dans les marges, proportions gardées), « Taille réelle » (d'après la résolution de
l'image, en points par pouce), ou une largeur choisie en centimètres.
"""
from __future__ import annotations

import os

from PySide6.QtCore import QMarginsF, QRectF, QSettings, QSizeF, Qt
from PySide6.QtGui import QColor, QImage, QPageLayout, QPageSize, QPainter, QPen, QPixmap
from PySide6.QtPrintSupport import QPrinter, QPrinterInfo
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QHBoxLayout,
                               QLabel, QSpinBox, QVBoxLayout)

from .langue import langue, tr


def _nb(x: float) -> str:
    """Nombre à une décimale, avec la virgule en français."""
    s = f"{x:.1f}"
    return s if langue() == "en" else s.replace(".", ",")

PAPIERS = [("A4", QPageSize.A4), ("A5", QPageSize.A5), ("A3", QPageSize.A3), ("Letter", QPageSize.Letter),
           ("10 × 15 cm", (100, 150)), ("13 × 18 cm", (130, 180)), ("20 × 30 cm", (200, 300))]
TAILLES = ("remplir", "reelle", "largeur")


def _reglages() -> QSettings:
    return QSettings("Pixane", os.environ.get("PIXANE_REGLAGES", "Pixane"))


def taille_page(papier: int, paysage: bool) -> QSizeF:
    """Taille de la feuille en mm."""
    _n, p = PAPIERS[papier]
    s = QPageSize(QSizeF(*p), QPageSize.Millimeter) if isinstance(p, tuple) else QPageSize(p)
    t = s.size(QPageSize.Millimeter)
    return QSizeF(t.height(), t.width()) if paysage else t


def place_image(page: QSizeF, marge: float, img_w: int, img_h: int, mode: str, dpi: float,
                largeur_cm: float) -> QRectF:
    """Rectangle de l'image sur la feuille, en mm, centré."""
    zone_w, zone_h = page.width() - 2 * marge, page.height() - 2 * marge
    if mode == "reelle":
        w, h = img_w / max(1.0, dpi) * 25.4, img_h / max(1.0, dpi) * 25.4
    elif mode == "largeur":
        w = largeur_cm * 10
        h = w * img_h / img_w
    else:
        k = min(zone_w / img_w, zone_h / img_h)
        w, h = img_w * k, img_h * k
    return QRectF((page.width() - w) / 2, (page.height() - h) / 2, w, h)


def imprimer_sur(printer: QPrinter, image: QImage, place_mm: QRectF) -> None:
    """Dessine l'image sur le périphérique (feuille entière, coordonnées en mm)."""
    p = QPainter(printer)
    r = printer.pageLayout().fullRectPixels(printer.resolution())
    k = r.width() / printer.pageLayout().fullRect(QPageLayout.Millimeter).width()
    cible = QRectF(place_mm.x() * k, place_mm.y() * k, place_mm.width() * k, place_mm.height() * k)
    # sans le décalage des marges non imprimables (feuille entière)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    p.drawImage(cible, image)
    p.end()


class DialogueImprimer(QDialog):
    APERCU = 300

    def __init__(self, image: QImage, dpi: float, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Imprimer"))
        self.image = image
        self.dpi = dpi or 72.0
        r = _reglages()
        lay = QHBoxLayout(self)
        gauche = QVBoxLayout()
        form = QFormLayout()
        self.imprimante = QComboBox()
        noms = QPrinterInfo.availablePrinterNames()
        self.imprimante.addItems(noms)
        dernier = r.value("imprimer_imprimante", "") or QPrinterInfo.defaultPrinterName()
        if dernier in noms:
            self.imprimante.setCurrentText(dernier)
        form.addRow(tr("Imprimante"), self.imprimante)
        self.papier = QComboBox()
        for n, _p in PAPIERS:
            self.papier.addItem(n)
        self.papier.setCurrentIndex(min(len(PAPIERS) - 1, int(r.value("imprimer_papier", 0) or 0)))
        form.addRow(tr("Papier"), self.papier)
        self.sens = QComboBox()
        self.sens.addItem(tr("Automatique (comme l'image)"), "auto")
        self.sens.addItem(tr("Portrait"), "portrait")
        self.sens.addItem(tr("Paysage"), "paysage")
        form.addRow(tr("Orientation"), self.sens)
        self.mode = QComboBox()
        self.mode.addItem(tr("Remplir la page (dans les marges)"), "remplir")
        cm_w = image.width() / self.dpi * 2.54
        cm_h = image.height() / self.dpi * 2.54
        self.mode.addItem(tr("Taille réelle ({l} × {h} cm à {dpi} dpi)", l=_nb(cm_w), h=_nb(cm_h),
                             dpi=round(self.dpi)), "reelle")
        self.mode.addItem(tr("Largeur choisie"), "largeur")
        self.mode.setCurrentIndex(max(0, self.mode.findData(r.value("imprimer_mode", "remplir"))))
        form.addRow(tr("Taille"), self.mode)
        self.largeur = QDoubleSpinBox()
        self.largeur.setRange(1, 200)
        self.largeur.setDecimals(1)
        self.largeur.setSuffix(" cm")
        self.largeur.setValue(float(r.value("imprimer_largeur", 15) or 15))
        form.addRow(tr("Largeur"), self.largeur)
        self.marge = QSpinBox()
        self.marge.setRange(0, 50)
        self.marge.setSuffix(" mm")
        self.marge.setValue(int(r.value("imprimer_marge", 10) or 10))
        form.addRow(tr("Marges"), self.marge)
        self.copies = QSpinBox()
        self.copies.setRange(1, 99)
        form.addRow(tr("Copies"), self.copies)
        gauche.addLayout(form)
        self.info = QLabel()
        self.info.setWordWrap(True)
        self.info.setObjectName("discret")
        gauche.addWidget(self.info)
        gauche.addStretch(1)
        boutons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        boutons.button(QDialogButtonBox.Ok).setText(tr("Imprimer"))
        boutons.button(QDialogButtonBox.Cancel).setText(tr("Annuler"))
        boutons.accepted.connect(self.accept)
        boutons.rejected.connect(self.reject)
        gauche.addWidget(boutons)
        lay.addLayout(gauche)
        self.apercu = QLabel()
        self.apercu.setFixedSize(self.APERCU, self.APERCU)
        self.apercu.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.apercu)
        for w in (self.papier, self.sens, self.mode):
            w.currentIndexChanged.connect(lambda _i: self._maj())
        for w in (self.largeur, self.marge):
            w.valueChanged.connect(lambda _v: self._maj())
        self._maj()

    # -------------------------------------------------- calculs
    def paysage(self) -> bool:
        s = self.sens.currentData()
        if s == "auto":
            return self.image.width() > self.image.height()
        return s == "paysage"

    def page(self) -> QSizeF:
        return taille_page(self.papier.currentIndex(), self.paysage())

    def place(self) -> QRectF:
        return place_image(self.page(), self.marge.value(), self.image.width(), self.image.height(),
                           self.mode.currentData(), self.dpi, self.largeur.value())

    def _maj(self):
        self.largeur.setEnabled(self.mode.currentData() == "largeur")
        page, place = self.page(), self.place()
        dpi_reel = self.image.width() / (place.width() / 25.4) if place.width() > 0 else 0
        texte = tr("Sur la feuille : {l} × {h} cm, soit {dpi} points par pouce.", l=_nb(place.width() / 10),
                   h=_nb(place.height() / 10), dpi=round(dpi_reel))
        if dpi_reel < 150:
            texte += " " + tr("Moins de 150 : l'impression risque d'être floue (IA > Upscale peut aider).")
        if place.left() < -0.5 or place.top() < -0.5:
            texte += " " + tr("L'image dépasse de la feuille : elle sera coupée.")
        self.info.setText(texte)
        # aperçu : la feuille, ses marges, l'image
        k = (self.APERCU - 20) / max(page.width(), page.height())
        pm = QPixmap(self.APERCU, self.APERCU)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        fw, fh = page.width() * k, page.height() * k
        ox, oy = (self.APERCU - fw) / 2, (self.APERCU - fh) / 2
        p.fillRect(QRectF(ox + 3, oy + 3, fw, fh), QColor(0, 0, 0, 60))
        p.fillRect(QRectF(ox, oy, fw, fh), Qt.white)
        p.setClipRect(QRectF(ox, oy, fw, fh))
        p.drawImage(QRectF(ox + place.x() * k, oy + place.y() * k, place.width() * k, place.height() * k),
                    self.image)
        m = self.marge.value() * k
        if m > 0:
            p.setPen(QPen(QColor(120, 160, 255), 1, Qt.DashLine))
            p.drawRect(QRectF(ox + m, oy + m, fw - 2 * m, fh - 2 * m))
        p.end()
        self.apercu.setPixmap(pm)

    def imprimante_qt(self, fichier_pdf: str | None = None) -> QPrinter:
        """QPrinter réglé d'après la fenêtre ; fichier_pdf : impression dans un PDF (essais)."""
        pr = QPrinter(QPrinter.HighResolution)
        if fichier_pdf:
            pr.setOutputFormat(QPrinter.PdfFormat)
            pr.setOutputFileName(fichier_pdf)
        else:
            pr.setPrinterName(self.imprimante.currentText())
        _n, papier = PAPIERS[self.papier.currentIndex()]
        taille = QPageSize(QSizeF(*papier), QPageSize.Millimeter) if isinstance(papier, tuple) else QPageSize(papier)
        pr.setPageLayout(QPageLayout(taille, QPageLayout.Landscape if self.paysage() else QPageLayout.Portrait,
                                     QMarginsF(0, 0, 0, 0)))
        pr.setFullPage(True)
        pr.setCopyCount(self.copies.value())
        pr.setDocName("Pixane")
        return pr

    def imprimer(self, fichier_pdf: str | None = None) -> None:
        r = _reglages()
        for cle, v in (("imprimer_imprimante", self.imprimante.currentText()),
                       ("imprimer_papier", self.papier.currentIndex()), ("imprimer_mode", self.mode.currentData()),
                       ("imprimer_largeur", self.largeur.value()), ("imprimer_marge", self.marge.value())):
            r.setValue(cle, v)
        imprimer_sur(self.imprimante_qt(fichier_pdf), self.image, self.place())
