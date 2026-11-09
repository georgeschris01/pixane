"""Actions de la fenêtre pour les masques, groupes, calques de réglage, réglages de couleur et filtres
(menus Image > Réglages, Calque, Filtres). Partie de la classe Fenetre (classe « mixin »)."""
from __future__ import annotations

import copy
from dataclasses import replace

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from . import ajustements, filtres
from .dialogues_reglage import PANNEAUX, DialogueReglage, PanneauFiltre, histogramme
from .document import FORMAT_IMAGE, masque, tableau
from .langue import tr


class ActionsCalques:
    # ---------------------------------------------------------------- menus
    def _menus_calques(self, m_image, m_calque):
        sous = m_image.addMenu(tr("Réglages"))
        for t in ("niveaux", "courbes", "balance", "noir_blanc", "vibrance"):
            raccourci = {"niveaux": "Ctrl+L", "courbes": "Ctrl+M", "balance": "Ctrl+B",
                         "noir_blanc": "Ctrl+Alt+Shift+B"}.get(t)
            self._action(sous, ajustements.nom(t) + "…", raccourci, lambda *_, t=t: self.reglage(t), f"a_regl_{t}")

        m_calque.addSeparator()
        sous = m_calque.addMenu(tr("Nouveau calque de réglage"))
        for t in ajustements.TYPES:
            self._action(sous, ajustements.nom(t) + "…", None, lambda *_, t=t: self.nouveau_calque_reglage(t),
                         f"a_cr_{t}")
        self._action(m_calque, tr("Modifier le réglage…"), None, self.modifier_reglage, "a_modifier_reglage")
        m_calque.addSeparator()
        self._action(m_calque, tr("Nouveau groupe"), None, lambda: self.calques.nouveau_groupe(), "a_nouveau_groupe")
        self._action(m_calque, tr("Grouper le calque"), "Ctrl+G", lambda: self.calques.grouper(), "a_grouper")
        self._action(m_calque, tr("Dégrouper"), "Ctrl+Shift+G", lambda: self.calques.degrouper(), "a_degrouper")
        m_calque.addSeparator()
        sous = m_calque.addMenu(tr("Masque de calque"))
        self._action(sous, tr("Ajouter : tout visible"), None, lambda: self.calques.ajouter_masque("blanc"),
                     "a_masque_blanc")
        self._action(sous, tr("Ajouter : montrer la sélection"), None,
                     lambda: self.calques.ajouter_masque("selection"), "a_masque_sel")
        self._action(sous, tr("Ajouter : cacher la sélection"), None,
                     lambda: self.calques.ajouter_masque("cacher_selection"), "a_masque_cacher")
        sous.addSeparator()
        self._action(sous, tr("Peindre le masque / les pixels"), "Ctrl+\\", self.basculer_cible_masque,
                     "a_masque_cible")
        self._action(sous, tr("Désactiver / réactiver le masque"), None, self.basculer_masque, "a_masque_actif")
        self._action(sous, tr("Inverser le masque"), None, self.inverser_masque, "a_masque_inverser")
        self._action(sous, tr("Masque vers sélection"), None, self.masque_vers_selection, "a_masque_selection")
        self._action(sous, tr("Appliquer le masque (dans les pixels)"), None, self.appliquer_masque,
                     "a_masque_appliquer")
        self._action(sous, tr("Supprimer le masque"), None, self.supprimer_masque, "a_masque_supprimer")

        m = self.menuBar().addMenu(tr("Fi&ltres"))
        noms = filtres.noms()
        for t in filtres.FILTRES:
            self._action(m, noms[t] + "…", None, lambda *_, t=t: self.filtre(t), f"a_filtre_{t}")
        return m

    def _actions_calques_doc(self) -> list:
        noms = [f"a_regl_{t}" for t in ("niveaux", "courbes", "balance", "noir_blanc", "vibrance")]
        noms += [f"a_cr_{t}" for t in ajustements.TYPES] + [f"a_filtre_{t}" for t in filtres.FILTRES]
        noms += ["a_taille_grille", "a_nouveau_repere", "a_effacer_reperes", "a_exporter_web"]
        noms += ["a_modifier_reglage", "a_nouveau_groupe", "a_grouper", "a_degrouper", "a_masque_blanc",
                 "a_masque_sel", "a_masque_cacher", "a_masque_cible", "a_masque_actif", "a_masque_inverser",
                 "a_masque_selection", "a_masque_appliquer", "a_masque_supprimer"]
        return [getattr(self, n) for n in noms]

    # ---------------------------------------------------------------- export web, lot
    def exporter_web(self):
        from .document import qimage_vers_pil
        from .export import DialogueExport
        if self.doc is None:
            return
        nom = self.doc.chemin.stem if self.doc.chemin else tr("sans titre")
        nom += getattr(self.doc, "suffixe_nom", None) or ""      # ex. « photo_restaurée » → photo_restaurée_web
        d = DialogueExport(self, qimage_vers_pil(self.doc.image), nom, self.doc.exif, self.doc.icc)
        if d.exec() == d.Accepted:
            self.statusBar().showMessage(tr("Exporté : {chemin}", chemin=d.chemin), 8000)
        d.deleteLater()

    def traitement_lot(self):
        from .export import DialogueLot
        d = DialogueLot(self)
        d.exec()
        d.deleteLater()

    # ---------------------------------------------------------------- règles, repères, grille
    def _menu_regles(self, m):
        def case(texte, raccourci, cle, defaut, fonction):
            a = self._action(m, texte, raccourci, None, cle)
            a.setCheckable(True)
            a.setChecked(self.reglages.value(cle, defaut) == "true")
            a.toggled.connect(lambda v: (self.reglages.setValue(cle, "true" if v else "false"), fonction(v)))
            fonction(a.isChecked())
            return a
        c = self.canevas
        case(tr("Règles"), "Ctrl+R", "a_regles", "false",
             lambda v: [w.setVisible(v) for w in (self.regle_h, self.regle_v, self.coin_regles)])
        case(tr("Grille"), "Ctrl+'", "a_grille", "false", lambda v: (setattr(c, "grille_visible", v), c.update()))
        case(tr("Repères"), "Ctrl+;", "a_reperes", "true", lambda v: (setattr(c, "reperes_visibles", v), c.update()))
        case(tr("Magnétisme (repères, grille, bords)"), "Ctrl+Shift+;", "a_magnetisme", "true",
             lambda v: setattr(c, "magnetisme", v))
        c.pas_grille = int(self.reglages.value("pas_grille", 100))
        self._action(m, tr("Taille de la grille…"), None, self.taille_grille, "a_taille_grille")
        self._action(m, tr("Nouveau repère…"), None, self.nouveau_repere, "a_nouveau_repere")
        self._action(m, tr("Effacer les repères"), None, self.effacer_reperes, "a_effacer_reperes")

    def taille_grille(self):
        from PySide6.QtWidgets import QInputDialog
        v, ok = QInputDialog.getInt(self, tr("Grille"), tr("Écart entre les lignes (pixels de l'image) :"),
                                    self.canevas.pas_grille, 2, 5000)
        if ok:
            self.canevas.pas_grille = v
            self.reglages.setValue("pas_grille", v)
            self.a_grille.setChecked(True)
            self.canevas.update()

    def nouveau_repere(self):
        if not self.doc:
            return
        from PySide6.QtWidgets import QInputDialog
        sens, ok = QInputDialog.getItem(self, tr("Nouveau repère"), tr("Sens :"), [tr("Horizontal"), tr("Vertical")],
                                        0, False)
        if not ok:
            return
        h = sens == tr("Horizontal")
        w_, h_ = self.doc.taille()
        v, ok = QInputDialog.getInt(self, tr("Nouveau repère"), tr("Position (pixels depuis le haut)") if h else
                                    tr("Position (pixels depuis la gauche)"), (h_ if h else w_) // 2, 0,
                                    h_ if h else w_)
        if ok:
            self.doc.reperes.append(("h" if h else "v", v))
            self.a_reperes.setChecked(True)
            self.canevas.update()

    def effacer_reperes(self):
        if self.doc:
            self.doc.reperes.clear()
            self.canevas.update()

    # ---------------------------------------------------------------- options des outils de dessin
    def _options_dessin(self, tout):
        from PySide6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QLabel, QSpinBox, QWidget
        from PySide6.QtGui import QColor
        from .outils_dessin import FORMES, noms_formes
        from .panneau_texte import BoutonCouleur
        c = self.canevas
        # dégradé
        self.opt_degrade = QWidget()
        lay = QHBoxLayout(self.opt_degrade)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        forme = QComboBox()
        forme.addItem(tr("Linéaire"), "lineaire")
        forme.addItem(tr("Radial"), "radial")
        forme.setCurrentIndex(max(0, forme.findData(self.reglages.value("degrade_forme", "lineaire"))))
        lay.addWidget(forme)
        lay.addWidget(QLabel(tr("vers")))
        self.opt_couleur2 = BoutonCouleur(tr("Couleur d'arrivée"))
        self.opt_couleur2.definir(self.reglages.value("degrade_couleur2", "#ffffffff"))
        transparent = QCheckBox(tr("transparent"))
        transparent.setChecked(self.reglages.value("degrade_transparent", "true") == "true")
        lay.addWidget(self.opt_couleur2)
        lay.addWidget(transparent)

        def maj_degrade(*_):
            c.forme_degrade = forme.currentData()
            c.couleur2 = None if transparent.isChecked() else QColor(self.opt_couleur2.couleur)
            self.opt_couleur2.setEnabled(not transparent.isChecked())
            self.reglages.setValue("degrade_forme", forme.currentData())
            self.reglages.setValue("degrade_couleur2", self.opt_couleur2.couleur)
            self.reglages.setValue("degrade_transparent", "true" if transparent.isChecked() else "false")
        forme.currentIndexChanged.connect(maj_degrade)
        transparent.toggled.connect(maj_degrade)
        self.opt_couleur2.change.connect(maj_degrade)
        maj_degrade()
        tout.addWidget(self.opt_degrade)
        # pot de peinture
        self.opt_seau = QWidget()
        lay = QHBoxLayout(self.opt_seau)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(QLabel(tr("Tolérance")))
        tol = QSpinBox()
        tol.setRange(0, 255)
        tol.setValue(int(self.reglages.value("seau_tolerance", 32)))
        tol.setToolTip(tr("Plus haut : la couleur déborde sur des teintes plus éloignées"))

        def maj_seau(v):
            c.tolerance_seau = v
            self.reglages.setValue("seau_tolerance", v)
        tol.valueChanged.connect(maj_seau)
        maj_seau(tol.value())
        lay.addWidget(tol)
        tout.addWidget(self.opt_seau)
        # formes
        self.opt_formes = QWidget()
        lay = QHBoxLayout(self.opt_formes)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        genre = QComboBox()
        for k, n in noms_formes().items():
            genre.addItem(n, k)
        genre.setCurrentIndex(max(0, genre.findData(self.reglages.value("forme", "rectangle"))))
        remplie = QCheckBox(tr("Remplie"))
        remplie.setChecked(self.reglages.value("forme_remplie", "true") == "true")
        remplie.setToolTip(tr("Décoché : seulement le contour (épaisseur = taille)"))

        def maj_forme(*_):
            c.forme = genre.currentData()
            c.forme_remplie = remplie.isChecked()
            remplie.setEnabled(c.forme not in ("ligne", "fleche"))
            self.reglages.setValue("forme", c.forme)
            self.reglages.setValue("forme_remplie", "true" if remplie.isChecked() else "false")
        genre.currentIndexChanged.connect(maj_forme)
        remplie.toggled.connect(maj_forme)
        maj_forme()
        lay.addWidget(genre)
        lay.addWidget(remplie)
        tout.addWidget(self.opt_formes)
        for w in (self.opt_degrade, self.opt_seau, self.opt_formes):
            w.hide()

    # ---------------------------------------------------------------- masques
    def basculer_cible_masque(self):
        if self.doc and self.doc.calque_actif.masque is not None:
            self.doc.cible_masque = not self.doc.cible_masque
            self.doc.calques_changes.emit()
            self.statusBar().showMessage(tr("Les outils de peinture travaillent sur le masque (noir cache, blanc "
                                            "montre).") if self.doc.cible_masque else
                                         tr("Les outils de peinture travaillent sur les pixels du calque."), 4000)

    def _masque_ou_message(self):
        if not self.doc:
            return None
        c = self.doc.calque_actif
        if c.masque is None:
            self.statusBar().showMessage(tr("Le calque « {nom} » n'a pas de masque.", nom=c.nom), 4000)
            return None
        return c

    def basculer_masque(self):
        c = self._masque_ou_message()
        if c is not None:
            self._commande_calques(self.doc.etat_calque_modifie(self.doc.actif, masque_actif=not c.masque_actif),
                                   tr("Désactiver le masque") if c.masque_actif else tr("Réactiver le masque"))

    def inverser_masque(self):
        c = self._masque_ou_message()
        if c is not None:
            m = c.masque.copy()
            m.invertPixels()
            self._commande_calques(self.doc.etat_calque_modifie(self.doc.actif, masque=m), tr("Inverser le masque"))

    def masque_vers_selection(self):
        c = self._masque_ou_message()
        if c is not None:
            from .composition import masque_tableau
            from .document import _masque_vers_selection
            avant = self.doc.etat()
            self.doc.selection = _masque_vers_selection(masque_tableau(c.masque)).convertToFormat(
                self.doc.selection.format())
            self.doc.change.emit()
            self._selection_modifiee(avant, tr("Masque vers sélection"))

    def appliquer_masque(self):
        etat = self.doc.etat_appliquer_masque() if self.doc else None
        if etat:
            self.doc.cible_masque = False
            self._commande_calques(etat, tr("Appliquer le masque"))

    def supprimer_masque(self):
        c = self._masque_ou_message()
        if c is not None:
            self.doc.cible_masque = False
            self._commande_calques(self.doc.etat_calque_modifie(self.doc.actif, masque=None), tr("Supprimer le masque"))

    # ---------------------------------------------------------------- aperçu commun
    def _histo_calque(self):
        doc = self.doc
        t = tableau(doc.image.convertToFormat(FORMAT_IMAGE)) if doc.calque_actif.special else \
            tableau(doc.calque_actif.image.convertToFormat(FORMAT_IMAGE))
        ok = t[..., 3] > 128
        if not doc.selection_vide():
            ok &= masque(doc.selection) > 128
        return histogramme(t[ok][:, :3] if ok.any() else t[..., :3])

    def _verifier_pixels(self, action: str) -> bool:
        if not self.doc or not self._verifier_verrou(action):
            return False
        c = self.doc.calque_actif
        if c.special:
            quoi = tr("un groupe") if c.groupe else tr("un calque de réglage")
            QMessageBox.information(self, action, tr("« {nom} » est {quoi} : il n'a pas de pixels. Choisis un "
                                                     "calque d'image.", nom=c.nom, quoi=quoi))
            return False
        return True

    def _dialogue_pixels(self, titre: str, panneau, neutres: dict, calcul, auto: bool = False,
                         toujours: bool = False):
        """Réglage ou filtre appliqué dans les pixels du calque choisi (dans la sélection s'il y en a une), avec un
        aperçu en direct calculé en arrière-plan."""
        from .fenetre import CommandeEtat, Tache
        doc = self.doc
        avant, modifie = doc.etat(), doc.modifie
        index, calque = doc.actif, doc.calque_actif
        selection = None if doc.selection_vide() else doc.selection.copy()
        ou = tr("dans la sélection") if selection is not None else tr("sur tout le calque")
        d = DialogueReglage(self, titre, tr("S'applique au calque « {nom} », {ou}.", nom=calque.nom, ou=ou),
                            panneau, neutres, auto)
        d.adjustSize()
        coin = self.mapToGlobal(self.rect().topRight())
        d.move(coin.x() - d.width() - 20, coin.y() + 110)
        suivi = {"occupe": False, "attente": None, "ouvert": True}

        def montrer(p, img):
            if not suivi["ouvert"]:
                return
            if img is None:
                doc.apercu_calque(index, calque.image, calque.texte)
            else:
                doc.apercu_calque(index, img)

        def calculer(p):
            if suivi["occupe"]:
                suivi["attente"] = p
                return
            if p is None or (p == neutres and not toujours):
                montrer(p, None)
                return
            suivi["occupe"] = True
            t = Tache(lambda _progres: filtres.appliquer_calque(calque.image, lambda a: calcul(a, p), selection))
            t.fini.connect(lambda img: fini(p, img))
            t.echec.connect(lambda _m: fini(p, None))
            suivi["tache"] = t
            t.lancer()

        def fini(p, img):
            suivi["occupe"] = False
            montrer(p, img)
            if suivi["attente"] is not None:
                p2, suivi["attente"] = suivi["attente"], None
                calculer(p2)

        d.change.connect(calculer)
        d.change.emit(d.valeurs_apercu())
        ok = d.exec() == QDialog.Accepted
        suivi["ouvert"] = False
        p = d.valeurs()
        d.fermer()
        doc.appliquer_etat(avant)
        doc.modifie = modifie
        if ok and (p != neutres or toujours):
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                img = filtres.appliquer_calque(calque.image, lambda a: calcul(a, p), selection)
            finally:
                QApplication.restoreOverrideCursor()
            apres = doc.etat_calque_modifie(index, image=img, texte=None)
            self.historique.push(CommandeEtat(doc, avant, apres, titre))
        return ok

    # ---------------------------------------------------------------- réglages de couleur
    def reglage(self, type_: str):
        """Image > Réglages : le réglage va dans les pixels du calque choisi."""
        titre = ajustements.nom(type_)
        if not self._verifier_pixels(titre):
            return
        neutres = ajustements.defaut(type_)
        panneau = PANNEAUX[type_](neutres, self._histo_calque())
        self._dialogue_pixels(titre, panneau, neutres,
                              lambda a, p: ajustements.appliquer_rgba(a, type_, p), auto=type_ == "niveaux")

    def nouveau_calque_reglage(self, type_: str):
        """Calque de réglage : modifiable à tout moment (double-clic), sans toucher aux pixels."""
        if not self.doc:
            return
        avant = self.doc.etat()
        etat = self.doc.etat_nouveau_reglage(type_, ajustements.defaut(type_), ajustements.nom(type_))
        self.doc.appliquer_etat(etat)
        if not self._editer_reglage(avant, ajustements.nom(type_), nouveau=True):
            self.doc.appliquer_etat(avant)

    def modifier_reglage(self):
        if not self.doc:
            return
        c = self.doc.calque_actif
        if c.reglage is None:
            QMessageBox.information(self, tr("Modifier le réglage"), tr("Choisis d'abord un calque de réglage dans "
                                                                         "le panneau Calques."))
            return
        self._editer_reglage(self.doc.etat(), tr("Modifier le réglage"))

    def _editer_reglage(self, avant, titre: str, nouveau: bool = False) -> bool:
        from .fenetre import CommandeEtat
        doc = self.doc
        index = doc.actif
        c = doc.calque_actif
        type_ = c.reglage["type"]
        depart = copy.deepcopy(c.reglage["params"])
        dessous = doc.calques[:index]
        from .composition import fusionner
        w, h = doc.taille()
        fond = tableau(fusionner(dessous, w, h).convertToFormat(FORMAT_IMAGE))
        histo = histogramme(fond[fond[..., 3] > 128][:, :3] if (fond[..., 3] > 128).any() else fond[..., :3])
        panneau = PANNEAUX[type_](depart, histo)
        neutres = ajustements.defaut(type_)
        d = DialogueReglage(self, ajustements.nom(type_), tr("Calque de réglage « {nom} » : il change tout ce qui est "
                                                             "dessous ; double-clic dessus pour y revenir.",
                                                             nom=c.nom), panneau, neutres,
                            auto=type_ == "niveaux")
        d.b_ok.setText(tr("OK"))
        d.adjustSize()
        coin = self.mapToGlobal(self.rect().topRight())
        d.move(coin.x() - d.width() - 20, coin.y() + 110)

        def montrer(p):
            if p is None:
                p = neutres
            calques = list(doc.calques)
            if index < len(calques) and calques[index].reglage is not None:
                calques[index] = replace(calques[index], reglage={"type": type_, "params": p})
                doc.calques = tuple(calques)
                doc._fusion = None
                doc.change.emit()
        d.change.connect(montrer)
        ok = d.exec() == QDialog.Accepted
        p = d.valeurs()
        d.fermer()
        montrer(depart)
        if not ok:
            return False
        apres = doc.etat_calque_modifie(index, reglage={"type": type_, "params": p})
        self.historique.push(CommandeEtat(doc, avant, apres, ajustements.nom(type_) if nouveau else titre))
        return True

    # ---------------------------------------------------------------- filtres
    def filtre(self, type_: str):
        titre = filtres.noms()[type_]
        if not self._verifier_pixels(titre):
            return
        neutres = filtres.defauts(type_)
        panneau = PanneauFiltre(type_, neutres, {})
        fonction = filtres.FONCTIONS[type_]
        self._dialogue_pixels(titre, panneau, neutres, lambda a, p: fonction(a, p), toujours=True)
