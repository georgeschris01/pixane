"""Fenêtre principale de Chrypix."""
from __future__ import annotations

import json
import os
import sys
import threading
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QBuffer, QMimeData, QObject, QPoint, QProcess, QSettings, QSize, Qt, QTimer, Signal
from PySide6.QtCore import QUrl
from PySide6.QtGui import (QAction, QActionGroup, QColor, QDesktopServices, QIcon, QImage, QKeySequence, QUndoCommand,
                           QUndoStack)
from PySide6.QtWidgets import (QApplication, QButtonGroup, QCheckBox, QComboBox, QDialog, QDockWidget, QFileDialog, QHBoxLayout, QLabel,
                               QLineEdit, QMainWindow, QMenu, QMessageBox, QPushButton, QSizePolicy, QSlider,
                               QSpinBox, QToolBar, QToolButton, QUndoView, QVBoxLayout, QWidget, QInputDialog)

from . import langue, recettes, theme
from .icones import icone
from .langue import tr
from .calques import PanneauCalques
from .canevas import (BAGUETTE, DEPLACER, GOMME, GOMME_CALQUE, LASSO, MAIN, OBJET, OUTILS_AUTO, OUTILS_ROND,
                      PEINTURE, PINCEAU, RAPIDE, RECADRER, RECTANGLE, SUPPRIMER, TAMPON, TEXTE, Canevas)
from .dialogues import Attente, BarreAgrandir, ChoixResultat, ReglagesUpscale
from .document import EXTENSIONS_LECTURE, FORMAT_IMAGE, Document, nouvelle_selection, qimage_rgb, tableau
from .moteur import Annule, ErreurMoteur, Moteur, trouver_comfyui
from .panneau_texte import BoutonCouleur, PanneauTexte
from .raccord import finaliser, lisere_auto, preparer
from .reglages_image import FenetreReglages, ajuster, auto, neutre
from .dialogues_image import APropos, NouvelleImage, Redresser, TailleImage
from .transformation import Transformation
from . import mises_a_jour
from .texte import Texte

NOM = "Chrypix"
MIME_PLACE = "application/x-chrypix-place"   # presse-papiers : place d'origine de ce qui a été copié dans Chrypix


def reglages() -> QSettings:
    """Réglages de l'utilisateur ; les essais automatiques ont les leurs (variable CHRYPIX_REGLAGES)."""
    return QSettings("Chrypix", os.environ.get("CHRYPIX_REGLAGES", "Chrypix"))


class Tache(QObject):
    """Exécute une fonction dans un fil secondaire et renvoie le résultat par signal."""
    fini = Signal(object)
    echec = Signal(str)
    progres = Signal(object)

    def __init__(self, fonction):
        super().__init__()
        self.fonction = fonction

    def lancer(self):
        threading.Thread(target=self._executer, daemon=True).start()

    def _executer(self):
        try:
            self.fini.emit(self.fonction(self.progres.emit))
        except Annule:
            self.echec.emit("")
        except ErreurMoteur as e:
            self.echec.emit(str(e))
        except Exception as e:  # erreur imprévue : on l'affiche plutôt que de planter
            self.echec.emit(f"{type(e).__name__} : {e}")


class CommandeEtat(QUndoCommand):
    """Passage d'un état du document à un autre. Deux commandes de même `cle` à la suite n'en font qu'une
    (ex. les lettres tapées dans un texte : un seul Ctrl+Z annule toute la saisie)."""

    def __init__(self, doc: Document, avant, apres, texte: str, cle=None):
        super().__init__(texte)
        self.doc, self.avant, self.apres, self.cle = doc, avant, apres, cle

    def id(self):
        return 1 if self.cle is not None else -1

    def mergeWith(self, autre):
        if autre.cle != self.cle or autre.doc is not self.doc:
            return False
        self.apres = autre.apres
        return True

    def redo(self):
        self.doc.appliquer_etat(self.apres)

    def undo(self):
        self.doc.appliquer_etat(self.avant)


class Carte(QPushButton):
    """Bouton large du panneau IA : icône, titre et une ligne d'explication."""

    def __init__(self, titre: str, explication: str):
        super().__init__()
        self.setObjectName("carte")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(64)
        self.image = QLabel()
        self.image.setFixedSize(28, 28)
        t = QLabel(f"<b>{titre}</b>")
        e = QLabel(explication)
        e.setObjectName("discret")
        e.setWordWrap(True)
        textes = QVBoxLayout()
        textes.setSpacing(1)
        textes.addWidget(t)
        textes.addWidget(e)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(12)
        lay.addWidget(self.image, 0, Qt.AlignVCenter)
        lay.addLayout(textes, 1)
        for w in (self.image, t, e):
            w.setAttribute(Qt.WA_TransparentForMouseEvents)

    def definir_icone(self, ic: QIcon):
        self.image.setPixmap(ic.pixmap(28, 28))


class Fenetre(QMainWindow):
    etat_moteur = Signal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle(NOM)
        self.resize(1440, 920)
        self.setAcceptDrops(True)
        # les essais automatiques utilisent leurs propres réglages (variable CHRYPIX_REGLAGES)
        self.reglages = reglages()
        self.doc: Document | None = None
        self.historique = QUndoStack(self)
        self.historique.setUndoLimit(30)
        self.moteur = Moteur()
        self._taches = set()
        self._icones = []            # (objet, nom d'icône) à redessiner quand le thème change
        self.mode_theme = self.reglages.value("theme", theme.AUTO)
        self.couleurs = theme.appliquer(QApplication.instance(), self.mode_theme)
        self.texte_moteur = tr("démarrage…")

        self.canevas = Canevas()
        self.canevas.selection_modifiee.connect(self._selection_modifiee)
        self.canevas.refus.connect(lambda m: self.statusBar().showMessage(m, 6000))
        self.setCentralWidget(self.canevas)
        self.barre_agrandir = BarreAgrandir(self.canevas)
        self.barre_agrandir.lancer.connect(self._lancer_agrandir)
        self.barre_agrandir.annuler.connect(self._fin_agrandir)
        self.barre_agrandir.valeurs_changees.connect(self.canevas.definir_cadre)
        self.canevas.cadre_change.connect(self.barre_agrandir.definir_px)
        self.canevas.cadre_valide.connect(self._lancer_agrandir)
        self.canevas.cadre_annule.connect(self._fin_agrandir)
        self.canevas.texte_nouveau.connect(self._nouveau_texte)
        self.canevas.texte_choisi.connect(self._texte_choisi)
        self.canevas.message.connect(lambda m: self.statusBar().showMessage(m, 6000))
        self.canevas.recadre_change.connect(self._recadre_change)
        self.canevas.recadre_valide.connect(self._recadrer)
        self.canevas.couleur_prise.connect(self._couleur_prise)
        self.canevas.transfo_change.connect(self._transfo_change)
        self.canevas.transfo_valide.connect(self._valider_transfo)
        self.canevas.transfo_annule.connect(self._annuler_transfo)
        self._transfo_avant = None
        self.historique.indexChanged.connect(self._historique_bouge)
        self._session_texte = 0      # regroupe les changements d'un même texte dans Annuler

        self._menus()
        self._barre_commandes()
        self._outils()
        self._panneau_ia()
        self._panneau_calques()
        self._panneau_historique()
        self._panneau_texte()
        self._barre_etat()
        from .selection_ia import SelectionAuto
        self.selection_auto = SelectionAuto(self)
        from .suppression import Suppression
        self.suppression = Suppression(self)
        self.canevas.fin_session_ia.connect(self.selection_auto.fin_session)
        self._appliquer_theme()
        self._choisir_outil(PINCEAU)
        self._actualiser()
        self._demarrer_moteur()
        if self.reglages.value("maj_auto", False, type=bool):
            QTimer.singleShot(8000, lambda: self.verifier_maj(silencieux=True))
        # suivre les changements de couleur ou de thème faits dans Windows
        self._signature_windows = theme.signature_windows()
        self._veille_windows = QTimer(self)
        self._veille_windows.timeout.connect(self._verifier_windows)
        self._veille_windows.start(2000)

    # ================================================================ interface
    def _icone(self, objet, nom: str):
        self._icones.append((objet, nom))
        return objet

    def _action(self, menu, texte, raccourci=None, fonction=None, cle=None, icone=None):
        a = QAction(texte, self)
        if raccourci:
            a.setShortcut(QKeySequence(raccourci))
        if fonction:
            a.triggered.connect(fonction)
        if menu is not None:
            menu.addAction(a)
        if cle:
            setattr(self, cle, a)
        if icone:
            self._icone(a, icone)
        return a

    def _menus(self):
        m = self.menuBar().addMenu(tr("&Fichier"))
        self._action(m, tr("Nouvelle image…"), QKeySequence.New, self.nouvelle_image, "a_nouvelle")
        self._action(m, tr("Nouvelle image depuis le presse-papiers"), "Ctrl+Alt+V", self.nouvelle_depuis_presse_papiers,
                     "a_nouvelle_pp")
        self._action(m, tr("Ouvrir…"), QKeySequence.Open, self.ouvrir, "a_ouvrir", "ouvrir")
        self.m_recents = m.addMenu(tr("Fichiers récents"))
        self.m_recents.aboutToShow.connect(self._remplir_recents)
        self._action(m, tr("Enregistrer"), QKeySequence.Save, self.enregistrer, "a_enregistrer", "enregistrer")
        self._action(m, tr("Enregistrer sous…"), "Ctrl+Shift+S", self.enregistrer_sous, "a_enregistrer_sous")
        m.addSeparator()
        self._action(m, tr("Quitter"), "Ctrl+Q", self.close)

        m = self.menuBar().addMenu(tr("&Édition"))
        self.a_annuler = self.historique.createUndoAction(self, tr("Annuler|édition"))
        self.a_annuler.setShortcut(QKeySequence.Undo)
        self.a_retablir = self.historique.createRedoAction(self, tr("Rétablir|édition"))
        self.a_retablir.setShortcuts([QKeySequence("Ctrl+Y"), QKeySequence("Ctrl+Shift+Z")])
        self._icone(self.a_annuler, "annuler")
        self._icone(self.a_retablir, "retablir")
        m.addAction(self.a_annuler)
        m.addAction(self.a_retablir)
        m.addSeparator()
        self._action(m, tr("Couper"), QKeySequence.Cut, self.couper, "a_couper")
        self._action(m, tr("Copier"), QKeySequence.Copy, self.copier, "a_copier")
        self._action(m, tr("Coller"), QKeySequence.Paste, self.coller, "a_coller")
        self._action(m, tr("Supprimer la sélection"), QKeySequence.Delete, self.supprimer_selection,
                     "a_supprimer_selection")
        m.addSeparator()
        self._action(m, tr("Transformer le calque"), "Ctrl+T", self.transformer, "a_transformer")

        m = self.menuBar().addMenu(tr("&Sélection"))
        self._action(m, tr("Tout sélectionner"), "Ctrl+A", lambda: self._modifier_selection("tout"), "a_tout")
        self._action(m, tr("Désélectionner"), "Ctrl+D", lambda: self._modifier_selection("rien"), "a_rien")
        self._action(m, tr("Inverser la sélection"), "Ctrl+Shift+I", lambda: self._modifier_selection("inverser"),
                     "a_inverser")
        sous = m.addMenu(tr("Modifier la sélection"))
        self._action(sous, tr("Agrandir…"), None, lambda: self._modifier_bord("agrandir"), "a_sel_agrandir")
        self._action(sous, tr("Réduire…"), None, lambda: self._modifier_bord("reduire"), "a_sel_reduire")
        self._action(sous, tr("Adoucir les bords…"), None, lambda: self._modifier_bord("adoucir"), "a_sel_adoucir")
        self._action(m, tr("Sélectionner le sujet (IA)"), "Ctrl+Alt+S", self.selectionner_sujet, "a_sujet")
        m.addSeparator()
        self._action(m, tr("Recadrer à la sélection"), None, self._recadrer_selection, "a_recadrer_selection",
                     "recadrer")

        m = self.menuBar().addMenu(tr("I&mage"))
        self._action(m, tr("Réglages de l'image…"), "Ctrl+U", self.reglages_image, "a_reglages_image", "reglages")
        m.addSeparator()
        self._action(m, tr("Taille de l'image…"), "Ctrl+Alt+I", self.taille_image, "a_taille")
        self._action(m, tr("Pivoter de 90° à droite"), None, lambda: self._geometrie(tr("Pivoter"), 90), "a_pivoter_d")
        self._action(m, tr("Pivoter de 90° à gauche"), None, lambda: self._geometrie(tr("Pivoter"), -90),
                     "a_pivoter_g")
        self._action(m, tr("Pivoter de 180°"), None, lambda: self._geometrie(tr("Pivoter"), 180), "a_pivoter_180")
        self._action(m, tr("Retourner horizontalement"), None, lambda: self._geometrie(tr("Retourner"), "h"),
                     "a_miroir_h")
        self._action(m, tr("Retourner verticalement"), None, lambda: self._geometrie(tr("Retourner"), "v"),
                     "a_miroir_v")
        self._action(m, tr("Redresser…"), None, self.redresser, "a_redresser")

        m = self.menuBar().addMenu(tr("&Calque"))
        self._action(m, tr("Style du calque…"), "Ctrl+Alt+F", self.style_calque, "a_style", "style")
        self._action(m, tr("Copier le style"), None, self.copier_style, "a_copier_style")
        self._action(m, tr("Coller le style"), None, self.coller_style, "a_coller_style")
        self._action(m, tr("Enlever le style"), None, self.enlever_style, "a_enlever_style")
        self._action(m, tr("Mettre le style dans les pixels"), None, self.figer_style, "a_figer_style")
        m.addSeparator()
        self._action(m, tr("Nouveau calque"), "Ctrl+Shift+N", lambda: self.calques.nouveau() if self.doc else None,
                     "a_nouveau_calque")
        self._action(m, tr("Dupliquer le calque"), "Ctrl+J", lambda: self.calques.dupliquer() if self.doc else None,
                     "a_dupliquer_calque")

        m = self.menuBar().addMenu(tr("&Affichage"))
        self._action(m, tr("Zoom avant"), "Ctrl++", lambda: self.canevas.zoomer(1.25), "a_zoom_plus", "zoom_plus")
        self._action(m, tr("Zoom arrière"), "Ctrl+-", lambda: self.canevas.zoomer(0.8), "a_zoom_moins", "zoom_moins")
        self._action(m, tr("Ajuster à la fenêtre"), "Ctrl+0", self.canevas.ajuster, "a_ajuster", "ajuster")
        self._action(m, tr("Taille réelle (100 %)"), "Ctrl+1", self.canevas.zoom_100)
        m.addSeparator()
        sous = m.addMenu(tr("Thème"))
        groupe = QActionGroup(self)
        for mode, texte in ((theme.AUTO, tr("Comme Windows")), (theme.CLAIR, tr("Clair")), (theme.SOMBRE, tr("Sombre"))):
            a = QAction(texte, self, checkable=True)
            a.setChecked(mode == self.mode_theme)
            a.triggered.connect(lambda _=False, md=mode: self.changer_theme(md))
            groupe.addAction(a)
            sous.addAction(a)
        self._actions_theme = groupe
        sous = m.addMenu(tr("Langue"))
        groupe = QActionGroup(self)
        actuel = self.reglages.value("langue", langue.AUTO)
        for code, texte in [(langue.AUTO, tr("Comme Windows"))] + list(langue.LANGUES.items()):
            a = QAction(texte, self, checkable=True)
            a.setChecked(code == actuel)
            a.triggered.connect(lambda _=False, c=code: self.changer_langue(c))
            groupe.addAction(a)
            sous.addAction(a)

        m = self.menuBar().addMenu(tr("&IA"))
        self._action(m, tr("Effacer"), "Shift+E", self.ia_effacer, "a_effacer", "effacer")
        self._action(m, tr("Remplir"), "Shift+R", self.ia_remplir, "a_remplir", "remplir")
        self._action(m, tr("Agrandir l'image…"), "Shift+A", self.ia_agrandir, "a_agrandir", "agrandir")
        self._action(m, tr("Upscale…"), "Shift+U", self.ia_upscale, "a_upscale", "upscale")
        self._action(m, tr("Supprimer l'arrière-plan"), "Shift+B", self.supprimer_arriere_plan, "a_arriere_plan",
                     "arriere_plan")
        m.addSeparator()
        self._action(m, tr("Installer le moteur IA…"), None, self.installer_moteur, "a_installer_moteur")

        m = self.menuBar().addMenu(tr("&Aide"))
        self._action(m, tr("Guide de Chrypix"), None, lambda: self.guide(), "a_guide")
        self._action(m, tr("Raccourcis"), "F1", lambda: self.guide(tr("Raccourcis")), "a_raccourcis")
        m.addSeparator()
        self._action(m, tr("Rechercher une mise à jour…"), None, lambda: self.verifier_maj(False))
        a = self._action(m, tr("Vérifier les mises à jour au démarrage"), None, None, "a_maj_auto")
        a.setCheckable(True)
        a.setChecked(self.reglages.value("maj_auto", False, type=bool))
        a.toggled.connect(lambda v: self.reglages.setValue("maj_auto", v))
        m.addSeparator()
        self._action(m, tr("À propos de Chrypix"), None, self.a_propos)

    def _barre_commandes(self):
        """Barre du haut : fichiers, annuler, options de l'outil, zoom, thème."""
        b = QToolBar(tr("Commandes"))
        self.barre_haut = b
        b.setMovable(False)
        b.setIconSize(QSize(20, 20))
        self.addToolBar(Qt.TopToolBarArea, b)
        for a in (self.a_ouvrir, self.a_enregistrer):
            b.addAction(a)
        b.addSeparator()
        b.addAction(self.a_annuler)
        b.addAction(self.a_retablir)
        b.addSeparator()

        # options de l'outil (comme Photoshop) : chaque groupe n'apparaît qu'avec les outils qui s'en servent
        self.options = QWidget()
        tout = QHBoxLayout(self.options)
        tout.setContentsMargins(6, 0, 6, 0)
        tout.setSpacing(14)
        self.opt_taille = QWidget()
        lay = QHBoxLayout(self.opt_taille)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        lay.addWidget(QLabel(tr("Taille")))
        self.curseur_taille = QSlider(Qt.Horizontal)
        self.curseur_taille.setRange(2, 600)
        self.curseur_taille.setFixedWidth(160)
        self.curseur_taille.setValue(self.canevas.taille_pinceau)
        self.valeur_taille = QLabel(f"{self.canevas.taille_pinceau} px")
        self.valeur_taille.setMinimumWidth(52)
        self.curseur_taille.valueChanged.connect(self.canevas.definir_taille)
        self.canevas.taille_changee.connect(self._taille_changee)
        lay.addWidget(self.curseur_taille)
        lay.addWidget(self.valeur_taille)
        tout.addWidget(self.opt_taille)
        self.opt_selection = QWidget()
        lay = QHBoxLayout(self.opt_selection)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        self.p_nouvelle = QPushButton(tr("Nouvelle"))
        self.p_ajouter = QPushButton(tr("Ajouter"))
        self.p_retirer = QPushButton(tr("Retirer"))
        self.p_nouvelle.setToolTip(tr("Nouvelle : la sélection tracée remplace l'ancienne (un simple clic "
                                      "désélectionne). Pendant le tracé : Maj ajoute, Alt retire."))
        self.p_ajouter.setToolTip(tr("Ajouter à la sélection (Maj pendant le tracé du rectangle ou du lasso)"))
        self.p_retirer.setToolTip(tr("Retirer de la sélection (Alt pendant le tracé)"))
        groupe = QButtonGroup(self)
        for p_, mode in ((self.p_nouvelle, "nouvelle"), (self.p_ajouter, "ajouter"), (self.p_retirer, "retirer")):
            p_.setObjectName("pastille")
            p_.setCheckable(True)
            p_.setCursor(Qt.PointingHandCursor)
            p_.clicked.connect(lambda _=False, m=mode: self._mode_selection(m))
            groupe.addButton(p_)
            lay.addWidget(p_)
        self.p_nouvelle.setChecked(True)
        tout.addWidget(self.opt_selection)
        self.opt_transfo = QWidget()
        lay = QHBoxLayout(self.opt_transfo)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        self.info_transfo = QLabel()
        lay.addWidget(self.info_transfo)
        b_ok = QPushButton(tr("Valider"))
        b_ok.clicked.connect(self._valider_transfo)
        b_non = QPushButton(tr("Annuler"))
        b_non.clicked.connect(self._annuler_transfo)
        lay.addWidget(b_ok)
        lay.addWidget(b_non)
        self.opt_transfo.hide()
        tout.addWidget(self.opt_transfo)
        self._options_retouche(tout)
        self._options_recadrer(tout)
        b.addWidget(self.options)

        vide = QWidget()
        vide.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        b.addWidget(vide)
        b.addAction(self.a_zoom_moins)
        self.valeur_zoom = QLabel("—")
        self.valeur_zoom.setMinimumWidth(52)
        self.valeur_zoom.setAlignment(Qt.AlignCenter)
        b.addWidget(self.valeur_zoom)
        b.addAction(self.a_zoom_plus)
        b.addAction(self.a_ajuster)
        b.addSeparator()
        self.a_theme = QAction(tr("Thème clair / sombre"), self)
        self.a_theme.triggered.connect(self._basculer_theme)
        b.addAction(self.a_theme)

    def _options_retouche(self, tout: QHBoxLayout):
        """Pinceau de couleur et tampon : couleur, opacité, dureté."""
        self.opt_couleur = BoutonCouleur(tr("Couleur du pinceau"))
        self.opt_couleur.definir(self.reglages.value("peinture_couleur", "#ff000000"))
        self.opt_couleur.change.connect(self._couleur_peinture)
        self._couleur_peinture(self.opt_couleur.couleur, enregistrer=False)
        tout.addWidget(self.opt_couleur)
        self.opt_retouche = QWidget()
        lay = QHBoxLayout(self.opt_retouche)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        self.opt_opacite = QSpinBox()
        self.opt_durete = QSpinBox()
        for nom, case, cle, defaut, aide in (
                (tr("Opacité"), self.opt_opacite, "outil_opacite", 100, tr("100 % = couvre tout ; moins = laisse "
                                                                            "voir dessous")),
                (tr("Dureté"), self.opt_durete, "outil_durete", 80, tr("100 % = bord net ; 0 % = bord très doux"))):
            lay.addWidget(QLabel(nom))
            case.setRange(1 if case is self.opt_opacite else 0, 100)
            case.setSuffix(" %")
            case.setToolTip(aide)
            case.setValue(int(self.reglages.value(cle, defaut)))
            case.valueChanged.connect(self._reglages_retouche)
            lay.addWidget(case)
            lay.addSpacing(6)
        tout.addWidget(self.opt_retouche)
        self._reglages_retouche()

    def _options_recadrer(self, tout: QHBoxLayout):
        self.opt_recadrer = QWidget()
        lay = QHBoxLayout(self.opt_recadrer)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        lay.addWidget(QLabel(tr("Proportions")))
        self.opt_proportion = QComboBox()
        for texte, valeur in ((tr("Libre"), None), (tr("Comme la photo"), "photo"), ("1:1", 1.0), ("4:3", 4 / 3),
                              ("3:2", 1.5), ("16:9", 16 / 9), ("3:4", 3 / 4), ("2:3", 2 / 3), ("9:16", 9 / 16)):
            self.opt_proportion.addItem(texte, valeur)
        self.opt_proportion.currentIndexChanged.connect(self._proportion)
        lay.addWidget(self.opt_proportion)
        self.b_recadrer = QPushButton(tr("Recadrer"))
        self.b_recadrer.setToolTip(tr("Garder seulement l'intérieur du cadre (Entrée, ou double-clic dans le cadre)"))
        self.b_recadrer.clicked.connect(self._recadrer)
        self.b_annuler_recadre = QPushButton(tr("Annuler"))
        self.b_annuler_recadre.setToolTip(tr("Enlever le cadre (Échap)"))
        self.b_annuler_recadre.clicked.connect(self.canevas.annuler_recadre)
        lay.addWidget(self.b_recadrer)
        lay.addWidget(self.b_annuler_recadre)
        tout.addWidget(self.opt_recadrer)
        self._recadre_change(None)
        # baguette magique
        self.opt_baguette = QWidget()
        lay = QHBoxLayout(self.opt_baguette)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        lay.addWidget(QLabel(tr("Tolérance")))
        self.opt_tolerance = QSpinBox()
        self.opt_tolerance.setRange(0, 255)
        self.opt_tolerance.setValue(self.reglages.value("baguette_tolerance", 32, type=int))
        self.opt_tolerance.setToolTip(tr("Écart de couleur accepté. Astuce : après le clic, glisse la souris à droite "
                                         "ou à gauche pour régler la tolérance en voyant le résultat."))
        self.opt_tolerance.valueChanged.connect(lambda v: self.reglages.setValue("baguette_tolerance", v))
        lay.addWidget(self.opt_tolerance)
        self.opt_contigu = QCheckBox(tr("Contiguë"))
        self.opt_contigu.setToolTip(tr("Coché : seulement la zone touchée. Décoché : toutes les couleurs proches de "
                                       "l'image."))
        self.opt_doux = QCheckBox(tr("Bords doux"))
        self.opt_doux.setToolTip(tr("Bord progressif, selon l'écart de couleur (pas d'escalier)"))
        self.opt_trous = QCheckBox(tr("Boucher les trous"))
        self.opt_trous.setToolTip(tr("Ajoute ce qui est entièrement entouré par la zone (oiseaux dans un ciel, "
                                     "reflets…)"))
        for case, cle, defaut in ((self.opt_contigu, "baguette_contigu", True), (self.opt_doux, "baguette_doux", True),
                                  (self.opt_trous, "baguette_trous", False)):
            case.setChecked(self.reglages.value(cle, defaut, type=bool))
            case.toggled.connect(lambda v, c=cle: self.reglages.setValue(c, v))
            lay.addWidget(case)
        self.opt_echantillon = QComboBox()
        self.opt_echantillon.addItem(tr("Image visible"), "image")
        self.opt_echantillon.addItem(tr("Calque choisi"), "calque")
        self.opt_echantillon.setToolTip(tr("Couleurs comparées sur l'image telle qu'on la voit, ou sur le calque "
                                           "choisi seulement"))
        lay.addWidget(self.opt_echantillon)
        tout.addWidget(self.opt_baguette)

    def _couleur_peinture(self, couleur: str, enregistrer: bool = True):
        self.canevas.couleur_peinture = QColor(couleur)
        if enregistrer:
            self.reglages.setValue("peinture_couleur", couleur)

    def _couleur_prise(self, couleur: str):
        self.opt_couleur.definir(QColor(couleur).name(QColor.HexArgb))
        self._couleur_peinture(self.opt_couleur.couleur)
        self.statusBar().showMessage(tr("Couleur prise : {couleur}", couleur=couleur), 4000)

    def _reglages_retouche(self, *_):
        self.canevas.opacite = self.opt_opacite.value() / 100
        self.canevas.durete = self.opt_durete.value() / 100
        self.reglages.setValue("outil_opacite", self.opt_opacite.value())
        self.reglages.setValue("outil_durete", self.opt_durete.value())

    def _proportion(self, *_):
        v = self.opt_proportion.currentData()
        if v == "photo":
            v = self.doc.image.width() / self.doc.image.height() if self.doc else None
        self.canevas.definir_proportion(v)

    def _recadre_change(self, r):
        self.b_recadrer.setEnabled(r is not None)
        self.b_annuler_recadre.setEnabled(r is not None)

    def _recadrer(self):
        r = self.canevas.rect_recadre()
        if not self.doc or r is None:
            return
        if r == self.doc.image.rect():
            self.canevas.annuler_recadre()
            return
        avant = self.doc.etat()
        apres = self.doc.etat_recadre(r)
        self.canevas.annuler_recadre()
        self.historique.push(CommandeEtat(self.doc, avant, apres, tr("Recadrer")))
        self.statusBar().showMessage(tr("Recadré : {l} × {h} px (Ctrl+Z pour revenir)", l=r.width(), h=r.height()),
                                     6000)

    def _recadrer_selection(self):
        if not self.doc:
            return
        r = self.doc.rect_selection()
        if r is None:
            QMessageBox.information(self, NOM, tr("Sélectionne d'abord la partie à garder (rectangle, lasso ou "
                                                  "pinceau)."))
            return
        avant = self.doc.etat()
        apres = self.doc.etat_recadre(r)
        w, h = apres[0][0].image.width(), apres[0][0].image.height()
        apres = (apres[0], apres[1], nouvelle_selection(w, h))
        self.historique.push(CommandeEtat(self.doc, avant, apres, tr("Recadrer à la sélection")))

    def _outils(self):
        barre = QToolBar(tr("Outils"))
        barre.setMovable(False)
        barre.setIconSize(QSize(22, 22))
        barre.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.addToolBar(Qt.LeftToolBarArea, barre)
        groupe = QActionGroup(self)
        self._actions_outils = {}
        for outil, texte, touche, nom in ((MAIN, tr("Main : déplacer la vue"), "H", "main"),
                                          (DEPLACER, tr("Déplacer : bouge le calque choisi"), "V", "deplacer"),
                                          (RECTANGLE, tr("Sélection rectangle"), "M", "rectangle"),
                                          (LASSO, tr("Lasso"), "L", "lasso"),
                                          (PINCEAU, tr("Pinceau de sélection"), "B", "pinceau"),
                                          (GOMME, tr("Gomme de sélection"), "E", "gomme"),
                                          (BAGUETTE, tr("Baguette magique : zone de couleur proche (glisser après "
                                                        "le clic : tolérance)"), "W", "baguette"),
                                          (RAPIDE, tr("Sélection rapide (IA) : peins sur l'objet, Alt pour "
                                                      "retirer"), "Q", "rapide"),
                                          (OBJET, tr("Sélection d'objet (IA) : cadre autour de l'objet, ou clic "
                                                     "dessus"), "O", "objet"),
                                          (GOMME_CALQUE, tr("Gomme de calque : efface les pixels du calque choisi"),
                                           "G", "gomme_calque"),
                                          (TEXTE, tr("Texte : écrire, déplacer, tourner"), "T", "texte"),
                                          (RECADRER, tr("Recadrer : garder une partie de la photo"), "C", "recadrer"),
                                          (PEINTURE, tr("Pinceau de couleur : peint sur le calque choisi (Alt+clic : "
                                                        "prendre une couleur)"), "P", "peinture"),
                                          (TAMPON, tr("Tampon : recopie une zone (Alt+clic : endroit à copier)"),
                                           "S", "tampon"),
                                          (SUPPRIMER, tr("Supprimer (IA) : peins sur un défaut, il disparaît au "
                                                         "lâcher"), "J", "suppression")):
            a = QAction(texte, self, checkable=True)
            a.setShortcut(touche)
            a.setToolTip(f"{texte}  ({touche})")
            a.triggered.connect(lambda _=False, o=outil: self._choisir_outil(o))
            self._icone(a, nom)
            groupe.addAction(a)
            self.addAction(a)                  # raccourci actif même quand l'outil est caché dans son groupe
            self._actions_outils[outil] = a
            if outil == PINCEAU:
                a.setChecked(True)
        # comme Photoshop : un bouton par famille d'outils ; clic droit (ou clic maintenu) pour choisir dans la
        # famille ; le bouton montre le dernier outil choisi. Main et Déplacer restent seuls.
        self._bouton_groupe = {}
        for famille in ((MAIN,), (DEPLACER,), (RECTANGLE, LASSO, PINCEAU, GOMME), (OBJET, RAPIDE, BAGUETTE),
                        (SUPPRIMER, PEINTURE, TAMPON, GOMME_CALQUE), (RECADRER,), (TEXTE,)):
            if len(famille) == 1:
                barre.addAction(self._actions_outils[famille[0]])
                continue
            bouton = QToolButton()
            bouton.setPopupMode(QToolButton.DelayedPopup)
            bouton.setToolButtonStyle(Qt.ToolButtonIconOnly)
            bouton.setIconSize(barre.iconSize())
            bouton.setAutoRaise(True)
            menu = QMenu(bouton)
            for o in famille:
                a = self._actions_outils[o]
                a.setToolTip(a.toolTip() + "\n" + tr("Clic droit (ou clic maintenu) : les autres outils de ce groupe"))
                menu.addAction(a)
                self._bouton_groupe[o] = bouton
            bouton.setMenu(menu)
            bouton.setDefaultAction(self._actions_outils[famille[0]])
            bouton.setContextMenuPolicy(Qt.CustomContextMenu)
            bouton.customContextMenuRequested.connect(
                lambda _p, b=bouton: b.menu().exec(b.mapToGlobal(b.rect().topRight())))
            barre.addWidget(bouton)

    def _mode_selection(self, mode: str):
        if self.canevas.outil in (RECTANGLE, LASSO) + OUTILS_AUTO:
            self.canevas.mode_forme = mode
        else:
            self.canevas.definir_mode_retirer(mode == "retirer")

    def _choisir_outil(self, outil: str):
        if getattr(self.canevas, "transfo", None) is not None:
            self._valider_transfo()
        if self.canevas.outil != outil and hasattr(self, "selection_auto"):
            self.selection_auto.fin_session()
        self.canevas.definir_outil(outil)
        self._actions_outils[outil].setChecked(True)
        if outil in self._bouton_groupe:
            bouton = self._bouton_groupe[outil]
            menu = bouton.menu()
            bouton.setDefaultAction(self._actions_outils[outil])
            bouton.setMenu(menu)
        if outil in (RECTANGLE, LASSO) + OUTILS_AUTO:
            {"nouvelle": self.p_nouvelle, "ajouter": self.p_ajouter,
             "retirer": self.p_retirer}[self.canevas.mode_forme].setChecked(True)
        elif outil == PINCEAU:
            (self.p_retirer if self.canevas.mode_retirer else self.p_ajouter).setChecked(True)
        self.p_nouvelle.setVisible(outil in (RECTANGLE, LASSO) + OUTILS_AUTO)
        self.options.setEnabled(outil not in (MAIN, TEXTE, DEPLACER))
        self.opt_taille.setVisible(outil in OUTILS_ROND or outil in (MAIN, TEXTE, DEPLACER, RECTANGLE, LASSO))
        if outil in (BAGUETTE, OBJET):
            self.opt_taille.setVisible(False)
        self.opt_selection.setVisible(outil in (RECTANGLE, LASSO, PINCEAU) + OUTILS_AUTO)
        self.opt_baguette.setVisible(outil == BAGUETTE)
        self.opt_couleur.setVisible(outil == PEINTURE)
        self.opt_retouche.setVisible(outil in (PEINTURE, TAMPON))
        self.opt_recadrer.setVisible(outil == RECADRER)
        # la barre du haut se remet en page (sinon un groupe trop large la ferait déborder)
        self.options.adjustSize()
        self.barre_haut.layout().invalidate()
        aides = {RECTANGLE: tr("Rectangle : la nouvelle sélection remplace l'ancienne. Maj : ajouter, Alt : retirer. "
                               "Un simple clic désélectionne."),
                 LASSO: tr("Lasso : entoure la zone en gardant le bouton appuyé. Maj : ajouter, Alt : retirer."),
                 BAGUETTE: tr("Baguette magique : clic sur une couleur ; garde le bouton appuyé et glisse à droite ou "
                              "à gauche pour régler la tolérance. Maj : ajouter, Alt : retirer."),
                 RAPIDE: tr("Sélection rapide (IA) : peins grossièrement sur l'objet, l'IA trouve ses contours. "
                            "Alt + peindre : retirer une partie. Maj : objet suivant. Échap : recommencer."),
                 OBJET: tr("Sélection d'objet (IA) : tire un cadre autour de l'objet, ou clique dessus. "
                           "Maj : ajouter, Alt : retirer."),
                 RECADRER: tr("Recadrer : tire un cadre sur la photo, ajuste-le, puis Entrée (ou double-clic). "
                              "Échap pour annuler."),
                 PEINTURE: tr("Pinceau de couleur : peint sur le calque choisi. Alt+clic sur la photo : prendre une "
                              "couleur."),
                 TAMPON: tr("Tampon : Alt+clic sur l'endroit à copier, puis peins là où il doit être recopié."),
                 SUPPRIMER: tr("Supprimer (IA) : peins sur un fil, une tache, un bouton… ; au lâcher, il disparaît "
                               "(calque « Suppressions »). Pour un gros objet, préfère Effacer.")}
        if outil in aides:
            self.statusBar().showMessage(aides[outil], 10000)
        if outil == RECADRER:
            self._proportion()
        self.dock_texte.setVisible(outil == TEXTE)
        if outil == TEXTE:
            self._sync_texte()

    def _taille_changee(self, v: int):
        self.curseur_taille.blockSignals(True)
        self.curseur_taille.setValue(min(v, 600))
        self.curseur_taille.blockSignals(False)
        self.valeur_taille.setText(f"{v} px")

    def _panneau_ia(self):
        dock = QDockWidget(tr("INTELLIGENCE ARTIFICIELLE"), self)
        dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(10, 4, 10, 10)
        lay.setSpacing(8)
        aide = QLabel(tr("Peins sur l'objet avec le pinceau (ou entoure-le au lasso), puis choisis une action."))
        aide.setObjectName("discret")
        aide.setWordWrap(True)
        lay.addWidget(aide)
        self.b_effacer = Carte(tr("Effacer"), tr("Enlève ce qui est peint"))
        self.b_remplir = Carte(tr("Remplir"), tr("Redessine ce qui est peint"))
        self.texte_remplir = QLineEdit()
        self.texte_remplir.setPlaceholderText(tr("Texte facultatif (laisser vide)"))
        self.b_agrandir = Carte(tr("Agrandir l'image"), tr("Étend la photo au-delà des bords"))
        self.b_upscale = Carte(tr("Upscale"), tr("Augmente la définition"))
        self.b_arriere_plan = Carte(tr("Arrière-plan"), tr("Supprime le fond, garde le sujet"))
        for carte, fonction, nom in ((self.b_effacer, self.ia_effacer, "effacer"),
                                     (self.b_remplir, self.ia_remplir, "remplir"),
                                     (self.b_agrandir, self.ia_agrandir, "agrandir"),
                                     (self.b_upscale, self.ia_upscale, "upscale"),
                                     (self.b_arriere_plan, self.supprimer_arriere_plan, "arriere_plan")):
            carte.clicked.connect(fonction)
            self._icone(carte, nom)
        lay.addWidget(self.b_effacer)
        lay.addWidget(self.b_remplir)
        lay.addWidget(self.texte_remplir)
        lay.addSpacing(6)
        lay.addWidget(self.b_agrandir)
        lay.addWidget(self.b_upscale)
        lay.addWidget(self.b_arriere_plan)
        dock.setWidget(w)
        dock.setFixedWidth(290)
        w.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)

    def _panneau_calques(self):
        dock = QDockWidget(tr("CALQUES"), self)
        dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.calques = PanneauCalques(lambda nom: icone(nom, self.couleurs.texte, self.couleurs.accent, 20))
        self.calques.demande.connect(self._commande_calques)
        self.calques.style_demande.connect(self.style_calque)
        dock.setWidget(self.calques)
        dock.setFixedWidth(290)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)
        self.dock_calques = dock

    def _panneau_historique(self):
        """Liste des étapes (comme Photoshop) : un clic revient à cette étape ; les suivantes restent dans
        Rétablir tant qu'on ne fait rien d'autre."""
        dock = QDockWidget(tr("HISTORIQUE"), self)
        dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.vue_historique = QUndoView(self.historique)
        self.vue_historique.setEmptyLabel(tr("Photo ouverte"))
        dock.setWidget(self.vue_historique)
        dock.setFixedWidth(290)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)
        self.tabifyDockWidget(self.dock_calques, dock)
        self.dock_calques.raise_()
        self.dock_historique = dock

    def _panneau_texte(self):
        self.dock_texte = QDockWidget(tr("TEXTE"), self)
        self.dock_texte.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.panneau_texte = PanneauTexte(lambda nom: icone(nom, self.couleurs.texte, self.couleurs.accent, 20))
        try:                                       # style du dernier texte écrit
            self.panneau_texte.defaut = Texte.depuis_dict(json.loads(self.reglages.value("texte_defaut", "{}")))
            self.panneau_texte.afficher(None)
        except (ValueError, TypeError):
            pass
        self.panneau_texte.modifie.connect(self._texte_modifie)
        self.dock_texte.setWidget(self.panneau_texte)
        self.dock_texte.setFixedWidth(290)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.dock_texte)
        self.dock_texte.hide()

    # ---------------------------------------------------------- texte
    def _sync_texte(self):
        """Le panneau Texte montre le calque choisi s'il est un texte."""
        if not hasattr(self, "panneau_texte"):
            return
        c = self.doc.calque_actif if self.doc else None
        if c is not None and c.texte is not None:
            if self.panneau_texte.t is not c.texte:
                self.panneau_texte.afficher(c.texte, c.verrou)
        elif self.panneau_texte.lie or c is None:
            self.panneau_texte.afficher(None)
        self.canevas.update()

    def _nouveau_texte(self, pt):
        if not self.doc:
            return
        w, h = self.doc.taille()
        t = replace(self.panneau_texte.defaut, texte=tr("Texte"), x=pt.x(), y=pt.y(), angle=0.0,
                    taille=float(max(12, round(min(w, h) / 12))))
        self._session_texte += 1
        self.historique.push(CommandeEtat(self.doc, self.doc.etat(), self.doc.etat_nouveau_texte(t),
                                          tr("Nouveau texte")))
        self.panneau_texte.commencer_saisie()

    def _texte_choisi(self, index: int):
        if self.doc and index != self.doc.actif:
            self._session_texte += 1
            self.doc.actif = index
            self.doc.calques_changes.emit()

    def _texte_modifie(self, t: Texte, champ: str):
        doc = self.doc
        if not doc or doc.calque_actif.texte is None:
            return
        if doc.calque_actif.verrou:
            self.statusBar().showMessage(tr("Le calque « {nom} » est verrouillé : clique sur son cadenas pour "
                                            "pouvoir le modifier.", nom=doc.calque_actif.nom), 6000)
            self.panneau_texte.afficher(doc.calque_actif.texte, True)
            return
        cle = ("texte", self._session_texte, doc.actif, champ)
        self.historique.push(CommandeEtat(doc, doc.etat(), doc.etat_texte_modifie(doc.actif, t),
                                          tr("Modifier le texte"), cle))

    def _texte_en_pixels(self):
        if self.doc and self.doc.calque_actif.texte is not None and not self.doc.calque_actif.verrou:
            self.historique.push(CommandeEtat(self.doc, self.doc.etat(), self.doc.etat_en_pixels(self.doc.actif),
                                              tr("Convertir en image")))

    def _commande_calques(self, etat, texte: str):
        if self.doc and etat is not None:
            self.historique.push(CommandeEtat(self.doc, self.doc.etat(), etat, texte))

    def _barre_etat(self):
        self.pastille_moteur = QLabel()
        self.pastille_image = QLabel()
        for p_ in (self.pastille_moteur, self.pastille_image):
            p_.setObjectName("pastille_etat")
        self.statusBar().addWidget(self.pastille_moteur)
        self.statusBar().addPermanentWidget(self.pastille_image)
        self.statusBar().setSizeGripEnabled(False)
        self.canevas.infos.connect(self._infos_image)
        self.etat_moteur.connect(self._moteur_change)
        self.pastille_image.hide()

    def _infos_image(self, largeur: int, hauteur: int, zoom: float):
        self.pastille_image.setText(f"{largeur} × {hauteur} px")
        self.pastille_image.show()
        self.valeur_zoom.setText(f"{zoom * 100:.0f} %")

    def _moteur_change(self, texte: str):
        self.texte_moteur = texte
        self._peindre_pastille_moteur()

    def _peindre_pastille_moteur(self):
        c = self.couleurs
        etat = self.moteur.etat
        couleur = c.vert if etat == "prêt" else c.rouge if etat in ("introuvable", "erreur", "incomplet") \
            else c.orange
        texte = tr("Moteur IA : {etat}", etat=self.texte_moteur)
        self.pastille_moteur.setText(f'<span style="color:{couleur}">●</span>&nbsp; {texte}')

    # ---------------------------------------------------------- thème
    def changer_theme(self, mode: str):
        self.mode_theme = mode
        self.reglages.setValue("theme", mode)
        self.couleurs = theme.appliquer(QApplication.instance(), mode)
        self._appliquer_theme()

    def changer_langue(self, code: str):
        """La langue est choisie au démarrage : on propose de redémarrer Chrypix."""
        if code == self.reglages.value("langue", langue.AUTO):
            return
        self.reglages.setValue("langue", code)
        rep = QMessageBox.question(self, NOM, tr("La nouvelle langue sera utilisée au prochain démarrage de "
                                                 "Chrypix.\n\nRedémarrer maintenant ?"))
        if rep == QMessageBox.Yes and self._peut_fermer():
            chemin = str(self.doc.chemin) if self.doc and self.doc.chemin else None
            if self.doc:
                self.doc.modifie = False      # déjà proposé par _peut_fermer
            racine = str(Path(__file__).resolve().parents[1])
            QProcess.startDetached(sys.executable, ["-m", "chrypix"] + ([chemin] if chemin else []), racine)
            self.close()

    def _verifier_windows(self):
        signature = theme.signature_windows()
        if signature != self._signature_windows:
            self._signature_windows = signature
            self.changer_theme(self.mode_theme)

    def _basculer_theme(self):
        mode = theme.CLAIR if self.couleurs.sombre else theme.SOMBRE
        for a in self._actions_theme.actions():
            a.setChecked(a.text() == (tr("Clair") if mode == theme.CLAIR else tr("Sombre")))
        self.changer_theme(mode)

    def _appliquer_theme(self):
        c = self.couleurs
        for objet, nom in self._icones:
            ic = icone(nom, c.texte, c.accent)
            if isinstance(objet, Carte):
                objet.definir_icone(ic)
            else:
                objet.setIcon(ic)
        self.a_theme.setIcon(icone("soleil" if c.sombre else "lune", c.texte, c.accent))
        self.canevas.definir_couleurs(c.canevas, c.discret, c.accent)
        if hasattr(self, "calques"):
            self.calques.appliquer_icones()
        if hasattr(self, "panneau_texte"):
            self.panneau_texte.appliquer_icones()
        self._peindre_pastille_moteur()

    def _actualiser(self):
        a_doc = self.doc is not None
        pret = a_doc and self.moteur.etat == "prêt"
        for a in (self.a_enregistrer, self.a_enregistrer_sous, self.a_tout, self.a_rien, self.a_inverser,
                  self.a_zoom_plus, self.a_zoom_moins, self.a_ajuster, self.a_recadrer_selection, self.a_taille,
                  self.a_pivoter_d, self.a_pivoter_g, self.a_pivoter_180, self.a_miroir_h, self.a_miroir_v,
                  self.a_redresser, self.a_transformer, self.a_reglages_image, self.a_sel_agrandir,
                  self.a_sel_reduire, self.a_sel_adoucir, self.a_couper, self.a_copier, self.a_supprimer_selection,
                  self.a_style, self.a_copier_style, self.a_coller_style, self.a_enlever_style, self.a_figer_style,
                  self.a_nouveau_calque, self.a_dupliquer_calque):
            a.setEnabled(a_doc)
        for a in (self.a_effacer, self.a_remplir, self.a_agrandir, self.a_upscale, self.a_arriere_plan,
                  self.a_sujet):
            a.setEnabled(pret)
        for b in (self.b_effacer, self.b_remplir, self.b_agrandir, self.b_upscale, self.b_arriere_plan):
            b.setEnabled(pret)
        titre = NOM
        if self.doc:
            nom = self.doc.chemin.name if self.doc.chemin else tr("sans titre")
            titre = f"{nom}{' •' if self.doc.modifie else ''} — {NOM}"
        self.setWindowTitle(titre)

    def guide(self, chapitre: str | None = None):
        """Guide de Chrypix dans sa propre fenêtre (comme TwinPanel) ; F1 l'ouvre sur les raccourcis."""
        from .aide import FenetreGuide
        if getattr(self, "_fenetre_guide", None) is None or self._fenetre_guide.c is not self.couleurs:
            self._fenetre_guide = FenetreGuide(self.couleurs, self)
        self._fenetre_guide.ouvrir(chapitre)

    # ================================================================ moteur
    def installer_moteur(self):
        """Télécharge ComfyUI portable, ses extensions et les modèles (fenêtre qui montre tout avant)."""
        from .installation_moteur import PORTABLE, FenetreInstallation
        install = trouver_comfyui()
        dossier = None
        if install is not None:
            racine = Path(install["dir"]).parent
            if racine.name != PORTABLE or not (racine / "chrypix.json").is_file():
                QMessageBox.information(self, tr("Installer le moteur IA"),
                                        tr("Un ComfyUI est déjà installé sur ce PC et Chrypix l'utilise :\n{dossier}"
                                           "\n\nPour ajouter un modèle, mets-le dans son dossier « models ».",
                                           dossier=install["dir"]))
                return
            dossier = str(racine.parent)        # installé par Chrypix : on complète (ex. Flux Schnell)
        schnell = False
        if dossier is not None:
            from .installation_moteur import lire_infos
            infos = lire_infos(Path(dossier)) or {}
            schnell = "schnell" in infos.get("elements", []) or "schnell" in (infos.get("versions") or {})
        f = FenetreInstallation(self, dossier=dossier, schnell=schnell)
        f.commence.connect(self.moteur.arreter)      # ComfyUI ne doit pas tourner pendant qu'on le remplace
        f.installe.connect(lambda _d: self._redemarrer_moteur())
        f.exec()
        if self.moteur.etat == "arrêté":               # arrêté en route : on relance l'ancien
            self._redemarrer_moteur()

    def _verifier_moteur_a_jour(self):
        """Après le démarrage du moteur : si Chrypix l'a installé et qu'une nouvelle version de Chrypix demande
        d'autres versions (ComfyUI, extension, modèle), le proposer une fois."""
        from .installation_moteur import PORTABLE, go, mises_a_jour_moteur
        install = trouver_comfyui()
        if install is None:
            return
        r = Path(install["dir"]).parent
        if r.name != PORTABLE:
            return
        maj = mises_a_jour_moteur(r.parent)
        if not maj:
            return
        cle = ",".join(f"{e.cle}:{e.sha256 or e.url}" for e in maj)
        if self.reglages.value("moteur_maj_vue", "") == cle:
            self.statusBar().showMessage(tr("Une mise à jour du moteur IA attend : menu IA > Installer le moteur "
                                            "IA."), 10000)
            return
        self.reglages.setValue("moteur_maj_vue", cle)
        taille = sum(e.taille or 0 for e in maj)
        if QMessageBox.question(self, tr("Moteur IA"), tr(
                "Cette version de Chrypix utilise de nouvelles versions pour le moteur IA :\n{liste}\n\n"
                "À télécharger : environ {taille}. Le moteur sera arrêté pendant la mise à jour.\n\n"
                "Mettre à jour maintenant ? (Plus tard : menu IA > Installer le moteur IA.)",
                liste="\n".join("• " + e.nom for e in maj), taille=go(taille))) == QMessageBox.Yes:
            self.installer_moteur()

    def _redemarrer_moteur(self):
        self.moteur.arreter()
        self.moteur = Moteur()
        self.etat_moteur.emit(tr("démarrage…"))
        self._demarrer_moteur()

    def _demarrer_moteur(self):
        def travail(_progres):
            self.moteur.demarrer(self.etat_moteur.emit)
        t = self._tache(travail, lambda _: (self._actualiser(), self._verifier_moteur_a_jour()),
                        self._moteur_en_echec)
        t.lancer()

    def _moteur_en_echec(self, message: str):
        self.etat_moteur.emit(tr("indisponible"))
        self._actualiser()
        if self.moteur.etat == "introuvable":
            if QMessageBox.question(self, tr("Moteur IA"),
                                    tr("Le moteur IA (ComfyUI) n'est pas installé sur ce PC.\n\nVeux-tu que Chrypix "
                                       "l'installe maintenant ? Tu verras d'abord la liste des téléchargements "
                                       "(taille, source, licence).\n\nSans lui, tu peux quand même ouvrir, "
                                       "retoucher et enregistrer des photos.")) == QMessageBox.Yes:
                self.installer_moteur()
            return
        QMessageBox.warning(self, tr("Moteur IA"), tr("Le moteur IA n'a pas pu démarrer.\n\n{message}\n\n"
                                                      "Tu peux quand même ouvrir et enregistrer des photos.",
                                                      message=message))

    def _tache(self, fonction, ok, erreur) -> Tache:
        t = Tache(fonction)
        self._taches.add(t)

        def fin_ok(r):
            self._taches.discard(t)
            ok(r)

        def fin_erreur(m):
            self._taches.discard(t)
            erreur(m)
        t.fini.connect(fin_ok)
        t.echec.connect(fin_erreur)
        return t

    # ================================================================ fichiers
    def ouvrir(self):
        if not self._peut_fermer():
            return
        dossier = self.reglages.value("dossier", str(Path.home() / "Pictures"))
        chemin, _ = QFileDialog.getOpenFileName(self, tr("Ouvrir une photo"), dossier,
                                                f"{tr('Images')} ({EXTENSIONS_LECTURE});;{tr('Tous les fichiers')} (*)")
        if chemin:
            self.charger(chemin)

    def charger(self, chemin: str):
        try:
            doc = Document.ouvrir(chemin)
        except Exception as e:
            QMessageBox.critical(self, tr("Ouvrir"), tr("Impossible d'ouvrir ce fichier :\n{erreur}", erreur=e))
            return
        self.reglages.setValue("dossier", str(Path(chemin).parent))
        self._ajouter_recent(chemin)
        self._installer_document(doc)

    def _installer_document(self, doc: Document):
        if self.canevas.transfo is not None:
            self.canevas.finir_transfo()
            self._transfo_avant = None
        self.doc = doc
        self.historique.clear()
        doc.change.connect(self._actualiser)
        doc.calques_changes.connect(self._sync_texte)
        self.barre_agrandir.hide()
        self.canevas.cadre = None
        if hasattr(self, "selection_auto"):
            self.selection_auto.fin_session()
        self.canevas.definir_document(doc)
        self.calques.definir_document(doc)
        self._sync_texte()
        self._actualiser()
        if doc.remarques:
            self.statusBar().showMessage("  ".join(doc.remarques), 15000)

    def enregistrer(self) -> bool:
        if not self.doc:
            return False
        if self.doc.chemin is None:
            return self.enregistrer_sous()
        rep = QMessageBox.question(self, tr("Enregistrer"),
                                   tr("Remplacer le fichier d'origine ?\n{chemin}\n\n"
                                      "(« Non » pour choisir un autre nom)", chemin=self.doc.chemin),
                                   QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel, QMessageBox.No)
        if rep == QMessageBox.Cancel:
            return False
        if rep == QMessageBox.No:
            return self.enregistrer_sous()
        return self._ecrire(self.doc.chemin)

    def enregistrer_sous(self) -> bool:
        if not self.doc:
            return False
        plusieurs = len(self.doc.calques) > 1 or any(c.texte is not None or c.style is not None
                                                      for c in self.doc.calques)
        if self.doc.chemin:
            garde = not plusieurs or self.doc.chemin.suffix.lower() in (".psd", ".ora")
            ext = self.doc.chemin.suffix if garde else ".chr"
            propose = str(self.doc.chemin.with_name(self.doc.chemin.stem + tr("_retouche") + ext))
        else:
            propose = str(Path(self.reglages.value("dossier", str(Path.home()))) / ("image.chr" if plusieurs
                                                                                     else "image.jpg"))
        formats = [tr("Projet Chrypix") + " (*.chr)", tr("Photoshop, avec les calques") + " (*.psd)",
                   tr("OpenRaster, pour Krita et GIMP") + " (*.ora)",
                   "JPEG (*.jpg)", "PNG (*.png)", "TIFF (*.tif)", "WebP (*.webp)"]
        if self.doc.chemin and self.doc.chemin.suffix.lower() == ".psd":
            formats.insert(0, formats.pop(1))           # photo venue de Photoshop : PSD proposé d'abord
        elif not plusieurs:
            formats = formats[3:] + formats[:3]
        chemin, _ = QFileDialog.getSaveFileName(self, tr("Enregistrer sous"), propose, ";;".join(formats),
                                                formats[0])
        if not chemin:
            return False
        if not Path(chemin).suffix:
            chemin += ".jpg"
        return self._ecrire(Path(chemin))

    def _ecrire(self, chemin: Path) -> bool:
        if self.canevas.transfo is not None:
            self._valider_transfo()
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            self.doc.enregistrer(chemin)
        except Exception as e:
            QMessageBox.critical(self, tr("Enregistrer"), tr("Impossible d'enregistrer :\n{erreur}", erreur=e))
            return False
        finally:
            QApplication.restoreOverrideCursor()
        self._ajouter_recent(str(chemin))
        ext = chemin.suffix.lower()
        textes = any(c.texte is not None for c in self.doc.calques)
        styles = any(c.style is not None and not c.style.vide() for c in self.doc.calques)
        if len(self.doc.calques) > 1 and ext not in (".chr", ".ora", ".psd"):
            self.statusBar().showMessage(tr("Enregistré à plat (sans les calques) : {chemin}  —  pour garder les "
                                            "calques, enregistre aussi en .chr", chemin=chemin), 10000)
        elif ext in (".ora", ".psd") and textes:
            self.statusBar().showMessage(tr("Enregistré : {chemin}  —  dans ce format, les textes sont des images ; "
                                            "pour les garder modifiables, enregistre aussi en .chr",
                                            chemin=chemin), 10000)
        elif ext in (".ora", ".psd") and styles:
            self.statusBar().showMessage(tr("Enregistré : {chemin}  —  dans ce format, les styles de calque sont mis "
                                            "dans les pixels ; pour les garder modifiables, enregistre aussi en .chr",
                                            chemin=chemin), 10000)
        else:
            self.statusBar().showMessage(tr("Enregistré : {chemin}", chemin=chemin), 5000)
        self._actualiser()
        return True

    def _peut_fermer(self) -> bool:
        if not self.doc or not self.doc.modifie:
            return True
        rep = QMessageBox.question(self, NOM, tr("La photo a été modifiée. Enregistrer avant de continuer ?"),
                                   QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
        if rep == QMessageBox.Save:
            return self.enregistrer_sous()
        return rep == QMessageBox.Discard

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        urls = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        if urls and self._peut_fermer():
            self.charger(urls[0])

    def closeEvent(self, e):
        if not self._peut_fermer():
            e.ignore()
            return
        self.moteur.arreter()
        self.reglages.setValue("texte_defaut", json.dumps(self.panneau_texte.defaut.vers_dict(), ensure_ascii=False))
        e.accept()

    # ================================================================ sélection
    def _selection_modifiee(self, avant, texte):
        self.historique.push(CommandeEtat(self.doc, avant, self.doc.etat(), texte))

    # ================================================================ couper, copier, coller, supprimer
    def copier(self) -> bool:
        """Copie les pixels sélectionnés du calque choisi (tout le calque sans sélection) ; ils gardent leur
        transparence et leur place (pour Coller), et vont aussi aux autres logiciels (PNG)."""
        if not self.doc:
            return False
        img, place = self.doc.pixels_choisis()
        donnees = QMimeData()
        donnees.setImageData(img)
        tampon = QBuffer()
        tampon.open(QBuffer.WriteOnly)
        img.save(tampon, "PNG")
        donnees.setData("image/png", tampon.data())
        donnees.setData(MIME_PLACE, f"{place.x()},{place.y()}".encode())
        QApplication.clipboard().setMimeData(donnees)
        self.statusBar().showMessage(tr("Copié : {l} × {h} px (calque « {nom} »).", l=img.width(), h=img.height(),
                                        nom=self.doc.calque_actif.nom), 5000)
        return True

    def couper(self):
        if not self.doc or not self._verifier_selection_simple() or not self._verifier_verrou(tr("Couper")):
            return
        avant = self.doc.etat()
        apres = self.doc.etat_effacer_selection()
        if apres is not None and self.copier():
            self.historique.push(CommandeEtat(self.doc, avant, apres, tr("Couper")))

    def coller(self):
        if not self.doc:
            self.nouvelle_depuis_presse_papiers()
            return
        donnees = QApplication.clipboard().mimeData()
        img = QApplication.clipboard().image()
        if donnees is None or img.isNull():
            self.statusBar().showMessage(tr("Le presse-papiers ne contient pas d'image."), 5000)
            return
        place = None
        if donnees.hasFormat(MIME_PLACE):
            try:
                x, y = (int(v) for v in bytes(donnees.data(MIME_PLACE)).decode().split(","))
                place = QPoint(x, y)
            except ValueError:
                pass
        avant = self.doc.etat()
        apres = self.doc.etat_coller(img.convertToFormat(QImage.Format_ARGB32_Premultiplied), place)
        self.historique.push(CommandeEtat(self.doc, avant, apres, tr("Coller")))

    def supprimer_selection(self):
        if not self.doc or not self._verifier_selection_simple() or \
                not self._verifier_verrou(tr("Supprimer la sélection")):
            return
        if self.doc.calque_actif.texte is not None:
            self.statusBar().showMessage(tr("Le texte « {nom} » devient une image : il n'est plus modifiable comme "
                                            "texte (Ctrl+Z pour revenir).", nom=self.doc.calque_actif.nom), 6000)
        avant = self.doc.etat()
        apres = self.doc.etat_effacer_selection()
        if apres is not None:
            self.historique.push(CommandeEtat(self.doc, avant, apres, tr("Supprimer la sélection")))

    # ================================================================ réglages de l'image
    def reglages_image(self):
        """Luminosité, contraste, couleurs, netteté du calque choisi (dans la sélection s'il y en a une), avec un
        aperçu en direct calculé en arrière-plan (la fenêtre reste fluide même sur une grande photo)."""
        if not self.doc or not self._verifier_verrou(tr("Réglages de l'image")):
            return
        doc = self.doc
        avant, modifie = doc.etat(), doc.modifie
        index, calque = doc.actif, doc.calque_actif
        selection = None if doc.selection_vide() else doc.selection.copy()
        d = FenetreReglages(calque.nom, selection is not None, self,
                            propose_auto=lambda: auto(calque.image, selection))
        d.adjustSize()                               # à droite, sur le panneau IA : la photo reste visible
        coin = self.mapToGlobal(self.rect().topRight())
        d.move(coin.x() - d.width() - 20, coin.y() + 110)
        suivi = {"occupe": False, "attente": None, "ouvert": True}

        def montrer(r, img):
            if not suivi["ouvert"]:
                return
            if neutre(r) or img is None:
                doc.apercu_calque(index, calque.image, calque.texte)
            else:
                doc.apercu_calque(index, img)

        def calculer(r):
            if suivi["occupe"]:
                suivi["attente"] = r                 # on ne garde que la dernière demande
                return
            if neutre(r):
                montrer(r, None)
                return
            suivi["occupe"] = True
            t = Tache(lambda _progres: ajuster(calque.image, r, selection))
            t.fini.connect(lambda img: fini(r, img))
            t.echec.connect(lambda _m: fini(r, None))
            suivi["tache"] = t                       # garde la tâche en vie
            t.lancer()

        def fini(r, img):
            suivi["occupe"] = False
            montrer(r, img)
            if suivi["attente"] is not None:
                r2, suivi["attente"] = suivi["attente"], None
                calculer(r2)

        d.change.connect(calculer)
        ok = d.exec() == QDialog.Accepted
        suivi["ouvert"] = False
        r = d.valeurs()
        doc.appliquer_etat(avant)
        doc.modifie = modifie
        if ok and not neutre(r):
            if calque.texte is not None:
                self.statusBar().showMessage(tr("Le texte « {nom} » devient une image : il n'est plus modifiable "
                                                "comme texte (Ctrl+Z pour revenir).", nom=calque.nom), 6000)
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                img = ajuster(calque.image, r, selection)
            finally:
                QApplication.restoreOverrideCursor()
            apres = doc.etat_calque_modifie(index, image=img, texte=None)
            self.historique.push(CommandeEtat(doc, avant, apres, tr("Réglages de l'image")))

    # ================================================================ nouvelle image, fichiers récents
    def nouvelle_image(self):
        if not self._peut_fermer():
            return
        pp = QApplication.clipboard().image()
        l, h = (pp.width(), pp.height()) if not pp.isNull() else (1920, 1080)
        d = NouvelleImage(l, h, self)
        if d.exec():
            self._installer_document(Document(d.image()))
            self.doc.modifie = True
            self._actualiser()

    def nouvelle_depuis_presse_papiers(self):
        img = QApplication.clipboard().image()
        if img.isNull():
            self.statusBar().showMessage(tr("Le presse-papiers ne contient pas d'image."), 5000)
            return
        if not self._peut_fermer():
            return
        self._installer_document(Document(img.convertToFormat(QImage.Format_ARGB32_Premultiplied)))
        self.doc.modifie = True
        self._actualiser()

    def _recents(self) -> list[str]:
        v = self.reglages.value("recents", [])
        return [v] if isinstance(v, str) else list(v or [])

    def _ajouter_recent(self, chemin: str):
        chemin = str(Path(chemin))
        liste = [chemin] + [c for c in self._recents() if c.lower() != chemin.lower()]
        self.reglages.setValue("recents", liste[:10])

    def _remplir_recents(self):
        m = self.m_recents
        m.clear()
        liste = self._recents()
        if not liste:
            a = m.addAction(tr("(aucun)"))
            a.setEnabled(False)
            return
        for i, c in enumerate(liste):
            a = m.addAction(f"&{(i + 1) % 10}  {Path(c).name}")
            a.setToolTip(c)
            a.setStatusTip(c)
            a.triggered.connect(lambda _=False, ch=c: self._ouvrir_recent(ch))
        m.addSeparator()
        m.addAction(tr("Effacer la liste"), lambda: self.reglages.setValue("recents", []))

    def _ouvrir_recent(self, chemin: str):
        if not Path(chemin).is_file():
            QMessageBox.information(self, tr("Fichiers récents"),
                                    tr("Ce fichier n'existe plus :\n{chemin}", chemin=chemin))
            self.reglages.setValue("recents", [c for c in self._recents() if c != chemin])
            return
        if self._peut_fermer():
            self.charger(chemin)

    # ================================================================ géométrie de l'image
    def _geometrie(self, titre: str, quoi):
        if not self.doc or not self._verifier_verrou(titre, tous=True):
            return
        avant = self.doc.etat()
        if quoi in ("h", "v"):
            apres = self.doc.etat_miroir(quoi == "h")
            if any(c.texte is not None for c in self.doc.calques):
                self.statusBar().showMessage(tr("Les textes retournés deviennent des images (Ctrl+Z pour "
                                                "revenir)."), 6000)
        else:
            apres = self.doc.etat_pivote(quoi)
        self.historique.push(CommandeEtat(self.doc, avant, apres, titre))

    def taille_image(self):
        if not self.doc or not self._verifier_verrou(tr("Taille de l'image"), tous=True):
            return
        w, h = self.doc.taille()
        d = TailleImage(w, h, self)
        if d.exec() and d.valeurs() != (w, h):
            W, H = d.valeurs()
            avant = self.doc.etat()
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                apres = self.doc.etat_taille(W, H)
            finally:
                QApplication.restoreOverrideCursor()
            self.historique.push(CommandeEtat(self.doc, avant, apres, tr("Taille de l'image")))

    def redresser(self):
        if not self.doc or not self._verifier_verrou(tr("Redresser"), tous=True):
            return
        d = Redresser(self.doc.image, self)
        if d.exec():
            angle, recadrer = d.valeurs()
            if abs(angle) < 0.05:
                return
            avant = self.doc.etat()
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                apres = self.doc.etat_redresse(angle, recadrer)
            finally:
                QApplication.restoreOverrideCursor()
            self.historique.push(CommandeEtat(self.doc, avant, apres, tr("Redresser")))

    # ================================================================ transformer un calque (Ctrl+T)
    # ================================================================ style du calque
    def style_calque(self):
        if not self.doc or getattr(self, "_dialogue_style", None) is not None:
            return
        if self.canevas.transfo is not None:
            self._valider_transfo()
        from .dialogue_style import DialogueStyle
        d = DialogueStyle(self, self.doc.actif)
        self._dialogue_style = d
        self.canevas.style_ouvert = True
        self.canevas._curseur()

        def fin():
            self.canevas.style_ouvert = False
            self.canevas._curseur()
            self.canevas.update()
            self._dialogue_style = None
            d.deleteLater()
        d.fini.connect(fin)
        d.show()

    def copier_style(self):
        if not self.doc:
            return
        st = self.doc.calque_actif.style
        if st is None or st.vide():
            self.statusBar().showMessage(tr("Ce calque n'a pas de style à copier."), 5000)
            return
        self._style_copie = st
        self.statusBar().showMessage(tr("Style copié : choisis un autre calque, puis Calque > Coller le style."), 6000)

    def coller_style(self):
        st = getattr(self, "_style_copie", None)
        if not self.doc or st is None:
            self.statusBar().showMessage(tr("Aucun style copié (Calque > Copier le style)."), 5000)
            return
        self._commande_calques(self.doc.etat_calque_modifie(self.doc.actif, style=st), tr("Coller le style"))

    def enlever_style(self):
        if self.doc and self.doc.calque_actif.style is not None:
            self._commande_calques(self.doc.etat_calque_modifie(self.doc.actif, style=None), tr("Enlever le style"))

    def figer_style(self):
        """Les effets deviennent des pixels du calque (pour le gommer, le peindre… avec ses effets)."""
        if not self.doc:
            return
        c = self.doc.calque_actif
        if c.style is None or c.style.vide():
            self.statusBar().showMessage(tr("Ce calque n'a pas de style."), 5000)
            return
        if not self._verifier_verrou(tr("Mettre le style dans les pixels")):
            return
        from .styles import image_rendue
        self._commande_calques(self.doc.etat_calque_modifie(self.doc.actif, image=image_rendue(c), style=None,
                                                            texte=None), tr("Mettre le style dans les pixels"))

    def transformer(self):
        if not self.doc or self.canevas.transfo is not None or self.canevas.cadre is not None:
            return
        if not self._verifier_verrou(tr("Transformer le calque")):
            return
        c = self.doc.calque_actif
        a = tableau(c.image)[:, :, 3]
        ys, xs = (a > 0).nonzero()
        if not len(ys):
            self.statusBar().showMessage(tr("Le calque « {nom} » est vide : rien à transformer.", nom=c.nom), 6000)
            return
        from PySide6.QtCore import QRect
        rect = QRect(int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1))
        if c.texte is not None:
            self.statusBar().showMessage(tr("Le texte « {nom} » devient une image (pour garder un texte modifiable, "
                                            "change sa taille et tourne-le avec l'outil Texte).", nom=c.nom), 8000)
        self._transfo_avant = (self.doc.etat(), self.doc.modifie)
        self.canevas.commencer_transfo(Transformation(c.image, rect), self.doc.actif)
        self.opt_transfo.show()
        self._transfo_change()
        self.statusBar().showMessage(tr("Transformer : coins = taille (Maj : libre), dedans = déplacer, dehors = "
                                        "tourner (Maj : par 15°). Entrée pour valider, Échap pour annuler."), 15000)

    def _historique_bouge(self, _index):
        """Ctrl+Z ou clic dans l'Historique pendant une transformation : elle est abandonnée."""
        if self.canevas.transfo is not None:
            self.canevas.finir_transfo()
            self.opt_transfo.hide()
            self._transfo_avant = None

    def _transfo_change(self):
        t = self.canevas.transfo
        if t is not None:
            l, h, a = t.resume()
            self.info_transfo.setText(tr("Largeur {l} %  ·  Hauteur {h} %  ·  Angle {a}°", l=f"{l:.0f}",
                                         h=f"{h:.0f}", a=f"{a:.1f}"))

    def _valider_transfo(self):
        t = self.canevas.transfo
        if t is None or self._transfo_avant is None:
            return
        avant, _modifie = self._transfo_avant
        index = self.canevas._transfo_index
        w, h = self.doc.taille()
        img = t.rendu(w, h, lisse=True)
        self.canevas.finir_transfo()
        self.opt_transfo.hide()
        self._transfo_avant = None
        self.doc.appliquer_etat(avant)
        self.doc.modifie = _modifie
        c = self.doc.calques[index]
        style = c.style.mis_a_l_echelle(abs(t.sx * t.sy) ** 0.5) if c.style is not None else None
        apres = self.doc.etat_calque_modifie(index, image=img, texte=None, style=style)
        self.historique.push(CommandeEtat(self.doc, avant, apres, tr("Transformer le calque")))

    def _annuler_transfo(self):
        if self.canevas.transfo is None or self._transfo_avant is None:
            return
        avant, modifie = self._transfo_avant
        self.canevas.finir_transfo()
        self.opt_transfo.hide()
        self._transfo_avant = None
        self.doc.appliquer_etat(avant)
        self.doc.modifie = modifie
        self.statusBar().clearMessage()

    # ================================================================ sélection : agrandir, réduire, adoucir
    def _modifier_bord(self, mode: str):
        if not self.doc or not self._verifier_selection_simple():
            return
        titres = {"agrandir": tr("Agrandir la sélection"), "reduire": tr("Réduire la sélection"),
                  "adoucir": tr("Adoucir les bords")}
        cle = f"sel_{mode}"
        px, ok = QInputDialog.getInt(self, titres[mode], tr("De combien de pixels ?"),
                                     self.reglages.value(cle, 10, type=int), 1, 500)
        if not ok:
            return
        self.reglages.setValue(cle, px)
        avant = self.doc.etat()
        sel = self.doc.selection_modifiee(mode, px)
        apres = (self.doc.calques, self.doc.actif, sel)
        self.historique.push(CommandeEtat(self.doc, avant, apres, titres[mode]))

    # ================================================================ sujet / arrière-plan (IA, BiRefNet)
    def _detourage(self, titre: str, suite):
        """Demande au moteur le masque du sujet (calculé sur l'image visible), puis appelle suite(masque 0..255)."""
        if not self.doc:
            return
        if not recettes.detourage_disponible():
            QMessageBox.information(self, titre, tr(
                "Cette action a besoin du modèle BiRefNet (444 Mo), qui n'est pas installé. Menu IA > Installer le "
                "moteur IA permet de l'ajouter."))
            return
        doc = self.doc
        png = doc.png_pour_ia(False)
        annuler = threading.Event()

        def calcul(progres):
            nom = self.moteur.envoyer_image(png)
            prompt, sorties = recettes.detourer(nom)
            res = self.moteur.executer(prompt, sorties, annuler, progres)
            if not res:
                raise ErreurMoteur(tr("Le calcul s'est arrêté sans résultat."))
            img = QImage.fromData(res[0][1])
            if img.isNull():
                raise ErreurMoteur(tr("Résultat illisible."))
            w, h = doc.taille()
            if (img.width(), img.height()) != (w, h):
                img = img.scaled(w, h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            return tableau(img.convertToFormat(FORMAT_IMAGE))[:, :, 0].copy()

        attente = Attente(titre, self)
        attente.annuler.connect(annuler.set)

        def ok(m):
            attente.hide()
            attente.deleteLater()
            if doc is self.doc:
                suite(m)

        def echec(message):
            attente.hide()
            attente.deleteLater()
            if message:
                QMessageBox.warning(self, titre, message)

        t = self._tache(calcul, ok, echec)
        t.progres.connect(attente.maj)
        t.lancer()
        attente.show()

    def selectionner_sujet(self):
        def suite(m):
            from .document import _masque_vers_selection
            avant = self.doc.etat()
            sel = _masque_vers_selection(m).convertToFormat(QImage.Format_ARGB32_Premultiplied)
            self.historique.push(CommandeEtat(self.doc, avant, (self.doc.calques, self.doc.actif, sel),
                                              tr("Sélectionner le sujet")))
        self._detourage(tr("Sélectionner le sujet"), suite)

    def supprimer_arriere_plan(self):
        if not self.doc or not self._verifier_verrou(tr("Supprimer l'arrière-plan")):
            return

        def suite(m):
            import numpy as np
            from .document import qimage_rgba
            c = self.doc.calque_actif
            t = tableau(c.image.convertToFormat(FORMAT_IMAGE))
            t[:, :, 3] = (t[:, :, 3].astype(np.uint16) * m // 255).astype(np.uint8)
            img = qimage_rgba(t).convertToFormat(QImage.Format_ARGB32_Premultiplied)
            avant = self.doc.etat()
            apres = self.doc.etat_calque_modifie(self.doc.actif, image=img, texte=None)
            self.historique.push(CommandeEtat(self.doc, avant, apres, tr("Supprimer l'arrière-plan")))
            self.statusBar().showMessage(tr("Arrière-plan supprimé sur le calque « {nom} » : enregistrez en PNG, "
                                            "PSD ou .chr pour garder la transparence.", nom=c.nom), 10000)
        self._detourage(tr("Supprimer l'arrière-plan"), suite)

    # ================================================================ aide : à propos, mises à jour
    def a_propos(self):
        icone_app = QApplication.instance().windowIcon()
        APropos(icone_app.pixmap(96, 96) if not icone_app.isNull() else None, self, self.couleurs).exec()

    def verifier_maj(self, silencieux: bool = False):
        def ok(info):
            if mises_a_jour.plus_recente(info["version"]):
                notes = info["notes"][:600] + ("…" if len(info["notes"]) > 600 else "")
                rep = QMessageBox.question(self, tr("Mise à jour"), tr(
                    "Une nouvelle version de Chrypix est disponible : {v} (vous avez {actuelle}).\n\n{notes}\n\n"
                    "Ouvrir la page de téléchargement ?", v=info["version"], actuelle=__import__("chrypix").__version__,
                    notes=notes))
                if rep == QMessageBox.Yes:
                    QDesktopServices.openUrl(QUrl(info["page"]))
            elif not silencieux:
                QMessageBox.information(self, tr("Mise à jour"), tr("Chrypix est à jour."))

        def echec(message):
            if not silencieux:
                QMessageBox.information(self, tr("Mise à jour"), message or tr("La recherche a échoué."))

        def chercher(_progres):
            try:
                return mises_a_jour.derniere_version()
            except OSError as e:
                raise ErreurMoteur(str(e)) from e
        t = self._tache(chercher, ok, echec)
        t.lancer()

    def _verifier_selection_simple(self) -> bool:
        if self.doc.selection_vide():
            self.statusBar().showMessage(tr("Sélectionne d'abord une zone (rectangle, lasso ou pinceau de "
                                            "sélection)."), 6000)
            return False
        return True

    def _modifier_selection(self, quoi):
        if not self.doc:
            return
        avant = self.doc.etat()
        {"tout": self.doc.tout_selectionner, "rien": self.doc.deselectionner,
         "inverser": self.doc.inverser_selection}[quoi]()
        textes = {"tout": tr("Tout sélectionner"), "rien": tr("Désélectionner"), "inverser": tr("Inverser la sélection")}
        self.historique.push(CommandeEtat(self.doc, avant, self.doc.etat(), textes[quoi]))

    # ================================================================ IA
    def _verifier_selection(self) -> bool:
        if self.doc.selection_vide():
            QMessageBox.information(self, NOM, tr("Peins d'abord sur l'objet avec le pinceau (ou entoure-le au "
                                                  "lasso ou au rectangle)."))
            return False
        return True

    def _verifier_verrou(self, action: str, tous: bool = False) -> bool:
        """Faux (avec un message) si le calque choisi, ou un calque quelconque (tous=True), est verrouillé."""
        calques = self.doc.calques if tous else [self.doc.calque_actif]
        bloques = [c.nom for c in calques if c.verrou]
        if not bloques:
            return True
        noms = ", ".join(tr("« {nom} »", nom=n) for n in bloques)
        sujet = (tr("Les calques {noms} sont cadenassés", noms=noms) if len(bloques) > 1
                 else tr("Le calque {noms} est cadenassé", noms=noms))
        raison = (tr("{action} change la taille de tous les calques", action=action) if tous
                  else tr("{action} modifie le calque choisi", action=action))
        QMessageBox.information(self, action, tr("{sujet} : {raison}, c'est donc impossible.\n\nClique sur le "
                                                 "cadenas du calque dans le panneau Calques pour le déverrouiller.",
                                                 sujet=sujet, raison=raison))
        return False

    def ia_effacer(self):
        if self.doc and self._verifier_verrou(tr("Effacer")) and self._verifier_selection():
            self._lancer(tr("Effacer"), True, lambda nom: recettes.effacer(nom))

    def ia_remplir(self):
        if self.doc and self._verifier_verrou(tr("Remplir")) and self._verifier_selection():
            texte = self.texte_remplir.text().strip()
            self._lancer(tr("Remplir"), True, lambda nom: recettes.remplir(nom, texte))

    def ia_agrandir(self):
        if not self.doc:
            return
        if self.canevas.cadre is not None or not self._verifier_verrou(tr("Agrandir"), tous=True):
            return
        # bord abîmé proposé d'office : le liseré clair ou foncé détecté sur chaque bord
        abime = lisere_auto(tableau(self.doc.image)[:, :, :3])
        self.barre_agrandir.ouvrir(self.doc.image.width(), self.doc.image.height(), abime)
        self.canevas.commencer_cadre(abime)

    def _fin_agrandir(self):
        self.barre_agrandir.hide()
        self.canevas.finir_cadre()

    def _lancer_agrandir(self):
        if self.canevas.cadre is None or not self.barre_agrandir.b_lancer.isEnabled():
            return
        ajout, abime = self.barre_agrandir.valeurs_px()
        self._fin_agrandir()
        # 1. jeter le bord abîmé : la partie saine sert de base
        iw, ih = self.doc.image.width(), self.doc.image.height()
        ah, ab, ag, ad = abime
        image = self.doc.image.copy(ag, ah, iw - ag - ad, ih - ah - ab)
        # 2. l'IA redessine le bord jeté + l'agrandissement (taille finale = photo + ajout)
        total = [a + m for a, m in zip(ajout, abime)]
        w, h = image.width(), image.height()
        v = {cle: t * 100 / n for cle, t, n in zip(("haut", "bas", "gauche", "droite"), total, (h, h, w, w))}
        png, geo, orig = preparer(tableau(image)[:, :, :3], **v, enlever_lisere=False)

        def raccord(img: QImage) -> QImage:
            return qimage_rgb(finaliser(orig, tableau(img)[:, :, :3], geo))
        doc = self.doc

        def placer(img: QImage):   # calques décalés ; l'ajout de l'IA dans un nouveau calque
            return doc.etat_agrandi(tr("Agrandir"), img, (ajout[2], ajout[0]))
        self._lancer(tr("Agrandir"), False, lambda nom: recettes.agrandir(nom), apres=raccord, png=png,
                     placer=placer)

    def ia_upscale(self):
        if not self.doc or not self._verifier_verrou(tr("Upscale"), tous=True):
            return
        d = ReglagesUpscale(self.doc.image.width(), self.doc.image.height(), self)
        if d.exec():
            v = d.valeurs()
            if v["net"] and not recettes.schnell_disponible():
                QMessageBox.information(self, tr("Upscale"), tr(
                    "« Upscale net » a besoin du modèle Flux Schnell, qui n'est pas installé. Menu IA > Installer "
                    "le moteur IA permet de l'ajouter ; l'upscale simple marche sans."))
                return
            if v["net"]:
                taille = (self.doc.image.width(), self.doc.image.height())
                self._lancer(tr("Upscale"), False,
                             lambda nom: recettes.upscale_net(nom, v["facteur"], v["force"], taille))
            else:
                self._lancer(tr("Upscale"), False, lambda nom: recettes.upscale_rapide(nom, v["facteur"]))

    def _lancer(self, titre: str, avec_selection: bool, fabriquer, apres=None, png: bytes | None = None,
                placer=None):
        """Envoie l'image au moteur, attend, puis propose les résultats."""
        doc = self.doc
        if png is None:
            png = doc.png_pour_ia(avec_selection)
        original = doc.image
        choix = ChoixResultat(titre, original, self)
        annuler = threading.Event()
        nom_image = {}

        def calcul(progres):
            if "nom" not in nom_image:
                nom_image["nom"] = self.moteur.envoyer_image(png)
            recette = fabriquer(nom_image["nom"])
            prompt, sorties = recette[0], recette[1]
            morceaux = recette[2] if len(recette) > 2 else 1
            res = []
            for libelle, donnees in self.moteur.executer(prompt, sorties, annuler, progres, morceaux):
                img = QImage.fromData(donnees)
                if img.isNull():
                    raise ErreurMoteur(tr("Résultat illisible."))
                img = img.convertToFormat(FORMAT_IMAGE)
                res.append((libelle, apres(img) if apres else img))
            return res

        attente = Attente(titre, self)
        attente.annuler.connect(annuler.set)

        def premier_ok(res):
            attente.hide()
            attente.deleteLater()
            choix.ajouter(res)
            if choix.exec() and choix.choix() is not None:
                self._appliquer_resultat(doc, choix.choix(), titre, placer)
            annuler.set()

        def premier_echec(message):
            attente.hide()
            attente.deleteLater()
            if message:
                QMessageBox.warning(self, titre, message)

        def autres():
            annuler.clear()
            t2 = self._tache(calcul, choix.ajouter,
                             lambda m: choix.occupe(False, m or tr("Annulé.")))
            t2.progres.connect(choix.progression)
            t2.lancer()

        choix.autres_demandees.connect(autres)
        t = self._tache(calcul, premier_ok, premier_echec)
        t.progres.connect(attente.maj)
        t.lancer()
        attente.show()

    def _appliquer_resultat(self, doc: Document, image: QImage, titre: str, placer=None):
        """Le résultat choisi devient un nouveau calque (annulable)."""
        if doc is not self.doc:
            return
        avant = doc.etat()
        if placer is not None:
            apres = placer(image)
        elif image.size() == doc.image.size():
            apres = doc.etat_resultat_ia(titre, image)      # seulement les pixels retouchés
        else:
            apres = doc.etat_redimensionne(titre, image)    # Upscale
        # travail fini : la sélection disparaît (Ctrl+Z la fait revenir avec l'image d'avant)
        calques, actif, _sel = apres
        apres = (calques, actif, nouvelle_selection(calques[0].image.width(), calques[0].image.height()))
        self.historique.push(CommandeEtat(doc, avant, apres, titre))
