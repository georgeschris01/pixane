"""Fenêtre « Style du calque » : liste des effets (plusieurs du même type possibles), réglages de l'effet choisi,
styles tout prêts (vignettes calculées sur le calque lui-même), styles enregistrés, aperçu en direct sur la photo.

La fenêtre n'est pas modale : la photo reste visible et, pour l'ombre au sol, sa poignée se tire sur la photo. Le
reste de Pixane est bloqué tant qu'elle est ouverte (seuls la photo, le zoom et la poignée répondent).
"""
from __future__ import annotations

import json
import math
from dataclasses import replace

import numpy as np
from PySide6.QtCore import QEvent, QObject, QPointF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (QApplication, QCheckBox, QColorDialog, QComboBox, QDial, QDialog, QFormLayout,
                               QHBoxLayout, QInputDialog, QLabel, QListWidget, QListWidgetItem, QMenu,
                               QMessageBox, QPushButton, QScrollArea, QSlider, QSpinBox, QDoubleSpinBox,
                               QToolButton, QVBoxLayout, QWidget)

from .langue import tr
from .styles import REGLAGES, TYPES, Effet, Style, bout_ombre_sol, nom_effet, rendre_style, styles_prets

VIGNETTE = QSize(92, 64)


def styles_perso(reglages) -> list[tuple[str, Style]]:
    try:
        liste = json.loads(reglages.value("styles_perso", "[]"))
        return [(d["nom"], Style.depuis_dict(d["style"])) for d in liste]
    except (ValueError, TypeError, KeyError):
        return []


def enregistrer_styles_perso(reglages, liste) -> None:
    reglages.setValue("styles_perso", json.dumps([{"nom": n, "style": s.vers_dict()} for n, s in liste],
                                                 ensure_ascii=False))


# ------------------------------------------------------------------ petits champs de réglage
class Curseur(QWidget):
    """Curseur + case chiffrée, liés."""
    change = Signal(float)

    def __init__(self, mini, maxi, valeur, suffixe="", decimales=False):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.k = 10 if decimales else 1
        self.curseur = QSlider(Qt.Horizontal)
        self.curseur.setRange(int(mini * self.k), int(maxi * self.k))
        self.case = QDoubleSpinBox() if decimales else QSpinBox()
        if decimales:
            self.case.setDecimals(1)
            self.case.setSingleStep(0.5)
        self.case.setRange(mini, maxi)
        self.case.setSuffix(suffixe)
        self.case.setFixedWidth(78)
        self.curseur.setValue(int(round(valeur * self.k)))
        self.case.setValue(valeur)
        self.curseur.valueChanged.connect(lambda v: self.case.setValue(v / self.k))
        self.case.valueChanged.connect(self._case)
        lay.addWidget(self.curseur, 1)
        lay.addWidget(self.case)

    def _case(self, v):
        self.curseur.blockSignals(True)
        self.curseur.setValue(int(round(v * self.k)))
        self.curseur.blockSignals(False)
        self.change.emit(float(v))


class ChampAngle(QWidget):
    change = Signal(float)

    def __init__(self, valeur):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.cadran = QDial()
        self.cadran.setRange(0, 359)
        self.cadran.setWrapping(True)
        self.cadran.setFixedSize(46, 46)
        self.case = QSpinBox()
        self.case.setRange(-180, 180)
        self.case.setSuffix(" °")
        self.case.setWrapping(True)
        self.case.setFixedWidth(78)
        self._mettre(valeur)
        # QDial : 0 en bas, sens horaire ; nos angles : 0 à droite, sens inverse
        self.cadran.valueChanged.connect(lambda v: self.case.setValue(((270 - v) + 180) % 360 - 180))
        self.case.valueChanged.connect(self._case)
        lay.addWidget(self.cadran)
        lay.addWidget(self.case)
        lay.addStretch(1)

    def _mettre(self, a):
        self.case.blockSignals(True)
        self.case.setValue(int(round(a)))
        self.case.blockSignals(False)
        self.cadran.blockSignals(True)
        self.cadran.setValue(int(round(270 - a)) % 360)
        self.cadran.blockSignals(False)

    def _case(self, v):
        self._mettre(v)
        self.change.emit(float(v))


class ChampCouleur(QPushButton):
    change = Signal(str)

    def __init__(self, valeur: str):
        super().__init__()
        self.setFixedSize(78, 26)
        self.valeur = valeur
        self._peindre()
        self.clicked.connect(self._choisir)

    def _peindre(self):
        pm = QPixmap(64, 16)
        pm.fill(QColor(self.valeur))
        self.setIcon(QIcon(pm))
        self.setIconSize(QSize(64, 16))
        self.setToolTip(self.valeur)

    def _choisir(self):
        c = QColorDialog.getColor(QColor(self.valeur), self.window(), tr("Couleur"))
        if c.isValid():
            self.valeur = c.name()
            self._peindre()
            self.change.emit(self.valeur)


# ------------------------------------------------------------------ blocage du reste de Pixane
class Bloqueur(QObject):
    """Pendant la fenêtre de style : clics et raccourcis de la fenêtre principale ignorés, sauf sur la photo."""

    def __init__(self, fenetre, canevas):
        super().__init__()
        self.f, self.c = fenetre, canevas

    def eventFilter(self, obj, ev):
        t = ev.type()
        if t in (QEvent.MouseButtonPress, QEvent.MouseButtonDblClick, QEvent.KeyPress, QEvent.Shortcut,
                 QEvent.ShortcutOverride, QEvent.Drop, QEvent.DragEnter):
            if isinstance(obj, QWidget) and obj.window() is self.f and obj is not self.c:
                return True
            if obj is self.c and t in (QEvent.KeyPress, QEvent.ShortcutOverride, QEvent.Shortcut):
                return True
        return False


# ------------------------------------------------------------------ la fenêtre
class DialogueStyle(QDialog):
    fini = Signal()

    def __init__(self, fenetre, index: int):
        super().__init__(fenetre)
        self.f = fenetre
        self.doc = fenetre.doc
        self.index = index
        self.setWindowTitle(tr("Style du calque — {nom}", nom=self.doc.calques[index].nom))
        self.setModal(False)
        self.avant = self.doc.etat()
        self.modifie_avant = self.doc.modifie
        c = self.doc.calques[index]
        self.style: Style = c.style if c.style is not None else Style()
        self.angle_depart = self.style.angle_global()
        self._attente = QTimer(self, singleShot=True, interval=40)
        self._attente.timeout.connect(self._apercu)
        self._fini = False

        lay = QVBoxLayout(self)
        # styles tout prêts + styles enregistrés
        haut = QHBoxLayout()
        haut.addWidget(QLabel(tr("Styles tout prêts (un clic pour essayer) :")))
        haut.addStretch(1)
        b = QPushButton(tr("Enregistrer ce style…"))
        b.clicked.connect(self._enregistrer_style)
        haut.addWidget(b)
        lay.addLayout(haut)
        self.galerie = QListWidget()
        self.galerie.setViewMode(QListWidget.IconMode)
        self.galerie.setFlow(QListWidget.LeftToRight)
        self.galerie.setWrapping(False)
        self.galerie.setIconSize(VIGNETTE)
        self.galerie.setGridSize(QSize(VIGNETTE.width() + 14, VIGNETTE.height() + 34))
        self.galerie.setFixedHeight(VIGNETTE.height() + 54)
        self.galerie.setMovement(QListWidget.Static)
        self.galerie.setHorizontalScrollMode(QListWidget.ScrollPerPixel)
        self.galerie.itemClicked.connect(self._style_pret)
        self.galerie.setContextMenuPolicy(Qt.CustomContextMenu)
        self.galerie.customContextMenuRequested.connect(self._menu_galerie)
        lay.addWidget(self.galerie)

        milieu = QHBoxLayout()
        gauche = QVBoxLayout()
        gauche.addWidget(QLabel(tr("Effets du calque :")))
        self.liste = QListWidget()
        self.liste.setFixedWidth(230)
        self.liste.currentRowChanged.connect(self._effet_choisi)
        self.liste.itemChanged.connect(self._case_effet)
        gauche.addWidget(self.liste, 1)
        boutons = QHBoxLayout()
        self.b_ajouter = QToolButton()
        self.b_ajouter.setText(tr("Ajouter"))
        self.b_ajouter.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(self.b_ajouter)
        for t in TYPES:
            menu.addAction(nom_effet(t), lambda *_, t=t: self._ajouter(t))
        self.b_ajouter.setMenu(menu)
        boutons.addWidget(self.b_ajouter)
        for texte, aide, fonction in (("⧉", tr("Dupliquer l'effet (ex. deux contours)"), self._dupliquer),
                                      ("▲", tr("Monter l'effet"), lambda: self._deplacer(-1)),
                                      ("▼", tr("Descendre l'effet"), lambda: self._deplacer(1)),
                                      ("✕", tr("Supprimer l'effet"), self._supprimer)):
            bt = QToolButton()
            bt.setText(texte)
            bt.setToolTip(aide)
            bt.clicked.connect(fonction)
            boutons.addWidget(bt)
        boutons.addStretch(1)
        gauche.addLayout(boutons)
        rem = QHBoxLayout()
        rem.addWidget(QLabel(tr("Remplissage")))
        self.remplissage = Curseur(0, 100, round(self.style.remplissage * 100), " %")
        self.remplissage.setToolTip(tr("Opacité du contenu seul : les effets restent. À 0 %, il ne reste que "
                                       "le contour, l'ombre ou la lueur."))
        self.remplissage.change.connect(self._remplissage)
        rem.addWidget(self.remplissage, 1)
        gauche.addLayout(rem)
        milieu.addLayout(gauche)

        droite = QVBoxLayout()
        self.titre_effet = QLabel()
        self.titre_effet.setStyleSheet("font-weight: bold")
        droite.addWidget(self.titre_effet)
        self.zone = QScrollArea()
        self.zone.setWidgetResizable(True)
        self.zone.setMinimumWidth(400)
        droite.addWidget(self.zone, 1)
        self.aide_sol = QLabel(tr("Astuce : tire le point rond sur la photo pour placer le bout de l'ombre."))
        self.aide_sol.setWordWrap(True)
        self.aide_sol.setObjectName("discret")
        droite.addWidget(self.aide_sol)
        milieu.addLayout(droite, 1)
        lay.addLayout(milieu, 1)

        bas = QHBoxLayout()
        b = QPushButton(tr("Tout enlever"))
        b.setToolTip(tr("Enlève tous les effets de ce calque"))
        b.clicked.connect(lambda: self._mettre_style(Style()))
        bas.addWidget(b)
        bas.addStretch(1)
        b_annuler = QPushButton(tr("Annuler"))
        b_annuler.clicked.connect(self.reject)
        b_ok = QPushButton(tr("OK"))
        b_ok.setDefault(True)
        b_ok.clicked.connect(self.accept)
        bas.addWidget(b_annuler)
        bas.addWidget(b_ok)
        lay.addLayout(bas)
        self.resize(760, 600)

        self._remplir_galerie()
        self._remplir_liste(0)
        self.bloqueur = Bloqueur(fenetre, fenetre.canevas)
        QApplication.instance().installEventFilter(self.bloqueur)
        fenetre.canevas.poignee_sol_bouge.connect(self._poignee_bouge)

    # ---------------------------------------------------------- galerie
    def _contenu(self):
        """Pixels du calque autour de son contenu (pour les vignettes), ou un « Aa » si le calque est vide."""
        from .document import FORMAT_IMAGE, tableau
        img = self.doc.calques[self.index].image
        a = tableau(img.convertToFormat(FORMAT_IMAGE))[:, :, 3]
        ys, xs = np.nonzero(a)
        if len(ys):
            from PySide6.QtCore import QRect
            r = QRect(int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1))
            return img.copy(r)
        im = QImage(200, 120, QImage.Format_ARGB32_Premultiplied)
        im.fill(0)
        p = QPainter(im)
        f = p.font()
        f.setPointSize(60)
        f.setBold(True)
        p.setFont(f)
        p.setPen(QColor("#3b82f6"))
        p.drawText(im.rect(), Qt.AlignCenter, "Aa")
        p.end()
        return im

    def _vignette(self, contenu: QImage, style: Style) -> QIcon:
        cible_w, cible_h = VIGNETTE.width() - 24, VIGNETTE.height() - 22
        k = min(cible_w / contenu.width(), cible_h / contenu.height(), 1.0)
        petit = contenu.scaled(max(1, round(contenu.width() * k)), max(1, round(contenu.height() * k)),
                               Qt.KeepAspectRatio, Qt.SmoothTransformation)
        toile = QImage(VIGNETTE, QImage.Format_ARGB32_Premultiplied)
        toile.fill(0)
        p = QPainter(toile)
        p.drawImage((VIGNETTE.width() - petit.width()) // 2, (VIGNETTE.height() - petit.height()) // 2 - 4, petit)
        p.end()
        rendu = rendre_style(toile, style.mis_a_l_echelle(max(k, 0.25)))
        pm = QPixmap(VIGNETTE)
        pm.fill(QColor("#cfcac0"))
        p = QPainter(pm)
        p.drawImage(0, 0, rendu)
        p.end()
        return QIcon(pm)

    def _remplir_galerie(self):
        self.galerie.clear()
        contenu = self._contenu()
        for perso, liste in ((False, styles_prets()), (True, styles_perso(self.f.reglages))):
            for nom, st in liste:
                it = QListWidgetItem(self._vignette(contenu, st), nom)
                it.setData(Qt.UserRole, st)
                it.setData(Qt.UserRole + 1, perso)
                it.setToolTip(nom + ("  " + tr("(mon style : clic droit pour le supprimer)") if perso else ""))
                self.galerie.addItem(it)

    def _style_pret(self, it):
        st = it.data(Qt.UserRole)
        angle = self.style.angle_global()
        if angle is not None:
            st = st.avec_angle_global(angle)          # la lumière commune reste celle de la photo
        self._mettre_style(st)

    def _menu_galerie(self, pos):
        it = self.galerie.itemAt(pos)
        if it is None or not it.data(Qt.UserRole + 1):
            return
        m = QMenu(self)
        a = m.addAction(tr("Supprimer ce style"))
        if m.exec(self.galerie.mapToGlobal(pos)) is a:
            liste = [(n, s) for n, s in styles_perso(self.f.reglages) if n != it.text()]
            enregistrer_styles_perso(self.f.reglages, liste)
            self._remplir_galerie()

    def _enregistrer_style(self):
        if not self.style.effets:
            QMessageBox.information(self, tr("Enregistrer ce style"), tr("Ajoute d'abord au moins un effet."))
            return
        nom, ok = QInputDialog.getText(self, tr("Enregistrer ce style"), tr("Nom du style :"))
        nom = nom.strip()
        if ok and nom:
            liste = [(n, s) for n, s in styles_perso(self.f.reglages) if n != nom] + [(nom, self.style)]
            enregistrer_styles_perso(self.f.reglages, liste)
            self._remplir_galerie()

    # ---------------------------------------------------------- liste des effets
    def _remplir_liste(self, choisi: int | None = None):
        if choisi is None:
            choisi = self.liste.currentRow()
        self.liste.blockSignals(True)
        self.liste.clear()
        noms = {}
        for e in self.style.effets:
            noms[e.type] = noms.get(e.type, 0) + 1
        vus = {}
        for e in self.style.effets:
            vus[e.type] = vus.get(e.type, 0) + 1
            texte = nom_effet(e.type) + (f" {vus[e.type]}" if noms[e.type] > 1 else "")
            it = QListWidgetItem(texte)
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked if e.actif else Qt.Unchecked)
            self.liste.addItem(it)
        self.liste.blockSignals(False)
        if self.style.effets:
            self.liste.setCurrentRow(max(0, min(choisi, len(self.style.effets) - 1)))
        else:
            self._effet_choisi(-1)

    def _effet(self) -> int:
        return self.liste.currentRow()

    def _effet_choisi(self, i: int):
        w = QWidget()
        form = QFormLayout(w)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        if i < 0 or i >= len(self.style.effets):
            self.titre_effet.setText(tr("Aucun effet"))
            form.addRow(QLabel(tr("Clique sur « Ajouter » ou sur un style tout prêt.")))
            self.zone.setWidget(w)
            self._poignee()
            return
        e = self.style.effets[i]
        self.titre_effet.setText(nom_effet(e.type))
        for reglage in REGLAGES[e.type]:
            cle, libelle, genre, _defaut = reglage[:4]
            v = e.r(cle)
            if genre == "couleur":
                champ = ChampCouleur(v)
            elif genre == "pourcent":
                mini, maxi = (reglage[4], reglage[5]) if len(reglage) > 5 else (0, 100)
                champ = Curseur(mini, maxi, v, " %")
            elif genre == "px":
                champ = Curseur(reglage[4], reglage[5], v, " px", decimales=True)
            elif genre == "nombre":
                champ = Curseur(reglage[4], reglage[5], v)
            elif genre == "angle":
                champ = ChampAngle(v)
            elif genre == "choix":
                champ = QComboBox()
                for code, nom in reglage[4].items():
                    champ.addItem(tr(nom), code)
                champ.setCurrentIndex(max(0, champ.findData(v)))
                champ.currentIndexChanged.connect(lambda _i, c=cle, ch=champ: self._changer(c, ch.currentData()))
            else:
                champ = QCheckBox(tr(libelle))
                champ.setChecked(bool(v))
                champ.toggled.connect(lambda val, c=cle: self._changer(c, val))
                form.addRow("", champ)
                continue
            if genre != "choix":
                champ.change.connect(lambda val, c=cle: self._changer(c, val))
            form.addRow(tr(libelle), champ)
        self.zone.setWidget(w)
        self._poignee()

    def _case_effet(self, it):
        i = self.liste.row(it)
        effets = list(self.style.effets)
        effets[i] = replace(effets[i], actif=it.checkState() == Qt.Checked)
        self._mettre_style(replace(self.style, effets=tuple(effets)), liste=False)

    def _changer(self, cle, valeur):
        i = self._effet()
        if i < 0:
            return
        effets = list(self.style.effets)
        e = effets[i]
        effets[i] = replace(e, reglages={**e.reglages, cle: valeur})
        st = replace(self.style, effets=tuple(effets))
        if cle == "angle" and e.reglages.get("global") or cle == "global" and valeur:
            st = st.avec_angle_global(effets[i].reglages["angle"])     # une seule lumière pour tous
        self._mettre_style(st, liste=False)

    def _ajouter(self, type_):
        e = Effet.nouveau(type_)
        angle = self.style.angle_global()
        if angle is not None and e.reglages.get("global"):
            e = replace(e, reglages={**e.reglages, "angle": angle})
        self._mettre_style(replace(self.style, effets=self.style.effets + (e,)), choisi=len(self.style.effets))

    def _dupliquer(self):
        i = self._effet()
        if i >= 0:
            effets = list(self.style.effets)
            effets.insert(i + 1, replace(effets[i], reglages=dict(effets[i].reglages)))
            self._mettre_style(replace(self.style, effets=tuple(effets)), choisi=i + 1)

    def _deplacer(self, sens):
        i = self._effet()
        j = i + sens
        if i >= 0 and 0 <= j < len(self.style.effets):
            effets = list(self.style.effets)
            effets[i], effets[j] = effets[j], effets[i]
            self._mettre_style(replace(self.style, effets=tuple(effets)), choisi=j)

    def _supprimer(self):
        i = self._effet()
        if i >= 0:
            effets = list(self.style.effets)
            del effets[i]
            self._mettre_style(replace(self.style, effets=tuple(effets)), choisi=max(0, i - 1))

    def _remplissage(self, v):
        self._mettre_style(replace(self.style, remplissage=v / 100), liste=False)

    def _mettre_style(self, st: Style, liste: bool = True, choisi: int | None = None):
        self.style = st
        if liste:
            self.remplissage.blockSignals(True)
            self.remplissage.case.setValue(round(st.remplissage * 100))
            self.remplissage.blockSignals(False)
            self._remplir_liste(choisi)
        self._attente.start()

    # ---------------------------------------------------------- aperçu et poignée de l'ombre au sol
    def _apercu(self):
        if self._fini:
            return
        self.doc.apercu_style(self.index, self.style)
        self._poignee()

    def _poignee(self):
        c = self.f.canevas
        i = self._effet()
        e = self.style.effets[i] if 0 <= i < len(self.style.effets) else None
        self.aide_sol.setVisible(e is not None and e.type == "ombre_sol")
        if e is None or e.type != "ombre_sol" or not e.actif:
            c.definir_poignee_sol(None)
            return
        from .document import FORMAT_IMAGE, tableau
        A = tableau(self.doc.calques[self.index].image.convertToFormat(FORMAT_IMAGE))[:, :, 3] / 255
        c.definir_poignee_sol(bout_ombre_sol(A, e))

    def _poignee_bouge(self, pt: QPointF):
        i = self._effet()
        if not (0 <= i < len(self.style.effets)) or self.style.effets[i].type != "ombre_sol":
            return
        from .document import FORMAT_IMAGE, tableau
        A = tableau(self.doc.calques[self.index].image.convertToFormat(FORMAT_IMAGE))[:, :, 3] / 255
        r = bout_ombre_sol(A, Effet.nouveau("ombre_sol"))
        if r is None:
            return
        (cx, pied), _ = r
        lignes = np.nonzero(A.max(axis=1) > 0.3)[0]
        hauteur = float(lignes[-1] - lignes[0] + 1)
        tx = max(-300, min(300, round((pt.x() - cx) / hauteur * 100)))
        ty = max(-200, min(200, round((pt.y() - pied) / hauteur * 100)))
        effets = list(self.style.effets)
        effets[i] = replace(effets[i], reglages={**effets[i].reglages, "tx": tx, "ty": ty})
        self._mettre_style(replace(self.style, effets=tuple(effets)), liste=False)
        self._effet_choisi(i)

    # ---------------------------------------------------------- fin
    def _terminer(self):
        self._fini = True
        self._attente.stop()
        QApplication.instance().removeEventFilter(self.bloqueur)
        try:
            self.f.canevas.poignee_sol_bouge.disconnect(self._poignee_bouge)
        except (RuntimeError, TypeError):
            pass
        self.f.canevas.definir_poignee_sol(None)

    def accept(self):
        self._terminer()
        style = None if self.style.vide() and not self.style.effets else self.style
        self.doc.appliquer_etat(self.avant)
        self.doc.modifie = self.modifie_avant
        calques = list(self.doc.calques)
        calques[self.index] = replace(calques[self.index], style=style)
        angle = self.style.angle_global()
        if angle is not None and angle != self.angle_depart:     # lumière commune : tous les calques suivent
            for k, c in enumerate(calques):
                if k != self.index and c.style is not None and c.style.angle_global() is not None:
                    calques[k] = replace(c, style=c.style.avec_angle_global(angle))
        avant_style = self.doc.calques[self.index].style
        if style is not avant_style:
            self.f._commande_calques(self.doc.etat_avec(calques), tr("Style du calque"))
        super().accept()
        self.fini.emit()

    def reject(self):
        self._terminer()
        self.doc.appliquer_etat(self.avant)
        self.doc.modifie = self.modifie_avant
        super().reject()
        self.fini.emit()

    def closeEvent(self, e):
        if not self._fini:
            self.reject()
        super().closeEvent(e)
