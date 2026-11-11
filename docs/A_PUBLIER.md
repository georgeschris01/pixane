# À publier — changements depuis la dernière publication

Carnet tenu à chaque modification (consigne de Christophe, 11/11/2026) : on ne publie que quand il le dit, après
plusieurs modifications. Ce jour-là, tout ce qui est listé ici sert à mettre à jour le README, les notes de version,
etc. ; puis le carnet est vidé (en gardant la « Dernière publication » à jour).

**Dernière publication : 0.19.0** (11/11/2026, GitHub v0.19.0).
Les installateurs fabriqués depuis portent toujours le numéro 0.19.0 (non publiés).

## Nouveautés

- **Traducteur proposé aussi avec un ComfyUI déjà installé** : case dans « Compléter le moteur IA » (avant : seulement
  dans la fenêtre d'installation complète, Christophe ne la voyait pas), cochée tant qu'il n'est pas installé, grisée
  ensuite (de même Flux Schnell et Flux Kontext déjà là : visibles, grisés) ; proposé une fois au démarrage avec ce
  qui manque. **Dossier du traducteur au choix** (« Changer… », gardé ; par défaut le dossier de Pixane), dans les
  trois fenêtres. *(demande de Christophe)*

- **Consigne pas en anglais, sans traducteur** : avertissement au clic sur Modifier (l'IA ne comprend bien que
  l'anglais : résultat au hasard), avec le choix Installer le traducteur… / Corriger / Envoyer quand même ; guide
  FR/EN : explication claire (français, polonais… : traducteur ou anglais), texte entre guillemets exactement comme
  sur l'image. *(essais de Christophe : « modifier par consigne », consigne en français sans traducteur)*

- **Pinceaux : styles prêts, pinceaux simples, familles** (demande de Christophe : « je ne vois que les textures ») :
  17 styles prêts en un clic (forme + réglages : crayon, fusain, craie, encre, feutre, calligraphie, aquarelle, huile,
  couteau, pinceau sec, aérographe, bombe, feuillage, herbe, étoiles, fumée, éclaboussures) ; groupe « Simples »
  (rond dur, rond doux, aérographe, carré, plat, biseau) ; pinceaux de Krita rangés par familles (Crayon et fusain,
  Peinture, Nature, Effets, Textures, Formes) ; les choix déjà enregistrés sont retrouvés. Guide : où est le pinceau
  de couleur (P).

## Corrections

- **Enregistrer en .pixane : « 'QPoint' object has no attribute 'convertToFormat' »** après avoir transformé (Ctrl+T,
  poignées de Déplacer) un calque qui dépasse de la feuille (un collage, par exemple) : la position du cadre était
  prise pour la meilleure version du calque. Corrigé. *(signalé par Christophe, capture dans « erreur »)*

## À mettre à jour le jour de la publication

- [ ] Numéro de version (`pixane\__init__.py`) selon la règle A.B.C.
- [ ] README.md et README.en.md, liste « Ce que Pixane sait faire » (écrite à la main).
- [ ] Recopier le guide dans les README : `.venv\Scripts\python outils\readme.py`.
- [ ] FEUILLE_DE_ROUTE : ligne « Dernière version d'essai ».
- [ ] Notes de version (« ## Nouveautés », « ## Corrections ») à partir des listes ci-dessus, sans pied « Generated
      with Claude Code ».
- [ ] Installateur, push, release GitHub, ligne au JOURNAL ; puis vider ce carnet.
