"""Affichage > Langues de l'orthographe… : les langues choisies à l'installation, modifiables ici. Une langue dont le
dictionnaire manque est téléchargée (LibreOffice) après accord ; décochée, un dictionnaire ajouté ici est effacé."""
from __future__ import annotations

import threading

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QLabel, QMessageBox, QProgressDialog,
                               QVBoxLayout)

from . import orthographe as o
from .langue import tr


class DialogueLangues(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Langues de l'orthographe"))
        lay = QVBoxLayout(self)
        aide = QLabel(tr("Langues dont l'orthographe est vérifiée (mots soulignés en rouge dans le panneau Texte). "
                         "La césure marche dans toutes ces langues, même sans dictionnaire."))
        aide.setWordWrap(True)
        lay.addWidget(aide)
        actives = o.langues_actives()
        self.cases = {}
        for l, nom in o.NOMS.items():
            src = o.SOURCES[l]
            if o.fichiers_langue(l) is not None:
                detail = tr("installé")
            else:
                detail = tr("à télécharger : {taille}, dictionnaire de LibreOffice ({auteur}), licence {licence}",
                            taille=src["taille"], auteur=src["auteur"], licence=src["licence"])
            c = QCheckBox(f"{nom} — {detail}")
            c.setChecked(l in actives)
            lay.addWidget(c)
            self.cases[l] = c
        boutons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        boutons.accepted.connect(self._valider)
        boutons.rejected.connect(self.reject)
        lay.addWidget(boutons)

    def _valider(self):
        voulues = [l for l, c in self.cases.items() if c.isChecked()]
        manquantes = [l for l in voulues if o.fichiers_langue(l) is None]
        if manquantes:
            details = "\n".join(f"• {o.NOMS[l]} : {o.SOURCES[l]['taille']}, licence {o.SOURCES[l]['licence']}"
                                for l in manquantes)
            if QMessageBox.question(self, tr("Télécharger"), tr(
                    "Télécharger depuis le dépôt des dictionnaires de LibreOffice (github.com/LibreOffice/"
                    "dictionaries) :\n{details}\n\nIls seront rangés dans %LOCALAPPDATA%\\Pixane\\dictionnaires.",
                    details=details)) != QMessageBox.Yes:
                return
            for l in manquantes:
                erreur = self._telecharger(l)
                if erreur:
                    QMessageBox.warning(self, tr("Télécharger"), tr(
                        "Le dictionnaire {nom} n'a pas pu être téléchargé (connexion ?) :\n{erreur}",
                        nom=o.NOMS[l], erreur=erreur))
                    voulues.remove(l)
        for l in o.FICHIERS:
            if l not in voulues:
                o.retirer_langue(l)
        o.choisir_langues(voulues)
        self.accept()

    def _telecharger(self, langue: str) -> str:
        """Téléchargement dans un fil à part (Pixane ne se fige pas) ; renvoie le message d'erreur, ou ""."""
        attente = QProgressDialog(tr("Téléchargement du dictionnaire {nom}…", nom=o.NOMS[langue]), None, 0, 0, self)
        attente.setWindowTitle(tr("Télécharger"))
        attente.setMinimumDuration(0)
        resultat = {}

        def travail():
            try:
                o.installer_langue(langue)
                resultat["ok"] = True
            except Exception as e:                      # réseau, disque…
                resultat["erreur"] = str(e) or type(e).__name__
        fil = threading.Thread(target=travail, daemon=True)
        fil.start()
        minuterie = QTimer(attente)
        minuterie.timeout.connect(lambda: attente.close() if not fil.is_alive() else None)
        minuterie.start(100)
        attente.exec()
        fil.join()
        return resultat.get("erreur", "")
