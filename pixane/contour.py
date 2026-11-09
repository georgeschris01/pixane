"""Améliorer le contour d'une sélection (cheveux, poils, bords flous ou détourés grossièrement).

Autour du bord de la sélection (bande de « rayon » pixels), la transparence est recalculée d'après les couleurs de la
photo : filtre guidé en couleur (He, Sun, Tang), qui suit les vrais bords du sujet. Puis : lissage, contraste
(bord plus net) et décalage (bord rentré ou sorti). Le résultat devient la sélection ou le masque du calque.
"""
from __future__ import annotations

import numpy as np
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QVBoxLayout

from .dialogues_reglage import Curseur, _Panneau
from .filtres import _flou_pil, boite
from .langue import tr

DEFAUT = {"rayon": 12, "lissage": 0, "contraste": 0, "decalage": 0, "vue": "noir", "sortie": "selection"}
NEUTRE_CALCUL = ("rayon", "lissage", "contraste", "decalage")


def _guide_couleur(I: np.ndarray, P: np.ndarray, r: int, eps: float) -> np.ndarray:
    """Filtre guidé avec une image guide en couleur (h, w, 3) : P lissé en suivant les bords de couleur."""
    mI = boite(I, r)
    mP = boite(P, r)
    cov = boite(I * P[..., None], r) - mI * mP[..., None]
    # variance de I : matrice 3×3 symétrique par pixel
    S = np.empty(I.shape[:2] + (3, 3), np.float32)
    for i in range(3):
        for j in range(i, 3):
            v = boite(I[..., i] * I[..., j], r) - mI[..., i] * mI[..., j]
            S[..., i, j] = v
            S[..., j, i] = v
    S += eps * np.eye(3, dtype=np.float32)
    a = np.linalg.solve(S, cov[..., None])[..., 0]
    b = mP - np.einsum("hwc,hwc->hw", a, mI)
    return np.einsum("hwc,hwc->hw", boite(a, r), I) + boite(b, r)


def _moyenne_connue(I: np.ndarray, poids: np.ndarray, rayon: int) -> np.ndarray:
    """Couleur moyenne des pixels « connus » autour de chaque pixel ; le voisinage grandit là où il n'y en a pas."""
    res = np.zeros_like(I)
    reste = np.ones(poids.shape, bool)
    r = max(2, rayon)
    for _ in range(5):
        den = boite(poids, r)
        ok = reste & (den > 1e-3)
        if ok.any():
            num = boite(I * poids[..., None], r)
            res[ok] = num[ok] / den[ok][:, None]
            reste &= ~ok
        if not reste.any():
            return res
        r *= 2
    total = poids.sum()
    res[reste] = (I * poids[..., None]).sum((0, 1)) / total if total else 0.5
    return res


def bande(m: np.ndarray, rayon: int) -> np.ndarray:
    """Pixels à moins de `rayon` du bord de la sélection (booléens)."""
    dur = (m >= 128).astype(np.float32)
    f = boite(dur, max(1, rayon))
    return (f > 0.002) & (f < 0.998)


def affiner(rgb: np.ndarray, m: np.ndarray, p: dict) -> np.ndarray:
    """rgb (h, w, 3) uint8, m (h, w) 0..255 -> nouveau masque 0..255."""
    a = m.astype(np.float32) / 255
    rayon = int(p.get("rayon", 0))
    if rayon > 0:
        zone = bande(m, rayon)
        if zone.any():
            ys, xs = np.nonzero(zone)
            marge = 2 * rayon + 2
            h, w = m.shape
            y0, y1 = max(0, ys.min() - marge), min(h, ys.max() + marge + 1)
            x0, x1 = max(0, xs.min() - marge), min(w, xs.max() + marge + 1)
            I = rgb[y0:y1, x0:x1].astype(np.float32) / 255
            z = zone[y0:y1, x0:x1]
            dedans = m[y0:y1, x0:x1] >= 128
            sur_sujet = (dedans & ~z).astype(np.float32)          # sûrement le sujet
            sur_fond = (~dedans & ~z).astype(np.float32)          # sûrement le fond
            # couleur du sujet (F) et du fond (B) près de chaque pixel du bord, puis alpha = position de la
            # couleur du pixel entre B et F
            F = _moyenne_connue(I, sur_sujet, rayon)
            B = _moyenne_connue(I, sur_fond, rayon)
            d = F - B
            n2 = np.einsum("hwc,hwc->hw", d, d)
            brut = np.clip(np.einsum("hwc,hwc->hw", I - B, d) / (n2 + 1e-4), 0, 1)
            # là où sujet et fond ont presque la même couleur, on garde la sélection d'origine
            confiance = n2 / (n2 + 0.01)
            P = confiance * brut + (1 - confiance) * dedans
            q = np.clip(_guide_couleur(I, P.astype(np.float32), 2, 1e-4), 0, 1)
            morceau = a[y0:y1, x0:x1]
            morceau[z] = q[z]
    lissage = float(p.get("lissage", 0))
    if lissage > 0:
        a = _flou_pil(a, lissage)
    contraste = float(p.get("contraste", 0)) / 100
    decalage = float(p.get("decalage", 0)) / 100
    if contraste or decalage:
        k = 1 / max(0.02, 1 - 0.98 * contraste)
        a = (a - 0.5 + 0.5 * decalage) * k + 0.5
    return (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)


def apercu(rgb: np.ndarray, a: np.ndarray, vue: str) -> np.ndarray:
    """Image RGBA (h, w, 4) pour voir le contour : sujet sur noir, sur blanc, ou noir et blanc (le masque)."""
    h, w = a.shape
    out = np.empty((h, w, 4), np.uint8)
    out[..., 3] = 255
    if vue == "masque":
        out[..., :3] = a[..., None]
        return out
    fond = 0 if vue == "noir" else 255
    k = a.astype(np.float32)[..., None] / 255
    out[..., :3] = (rgb * k + fond * (1 - k) + 0.5).astype(np.uint8)
    return out


def noms_vues() -> dict:
    return {"noir": tr("Sur noir"), "blanc": tr("Sur blanc"), "masque": tr("Noir et blanc (le masque)"),
            "selection": tr("Sélection (rouge)")}


class PanneauContour(_Panneau):
    def __init__(self, params, histo=None):
        super().__init__(params, histo or {})
        lay = QVBoxLayout(self)
        ligne = QHBoxLayout()
        ligne.addWidget(QLabel(tr("Voir")))
        self.vue = QComboBox()
        for k, n in noms_vues().items():
            self.vue.addItem(n, k)
        self.vue.setCurrentIndex(max(0, self.vue.findData(self.p.get("vue", "noir"))))
        self.vue.currentIndexChanged.connect(self._lire)
        ligne.addWidget(self.vue)
        ligne.addStretch(1)
        lay.addLayout(ligne)
        self.c = {}
        for cle, lib, mini, maxi, unite in (("rayon", tr("Rayon (zone recalculée)"), 0, 120, " px"),
                                            ("lissage", tr("Lissage"), 0, 20, " px"),
                                            ("contraste", tr("Contraste du bord"), 0, 100, " %"),
                                            ("decalage", tr("Décaler le bord"), -100, 100, " %")):
            c = Curseur(lib, mini, maxi, self.p.get(cle, DEFAUT[cle]), unite)
            c.change.connect(self._lire)
            lay.addWidget(c)
            self.c[cle] = c
        ligne = QHBoxLayout()
        ligne.addWidget(QLabel(tr("Résultat")))
        self.sortie = QComboBox()
        self.sortie.addItem(tr("Nouvelle sélection"), "selection")
        self.sortie.addItem(tr("Masque du calque choisi"), "masque")
        self.sortie.setCurrentIndex(max(0, self.sortie.findData(self.p.get("sortie", "selection"))))
        self.sortie.currentIndexChanged.connect(self._lire)
        ligne.addWidget(self.sortie)
        ligne.addStretch(1)
        lay.addLayout(ligne)
        aide = QLabel(tr("Augmente le rayon jusqu'à ce que les cheveux ou les poils apparaissent. Contraste : bord "
                         "plus net. Décaler : négatif rentre le bord (enlève un liseré), positif le sort."))
        aide.setObjectName("discret")
        aide.setWordWrap(True)
        lay.addWidget(aide)

    def _lire(self):
        self.p = {k: int(c.valeur()) for k, c in self.c.items()}
        self.p["vue"] = self.vue.currentData()
        self.p["sortie"] = self.sortie.currentData()
        self.change.emit()


class ActionContour:
    """Mixin de la fenêtre : Sélection > Améliorer le contour…"""

    def ameliorer_contour(self):
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QApplication, QDialog

        from .dialogues_reglage import DialogueReglage
        from .document import _masque_vers_selection, masque, tableau, FORMAT_SELECTION
        from .composition import masque_depuis
        from .fenetre import CommandeEtat, Tache
        titre = tr("Améliorer le contour")
        if not self.doc or not self._verifier_selection_simple():
            return
        doc = self.doc
        avant, modifie = doc.etat(), doc.modifie
        m0 = masque(doc.selection).copy()
        rgb = tableau(doc.image.convertToFormat(QImage.Format_RGBA8888))[..., :3].copy()
        h, w = m0.shape
        p0 = dict(DEFAUT)
        for k in p0:
            v = self.reglages.value(f"contour_{k}", p0[k])
            p0[k] = v if isinstance(p0[k], str) else int(v)
        d = DialogueReglage(self, titre, tr("Recalcule le bord de la sélection d'après les couleurs de la photo."),
                            PanneauContour(p0), dict(DEFAUT, vue=p0["vue"], sortie=p0["sortie"]))
        d.adjustSize()
        coin = self.mapToGlobal(self.rect().topRight())
        d.move(coin.x() - d.width() - 20, coin.y() + 110)
        c = self.canevas
        suivi = {"occupe": False, "attente": None, "ouvert": True, "cle": None, "a": None}

        def montrer(p, a):
            if not suivi["ouvert"]:
                return
            c.apercu_plein = None
            c.apercu_selection = None
            if p is not None and a is not None:
                if p["vue"] == "selection":
                    c.apercu_selection = _masque_vers_selection(a)
                else:
                    t = apercu(rgb, a, p["vue"])
                    c.apercu_plein = QImage(t.data, w, h, w * 4, QImage.Format_RGBA8888).copy()
            c.update()

        def calculer(p):
            if suivi["occupe"]:
                suivi["attente"] = p
                return
            if p is None:
                montrer(None, None)
                return
            cle = tuple(p[k] for k in NEUTRE_CALCUL)
            if cle == suivi["cle"]:
                montrer(p, suivi["a"])
                return
            suivi["occupe"] = True
            t = Tache(lambda _progres: affiner(rgb, m0, p))
            t.fini.connect(lambda a: fini(p, cle, a))
            t.echec.connect(lambda _m: fini(p, None, None))
            suivi["tache"] = t
            t.lancer()

        def fini(p, cle, a):
            suivi["occupe"] = False
            if a is not None:
                suivi["cle"], suivi["a"] = cle, a
            montrer(p, a)
            if suivi["attente"] is not None:
                p2, suivi["attente"] = suivi["attente"], None
                calculer(p2)

        d.change.connect(calculer)
        d.change.emit(d.valeurs_apercu())
        ok = d.exec() == QDialog.Accepted
        suivi["ouvert"] = False
        p = d.valeurs()
        d.fermer()
        c.apercu_plein = None
        c.apercu_selection = None
        c.update()
        doc.modifie = modifie
        if not ok:
            return
        for k, v in p.items():
            self.reglages.setValue(f"contour_{k}", v)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            a = affiner(rgb, m0, p)
        finally:
            QApplication.restoreOverrideCursor()
        if p["sortie"] == "masque":
            calque = doc.calque_actif
            if calque.special or calque.verrou:
                self.statusBar().showMessage(tr("Ce calque ne peut pas recevoir de masque."), 6000)
                return
            apres = doc.etat_calque_modifie(doc.actif, masque=masque_depuis(a), masque_actif=True)
            calques, actif, _sel = apres
            from .document import nouvelle_selection
            apres = (calques, actif, nouvelle_selection(w, h))
        else:
            apres = (doc.calques, doc.actif, _masque_vers_selection(a).convertToFormat(FORMAT_SELECTION))
        self.historique.push(CommandeEtat(doc, avant, apres, titre))
