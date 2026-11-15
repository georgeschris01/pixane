"""Transformer un calque (Ctrl+T, comme Photoshop) : agrandir, réduire, tourner, déplacer avec un cadre à poignées.

Le cadre entoure tous les pixels du calque, même ceux qui dépassent de la feuille, ou seulement ceux de la sélection
(le reste du calque, `fond`, ne bouge pas). Rien n'est coupé : `rendu_entier` donne le calque entier, la feuille
n'en montre qu'une partie. Coin : taille proportionnelle (Maj : libre), autour du coin opposé.
Milieu d'un côté : une seule direction. Dedans : déplacer. Dehors : tourner autour du centre, degré par degré
(Maj : par 15°) ; la barre d'options permet aussi de taper l'angle, la largeur et la hauteur.

Modes (comme Photoshop, Édition > Transformation) :
- « libre » : ci-dessus (Ctrl+coin : le coin bouge seul, on passe en « distordre ») ;
- « perspective » : un coin tiré entraîne le coin voisin du même bord en miroir (le bord s'élargit d'un côté et se
  rétrécit de l'autre, comme une façade vue de biais) ;
- « distordre » : chaque coin bouge seul (poser une image sur un écran, une boîte, un mur) ; un milieu de bord
  déplace ce bord entier ;
- « deformation » : grille de 4 × 4 points (surface de Bézier) : courber, gonfler, plier l'image.
Hors du mode « libre », l'image est rendue par une transformation projective (perspective, distordre) ou découpée en
petits morceaux qui suivent la surface (déformation).
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image
from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt
from PySide6.QtGui import QImage, QPainter, QPolygonF, QTransform

POIGNEES = {"hg": (-1, -1), "h": (0, -1), "hd": (1, -1), "d": (1, 0), "bd": (1, 1), "b": (0, 1), "bg": (-1, 1),
            "g": (-1, 0)}
MODES = ("libre", "perspective", "distordre", "deformation")
COINS = ("hg", "hd", "bd", "bg")                 # ordre des points de `quad`
MILIEUX = {"h": (0, 1), "d": (1, 2), "b": (2, 3), "g": (3, 0)}     # bord -> ses deux coins dans `quad`
DECOUPE = 24                                     # déformation : morceaux par côté au rendu final


def _bernstein(t: float) -> tuple[float, float, float, float]:
    s = 1 - t
    return s * s * s, 3 * s * s * t, 3 * s * t * t, t * t * t


def point_surface(maille, u: float, v: float) -> QPointF:
    """Point de la surface de Bézier (maille : 16 points, rangée par rangée) en u, v dans 0..1."""
    bu, bv = _bernstein(u), _bernstein(v)
    x = y = 0.0
    for i in range(4):
        for j in range(4):
            k = bv[i] * bu[j]
            p = maille[i * 4 + j]
            x += k * p.x()
            y += k * p.y()
    return QPointF(x, y)


def redimensionner(image: QImage, w: int, h: int) -> QImage:
    """Redimensionnement de qualité (Lanczos, comme le « bicubique » de Photoshop) : chaque pixel tient compte de
    tous ceux qu'il remplace (Qt n'en lit que 4 : crénelage et grain quand on réduit beaucoup). Transparence
    respectée (calcul en couleurs prémultipliées, pas de liseré sombre)."""
    w, h = max(1, w), max(1, h)
    if (w, h) == (image.width(), image.height()):
        return image
    from .profondeur import est_16, qimage16, tab16
    if est_16(image):                    # 16 bits : chaque couche en flottant (Pillow, mode « F »), sans arrondi
        t = tab16(image, premul=True).astype(np.float32)
        r = np.stack([np.asarray(Image.fromarray(np.ascontiguousarray(t[..., k]), "F").resize((w, h), Image.LANCZOS))
                      for k in range(4)], axis=-1)
        r = np.clip(r, 0, 65535)
        r[..., :3] = np.minimum(r[..., :3], r[..., 3:4])
        return qimage16(np.round(r).astype(np.uint16), premul=True)
    src = image.convertToFormat(QImage.Format_RGBA8888_Premultiplied)
    a = np.frombuffer(src.constBits(), np.uint8, src.bytesPerLine() * src.height())
    a = a.reshape(src.height(), src.bytesPerLine())[:, : src.width() * 4].reshape(src.height(), src.width(), 4)
    r = np.array(Image.frombuffer("RGBa", (src.width(), src.height()), np.ascontiguousarray(a), "raw", "RGBa", 0, 1)
                 .resize((w, h), Image.LANCZOS))
    r[..., :3] = np.minimum(r[..., :3], r[..., 3:4])         # prémultiplié : couleur jamais plus forte que l'opacité
    r = np.ascontiguousarray(r)
    return QImage(r.data, w, h, w * 4, QImage.Format_RGBA8888_Premultiplied).copy()


def _rot(v: QPointF, degres: float) -> QPointF:
    a = math.radians(degres)
    c, s = math.cos(a), math.sin(a)
    return QPointF(v.x() * c - v.y() * s, v.x() * s + v.y() * c)


class Transformation:
    def __init__(self, image: QImage, rect: QRect, fond: QImage | None = None, origine: QPoint = QPoint(0, 0)):
        """image : le calque entier, posé en `origine` dans la feuille ; rect : la partie à transformer (dans
        `image`) ; fond : le reste du calque (même taille et même place que `image`), qui ne bouge pas."""
        self.source = image.copy(rect)
        self.fond = fond                    # reste du calque, sous l'élément transformé (sélection)
        self.origine = QPoint(origine)
        self.bw, self.bh = rect.width(), rect.height()
        self.centre = QPointF(origine.x() + rect.x() + rect.width() / 2,
                              origine.y() + rect.y() + rect.height() / 2)
        self.sx = self.sy = 1.0
        self.angle = 0.0
        self.mode = "libre"
        self.quad: list[QPointF] | None = None       # 4 coins libres (perspective, distordre)
        self.maille: list[QPointF] | None = None     # 16 points (déformation)
        self._depart = None
        self._cache = None                  # (largeur, hauteur, image redimensionnée en qualité)

    # ---------------------------------------------------------- géométrie
    def transfo(self) -> QTransform:
        return (QTransform().translate(self.centre.x(), self.centre.y()).rotate(self.angle)
                .scale(self.sx, self.sy).translate(-self.bw / 2, -self.bh / 2))

    def demi(self) -> tuple[float, float]:
        return self.sx * self.bw / 2, self.sy * self.bh / 2

    def point(self, gx: float, gy: float) -> QPointF:
        """Point du cadre : gx, gy dans -1..1 (coins, milieux)."""
        hw, hh = self.demi()
        return self.centre + _rot(QPointF(gx * hw, gy * hh), self.angle)

    def coins(self) -> list[QPointF]:
        if self.maille is not None:
            m = self.maille
            return [QPointF(m[0]), QPointF(m[3]), QPointF(m[15]), QPointF(m[12])]
        if self.quad is not None:
            return [QPointF(c) for c in self.quad]
        return [self.point(-1, -1), self.point(1, -1), self.point(1, 1), self.point(-1, 1)]

    def local(self, p: QPointF) -> QPointF:
        return _rot(p - self.centre, -self.angle)

    def libre(self) -> bool:
        """Plus une simple mise à l'échelle + rotation (perspective, distorsion ou déformation)."""
        return self.quad is not None or self.maille is not None

    def contour(self, n: int = 16) -> QPolygonF:
        """Bord de l'image transformée (coordonnées de la feuille)."""
        if self.maille is None:
            return QPolygonF(self.coins())
        pts = []
        for u, v in ([(i / n, 0) for i in range(n)] + [(1, i / n) for i in range(n)]
                     + [(1 - i / n, 1) for i in range(n)] + [(0, 1 - i / n) for i in range(n)]):
            pts.append(point_surface(self.maille, u, v))
        return QPolygonF(pts)

    def dedans(self, p: QPointF) -> bool:
        if self.libre():
            return self.contour().containsPoint(p, Qt.OddEvenFill)
        l = self.local(p)
        hw, hh = self.demi()
        return abs(l.x()) <= hw and abs(l.y()) <= hh

    def _projective(self) -> QTransform | None:
        """Rectangle de la source -> les 4 coins libres."""
        t = QTransform()
        src = QPolygonF([QPointF(0, 0), QPointF(self.bw, 0), QPointF(self.bw, self.bh), QPointF(0, self.bh)])
        if not QTransform.quadToQuad(src, QPolygonF(self.quad), t):
            return None
        return t

    def passer_mode(self, mode: str):
        """Change de mode ; la forme actuelle est gardée (le cadre devient 4 coins libres, puis une grille)."""
        if mode not in MODES:
            return
        if mode in ("perspective", "distordre") and self.quad is None and self.maille is None:
            self.quad = self.coins()
        if mode == "deformation" and self.maille is None:
            if self.quad is not None:
                t = self._projective()
                self.maille = [t.map(QPointF(self.bw * j / 3, self.bh * i / 3)) if t is not None else
                               QPointF(self.quad[0]) for i in range(4) for j in range(4)]
            else:
                self.maille = [self.point(-1 + 2 * j / 3, -1 + 2 * i / 3) for i in range(4) for j in range(4)]
            self.quad = None
        if mode in ("perspective", "distordre") and self.maille is not None:
            m = self.maille                                  # retour aux coins : la courbure est abandonnée
            self.quad = [QPointF(m[0]), QPointF(m[3]), QPointF(m[15]), QPointF(m[12])]
            self.maille = None
        self.mode = mode

    def poignees(self) -> dict:
        """Poignées montrées -> point de la feuille."""
        if self.maille is not None:
            return {f"m{k}": QPointF(p) for k, p in enumerate(self.maille)}
        if self.quad is not None:
            q = self.quad
            res = {n: QPointF(q[i]) for i, n in enumerate(COINS)}
            for n, (a, b) in MILIEUX.items():
                res[n] = (q[a] + q[b]) / 2
            return res
        return {n: self.point(gx, gy) for n, (gx, gy) in POIGNEES.items()}

    def centre_forme(self) -> QPointF:
        pts = self.maille if self.maille is not None else self.quad if self.quad is not None else None
        if pts is None:
            return QPointF(self.centre)
        return QPointF(sum(p.x() for p in pts) / len(pts), sum(p.y() for p in pts) / len(pts))

    def rendu(self, W: int, H: int, lisse: bool = True) -> QImage:
        """La feuille W × H (aperçu posé dans le calque) : ce qui dépasse n'est pas dessiné. lisse=False : rapide,
        pendant le geste ; lisse=True (souris lâchée) : pleine qualité, comme le résultat validé, pour que le calque
        ne soit jamais dégradé, même si l'on passe à autre chose sans valider."""
        return self._dessiner(QRect(0, 0, W, H), lisse)

    def rendu_entier(self, lisse: bool = True) -> tuple[QImage, int, int]:
        """Le calque entier après transformation, même ce qui dépasse de la feuille -> (image, x, y)."""
        if self.libre():
            pts = self.maille if self.maille is not None else self.quad
            r = QPolygonF(pts).boundingRect().adjusted(-2, -2, 2, 2).toAlignedRect()
            if self.fond is not None:
                r = r.united(QRect(self.origine, self.fond.size()))
            return self._dessiner(r, lisse), r.x(), r.y()
        r = self.transfo().mapRect(QRectF(0, 0, self.bw, self.bh)).toAlignedRect()
        place = self._place() if lisse else None
        if place is not None:
            r = place
        if self.fond is not None:
            r = r.united(QRect(self.origine, self.fond.size()))
        return self._dessiner(r, lisse), r.x(), r.y()

    def _droit(self) -> bool:
        return not self.libre() and abs((self.angle + 180) % 360 - 180) < 1e-6

    def _place(self) -> QRect | None:
        """Sans rotation : rectangle d'arrivée calé sur des pixels entiers (pas de flou dû à un demi-pixel)."""
        if not self._droit():
            return None
        w, h = max(1, round(abs(self.sx) * self.bw)), max(1, round(abs(self.sy) * self.bh))
        return QRect(round(self.centre.x() - w / 2), round(self.centre.y() - h / 2), w, h)

    def _source_a(self, w: int, h: int) -> QImage:
        if self._cache is None or self._cache[:2] != (w, h):
            self._cache = (w, h, redimensionner(self.source, w, h))
        return self._cache[2]

    def _dessiner(self, r: QRect, lisse: bool, qualite: bool = True) -> QImage:
        from .profondeur import FORMAT_16, est_16
        img = QImage(max(1, r.width()), max(1, r.height()),
                     FORMAT_16 if est_16(self.source) else QImage.Format_ARGB32_Premultiplied)
        img.fill(0)
        p = QPainter(img)
        if self.fond is not None:
            p.drawImage(self.origine - r.topLeft(), self.fond)
        if self.libre():
            self._dessiner_libre(p, r, lisse and qualite)
            p.end()
            return img
        place = self._place() if lisse else None
        if place is not None:                    # sans rotation : redimensionné en qualité, posé pixel pour pixel
            if qualite:
                src = self._source_a(place.width(), place.height())
            else:
                src = self.source.scaled(place.width(), place.height(), Qt.IgnoreAspectRatio,
                                         Qt.SmoothTransformation)
            if self.sx < 0 or self.sy < 0:
                src = src.mirrored(self.sx < 0, self.sy < 0)
            p.drawImage(place.topLeft() - r.topLeft(), src)
            p.end()
            return img
        source = self.source
        if lisse and qualite and (abs(self.sx) < 1 or abs(self.sy) < 1):     # tourné et réduit : réduit en qualité d'abord
            source = self._source_a(max(1, round(abs(self.sx) * self.bw)), max(1, round(abs(self.sy) * self.bh)))
        p.setRenderHint(QPainter.SmoothPixmapTransform, lisse)
        p.setRenderHint(QPainter.Antialiasing, lisse)
        p.setTransform(self.transfo() * QTransform().translate(-r.x(), -r.y()))
        p.drawImage(QRectF(0, 0, self.bw, self.bh), source)
        p.end()
        return img

    def _source_reduite(self, largeur: float, hauteur: float) -> tuple[QImage, float, float]:
        """Source réduite en qualité si l'arrivée est plus petite (sinon crénelage) -> (image, kx, ky)."""
        w = max(1, min(self.bw, round(largeur)))
        h = max(1, min(self.bh, round(hauteur)))
        if (w, h) == (self.bw, self.bh):
            return self.source, 1.0, 1.0
        return self._source_a(w, h), w / self.bw, h / self.bh

    def _dessiner_libre(self, p: QPainter, r: QRect, qualite: bool):
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        p.setRenderHint(QPainter.Antialiasing, qualite)
        decale = QTransform().translate(-r.x(), -r.y())
        if self.maille is None:
            t = self._projective()
            if t is None:
                return
            q = self.quad
            larg = max(math.dist((q[0].x(), q[0].y()), (q[1].x(), q[1].y())),
                       math.dist((q[3].x(), q[3].y()), (q[2].x(), q[2].y())))
            haut = max(math.dist((q[0].x(), q[0].y()), (q[3].x(), q[3].y())),
                       math.dist((q[1].x(), q[1].y()), (q[2].x(), q[2].y())))
            src, kx, ky = self._source_reduite(larg, haut) if qualite else (self.source, 1.0, 1.0)
            p.setTransform(QTransform().scale(1 / kx, 1 / ky) * t * decale)
            p.drawImage(QPointF(0, 0), src)
            return
        # déformation : la source est découpée en petits rectangles, chacun posé sur son morceau de surface
        n = DECOUPE if qualite else 10
        bord = self.contour(n)
        larg = max(1.0, sum(math.dist((bord[i].x(), bord[i].y()), (bord[i + 1].x(), bord[i + 1].y()))
                            for i in range(n)))
        haut = max(1.0, sum(math.dist((bord[n + i].x(), bord[n + i].y()),
                                      (bord[n + i + 1].x(), bord[n + i + 1].y())) for i in range(n - 1)))
        src, kx, ky = self._source_reduite(larg, haut) if qualite else (self.source, 1.0, 1.0)
        sw, sh = src.width(), src.height()
        grille = [[point_surface(self.maille, j / n, i / n) for j in range(n + 1)] for i in range(n + 1)]
        e = max(0.8, 1.2 * max(sw / larg, sh / haut))        # recouvrement à l'intérieur (≈ 1 px) : pas de fente
        for i in range(n):
            for j in range(n):
                x0, x1 = sw * j / n, sw * (j + 1) / n
                y0, y1 = sh * i / n, sh * (i + 1) / n
                ex0 = e if j > 0 else 0
                ex1 = e if j < n - 1 else 0
                ey0 = e if i > 0 else 0
                ey1 = e if i < n - 1 else 0
                a, b = grille[i][j], grille[i][j + 1]
                c, d = grille[i + 1][j + 1], grille[i + 1][j]
                t = QTransform()
                if not QTransform.quadToQuad(QPolygonF([QPointF(x0, y0), QPointF(x1, y0), QPointF(x1, y1),
                                                        QPointF(x0, y1)]), QPolygonF([a, b, c, d]), t):
                    continue
                p.setTransform(t * decale)
                cible = QRectF(x0 - ex0, y0 - ey0, x1 - x0 + ex0 + ex1, y1 - y0 + ey0 + ey1)
                p.drawImage(cible, src, cible)

    def resume(self) -> tuple[float, float, float]:
        """Largeur %, hauteur %, angle (degrés, -180..180)."""
        return self.sx * 100, self.sy * 100, (self.angle + 180) % 360 - 180

    # ---------------------------------------------------------- glisser
    def commencer(self, mode, p: QPointF):
        """mode : « deplacer », « tourner » ou le nom d'une poignée (voir POIGNEES, COINS, MILIEUX, « mK »)."""
        self._depart = (mode, p, QPointF(self.centre), self.sx, self.sy, self.angle,
                        [QPointF(c) for c in self.quad] if self.quad is not None else None,
                        [QPointF(c) for c in self.maille] if self.maille is not None else None,
                        self.centre_forme())

    def _glisser_libre(self, quoi: str, p: QPointF, maj: bool):
        _m, p0, _c0, _sx, _sy, _a0, quad0, maille0, cf0 = self._depart
        d = p - p0
        pts0 = maille0 if maille0 is not None else quad0
        if quoi == "deplacer":
            nouv = [c + d for c in pts0]
        elif quoi == "tourner":
            v0, v = p0 - cf0, p - cf0
            a = math.degrees(math.atan2(v.y(), v.x()) - math.atan2(v0.y(), v0.x()))
            if maj:
                a = round(a / 15) * 15
            nouv = [cf0 + _rot(c - cf0, a) for c in pts0]
        elif maille0 is not None:                       # déformation : un point de la grille
            k = int(quoi[1:])
            nouv = [QPointF(c) for c in maille0]
            nouv[k] = maille0[k] + d
            i, j = divmod(k, 4)
            if i in (0, 3) and j in (0, 3):             # un coin emmène ses deux poignées voisines
                for kk in ((i * 4 + (1 if j == 0 else 2)), ((1 if i == 0 else 2) * 4 + j)):
                    nouv[kk] = maille0[kk] + d
        elif quoi in COINS:
            k = COINS.index(quoi)
            nouv = [QPointF(c) for c in quad0]
            nouv[k] = quad0[k] + d
            if self.mode == "perspective":
                # tiré de côté : le coin voisin du même bord horizontal s'écarte en miroir (ce bord s'élargit ou
                # rétrécit) ; tiré en hauteur : celui du même bord vertical
                if abs(d.x()) >= abs(d.y()):
                    voisin = {0: 1, 1: 0, 2: 3, 3: 2}[k]
                    nouv[voisin] = quad0[voisin] + QPointF(-d.x(), 0)
                    nouv[k] = quad0[k] + QPointF(d.x(), 0)
                else:
                    voisin = {0: 3, 3: 0, 1: 2, 2: 1}[k]
                    nouv[voisin] = quad0[voisin] + QPointF(0, -d.y())
                    nouv[k] = quad0[k] + QPointF(0, d.y())
        elif quoi in MILIEUX:
            a, b = MILIEUX[quoi]
            nouv = [QPointF(c) for c in quad0]
            nouv[a], nouv[b] = quad0[a] + d, quad0[b] + d
        else:
            return
        if maille0 is not None:
            self.maille = nouv
        else:
            self.quad = nouv

    def glisser(self, p: QPointF, maj: bool):
        if self._depart is None:
            return
        mode = self._depart[0]
        if self.libre():
            self._glisser_libre(mode, p, maj)
            return
        mode, p0, c0, sx0, sy0, a0 = self._depart[:6]
        if mode == "deplacer":
            self.centre = c0 + (p - p0)
            return
        if mode == "tourner":
            v0, v = p0 - c0, p - c0
            a = a0 + math.degrees(math.atan2(v.y(), v.x()) - math.atan2(v0.y(), v0.x()))
            self.angle = round(a / 15) * 15 if maj else round(a)      # au degré près
            return
        gx, gy = POIGNEES[mode]
        w0, h0 = sx0 * self.bw, sy0 * self.bh
        # point fixe : coin ou côté opposé
        fixe = c0 + _rot(QPointF(-gx * w0 / 2, -gy * h0 / 2), a0)
        d = _rot(p - fixe, -a0)
        w, h = w0, h0
        if gx and gy and not maj:                     # coin : proportions gardées
            k = (d.x() * gx * w0 + d.y() * gy * h0) / (w0 * w0 + h0 * h0)
            w, h = max(1.0, k * w0), max(1.0, k * h0)
        else:
            if gx:
                w = max(1.0, d.x() * gx)
            if gy:
                h = max(1.0, d.y() * gy)
        self.sx, self.sy = w / self.bw, h / self.bh
        self.centre = fixe + _rot(QPointF(gx * w / 2, gy * h / 2), a0)

    def finir(self):
        self._depart = None
