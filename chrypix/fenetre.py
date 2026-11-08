"""Fenêtre principale de Chrypix."""
from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import QObject, QSettings, QSize, Qt, Signal
from PySide6.QtGui import QAction, QActionGroup, QIcon, QImage, QKeySequence, QUndoCommand, QUndoStack
from PySide6.QtWidgets import (QApplication, QButtonGroup, QDockWidget, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
                               QMainWindow, QMessageBox, QPushButton, QSizePolicy, QSlider, QToolBar, QVBoxLayout,
                               QWidget)

from . import recettes, theme
from .icones import icone
from .canevas import GOMME, LASSO, MAIN, PINCEAU, RECTANGLE, Canevas
from .dialogues import Attente, ChoixResultat, ReglagesAgrandir, ReglagesUpscale
from .document import EXTENSIONS_LECTURE, FORMAT_IMAGE, Document, nouvelle_selection
from .moteur import Annule, ErreurMoteur, Moteur

NOM = "Chrypix"


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
    def __init__(self, doc: Document, avant, apres, texte: str):
        super().__init__(texte)
        self.doc, self.avant, self.apres = doc, avant, apres

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
        self.reglages = QSettings("Chrypix", "Chrypix")
        self.doc: Document | None = None
        self.historique = QUndoStack(self)
        self.historique.setUndoLimit(30)
        self.moteur = Moteur()
        self._taches = set()
        self._icones = []            # (objet, nom d'icône) à redessiner quand le thème change
        self.mode_theme = self.reglages.value("theme", theme.AUTO)
        self.couleurs = theme.appliquer(QApplication.instance(), self.mode_theme)
        self.texte_moteur = "démarrage…"

        self.canevas = Canevas()
        self.canevas.selection_modifiee.connect(self._selection_modifiee)
        self.setCentralWidget(self.canevas)

        self._menus()
        self._barre_commandes()
        self._outils()
        self._panneau_ia()
        self._barre_etat()
        self._appliquer_theme()
        self._actualiser()
        self._demarrer_moteur()

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
        m = self.menuBar().addMenu("&Fichier")
        self._action(m, "Ouvrir…", QKeySequence.Open, self.ouvrir, "a_ouvrir", "ouvrir")
        self._action(m, "Enregistrer", QKeySequence.Save, self.enregistrer, "a_enregistrer", "enregistrer")
        self._action(m, "Enregistrer sous…", "Ctrl+Shift+S", self.enregistrer_sous, "a_enregistrer_sous")
        m.addSeparator()
        self._action(m, "Quitter", "Ctrl+Q", self.close)

        m = self.menuBar().addMenu("&Édition")
        self.a_annuler = self.historique.createUndoAction(self, "Annuler")
        self.a_annuler.setShortcut(QKeySequence.Undo)
        self.a_retablir = self.historique.createRedoAction(self, "Rétablir")
        self.a_retablir.setShortcuts([QKeySequence("Ctrl+Y"), QKeySequence("Ctrl+Shift+Z")])
        self._icone(self.a_annuler, "annuler")
        self._icone(self.a_retablir, "retablir")
        m.addAction(self.a_annuler)
        m.addAction(self.a_retablir)

        m = self.menuBar().addMenu("&Sélection")
        self._action(m, "Tout sélectionner", "Ctrl+A", lambda: self._modifier_selection("tout"), "a_tout")
        self._action(m, "Désélectionner", "Ctrl+D", lambda: self._modifier_selection("rien"), "a_rien")
        self._action(m, "Inverser la sélection", "Ctrl+Shift+I", lambda: self._modifier_selection("inverser"),
                     "a_inverser")

        m = self.menuBar().addMenu("&Affichage")
        self._action(m, "Zoom avant", "Ctrl++", lambda: self.canevas.zoomer(1.25), "a_zoom_plus", "zoom_plus")
        self._action(m, "Zoom arrière", "Ctrl+-", lambda: self.canevas.zoomer(0.8), "a_zoom_moins", "zoom_moins")
        self._action(m, "Ajuster à la fenêtre", "Ctrl+0", self.canevas.ajuster, "a_ajuster", "ajuster")
        self._action(m, "Taille réelle (100 %)", "Ctrl+1", self.canevas.zoom_100)
        m.addSeparator()
        sous = m.addMenu("Thème")
        groupe = QActionGroup(self)
        for mode, texte in ((theme.AUTO, "Comme Windows"), (theme.CLAIR, "Clair"), (theme.SOMBRE, "Sombre")):
            a = QAction(texte, self, checkable=True)
            a.setChecked(mode == self.mode_theme)
            a.triggered.connect(lambda _=False, md=mode: self.changer_theme(md))
            groupe.addAction(a)
            sous.addAction(a)
        self._actions_theme = groupe

        m = self.menuBar().addMenu("&IA")
        self._action(m, "Effacer", "Shift+E", self.ia_effacer, "a_effacer", "effacer")
        self._action(m, "Remplir", "Shift+R", self.ia_remplir, "a_remplir", "remplir")
        self._action(m, "Agrandir l'image…", "Shift+A", self.ia_agrandir, "a_agrandir", "agrandir")
        self._action(m, "Upscale…", "Shift+U", self.ia_upscale, "a_upscale", "upscale")

        m = self.menuBar().addMenu("&Aide")
        self._action(m, "Raccourcis", "F1", self._aide)

    def _barre_commandes(self):
        """Barre du haut : fichiers, annuler, options de l'outil, zoom, thème."""
        b = QToolBar("Commandes")
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
        lay.addWidget(QLabel("Taille"))
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
        self.p_ajouter = QPushButton("Ajouter")
        self.p_retirer = QPushButton("Retirer")
        groupe = QButtonGroup(self)
        for p_, retirer in ((self.p_ajouter, False), (self.p_retirer, True)):
            p_.setObjectName("pastille")
            p_.setCheckable(True)
            p_.setCursor(Qt.PointingHandCursor)
            p_.setToolTip("Mode de sélection (Alt inverse le mode pendant le tracé)")
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
        self.a_theme = QAction("Thème clair / sombre", self)
        self.a_theme.triggered.connect(self._basculer_theme)
        b.addAction(self.a_theme)

    def _outils(self):
        barre = QToolBar("Outils")
        barre.setMovable(False)
        barre.setIconSize(QSize(22, 22))
        barre.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.addToolBar(Qt.LeftToolBarArea, barre)
        groupe = QActionGroup(self)
        for outil, texte, touche, nom in ((MAIN, "Main : déplacer la vue", "H", "main"),
                                          (RECTANGLE, "Sélection rectangle", "M", "rectangle"),
                                          (LASSO, "Lasso", "L", "lasso"),
                                          (PINCEAU, "Pinceau de sélection", "B", "pinceau"),
                                          (GOMME, "Gomme de sélection", "E", "gomme")):
            a = QAction(texte, self, checkable=True)
            a.setShortcut(touche)
            a.setToolTip(f"{texte}  ({touche})")
            a.triggered.connect(lambda _=False, o=outil: self._choisir_outil(o))
            self._icone(a, nom)
            groupe.addAction(a)
            barre.addAction(a)
            if outil == PINCEAU:
                a.setChecked(True)

    def _choisir_outil(self, outil: str):
        self.canevas.definir_outil(outil)
        self.options.setEnabled(outil != MAIN)

    def _taille_changee(self, v: int):
        self.curseur_taille.blockSignals(True)
        self.curseur_taille.setValue(min(v, 600))
        self.curseur_taille.blockSignals(False)
        self.valeur_taille.setText(f"{v} px")

    def _panneau_ia(self):
        dock = QDockWidget("INTELLIGENCE ARTIFICIELLE", self)
        dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(10, 4, 10, 10)
        lay.setSpacing(8)
        aide = QLabel("Entoure la zone avec le pinceau ou le lasso, puis choisis une action.")
        aide.setObjectName("discret")
        aide.setWordWrap(True)
        lay.addWidget(aide)
        self.b_effacer = Carte("Effacer", "Enlève l'objet entouré")
        self.b_remplir = Carte("Remplir", "Remplace la zone entourée")
        self.texte_remplir = QLineEdit()
        self.texte_remplir.setPlaceholderText("Texte facultatif (laisser vide)")
        self.b_agrandir = Carte("Agrandir l'image", "Étend la photo au-delà des bords")
        self.b_upscale = Carte("Upscale", "Augmente la définition")
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
        lay.addStretch(1)
        dock.setWidget(w)
        dock.setFixedWidth(290)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)

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
        self.pastille_moteur.setText(f'<span style="color:{couleur}">●</span>&nbsp; Moteur IA : {self.texte_moteur}')

    # ---------------------------------------------------------- thème
    def changer_theme(self, mode: str):
        self.mode_theme = mode
        self.reglages.setValue("theme", mode)
        self.couleurs = theme.appliquer(QApplication.instance(), mode)
        self._appliquer_theme()

    def _basculer_theme(self):
        mode = theme.CLAIR if self.couleurs.sombre else theme.SOMBRE
        for a in self._actions_theme.actions():
            a.setChecked(a.text() == ("Clair" if mode == theme.CLAIR else "Sombre"))
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
        self.canevas.definir_couleurs(c.canevas, c.discret)
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
            nom = self.doc.chemin.name if self.doc.chemin else "sans titre"
            titre = f"{nom}{' •' if self.doc.modifie else ''} — {NOM}"
        self.setWindowTitle(titre)

    def _aide(self):
        QMessageBox.information(self, "Raccourcis", (
            "Outils : H main, M rectangle, L lasso, B pinceau, E gomme\n"
            "[ et ] : taille du pinceau\n"
            "Alt pendant le tracé : inverse Ajouter / Retirer\n"
            "Espace + glisser, ou bouton du milieu : déplacer la vue\n"
            "Molette : zoom ; Ctrl+0 : ajuster ; Ctrl+1 : 100 %\n"
            "Ctrl+A tout, Ctrl+D désélectionner, Ctrl+Shift+I inverser\n"
            "Ctrl+Z annuler, Ctrl+Y rétablir\n"
            "Shift+E Effacer, Shift+R Remplir, Shift+A Agrandir, Shift+U Upscale"))

    # ================================================================ moteur
    def _demarrer_moteur(self):
        def travail(_progres):
            self.moteur.demarrer(self.etat_moteur.emit)
        t = self._tache(travail, lambda _: self._actualiser(), self._moteur_en_echec)
        t.lancer()

    def _moteur_en_echec(self, message: str):
        self.etat_moteur.emit("indisponible")
        self._actualiser()
        QMessageBox.warning(self, "Moteur IA", f"Le moteur IA n'a pas pu démarrer.\n\n{message}\n\n"
                            "Tu peux quand même ouvrir et enregistrer des photos.")

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
        chemin, _ = QFileDialog.getOpenFileName(self, "Ouvrir une photo", dossier,
                                                f"Images ({EXTENSIONS_LECTURE});;Tous les fichiers (*)")
        if chemin:
            self.charger(chemin)

    def charger(self, chemin: str):
        try:
            doc = Document.ouvrir(chemin)
        except Exception as e:
            QMessageBox.critical(self, "Ouvrir", f"Impossible d'ouvrir ce fichier :\n{e}")
            return
        self.reglages.setValue("dossier", str(Path(chemin).parent))
        self.doc = doc
        self.historique.clear()
        doc.change.connect(self._actualiser)
        self.canevas.definir_document(doc)
        self._actualiser()

    def enregistrer(self) -> bool:
        if not self.doc:
            return False
        if self.doc.chemin is None:
            return self.enregistrer_sous()
        rep = QMessageBox.question(self, "Enregistrer",
                                   f"Remplacer le fichier d'origine ?\n{self.doc.chemin}\n\n"
                                   "(« Non » pour choisir un autre nom)",
                                   QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel, QMessageBox.No)
        if rep == QMessageBox.Cancel:
            return False
        if rep == QMessageBox.No:
            return self.enregistrer_sous()
        return self._ecrire(self.doc.chemin)

    def enregistrer_sous(self) -> bool:
        if not self.doc:
            return False
        if self.doc.chemin:
            propose = str(self.doc.chemin.with_name(self.doc.chemin.stem + "_retouche" + self.doc.chemin.suffix))
        else:
            propose = str(Path(self.reglages.value("dossier", str(Path.home()))) / "image.jpg")
        chemin, _ = QFileDialog.getSaveFileName(self, "Enregistrer sous", propose,
                                                "JPEG (*.jpg);;PNG (*.png);;TIFF (*.tif);;WebP (*.webp)")
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
            QMessageBox.critical(self, "Enregistrer", f"Impossible d'enregistrer :\n{e}")
            return False
        finally:
            QApplication.restoreOverrideCursor()
        self.statusBar().showMessage(f"Enregistré : {chemin}", 5000)
        self._actualiser()
        return True

    def _peut_fermer(self) -> bool:
        if not self.doc or not self.doc.modifie:
            return True
        rep = QMessageBox.question(self, NOM, "La photo a été modifiée. Enregistrer avant de continuer ?",
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
        textes = {"tout": "Tout sélectionner", "rien": "Désélectionner", "inverser": "Inverser la sélection"}
        self.historique.push(CommandeEtat(self.doc, avant, self.doc.etat(), textes[quoi]))

    # ================================================================ IA
    def _verifier_selection(self) -> bool:
        if self.doc.selection_vide():
            QMessageBox.information(self, NOM, "Entoure d'abord la zone avec le pinceau, le lasso ou le rectangle.")
            return False
        return True

    def ia_effacer(self):
        if self.doc and self._verifier_selection():
            self._lancer("Effacer", True, lambda nom: recettes.effacer(nom))

    def ia_remplir(self):
        if self.doc and self._verifier_selection():
            texte = self.texte_remplir.text().strip()
            self._lancer("Remplir", True, lambda nom: recettes.remplir(nom, texte))

    def ia_agrandir(self):
        if not self.doc:
            return
        d = ReglagesAgrandir(self)
        if d.exec():
            v = d.valeurs()
            self._lancer("Agrandir", False, lambda nom: recettes.agrandir(nom, **v))

    def ia_upscale(self):
        if not self.doc:
            return
        d = ReglagesUpscale(self.doc.image.width(), self.doc.image.height(), self)
        if d.exec():
            v = d.valeurs()
            if v["net"]:
                taille = (self.doc.image.width(), self.doc.image.height())
                self._lancer("Upscale", False,
                             lambda nom: recettes.upscale_net(nom, v["facteur"], v["force"], taille))
            else:
                self._lancer("Upscale", False, lambda nom: recettes.upscale_rapide(nom, v["facteur"]))

    def _lancer(self, titre: str, avec_selection: bool, fabriquer):
        """Envoie l'image au moteur, attend, puis propose les résultats."""
        doc = self.doc
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
                    raise ErreurMoteur("Résultat illisible.")
                res.append((libelle, img.convertToFormat(FORMAT_IMAGE)))
            return res

        attente = Attente(titre, self)
        attente.annuler.connect(annuler.set)

        def premier_ok(res):
            attente.hide()
            attente.deleteLater()
            choix.ajouter(res)
            if choix.exec() and choix.choix() is not None:
                self._appliquer_resultat(doc, choix.choix(), titre)
            annuler.set()

        def premier_echec(message):
            attente.hide()
            attente.deleteLater()
            if message:
                QMessageBox.warning(self, titre, message)

        def autres():
            annuler.clear()
            t2 = self._tache(calcul, choix.ajouter,
                             lambda m: choix.occupe(False, m or "Annulé."))
            t2.progres.connect(choix.progression)
            t2.lancer()

        choix.autres_demandees.connect(autres)
        t = self._tache(calcul, premier_ok, premier_echec)
        t.progres.connect(attente.maj)
        t.lancer()
        attente.show()

    def _appliquer_resultat(self, doc: Document, image: QImage, titre: str):
        if doc is not self.doc:
            return
        avant = doc.etat()
        if image.size() == doc.image.size():
            apres = (image, doc.selection.copy())
        else:
            apres = (image, nouvelle_selection(image.width(), image.height()))
        self.historique.push(CommandeEtat(doc, avant, apres, titre))
