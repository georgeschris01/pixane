# À publier — changements depuis la dernière publication

Carnet tenu à chaque modification (consigne de Christophe, 11/11/2026) : on ne publie que quand il le dit, après
plusieurs modifications. Ce jour-là, tout ce qui est listé ici sert à mettre à jour le README, les notes de version,
etc. ; puis le carnet est vidé (en gardant la « Dernière publication » à jour).

**Dernière publication : 0.24.0** (15/11/2026, GitHub pixane-suite/photo v0.24.0, version normale).
Les installateurs fabriqués depuis portent toujours le numéro 0.24.0 (non publiés).

## Nouveautés

- **32 bits par couche (HDR)** (Image > Mode, demandé par Christophe) : les couleurs peuvent être plus claires que le
  blanc (soleil, lampes, ciels très lumineux), pour les photos HDR. Ouverture et enregistrement des **.exr**
  (OpenEXR), **.hdr** (Radiance) et **TIFF 32 bits** ; .pixane en 32 bits. Calculés en 32 bits sans couper au
  blanc : fusion des calques, calques de réglage, réglages, filtres, Dégradé, calques de remplissage, taille,
  géométrie. **Affichage > Exposition 32 bits** pour regarder les hautes lumières à l'écran ; **Virage HDR**
  (exposition, gamma, compression des hautes lumières, avec aperçu) en repassant en 16 ou 8 bits.
- **Les pinceaux travaillent dans la profondeur de l'image** (16 et 32 bits, demandé par Christophe) : pinceau,
  gomme, tampon de duplication, pinceau d'historique, Densité − / +, Éponge, Goutte d'eau, Netteté, Doigt. En 32
  bits, le tampon recopie aussi les zones plus claires que le blanc.
- Nouvelle bibliothèque livrée : **OpenEXR** 3.5.4 (BSD-3, 2,7 Mo) pour les fichiers .exr.

## Corrections

- 16 bits : en repassant en 16 bits le résultat d'une fonction 8 bits (pont), la comparaison des pixels pouvait lire
  une image déjà effacée de la mémoire (résultat faux possible) ; trouvé en écrivant le 32 bits.

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
