# À publier — changements depuis la dernière publication

Carnet tenu à chaque modification (consigne de Christophe, 11/11/2026) : on ne publie que quand il le dit, après
plusieurs modifications. Ce jour-là, tout ce qui est listé ici sert à mettre à jour le README, les notes de version,
etc. ; puis le carnet est vidé (en gardant la « Dernière publication » à jour).

**Dernière publication : 0.21.0** (14/11/2026, GitHub v0.21.0, version normale).
Les installateurs fabriqués depuis portent toujours le numéro 0.21.0 (non publiés).

## Nouveautés

- **Agrandir : proposition « Fond prolongé »**, faite sans IA, ajoutée aux propositions de Flux quand les bords à
  agrandir sont unis (fond de pochette, ciel lisse, dégradé) : le fond de la photo est continué ligne par ligne,
  avec le même grain ; ni raccord ni tourbillon visible, instantané. Absente si un objet touche le bord.
- **Calque de pinceau modifiable** : case « Calque modifiable » dans la barre du pinceau de couleur (décochée au
  départ). Les coups vont dans un calque de pinceau qui garde leur tracé : même plus tard, changer la couleur, la
  taille, l'opacité, la dureté, la rotation ou la forme du pinceau redessine tous ses traits. Il reste modifiable
  après déplacer, Ctrl+T, pivoter / retourner, taille de l'image, recadrer, Agrandir, Upscale ; gardé dans les
  .pixane ; marqué « pinceau modifiable » dans Calques. La gomme, un filtre, l'IA… en font une image (message).
- **Barre du haut** plus compacte (cases à chiffres à la largeur de leur texte).
- **Texte : réglages comme Photoshop** (nouveau moteur de mise en page, les textes existants restent identiques) :
  largeur / hauteur des lettres, casse (majuscules, minuscules, petites capitales, Première Lettre En Majuscule),
  exposant / indice, ligne de base, crénage de la police ou aucun, crénage à la main (case « Ici » ou Alt+flèches),
  ligatures / fractions / chiffres anciens, bords lissés ou nets, alignement justifié, texte vertical, texte en
  cadre (retour à la ligne automatique, hauteur, retrait, espace entre paragraphes), déformation comme « Déformer
  le texte » (Arc, Drapeau, Vague, Poisson, Gonflement, Torsion… avec force et distorsions).
- **Style par lettre** : sélectionner des lettres dans la case du panneau Texte pour ne changer qu'elles (police,
  taille, couleur, gras, exposant…) ; le style suit les lettres quand on tape.
- **Texte sur un tracé** : « Dessiner un tracé » puis glisser sur la photo, le texte suit la ligne (lissée) ;
  départ réglable, Retirer.
- **Glyphes** (bouton Ω du panneau Texte) : tous les caractères de la police, recherche par nom ou code, derniers
  utilisés ; un clic insère le caractère.
- **Styles de texte** : copier / coller le style d'un texte ; styles enregistrés sous un nom.
- **Masque d'écrêtage** (Ctrl+Alt+G, menu Calque, clic droit) : le calque ne se voit que dans celui du dessous,
  par exemple une photo dans les lettres d'un texte qui reste modifiable. Gardé en .pixane et .psd (les PSD qui en
  ont s'ouvrent maintenant correctement), mis dans les pixels en .ora.
- **Orthographe** des textes : mots mal écrits soulignés en rouge dans le panneau Texte ; clic droit : suggestions,
  Ignorer, Ajouter au dictionnaire. Français et anglais (langue choisie par texte). Dictionnaires de LibreOffice
  (Grammalecte MPL 2.0, SCOWL), lus par spylls (MIT).
- **Césure** des textes en cadre (pyphen) ; en justifié, une ligne d'un seul mot n'est plus étirée lettre par lettre.
- **Rechercher et remplacer dans les textes** (Ctrl+H) : tous les textes de l'image, Tout remplacer en une étape
  d'Annuler, styles par lettre gardés.
- **Installateur** : case « Orthographe et césure » avec le choix des langues (Français, Anglais) ; modifiable
  dans Affichage > Orthographe et césure et Affichage > Langues de l'orthographe… (une langue manquante y est
  téléchargée après accord).
- **Nouveaux réglages** (Image > Réglages, et en calques de réglage) : Filtre photo, Mélangeur de couches, Courbe
  de transfert de dégradé, Négatif (Ctrl+I), Seuil, Postérisation.
- **Remplacer la couleur** (Image > Réglages) : clic sur la couleur dans un aperçu, tolérance, nouvelle teinte /
  saturation / clarté ; plis et ombres gardés.
- **Plage de couleurs** (menu Sélection) : tous les points d'une ou plusieurs couleurs, dans toute l'image ;
  aperçu sur la photo, inverser, ajouter / retirer.
- **Nouveaux flous** (menu Filtres) : flou radial (rotation ou zoom), flou de l'objectif (reflets ronds), flou de
  surface (lisse la peau en gardant les bords).
- **Ctrl+T : Perspective, Distordre, Déformation** (liste Mode de la barre, Édition > Transformation, Ctrl+coin) :
  poser une image sur un écran, une boîte, un mur ; courber une image avec une grille de 16 points.
- **Recadrage en perspective** (menu Image) : 4 coins posés sur une façade, un tableau, un document vu de biais ;
  il devient un rectangle droit.
- **Pinceaux de retouche** (deux nouvelles familles d'outils) : Densité − / + (éclaircir, assombrir : ombres, tons
  moyens ou hautes lumières), Éponge (saturer, désaturer), Goutte d'eau (aussi sur un masque), Netteté, Doigt,
  Pinceau d'historique (repeint la photo d'ouverture, ou l'instantané pris).
- **Fluidité** (Filtres > Fluidité…, Ctrl+Maj+X) : pousser, gonfler, contracter, tourbillon, reconstruire au
  pinceau ; résultat en pleine définition.
- **Formes modifiables** : chaque forme est un calque de forme (remplissage, contour et épaisseur modifiables
  après coup, reste nette si on la déplace ou la redimensionne) ; nouvelles formes Étoile et Polygone.
- **Plume** (A) : tracés en lignes et en courbes, point par point, vers un calque de forme ou une sélection ; les
  points d'une forme se déplacent à la souris.
- **IA pour la photo** : Sélectionner le ciel, Remplacer le ciel (6 ciels au choix), Coloriser, Changer la lumière
  (8 lumières au choix), Flou selon la profondeur (clic sur ce qui reste net). Nouveau modèle facultatif Depth Anything
  3 Small (137 Mo, Apache-2.0) : case dans l'installateur et dans IA > Installer le moteur IA.

## Corrections

- **Agrandir** : les légers tourbillons (comme des courbes de niveau) que Flux laisse dans les fonds unis ajoutés
  sont lissés ; le grain fin et ce qui est vraiment dessiné sont gardés. Aussi après *Pleine définition*.
- **À propos** : « Pixane n'a pas la prétention de remplacer des programmes comme Photoshop, GIMP ou Krita… »
  (aussi dans le README et le guide).
- **Licence Pixane 1.2** : « code source disponible » au lieu de « code source ouvert » (Pixane n'est pas « open
  source » au sens strict, puisqu'il est non commercial) ; même contenu, seuls les mots changent. Image de licence
  ajoutée au README (sans rond derrière le logo). Déjà dans l'installateur 0.21.0 remplacé sur GitHub le 14/11 à
  17:51 (avec la phrase « À propos » ci-dessus).

## À mettre à jour le jour de la publication

- [ ] Numéro de version (`pixane\__init__.py`) selon la règle A.B.C.
- [ ] README.md et README.en.md, liste « Ce que Pixane sait faire » (écrite à la main).
- [ ] Recopier le guide dans les README : `.venv\Scripts\python outils\readme.py`.
- [ ] FEUILLE_DE_ROUTE : ligne « Dernière version d'essai ».
- [ ] Notes de version (« ## Nouveautés », « ## Corrections ») à partir des listes ci-dessus, sans pied « Generated
      with Claude Code ».
- [ ] Installateur, push, release GitHub, ligne au JOURNAL ; puis vider ce carnet.
