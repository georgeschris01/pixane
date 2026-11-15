# À publier — changements depuis la dernière publication

Carnet tenu à chaque modification (consigne de Christophe, 11/11/2026) : on ne publie que quand il le dit, après
plusieurs modifications. Ce jour-là, tout ce qui est listé ici sert à mettre à jour le README, les notes de version,
etc. ; puis le carnet est vidé (en gardant la « Dernière publication » à jour).

**Dernière publication : 0.22.0** (15/11/2026, GitHub v0.22.0, version normale).
Les installateurs fabriqués depuis portent toujours le numéro 0.22.0 (non publiés).

## Nouveautés

- **Pixane devient Pixane Photo**, premier logiciel de la **Suite Pixane** (dépôt GitHub transféré le 15/11/2026 :
  github.com/pixane-suite/photo ; l'ancienne adresse redirige, la recherche de mise à jour marche). Nom changé
  partout (fenêtre, À propos avec « Fait partie de la Suite Pixane », messages, guide, README, installateur
  `Pixane-Photo-Setup-…`, raccourci « Pixane Photo »). Inchangés : projets .pixane, réglages, dossier
  %LOCALAPPDATA%\Pixane (commun à la suite), moteur IA, traducteur.
- **Dossier d'installation** : `…\Pixane\Pixane Photo` (le dossier Pixane réunit la suite). Une installation à
  l'ancienne place (`…\Pixane`) y est déplacée à la mise à jour ; épingle de la barre des tâches et raccourci du
  Bureau suivis ; fichiers personnels laissés dans l'ancien dossier gardés.
- **Nouveau logo** (famille de la suite) : le « P en pixels » orange-rose avec un symbole photo (montagne et soleil)
  à la place de l'étincelle ; icône, images de l'installateur. L'emblème de la suite (P sans symbole) reste sur
  l'image de la licence (`logo\suite-pixane.svg`).
- À faire à la publication : capture du README (`docs/screenshots`) avec le nouveau titre ; vérifier la page de
  l'organisation pixane-suite.

## Corrections

## À mettre à jour le jour de la publication

- [ ] Numéro de version (`pixane\__init__.py`) selon la règle A.B.C.
- [ ] README.md et README.en.md, liste « Ce que Pixane sait faire » (écrite à la main).
- [ ] Recopier le guide dans les README : `.venv\Scripts\python outils\readme.py`.
- [ ] FEUILLE_DE_ROUTE : ligne « Dernière version d'essai ».
- [ ] Notes de version (« ## Nouveautés », « ## Corrections ») à partir des listes ci-dessus, sans pied « Generated
      with Claude Code ».
- [ ] Installateur, push, release GitHub, ligne au JOURNAL ; puis vider ce carnet.
