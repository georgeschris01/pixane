"""Fenêtre principale de Chrypix."""
from __future__ import annotations

import json
import os
import sys
import threading
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, QSettings, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QActionGroup, QIcon, QImage, QKeySequence, QUndoCommand, QUndoStack
from PySide6.QtWidgets import (QApplication, QButtonGroup, QDockWidget, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
                               QMainWindow, QMessageBox, QPushButton, QSizePolicy, QSlider, QToolBar, QVBoxLayout,
                               QWidget)

from . import langue, recettes, theme
from .icones import icone
from .langue import tr
from .calques import PanneauCalques
from .canevas import GOMME, GOMME_CALQUE, LASSO, MAIN, PINCEAU, RECTANGLE, TEXTE, Canevas
from .dialogues import Attente, BarreAgrandir, ChoixResultat, ReglagesUpscale
from .document import EXTENSIONS_LECTURE, FORMAT_IMAGE, Document, nouvelle_selection, qimage_rgb, tableau
from .moteur import Annule, ErreurMoteur, Moteur
from .panneau_texte import PanneauTexte
from .raccord import finaliser, lisere_auto, preparer
from .texte import Texte

NOM = "Chrypix"


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
        self._session_texte = 0      # regroupe les changements d'un même texte dans Annuler

        self._menus()
        self._barre_commandes()
        self._outils()
        self._panneau_ia()
        self._panneau_calques()
        self._panneau_texte()
        self._barre_etat()
        self._appliquer_theme()
        self._actualiser()
        self._demarrer_moteur()
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
        self._action(m, tr("Ouvrir…"), QKeySequence.Open, self.ouvrir, "a_ouvrir", "ouvrir")
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

        m = self.menuBar().addMenu(tr("&Sélection"))
        self._action(m, tr("Tout sélectionner"), "Ctrl+A", lambda: self._modifier_selection("tout"), "a_tout")
        self._action(m, tr("Désélectionner"), "Ctrl+D", lambda: self._modifier_selection("rien"), "a_rien")
        self._action(m, tr("Inverser la sélection"), "Ctrl+Shift+I", lambda: self._modifier_selection("inverser"),
                     "a_inverser")

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

        m = self.menuBar().addMenu(tr("&Aide"))
        self._action(m, tr("Raccourcis"), "F1", self._aide)

    def _barre_commandes(self):
        """Barre du haut : fichiers, annuler, options de l'outil, zoom, thème."""
        b = QToolBar(tr("Commandes"))
        b.setMovable(False)
        b.setIconSize(QSize(20, 20))
        self.addToolBar(Qt.TopToolBarArea, b)
        for a in (self.a_ouvrir, self.a_enregistrer):
            b.addAction(a)
        b.addSeparator()
        b.addAction(self.a_annuler)
        b.addAction(self.a_retablir)
        b.addSeparator()

        # options de l'outil (comme Photoshop)
        self.options = QWidget()
        lay = QHBoxLayout(self.options)
        lay.setContentsMargins(6, 0, 6, 0)
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
        lay.addSpacing(10)
        self.p_ajouter = QPushButton(tr("Ajouter"))
        self.p_retirer = QPushButton(tr("Retirer"))
        groupe = QButtonGroup(self)
        for p_, retirer in ((self.p_ajouter, False), (self.p_retirer, True)):
            p_.setObjectName("pastille")
            p_.setCheckable(True)
            p_.setCursor(Qt.PointingHandCursor)
            p_.setToolTip(tr("Mode de sélection (Alt inverse le mode pendant le tracé)"))
            p_.clicked.connect(lambda _=False, r=retirer: self.canevas.definir_mode_retirer(r))
            groupe.addButton(p_)
            lay.addWidget(p_)
        self.p_ajouter.setChecked(True)
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

    def _outils(self):
        barre = QToolBar(tr("Outils"))
        barre.setMovable(False)
        barre.setIconSize(QSize(22, 22))
        barre.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.addToolBar(Qt.LeftToolBarArea, barre)
        groupe = QActionGroup(self)
        self._actions_outils = {}
        for outil, texte, touche, nom in ((MAIN, tr("Main : déplacer la vue"), "H", "main"),
                                          (RECTANGLE, tr("Sélection rectangle"), "M", "rectangle"),
                                          (LASSO, tr("Lasso"), "L", "lasso"),
                                          (PINCEAU, tr("Pinceau de sélection"), "B", "pinceau"),
                                          (GOMME, tr("Gomme de sélection"), "E", "gomme"),
                                          (GOMME_CALQUE, tr("Gomme de calque : efface les pixels du calque choisi"),
                                           "G", "gomme_calque"),
                                          (TEXTE, tr("Texte : écrire, déplacer, tourner"), "T", "texte")):
            a = QAction(texte, self, checkable=True)
            a.setShortcut(touche)
            a.setToolTip(f"{texte}  ({touche})")
            a.triggered.connect(lambda _=False, o=outil: self._choisir_outil(o))
            self._icone(a, nom)
            groupe.addAction(a)
            barre.addAction(a)
            self._actions_outils[outil] = a
            if outil == PINCEAU:
                a.setChecked(True)

    def _choisir_outil(self, outil: str):
        self.canevas.definir_outil(outil)
        self._actions_outils[outil].setChecked(True)
        self.options.setEnabled(outil not in (MAIN, TEXTE))
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
        for carte, fonction, nom in ((self.b_effacer, self.ia_effacer, "effacer"),
                                     (self.b_remplir, self.ia_remplir, "remplir"),
                                     (self.b_agrandir, self.ia_agrandir, "agrandir"),
                                     (self.b_upscale, self.ia_upscale, "upscale")):
            carte.clicked.connect(fonction)
            self._icone(carte, nom)
        lay.addWidget(self.b_effacer)
        lay.addWidget(self.b_remplir)
        lay.addWidget(self.texte_remplir)
        lay.addSpacing(6)
        lay.addWidget(self.b_agrandir)
        lay.addWidget(self.b_upscale)
        dock.setWidget(w)
        dock.setFixedWidth(290)
        w.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)

    def _panneau_calques(self):
        dock = QDockWidget(tr("CALQUES"), self)
        dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.calques = PanneauCalques(lambda nom: icone(nom, self.couleurs.texte, self.couleurs.accent, 20))
        self.calques.demande.connect(self._commande_calques)
        dock.setWidget(self.calques)
        dock.setFixedWidth(290)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)

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
        self.panneau_texte.en_pixels.connect(self._texte_en_pixels)
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
                  self.a_zoom_plus, self.a_zoom_moins, self.a_ajuster):
            a.setEnabled(a_doc)
        for a in (self.a_effacer, self.a_remplir, self.a_agrandir, self.a_upscale):
            a.setEnabled(pret)
        for b in (self.b_effacer, self.b_remplir, self.b_agrandir, self.b_upscale):
            b.setEnabled(pret)
        titre = NOM
        if self.doc:
            nom = self.doc.chemin.name if self.doc.chemin else tr("sans titre")
            titre = f"{nom}{' •' if self.doc.modifie else ''} — {NOM}"
        self.setWindowTitle(titre)

    def _aide(self):
        QMessageBox.information(self, tr("Raccourcis"), tr(
            "Outils : H main, M rectangle, L lasso, B pinceau, E gomme de sélection, G gomme de calque, T texte\n"
            "[ et ] : taille du pinceau\n"
            "Alt pendant le tracé : inverse Ajouter / Retirer\n"
            "Espace + glisser, ou bouton du milieu : déplacer la vue\n"
            "Molette : zoom ; Ctrl+0 : ajuster ; Ctrl+1 : 100 %\n"
            "Ctrl+A tout, Ctrl+D désélectionner, Ctrl+Shift+I inverser\n"
            "Ctrl+Z annuler, Ctrl+Y rétablir\n"
            "Shift+E Effacer, Shift+R Remplir, Shift+A Agrandir, Shift+U Upscale\n"
            "Agrandir : Maj en tirant = les deux côtés ; Entrée lancer, Échap annuler\n"
            "Texte : clic = nouveau texte, glisser = déplacer, poignée ronde = tourner (Maj : par 15°)\n\n"
            "Le guide complet est dans docs\\{guide}.", guide=tr("GUIDE.md")))

    # ================================================================ moteur
    def _demarrer_moteur(self):
        def travail(_progres):
            self.moteur.demarrer(self.etat_moteur.emit)
        t = self._tache(travail, lambda _: self._actualiser(), self._moteur_en_echec)
        t.lancer()

    def _moteur_en_echec(self, message: str):
        self.etat_moteur.emit(tr("indisponible"))
        self._actualiser()
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
        self.doc = doc
        self.historique.clear()
        doc.change.connect(self._actualiser)
        doc.calques_changes.connect(self._sync_texte)
        self.barre_agrandir.hide()
        self.canevas.cadre = None
        self.canevas.definir_document(doc)
        self.calques.definir_document(doc)
        self._sync_texte()
        self._actualiser()

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
        plusieurs = len(self.doc.calques) > 1 or any(c.texte is not None for c in self.doc.calques)
        if self.doc.chemin:
            ext = ".chr" if plusieurs else self.doc.chemin.suffix
            propose = str(self.doc.chemin.with_name(self.doc.chemin.stem + tr("_retouche") + ext))
        else:
            propose = str(Path(self.reglages.value("dossier", str(Path.home()))) / ("image.chr" if plusieurs
                                                                                     else "image.jpg"))
        formats = [tr("Projet Chrypix") + " (*.chr)", tr("OpenRaster, pour Krita et GIMP") + " (*.ora)",
                   "JPEG (*.jpg)", "PNG (*.png)", "TIFF (*.tif)", "WebP (*.webp)"]
        if not plusieurs:
            formats = formats[2:] + formats[:2]
        chemin, _ = QFileDialog.getSaveFileName(self, tr("Enregistrer sous"), propose, ";;".join(formats),
                                                formats[0])
        if not chemin:
            return False
        if not Path(chemin).suffix:
            chemin += ".jpg"
        return self._ecrire(Path(chemin))

    def _ecrire(self, chemin: Path) -> bool:
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            self.doc.enregistrer(chemin)
        except Exception as e:
            QMessageBox.critical(self, tr("Enregistrer"), tr("Impossible d'enregistrer :\n{erreur}", erreur=e))
            return False
        finally:
            QApplication.restoreOverrideCursor()
        ext = chemin.suffix.lower()
        textes = any(c.texte is not None for c in self.doc.calques)
        if len(self.doc.calques) > 1 and ext not in (".chr", ".ora"):
            self.statusBar().showMessage(tr("Enregistré à plat (sans les calques) : {chemin}  —  pour garder les "
                                            "calques, enregistre aussi en .chr", chemin=chemin), 10000)
        elif ext == ".ora" and textes:
            self.statusBar().showMessage(tr("Enregistré : {chemin}  —  dans un .ora, les textes sont des images ; "
                                            "pour les garder modifiables, enregistre aussi en .chr",
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
        self._lancer(tr("Agrandir"), False, lambda nom: recettes.agrandir(nom), apres=raccord, png=png, placer=placer)

    def ia_upscale(self):
        if not self.doc or not self._verifier_verrou(tr("Upscale"), tous=True):
            return
        d = ReglagesUpscale(self.doc.image.width(), self.doc.image.height(), self)
        if d.exec():
            v = d.valeurs()
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
            bruts = self.moteur.executer(prompt, sorties, annuler, progres, morceaux)
            res = []
            for libelle, donnees in bruts:
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
        self.historique.push(CommandeEtat(doc, avant, apres, titre))
