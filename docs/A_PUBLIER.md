# À publier — changements depuis la dernière publication

Carnet tenu à chaque modification (consigne de Christophe, 11/11/2026) : on ne publie que quand il le dit, après
plusieurs modifications. Ce jour-là, tout ce qui est listé ici sert à mettre à jour le README, les notes de version,
etc. ; puis le carnet est vidé (en gardant la « Dernière publication » à jour).

**Dernière publication : 0.18.0** (11/11/2026, GitHub v0.18.0).
Les installateurs fabriqués depuis portent toujours le numéro 0.18.0 (non publiés).

## Nouveautés

- **Meilleure version de chaque calque (sans perte, comme un objet dynamique de Photoshop)** : réduire un calque
  (Déplacer, Ctrl+T, Taille de l'image…), valider, faire autre chose, enregistrer, rouvrir, puis le réagrandir :
  l'image revient pixel pour pixel, jusqu'à sa taille d'origine (par exemple après un Upscale). Suit aussi
  pivoter, retourner, recadrer, aligner ; enregistrée dans le .pixane. Pixels modifiés (pinceau, IA…) : la version
  modifiée devient la référence. *(commit 5f1aea2)*

- **Pot de peinture : case « Tous les calques »** (décochée par défaut, comme Photoshop) : la zone à remplir est
  cherchée dans le calque choisi ; sur un calque vide, un clic remplit tout le calque. Cochée : d'après l'image
  visible (ancien comportement), avec une bulle d'aide qui explique la différence. *(signalé par Christophe : un
  calque vide rempli laissait un trou à l'emplacement d'un autre calque supprimé ensuite)*

- **Pinceaux à forme (comme Photoshop, Krita)** : pinceau de couleur (et masques), gomme de calque et pinceau de
  sélection peuvent prendre une forme de la bibliothèque (bouton « Pinceau » dans la barre du haut, un choix par
  outil, gardé). **235 pinceaux et 87 motifs livrés** (ressources de Krita 3 et 4, licence CC-0, auteurs cités dans
  LICENCES_TIERS). « Ajouter des fichiers… » : Photoshop .abr (versions 1, 2 et 6+), GIMP / Krita .gbr, .gih
  (animés), paquets .bundle, images ; « Retirer ce groupe ». **Réglages…** avec aperçu : espacement, angle (ou qui
  suit le trait), rondeur, dispersion, nombre, variations, texture (motif), double pinceau, couleur variable, flux,
  **pression de la tablette** (même le pinceau rond la suit). Guide FR/EN : « Pinceaux à forme ».
  *Reste (étape 3) : les motifs (pot de peinture, Incrustation de motif, Remplir avec un motif, Tampon de motif).*
  *Le jour de la publication : README « Ce que Pixane sait faire », partie peinture : ajouter les pinceaux à forme
  et la tablette.*

## Corrections

- **Agrandir en pleine définition : message d'erreur** « Unknown format code 'd' for object of type 'float' »
  pendant le calcul (le travail continuait quand même) : le temps restant, un nombre à virgule, ne s'affichait
  pas. Corrigé. *(signalé par Christophe, capture « erreur »)*
- **Effacer / Remplir sur des trous transparents** (lettres d'un texte coupé dans une pochette) : les trous de la
  sélection entourés par l'image sont maintenant remplis, opaques, avec la couleur autour ; avant, ils restaient
  transparents (on voyait des lettres sombres : le fond de la fenêtre à travers). Le transparent qui continue hors
  de la sélection reste transparent. Guide : ce que l'IA regarde (image visible) et les trous.

- **Rétrécir sans valider** : dès la souris lâchée, le calque est en pleine qualité (avant : aperçu rapide, dégradé,
  tant qu'on n'appuyait pas sur Entrée). *(fe5d6b7)*
- **Upscale** : le calque « plus net » est ramené à sa taille en qualité (Lanczos), et lors d'un Upscale de toute
  l'image les autres calques sont agrandis en qualité (avant : un peu mous). *(ef39a19)*

## À mettre à jour le jour de la publication

- [ ] Numéro de version (`pixane\__init__.py`) selon la règle A.B.C : il y a des **nouveautés** -> B + 1 (0.19.0).
- [ ] README.md et README.en.md, liste « Ce que Pixane sait faire » (écrite à la main) : dans **Réglages et
      filtres**, ligne « transformer un calque » : ajouter « sans perte en réduisant puis réagrandissant (comme un
      objet dynamique) ».
- [ ] Recopier le guide dans les README : `.venv\Scripts\python outils\readme.py`.
- [ ] FEUILLE_DE_ROUTE : ligne « Dernière version d'essai ».
- [ ] Notes de version (« ## Nouveautés », « ## Corrections ») à partir des listes ci-dessus, sans pied « Generated
      with Claude Code ».
- [ ] Installateur, push, release GitHub, ligne au JOURNAL ; puis vider ce carnet.
