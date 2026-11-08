"""Fenêtre principale de Chrypix."""
from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import QObject, QSettings, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QActionGroup, QImage, QKeySequence, QUndoCommand, QUndoStack
from PySide6.QtWidgets import (QApplication, QDockWidget, QFileDialog, QLabel, QLineEdit, QMainWindow,
                               QMessageBox, QPushButton, QSlider, QToolBar, QVBoxLayout, QWidget)

from . import recettes
from .canevas import GOMME, LASSO, MAIN, PINCEAU, RECTANGLE, Canevas
from .dialogues import Attente, ChoixResultat, ReglagesAgrandir, ReglagesUpscale
from .document import EXTENSIONS_LECTURE, FORMAT_IMAGE, Document, nouvelle_selection
from .moteur import Annule, ErreurMoteur, Moteur

NOM = "Chrypix"


class Tache(QObject):
    """Exécute une fonction dans un fil secondaire et renvoie le résultat par signal."""
    fini = Signal(object)
    echec = Signal(str)
    progres = Signal(int)

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


class Fenetre(QMainWindow):
    etat_moteur = Signal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle(NOM)
        self.resize(1400, 900)
        self.setAcceptDrops(True)
        self.reglages = QSettings("Chrypix", "Chrypix")
        self.doc: Document | None = None
        self.historique = QUndoStack(self)
        self.historique.setUndoLimit(30)
        self.moteur = Moteur()
        self._taches = set()

        self.canevas = Canevas()
        self.canevas.selection_modifiee.connect(self._selection_modifiee)
        self.setCentralWidget(self.canevas)

        self.info_image = QLabel("")
        self.info_moteur = QLabel("Moteur IA : démarrage…")
        self.statusBar().addWidget(self.info_moteur)
        self.statusBar().addPermanentWidget(self.info_image)
        self.canevas.infos.connect(self.info_image.setText)
        self.etat_moteur.connect(lambda t: self.info_moteur.setText("Moteur IA : " + t))

        self._menus()
        self._outils()
        self._panneau_ia()
        self._actualiser()
        self._demarrer_moteur()

    # ================================================================ interface
    def _action(self, menu, texte, raccourci=None, fonction=None, cle=None):
        a = QAction(texte, self)
        if raccourci:
            a.setShortcut(QKeySequence(raccourci))
        if fonction:
            a.triggered.connect(fonction)
        menu.addAction(a)
        if cle:
            setattr(self, cle, a)
        return a

    def _menus(self):
        m = self.menuBar().addMenu("&Fichier")
        self._action(m, "Ouvrir…", QKeySequence.Open, self.ouvrir)
        self._action(m, "Enregistrer", QKeySequence.Save, self.enregistrer, "a_enregistrer")
        self._action(m, "Enregistrer sous…", "Ctrl+Shift+S", self.enregistrer_sous, "a_enregistrer_sous")
        m.addSeparator()
        self._action(m, "Quitter", "Ctrl+Q", self.close)

        m = self.menuBar().addMenu("&Édition")
        annuler = self.historique.createUndoAction(self, "Annuler")
        annuler.setShortcut(QKeySequence.Undo)
        retablir = self.historique.createRedoAction(self, "Rétablir")
        retablir.setShortcuts([QKeySequence("Ctrl+Y"), QKeySequence("Ctrl+Shift+Z")])
        m.addAction(annuler)
        m.addAction(retablir)

        m = self.menuBar().addMenu("&Sélection")
        self._action(m, "Tout sélectionner", "Ctrl+A", lambda: self._modifier_selection("tout"), "a_tout")
        self._action(m, "Désélectionner", "Ctrl+D", lambda: self._modifier_selection("rien"), "a_rien")
        self._action(m, "Inverser la sélection", "Ctrl+Shift+I", lambda: self._modifier_selection("inverser"),
                     "a_inverser")

        m = self.menuBar().addMenu("&Affichage")
        self._action(m, "Zoom avant", "Ctrl++", lambda: self.canevas.zoomer(1.25))
        self._action(m, "Zoom arrière", "Ctrl+-", lambda: self.canevas.zoomer(0.8))
        self._action(m, "Ajuster à la fenêtre", "Ctrl+0", self.canevas.ajuster)
        self._action(m, "Taille réelle (100 %)", "Ctrl+1", self.canevas.zoom_100)

        m = self.menuBar().addMenu("&IA")
        self._action(m, "Effacer", "Shift+E", self.ia_effacer, "a_effacer")
        self._action(m, "Remplir", "Shift+R", self.ia_remplir, "a_remplir")
        self._action(m, "Agrandir l'image…", "Shift+A", self.ia_agrandir, "a_agrandir")
        self._action(m, "Upscale…", "Shift+U", self.ia_upscale, "a_upscale")

        m = self.menuBar().addMenu("&Aide")
        self._action(m, "Raccourcis", None, self._aide)

    def _outils(self):
        barre = QToolBar("Outils")
        barre.setMovable(False)
        barre.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.addToolBar(Qt.LeftToolBarArea, barre)
        groupe = QActionGroup(self)
        for outil, texte, touche in ((MAIN, "Main", "H"), (RECTANGLE, "Rectangle", "M"), (LASSO, "Lasso", "L"),
                                     (PINCEAU, "Pinceau", "B"), (GOMME, "Gomme", "E")):
            a = QAction(texte, self, checkable=True)
            a.setShortcut(touche)
            a.setToolTip(f"{texte} ({touche})")
            a.triggered.connect(lambda _=False, o=outil: self.canevas.definir_outil(o))
            groupe.addAction(a)
            barre.addAction(a)
            if outil == PINCEAU:
                a.setChecked(True)
        barre.addSeparator()
        barre.addWidget(QLabel(" Taille"))
        self.curseur_taille = QSlider(Qt.Vertical)
        self.curseur_taille.setRange(2, 600)
        self.curseur_taille.setValue(self.canevas.taille_pinceau)
        self.curseur_taille.setFixedHeight(160)
        self.curseur_taille.valueChanged.connect(self.canevas.definir_taille)
        self.canevas.taille_changee.connect(lambda v: (self.curseur_taille.blockSignals(True),
                                                       self.curseur_taille.setValue(min(v, 600)),
                                                       self.curseur_taille.blockSignals(False)))
        barre.addWidget(self.curseur_taille)

    def _panneau_ia(self):
        dock = QDockWidget("IA", self)
        dock.setFeatures(QDockWidget.DockWidgetMovable)
        w = QWidget()
        lay = QVBoxLayout(w)
        aide = QLabel("1. Entoure la zone (pinceau, lasso…)\n2. Clique sur une action.\n"
                      "Alt + outil = retirer de la sélection.")
        aide.setWordWrap(True)
        lay.addWidget(aide)
        self.b_effacer = QPushButton("Effacer")
        self.b_effacer.clicked.connect(self.ia_effacer)
        self.texte_remplir = QLineEdit()
        self.texte_remplir.setPlaceholderText("Texte facultatif (laisser vide)")
        self.b_remplir = QPushButton("Remplir")
        self.b_remplir.clicked.connect(self.ia_remplir)
        self.b_agrandir = QPushButton("Agrandir l'image…")
        self.b_agrandir.clicked.connect(self.ia_agrandir)
        self.b_upscale = QPushButton("Upscale…")
        self.b_upscale.clicked.connect(self.ia_upscale)
        for b in (self.b_effacer, self.b_remplir, self.b_agrandir, self.b_upscale):
            b.setMinimumHeight(38)
        lay.addWidget(self.b_effacer)
        lay.addSpacing(8)
        lay.addWidget(self.texte_remplir)
        lay.addWidget(self.b_remplir)
        lay.addSpacing(8)
        lay.addWidget(self.b_agrandir)
        lay.addWidget(self.b_upscale)
        lay.addStretch(1)
        dock.setWidget(w)
        dock.setMinimumWidth(230)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)

    def _actualiser(self):
        a_doc = self.doc is not None
        pret = a_doc and self.moteur.etat == "prêt"
        for a in (self.a_enregistrer, self.a_enregistrer_sous, self.a_tout, self.a_rien, self.a_inverser):
            a.setEnabled(a_doc)
        for a in (self.a_effacer, self.a_remplir, self.a_agrandir, self.a_upscale):
            a.setEnabled(pret)
        for b in (self.b_effacer, self.b_remplir, self.b_agrandir, self.b_upscale):
            b.setEnabled(pret)
        titre = NOM
        if self.doc:
            nom = self.doc.chemin.name if self.doc.chemin else "sans titre"
            titre = f"{nom}{' *' if self.doc.modifie else ''} — {NOM}"
        self.setWindowTitle(titre)

    def _aide(self):
        QMessageBox.information(self, "Raccourcis", (
            "Outils : H main, M rectangle, L lasso, B pinceau, E gomme\n"
            "[ et ] : taille du pinceau\n"
            "Alt + outil : retirer de la sélection\n"
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
                self._lancer("Upscale", False, lambda nom: recettes.upscale_net(nom, v["facteur"], v["force"]))
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
            prompt, sorties = fabriquer(nom_image["nom"])
            bruts = self.moteur.executer(prompt, sorties, annuler, progres)
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
            t2.progres.connect(lambda s: choix.occupe(True, f"Calcul de nouvelles propositions… {s} s"))
            t2.lancer()

        choix.autres_demandees.connect(autres)
        t = self._tache(calcul, premier_ok, premier_echec)
        t.progres.connect(attente.secondes)
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
