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
