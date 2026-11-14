# À publier — changements depuis la dernière publication

Carnet tenu à chaque modification (consigne de Christophe, 11/11/2026) : on ne publie que quand il le dit, après
plusieurs modifications. Ce jour-là, tout ce qui est listé ici sert à mettre à jour le README, les notes de version,
etc. ; puis le carnet est vidé (en gardant la « Dernière publication » à jour).

**Dernière publication : 0.21.0** (14/11/2026, GitHub v0.21.0, version normale).
Les installateurs fabriqués depuis portent toujours le numéro 0.21.0 (non publiés).

## Nouveautés

## Corrections

- **À propos** : « Pixane n'a pas la prétention de remplacer des programmes comme Photoshop, GIMP ou Krita… »
  (aussi dans le README et le guide).
- **Licence Pixane 1.2** : « code source disponible » au lieu de « code source ouvert » (Pixane n'est pas « open
  source » au sens strict, puisqu'il est non commercial) ; même contenu, seuls les mots changent. Image de licence
  ajoutée au README (sans rond derrière le logo).

## À mettre à jour le jour de la publication

- [ ] Numéro de version (`pixane\__init__.py`) selon la règle A.B.C.
- [ ] README.md et README.en.md, liste « Ce que Pixane sait faire » (écrite à la main).
- [ ] Recopier le guide dans les README : `.venv\Scripts\python outils\readme.py`.
- [ ] FEUILLE_DE_ROUTE : ligne « Dernière version d'essai ».
- [ ] Notes de version (« ## Nouveautés », « ## Corrections ») à partir des listes ci-dessus, sans pied « Generated
      with Claude Code ».
- [ ] Installateur, push, release GitHub, ligne au JOURNAL ; puis vider ce carnet.
