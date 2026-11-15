"""IA pour la photo : sélectionner / remplacer le ciel (SAM 3.1 + Flux Fill), coloriser et changer la lumière
(Flux Kontext), flou selon la profondeur (Depth Anything 3 : carte de profondeur, puis flou calculé par Pixane).

Mélangé à la fenêtre (Fenetre) : utilise moteur, doc, historique, _tache, _lancer, Attente…
"""
from __future__ import annotations

import threading

import numpy as np
from PIL import Image, ImageFilter
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QLabel, QMessageBox, QVBoxLayout

from . import choix_exemple, recettes
from .document import FORMAT_IMAGE, tableau
from .langue import tr
from .moteur import ErreurMoteur


def noms_ciels() -> dict:
    return {"bleu": tr("Ciel bleu avec quelques nuages"), "nuages": tr("Grands nuages"),
            "coucher": tr("Coucher de soleil"), "orage": tr("Ciel d'orage"), "nuit": tr("Nuit étoilée"),
            "aube": tr("Aube (couleurs pastel)")}


def noms_lumieres() -> dict:
    return {"doree": tr("Lumière dorée de fin de journée"), "studio": tr("Lumière douce de studio"),
            "gauche": tr("Lumière venant de la gauche"),
            "droite": tr("Lumière venant de la droite"), "contre_jour": tr("Contre-jour"),
            "nuit": tr("Nuit, éclairée par des lampadaires"), "neon": tr("Néons colorés"),
            "nuageux": tr("Temps couvert, sans ombres")}


# ------------------------------------------------------------------ flou selon la profondeur (calcul)
def _a_la_taille(carte: np.ndarray, w: int, h: int) -> np.ndarray:
    if carte.shape == (h, w):
        return carte
    return np.asarray(Image.fromarray((carte * 255).astype(np.uint8)).resize((w, h), Image.BILINEAR),
                      np.float32) / 255


def flou_profondeur(rgba: np.ndarray, prof: np.ndarray, p: dict, sujet: np.ndarray | None = None) -> np.ndarray:
    """rgba (h, w, 4) ; prof (h, w) 0..1 (proche = 1). p : x, y (point net), flou (rayon max, px), zone (0..100 :
    profondeur gardée nette autour du point), arriere (seulement ce qui est plus loin que le point), sujet (garder
    net tout le sujet : masque `sujet` 0..1, 1 = sujet, donné par le détourage)."""
    h, w = rgba.shape[:2]
    prof = _a_la_taille(prof, w, h)
    x = int(min(w - 1, max(0, p.get("x", w // 2))))
    y = int(min(h - 1, max(0, p.get("y", h // 2))))
    net = float(np.median(prof[max(0, y - 2):y + 3, max(0, x - 2):x + 3]))
    zone = p.get("zone", 15) / 100 * 0.5
    ecart = net - prof if p.get("arriere", False) else np.abs(prof - net)
    quantite = np.clip((ecart - zone) / max(1e-3, 1 - zone) * 2.0, 0, 1)        # 0 = net, 1 = flou maximal
    if sujet is not None and p.get("sujet", True):
        # la carte de profondeur se trompe parfois sur une partie du sujet (veste grise devant un mur gris) :
        # le détourage la rattrape
        quantite = quantite * (1 - _a_la_taille(sujet, w, h))
    rmax = float(p.get("flou", 20))
    if rmax <= 0.3 or not quantite.any():
        return rgba.copy()
    f = rgba.astype(np.float32)
    f[..., :3] *= f[..., 3:4] / 255                                            # prémultiplié : pas de halo
    niveaux = [0.0, 0.15, 0.35, 0.6, 1.0]
    # le flou ne prend que ce qui est lui-même flou : les parties nettes (le sujet) ne bavent pas en halo clair
    # autour d'elles
    poids = np.clip(quantite / niveaux[1], 0, 1)[..., None]
    fp = Image.fromarray(np.clip(np.round(f * poids), 0, 255).astype(np.uint8), "RGBA")
    pp = Image.fromarray(np.round(poids[..., 0] * 255).astype(np.uint8), "L")
    flous = []
    for k in niveaux:
        r = rmax * k
        if r < 0.3:
            flous.append(f)
            continue
        bf = np.asarray(fp.filter(ImageFilter.GaussianBlur(r)), np.float32)       # canaux flous un à un
        bp = np.asarray(pp.filter(ImageFilter.GaussianBlur(r)), np.float32)[..., None] / 255
        flous.append(np.where(bp > 0.01, bf / np.maximum(bp, 0.01), f))
    # entre deux niveaux : mélange selon la quantité de flou du point
    pos = quantite * (len(niveaux) - 1)
    i0 = np.clip(pos.astype(np.int32), 0, len(niveaux) - 2)
    t = (pos - i0)[..., None]
    res = np.zeros_like(f)
    for i in range(len(niveaux) - 1):
        m = (i0 == i)[..., None]
        if m.any():
            res = np.where(m, flous[i] * (1 - t) + flous[i + 1] * t, res)
    a = res[..., 3:4]
    res[..., :3] = np.where(a > 0.5, res[..., :3] * 255 / np.maximum(a, 1e-3), 0)
    return np.clip(np.round(res), 0, 255).astype(np.uint8)


def panneau_profondeur(rgba: np.ndarray, prof: np.ndarray, avec_sujet: bool = False):
    """Panneau de la fenêtre de réglage : clic = point qui reste net ; flou ; zone nette ; arrière seulement."""
    from PySide6.QtWidgets import QCheckBox
    from .dialogues_reglage import Curseur, _Panneau
    from .plage_couleurs import ApercuCliquable

    class PanneauProfondeur(_Panneau):
        def __init__(self, params, histo):
            super().__init__(params, histo)
            lay = QVBoxLayout(self)
            info = QLabel(tr("Cliquez sur ce qui doit rester net. Clair = proche, foncé = loin."))
            info.setWordWrap(True)
            lay.addWidget(info)
            gris = np.dstack([(prof * 255).astype(np.uint8)] * 3 + [np.full(prof.shape, 255, np.uint8)])
            self.apercu = ApercuCliquable(gris)
            self.apercu.setToolTip(tr("Clic : le point qui reste net"))
            self.apercu.clic.connect(self._clic)
            lay.addWidget(self.apercu, 0, Qt.AlignHCenter)
            self.c_flou = Curseur(tr("Flou"), 0, 80, self.p.get("flou", 20), " px")
            self.c_zone = Curseur(tr("Zone nette"), 0, 100, self.p.get("zone", 15), " %")
            self.sujet = QCheckBox(tr("Garder net tout le sujet (personnes, objet principal)"))
            self.sujet.setToolTip(tr("Le détourage rattrape ce que la carte de profondeur met à tort au loin (par "
                                     "exemple une veste grise devant un mur gris)."))
            self.sujet.setChecked(bool(self.p.get("sujet", True)))
            self.sujet.setVisible(avec_sujet)
            self.arriere = QCheckBox(tr("Ne pas flouter ce qui est plus proche que le point net"))
            self.arriere_info = QLabel()
            self.arriere_info.setWordWrap(True)
            self.arriere.setChecked(bool(self.p.get("arriere", False)))
            for c in (self.c_flou, self.c_zone):
                c.change.connect(self._lire)
                lay.addWidget(c)
            for c in (self.sujet, self.arriere):
                c.toggled.connect(self._lire)
                lay.addWidget(c)
            lay.addWidget(self.arriere_info)
            self._montrer_point()

        def _clic(self, x, y, _mods):
            ph, pw = prof.shape
            h, w = rgba.shape[:2]
            self.p["x"], self.p["y"] = int(x * w / pw), int(y * h / ph)
            self._montrer_point()
            self.change.emit()

        def _lire(self):
            self.p["flou"] = int(self.c_flou.valeur())
            self.p["zone"] = int(self.c_zone.valeur())
            self.p["arriere"] = self.arriere.isChecked()
            self.p["sujet"] = self.sujet.isChecked()
            self.change.emit()

        def _montrer_point(self):
            # la case « plus proche » ne change rien si le point net est déjà ce qu'il y a de plus proche
            ph, pw = prof.shape
            h, w = rgba.shape[:2]
            px = min(pw - 1, int(self.p.get("x", w // 2) * pw / w))
            py = min(ph - 1, int(self.p.get("y", h // 2) * ph / h))
            rien_devant = prof[py, px] >= np.percentile(prof, 97) - 0.02
            self.arriere_info.setText(
                tr("Rien n'est plus proche que ce point : cette case ne change rien ici. Elle sert quand vous "
                   "cliquez sur quelque chose au loin.") if rien_devant else
                tr("Cochée : ce qui est devant le point net reste net aussi."))
            self.apercu.montrer_image()
            pm = QPixmap(self.apercu.pixmap())
            ph, pw = prof.shape
            h, w = rgba.shape[:2]
            k = self.apercu.k
            pt = QPointF(self.p.get("x", w // 2) * pw / w * k, self.p.get("y", h // 2) * ph / h * k)
            q = QPainter(pm)
            q.setRenderHint(QPainter.Antialiasing)
            for couleur, ep in ((QColor(0, 0, 0), 4), (QColor(255, 80, 40), 2)):
                q.setPen(QPen(couleur, ep))
                q.drawEllipse(pt, 7, 7)
            q.end()
            self.apercu.setPixmap(pm)

        def params(self):
            return dict(self.p)

    return PanneauProfondeur


# ------------------------------------------------------------------ actions
class ActionsPhotoIA:
    # ---------------------------------------------------------- calcul d'une carte (masque, profondeur)
    def _carte_ia(self, titre: str, fabriquer, suite, toutes: bool = False):
        """Le moteur calcule une image grise (sur l'image visible) ; suite(tableau 0..255 à la taille de l'image).
        toutes : la recette a plusieurs sorties, suite reçoit la liste des tableaux."""
        from .dialogues import Attente
        doc = self.doc
        png = doc.png_pour_ia(False)
        annuler = threading.Event()

        def calcul(progres):
            nom = self.moteur.envoyer_image(png)
            prompt, sorties = fabriquer(nom)
            res = self.moteur.executer(prompt, sorties, annuler, progres)
            if not res:
                raise ErreurMoteur(tr("Le calcul s'est arrêté sans résultat."))
            cartes = []
            for _nom, octets in (res if toutes else res[:1]):
                img = QImage.fromData(octets)
                if img.isNull():
                    raise ErreurMoteur(tr("Résultat illisible."))
                w, h = doc.taille()
                if (img.width(), img.height()) != (w, h):
                    img = img.scaled(w, h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
                cartes.append(tableau(img.convertToFormat(FORMAT_IMAGE))[:, :, 0].copy())
            return cartes if toutes else cartes[0]

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

    def _sam_present(self, titre: str) -> bool:
        if recettes.sam_disponible():
            return True
        QMessageBox.information(self, titre, tr(
            "Cette action a besoin du modèle SAM 3.1, qui n'est pas installé. Menu IA > Installer le moteur IA "
            "permet de l'ajouter."))
        return False

    @staticmethod
    def _masque_ciel(m: np.ndarray) -> np.ndarray:
        """Masque du ciel, nuages compris, bord adouci. SAM laisse de côté les nuages et les oiseaux : tout ce qui
        n'est pas du ciel mais n'est pas relié au bas de l'image (entouré de ciel) en fait partie."""
        from PIL import ImageDraw
        h, w = m.shape
        ciel = m > 127
        img = Image.fromarray(np.where(ciel, 0, 255).astype(np.uint8)).copy()   # 255 = pas du ciel (copie : modifiable)
        for x in range(0, w, max(1, w // 400)):                               # ce qui touche le bas : le sol
            if img.getpixel((x, h - 1)) == 255:
                ImageDraw.floodfill(img, (x, h - 1), 128)
        sol = np.asarray(img) == 128
        if sol.any():
            ciel = ~sol
        r = max(1.0, max(w, h) / 900)
        douce = Image.fromarray(np.where(ciel, 255, 0).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r))
        return np.asarray(douce).copy()

    def _poser_selection(self, m: np.ndarray, titre: str):
        from .document import _masque_vers_selection
        from .fenetre import CommandeEtat
        avant = self.doc.etat()
        sel = _masque_vers_selection(m).convertToFormat(QImage.Format_ARGB32_Premultiplied)
        self.historique.push(CommandeEtat(self.doc, avant, (self.doc.calques, self.doc.actif, sel), titre))

    def ia_selection_ciel(self):
        titre = tr("Sélectionner le ciel")
        if not self.doc or not self._sam_present(titre):
            return

        def suite(m):
            if (m > 127).mean() < 0.002:
                QMessageBox.information(self, titre, tr("Pas de ciel trouvé dans cette image."))
                return
            self._poser_selection(self._masque_ciel(m), titre)
        self._carte_ia(titre, recettes.ciel, suite)

    def ia_remplacer_ciel(self):
        titre = tr("Remplacer le ciel")
        if not self.doc or not self._sam_present(titre) or not self._verifier_verrou(titre)                 or not self._kontext_present(titre):
            return
        cle = choix_exemple.choisir(self, titre, tr("Nouveau ciel :"), noms_ciels(), "ciel",
                                    self.reglages.value("ciel_style", "bleu"))
        if cle is None:
            return
        self.reglages.setValue("ciel_style", cle)
        texte = recettes.CIELS[cle]

        def suite(m):
            if (m > 127).mean() < 0.002:
                QMessageBox.information(self, titre, tr("Pas de ciel trouvé dans cette image."))
                return
            # Flux Kontext redessine la photo avec le nouveau ciel (lumière et horizon cohérents) ; seul le ciel
            # sélectionné en est gardé : le reste garde ses pixels d'origine
            self._poser_selection(self._masque_ciel(m), tr("Sélectionner le ciel"))
            taille = self.doc.taille()
            self._lancer(titre, False, lambda n: recettes.restaurer(n, taille, texte=recettes.TEXTE_CIEL.format(
                ciel=texte)), apres=self._dans_selection(titre), nom_calque=tr("Ciel"), suffixe=tr("_ciel"))
        self._carte_ia(tr("Recherche du ciel"), recettes.ciel, suite)

    # ---------------------------------------------------------- Flux Kontext : coloriser, lumière
    def _kontext_present(self, titre: str) -> bool:
        if recettes.restauration_disponible():
            return True
        QMessageBox.information(self, titre, tr(
            "Cette action a besoin du modèle Flux Kontext (11,9 Go), qui n'est pas installé. Menu IA > Installer "
            "le moteur IA permet de l'ajouter (case « Flux Kontext »)."))
        return False

    def _kontext(self, titre: str, consigne: str, nom_calque: str, suffixe: str):
        """Consigne toute prête (en anglais) envoyée à Flux Kontext, comme « Modifier avec une consigne » : sur la
        sélection s'il y en a une, sinon sur toute l'image."""
        from . import modifier_ia
        from .document import masque
        doc = self.doc
        zone = None if doc.selection_vide() else masque(doc.selection).copy()
        prep = modifier_ia.preparer(doc, zone, self.a_ia_nouveau_calque.isChecked())
        visible = tableau(doc.image.convertToFormat(FORMAT_IMAGE))
        self._lancer(titre, False, lambda nom: recettes.restaurer(nom, prep.taille, texte=consigne),
                     png=prep.png, apres=lambda img: modifier_ia.image_complete(prep, img),
                     placer=lambda image: modifier_ia.etat(doc, prep, image, nom_calque),
                     vue=lambda img: modifier_ia.vue(prep, img, visible), nom_calque=nom_calque, suffixe=suffixe)

    def ia_coloriser(self):
        titre = tr("Coloriser")
        if self.doc and self._verifier_verrou(titre) and self._kontext_present(titre):
            self._kontext(titre, recettes.TEXTE_COLORISER_SEUL, tr("Colorisé"), tr("_colorise"))

    def ia_lumiere(self):
        titre = tr("Changer la lumière")
        if not self.doc or not self._verifier_verrou(titre) or not self._kontext_present(titre):
            return
        cle = choix_exemple.choisir(self, titre, tr("Nouvelle lumière :"), noms_lumieres(), "lumiere",
                                    self.reglages.value("lumiere_style", "doree"))
        if cle is None:
            return
        self.reglages.setValue("lumiere_style", cle)
        self._kontext(titre, recettes.TEXTE_LUMIERE.format(lumiere=recettes.LUMIERES[cle]), tr("Lumière"),
                      tr("_lumiere"))

    # ---------------------------------------------------------- flou selon la profondeur
    def ia_flou_profondeur(self):
        titre = tr("Flou selon la profondeur")
        if not self.doc or not self._verifier_pixels(titre):
            return
        if not recettes.profondeur_disponible():
            QMessageBox.information(self, titre, tr(
                "Cette action a besoin du modèle Depth Anything 3 (137 Mo), qui n'est pas installé. Menu IA > "
                "Installer le moteur IA permet de l'ajouter (case « Flou selon la profondeur »)."))
            return

        avec_sujet = recettes.detourage_disponible()

        def suite(cartes):
            carte = cartes[0]
            sujet = cartes[1].astype(np.float32) / 255 if len(cartes) > 1 else None
            prof = carte.astype(np.float32) / 255
            rgba = tableau(self.doc.calque_actif.image.convertToFormat(FORMAT_IMAGE))
            w, h = self.doc.taille()
            # point net de départ : le plus proche (le sujet, en général)
            ys, xs = np.nonzero(prof >= np.percentile(prof, 97))
            neutres = {"x": int(np.median(xs)) if len(xs) else w // 2, "y": int(np.median(ys)) if len(ys) else h // 2,
                       "flou": 0, "zone": 15, "arriere": False, "sujet": True}
            depart = dict(neutres, flou=int(self.reglages.value("profondeur_flou", 20)))
            petite = prof
            if max(w, h) > 700:                       # la carte montrée dans le panneau : réduite
                k = 700 / max(w, h)
                petite = np.asarray(Image.fromarray(carte).resize((max(1, round(w * k)), max(1, round(h * k))),
                                                                  Image.BILINEAR), np.float32) / 255
            panneau = panneau_profondeur(rgba, petite, sujet is not None)(depart, {})

            def calcul(a, p):
                self.reglages.setValue("profondeur_flou", p.get("flou", 20))
                return flou_profondeur(a, prof, p, sujet)
            self._dialogue_pixels(titre, panneau, neutres, calcul)
        self._carte_ia(tr("Calcul de la profondeur"), lambda nom: recettes.profondeur(nom, sujet=avec_sujet), suite,
                       toutes=True)
