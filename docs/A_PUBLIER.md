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

## Corrections

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
