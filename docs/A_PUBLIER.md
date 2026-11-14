# À publier — changements depuis la dernière publication

Carnet tenu à chaque modification (consigne de Christophe, 11/11/2026) : on ne publie que quand il le dit, après
plusieurs modifications. Ce jour-là, tout ce qui est listé ici sert à mettre à jour le README, les notes de version,
etc. ; puis le carnet est vidé (en gardant la « Dernière publication » à jour).

**Dernière publication : 0.20.0** (14/11/2026, GitHub v0.20.0, **préversion**).
Les installateurs fabriqués depuis portent toujours le numéro 0.20.0 (non publiés).

## Nouveautés

- **Pinceaux et motifs ajoutés rangés à part** (paquets `.pixpaquet`) : chaque pinceau à sa taille d'origine, sans
  perte (PNG), avec sa vignette ; seul le pinceau utilisé est lu. Plus d'attente à l'ouverture des réglages ou de la
  bibliothèque, même pour un .abr de 1,7 Go (devenu 855 Mo). Les anciens ajouts sont convertis une fois, en
  arrière-plan ; chaque ancienne copie n'est effacée qu'après vérification de son paquet.
- **Installateur** : la case « Lancer Pixane » est aussi proposée à la fin d'une installation neuve (avec le
  téléchargement du traducteur ou du moteur, Pixane démarre une fois ceux-ci terminés).

## Corrections


## À mettre à jour le jour de la publication

- [ ] Numéro de version (`pixane\__init__.py`) selon la règle A.B.C.
- [ ] README.md et README.en.md, liste « Ce que Pixane sait faire » (écrite à la main).
- [ ] Recopier le guide dans les README : `.venv\Scripts\python outils\readme.py`.
- [ ] FEUILLE_DE_ROUTE : ligne « Dernière version d'essai ».
- [ ] Notes de version (« ## Nouveautés », « ## Corrections ») à partir des listes ci-dessus, sans pied « Generated
      with Claude Code ».
- [ ] Installateur, push, release GitHub, ligne au JOURNAL ; puis vider ce carnet.
