# À publier — changements depuis la dernière publication

Carnet tenu à chaque modification (consigne de Christophe, 11/11/2026) : on ne publie que quand il le dit, après
plusieurs modifications. Ce jour-là, tout ce qui est listé ici sert à mettre à jour le README, les notes de version,
etc. ; puis le carnet est vidé (en gardant la « Dernière publication » à jour).

**Dernière publication : 0.25.0** (16/11/2026, GitHub pixane-suite/photo v0.25.0, version normale).
Les installateurs fabriqués depuis portent toujours le numéro 0.25.0 (non publiés).

## Nouveautés

- **Affichage > Taille de l'interface** (demandé par un utilisateur sur GitHub) : toute l'interface de 75 % à 200 %
  (textes, icônes, boutons, panneaux), en plus de la mise à l'échelle de Windows ; au prochain démarrage, que
  Pixane Photo propose aussitôt. Aussi choisie dans l'installateur (normale, compacte, grande, très grande), sans
  remplacer un choix déjà fait.
- **Affichage > Taille des icônes des outils** : petites, normales, grandes, très grandes, tout de suite.
- **Les projets Pixane Photo s'appellent maintenant .piximg** (au lieu de .pixane), comme .pixvid pour Pixane
  Video : chaque logiciel de la Suite a son extension. Le contenu du fichier ne change pas ; l'installateur ouvre les
  .piximg avec Pixane Photo et retire l'ancienne association .pixane.

## Corrections

- Cartes du panneau IA (Modifier…) : la deuxième ligne d'explication était coupée quand elle passait à la ligne.

## À mettre à jour le jour de la publication

- [ ] Numéro de version (`pixane\__init__.py`) selon la règle A.B.C.
- [ ] README.md et README.en.md, liste « Ce que Pixane sait faire » (écrite à la main).
- [ ] Recopier le guide dans les README : `.venv\Scripts\python outils\readme.py`.
- [ ] FEUILLE_DE_ROUTE : ligne « Dernière version d'essai ».
- [ ] Issue n°1 « Feuille de route » sur GitHub (`gh issue edit 1 -R pixane-suite/photo`) : Ajouté récemment, En
      cours, Prévu.
- [ ] Notes de version (« ## Nouveautés », « ## Corrections ») à partir des listes ci-dessus, sans pied « Generated
      with Claude Code ».
- [ ] Installateur, push, release GitHub, ligne au JOURNAL ; puis vider ce carnet.
