"""Actions (comme dans Photoshop) : enregistrer une suite d'opérations, puis la rejouer sur une autre image, ou sur
tout un dossier (Fichier > Traitement par lot).

Ce qui s'enregistre : les réglages (Image > Réglages), les filtres (Filtres), la taille de l'image, les rotations
et les retournements. Chaque étape garde ses réglages : elle se rejoue à l'identique, sans fenêtre.
Les actions sont gardées dans les réglages de Pixane (liste JSON) ; on peut les exporter / importer en .json.
"""
from __future__ import annotations

import json
import os

import numpy as np
from PySide6.QtCore import QSettings, Qt, Signal
from PySide6.QtWidgets import (QFileDialog, QHBoxLayout, QInputDialog, QLabel, QMenu, QMessageBox, QPushButton,
                               QToolButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from .langue import tr


def _reglages() -> QSettings:
    return QSettings("Pixane", os.environ.get("PIXANE_REGLAGES", "Pixane"))


def charger() -> list[dict]:
    try:
        d = json.loads(_reglages().value("actions", "[]") or "[]")
        return [a for a in d if isinstance(a, dict) and "nom" in a and isinstance(a.get("etapes"), list)]
    except (ValueError, TypeError):
        return []


def enregistrer(actions: list[dict]):
    _reglages().setValue("actions", json.dumps(actions, ensure_ascii=False))


# ------------------------------------------------------------------ étapes
def etape_taille(w: int, h: int, W: int, H: int) -> dict:
    """Taille de l'image : en proportion si les proportions sont gardées (marche sur des photos de toutes tailles),
    sinon en pixels."""
    if abs(W / w - H / h) < 0.01:
        return {"genre": "taille", "echelle": W / w}
    return {"genre": "taille", "largeur": W, "hauteur": H}


def nom_etape(e: dict) -> str:
    g = e.get("genre")
    if g == "reglage":
        from . import ajustements
        return ajustements.nom(e["type"])
    if g == "filtre":
        from . import filtres
        return filtres.noms().get(e["type"], e["type"])
    if g == "taille":
        if "echelle" in e:
            return tr("Taille de l'image : {p} %", p=f"{round(e['echelle'] * 100, 1):g}")
        return tr("Taille de l'image : {l} × {h} px", l=e["largeur"], h=e["hauteur"])
    if g == "geometrie":
        return {"h": tr("Retourner horizontalement"), "v": tr("Retourner verticalement"),
                90: tr("Pivoter de 90° à droite"), -90: tr("Pivoter de 90° à gauche"),
                180: tr("Pivoter de 180°")}.get(e["quoi"], str(e["quoi"]))
    return str(g)


def taille_apres(e: dict, w: int, h: int) -> tuple[int, int]:
    if "echelle" in e:
        return max(1, round(w * e["echelle"])), max(1, round(h * e["echelle"]))
    return int(e["largeur"]), int(e["hauteur"])


def appliquer_tableau(a: np.ndarray, e: dict) -> np.ndarray:
    """Une étape sur une image aplatie (RGBA uint8) : pour le traitement par lot."""
    from PIL import Image
    g = e.get("genre")
    if g == "reglage":
        from . import ajustements
        return ajustements.appliquer_rgba(a, e["type"], e["params"])
    if g == "filtre":
        from . import filtres
        return filtres.FONCTIONS[e["type"]](a, e["params"])
    if g == "taille":
        h, w = a.shape[:2]
        W, H = taille_apres(e, w, h)
        return np.asarray(Image.fromarray(a, "RGBA").resize((W, H), Image.LANCZOS))
    if g == "geometrie":
        q = e["quoi"]
        if q == "h":
            return a[:, ::-1].copy()
        if q == "v":
            return a[::-1].copy()
        return np.rot90(a, {90: -1, -90: 1, 180: 2}[q]).copy()
    return a


def etat_apres(doc, e: dict):
    """Une étape sur le document ouvert -> nouvel état (réglages et filtres : dans le calque choisi, dans la
    sélection s'il y en a une)."""
    from . import filtres
    g = e.get("genre")
    if g in ("reglage", "filtre"):
        if g == "reglage":
            from . import ajustements
            calcul = lambda t: ajustements.appliquer_rgba(t, e["type"], e["params"])
        else:
            calcul = lambda t: filtres.FONCTIONS[e["type"]](t, e["params"])
        c = doc.calque_actif
        if c.special:
            return None
        sel = None if doc.selection_vide() else doc.selection
        return doc.etat_calque_modifie(doc.actif, image=filtres.appliquer_calque(c.image, calcul, sel), texte=None)
    if g == "taille":
        w, h = doc.taille()
        return doc.etat_taille(*taille_apres(e, w, h))
    if g == "geometrie":
        q = e["quoi"]
        return doc.etat_miroir(q == "h") if q in ("h", "v") else doc.etat_pivote(q)
    return None


# ------------------------------------------------------------------ panneau
class PanneauActions(QWidget):
    """Liste des actions et de leurs étapes ; ● enregistrer, ■ arrêter, ▶ jouer."""
    jouer = Signal(dict)
    etat_change = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.liste_actions = charger()
        self.en_cours: dict | None = None       # action en cours d'enregistrement
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        self.info = QLabel()
        self.info.setWordWrap(True)
        self.info.setObjectName("discret")
        lay.addWidget(self.info)
        self.arbre = QTreeWidget()
        self.arbre.setHeaderHidden(True)
        self.arbre.setContextMenuPolicy(Qt.CustomContextMenu)
        self.arbre.customContextMenuRequested.connect(self._menu)
        self.arbre.itemDoubleClicked.connect(lambda it, _c: self.lancer())
        lay.addWidget(self.arbre, 1)
        rang = QHBoxLayout()
        self.b_enr = QPushButton("● " + tr("Enregistrer"))
        self.b_enr.setToolTip(tr("Nouvelle action : ce que tu fais ensuite (réglages, filtres, taille, rotations) "
                                 "est enregistré, jusqu'à « Arrêter »"))
        self.b_enr.clicked.connect(self.commencer)
        self.b_stop = QPushButton("■ " + tr("Arrêter"))
        self.b_stop.clicked.connect(self.arreter)
        self.b_jouer = QPushButton("▶ " + tr("Jouer"))
        self.b_jouer.setToolTip(tr("Rejoue l'action choisie sur l'image ouverte (double-clic aussi)"))
        self.b_jouer.clicked.connect(self.lancer)
        rang.addWidget(self.b_enr)
        rang.addWidget(self.b_stop)
        lay.addLayout(rang)
        rang = QHBoxLayout()
        rang.addWidget(self.b_jouer, 1)
        # bouton et menu gardés dans self (un menu dont Python perd la trace fait planter Qt à la fermeture)
        self.b_plus = QToolButton()
        self.b_plus.setText("…")
        self.b_plus.setPopupMode(QToolButton.InstantPopup)
        self.menu_plus = QMenu(self.b_plus)
        self.menu_plus.addAction(tr("Renommer…"), self.renommer)
        self.menu_plus.addAction(tr("Supprimer l'action ou l'étape"), self.supprimer)
        self.menu_plus.addSeparator()
        self.menu_plus.addAction(tr("Exporter les actions…"), self._exporter_menu)
        self.menu_plus.addAction(tr("Importer des actions…"), self._importer_menu)
        self.b_plus.setMenu(self.menu_plus)
        rang.addWidget(self.b_plus)
        lay.addLayout(rang)
        self._remplir()

    # -------------------------------------------------- enregistrement
    def enregistre(self) -> bool:
        return self.en_cours is not None

    def commencer(self, nom: str | None = None):
        if nom is None:
            nom, ok = QInputDialog.getText(self, tr("Nouvelle action"), tr("Nom de l'action :"),
                                           text=tr("Action {n}", n=len(self.liste_actions) + 1))
            if not ok or not nom.strip():
                return
        self.en_cours = {"nom": nom.strip(), "etapes": []}
        self.liste_actions.append(self.en_cours)
        self._remplir()

    def ajouter(self, e: dict):
        """Une opération vient d'être faite : elle s'ajoute à l'action en cours d'enregistrement."""
        if self.en_cours is None:
            return
        self.en_cours["etapes"].append(e)
        enregistrer(self.liste_actions)
        self._remplir()

    def arreter(self):
        if self.en_cours is None:
            return
        if not self.en_cours["etapes"]:
            self.liste_actions.remove(self.en_cours)
        self.en_cours = None
        enregistrer(self.liste_actions)
        self._remplir()

    # -------------------------------------------------- liste
    def _remplir(self):
        self.arbre.clear()
        for i, a in enumerate(self.liste_actions):
            it = QTreeWidgetItem([("● " if a is self.en_cours else "") + a["nom"]])
            it.setData(0, Qt.UserRole, (i, -1))
            for j, e in enumerate(a["etapes"]):
                sous = QTreeWidgetItem([nom_etape(e)])
                sous.setData(0, Qt.UserRole, (i, j))
                it.addChild(sous)
            self.arbre.addTopLevelItem(it)
            it.setExpanded(a is self.en_cours)
        if self.en_cours is not None:
            self.info.setText(tr("● Enregistrement de « {nom} » : fais tes réglages, filtres, changements de taille "
                                 "ou rotations, puis « Arrêter ».", nom=self.en_cours["nom"]))
        elif self.liste_actions:
            self.info.setText(tr("Choisis une action, puis ▶ Jouer (ou double-clic). Dans Fichier > Traitement par "
                                 "lot, une action peut traiter tout un dossier."))
        else:
            self.info.setText(tr("Aucune action. ● Enregistrer, puis fais tes réglages : ils pourront être rejoués "
                                 "d'un clic sur d'autres photos."))
        self.b_enr.setEnabled(self.en_cours is None)
        self.b_stop.setEnabled(self.en_cours is not None)
        self.b_jouer.setEnabled(self.en_cours is None and bool(self.liste_actions))
        self.etat_change.emit()

    def _choisie(self) -> tuple[int, int] | None:
        it = self.arbre.currentItem()
        if it is None:
            return (0, -1) if len(self.liste_actions) == 1 else None
        return it.data(0, Qt.UserRole)

    def _menu(self, pos):
        it = self.arbre.itemAt(pos)
        if it is None:
            return
        self.arbre.setCurrentItem(it)
        m = QMenu(self)
        if self.en_cours is None:
            m.addAction("▶ " + tr("Jouer"), self.lancer)
        m.addAction(tr("Renommer…"), self.renommer)
        m.addAction(tr("Supprimer l'action ou l'étape"), self.supprimer)
        m.exec(self.arbre.viewport().mapToGlobal(pos))

    def lancer(self):
        c = self._choisie()
        if c is None or self.en_cours is not None:
            return
        self.jouer.emit(self.liste_actions[c[0]])

    def renommer(self):
        c = self._choisie()
        if c is None:
            return
        a = self.liste_actions[c[0]]
        nom, ok = QInputDialog.getText(self, tr("Renommer"), tr("Nom de l'action :"), text=a["nom"])
        if ok and nom.strip():
            a["nom"] = nom.strip()
            enregistrer(self.liste_actions)
            self._remplir()

    def supprimer(self):
        c = self._choisie()
        if c is None:
            return
        i, j = c
        if j >= 0:
            del self.liste_actions[i]["etapes"][j]
        else:
            if self.liste_actions[i] is self.en_cours:
                self.en_cours = None
            del self.liste_actions[i]
        enregistrer(self.liste_actions)
        self._remplir()

    def _exporter_menu(self):
        self.exporter()

    def _importer_menu(self):
        self.importer()

    def exporter(self, chemin: str | None = None):
        if chemin is None:
            chemin, _f = QFileDialog.getSaveFileName(self, tr("Exporter les actions"), "actions-pixane.json",
                                                     tr("Actions Pixane (*.json)"))
        if chemin:
            with open(chemin, "w", encoding="utf-8") as f:
                json.dump({"pixane-actions": 1, "actions": self.liste_actions}, f, ensure_ascii=False, indent=1)

    def importer(self, chemin: str | None = None):
        if chemin is None:
            chemin, _f = QFileDialog.getOpenFileName(self, tr("Importer des actions"), "", tr("Actions Pixane (*.json)"))
        if not chemin:
            return
        try:
            with open(chemin, encoding="utf-8") as f:
                d = json.load(f)
            nouvelles = [a for a in d.get("actions", []) if isinstance(a, dict) and "nom" in a
                         and isinstance(a.get("etapes"), list)]
        except (OSError, ValueError, AttributeError) as e:
            QMessageBox.warning(self, tr("Importer des actions"), tr("Fichier illisible : {e}", e=e))
            return
        self.liste_actions.extend(nouvelles)
        enregistrer(self.liste_actions)
        self._remplir()
