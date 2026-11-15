# À publier — changements depuis la dernière publication

Carnet tenu à chaque modification (consigne de Christophe, 11/11/2026) : on ne publie que quand il le dit, après
plusieurs modifications. Ce jour-là, tout ce qui est listé ici sert à mettre à jour le README, les notes de version,
etc. ; puis le carnet est vidé (en gardant la « Dernière publication » à jour).

**Dernière publication : 0.23.0** (15/11/2026, GitHub pixane-suite/photo v0.23.0, version normale).
Les installateurs fabriqués depuis portent toujours le numéro 0.23.0 (non publiés).

## Nouveautés

- **16 bits par couche** (Image > Mode, comme Photoshop) : 65 536 nuances par couleur au lieu de 256, pour des
  dégradés et des réglages forts sans cassures. Ouverture automatique en 16 bits des PNG, TIFF et PSD 16 bits et des
  photos RAW ; enregistrement en 16 bits en .pixane, PSD, TIFF et PNG. Calculés en 16 bits : fusion des calques
  (modes, calques de réglage, masques), tous les réglages, les filtres, le Dégradé et les calques de remplissage,
  taille, rotation, miroir, redresser, transformer, recadrer, Agrandir. Les autres outils et l'IA ne touchent que la
  zone qu'ils changent : le reste garde ses 16 bits. Indiqué dans le titre ; Ctrl+Z annule le changement.
- **Tramage vers 8 bits** (Image > Mode, coché par défaut, demandé par Christophe) : une image 16 bits montrée à
  l'écran, exportée en JPEG / WebP ou repassée en 8 bits reçoit un grain invisible qui évite les marches dans les
  dégradés.

## Corrections

- **Édition > Remplir avec un motif…** affichait une erreur au lieu d'ouvrir sa fenêtre (signalé par Christophe le
  15/11/2026).
- Panneau Actions : le bouton **● Enregistrer** aurait affiché la même erreur (même cause, trouvé en cherchant).
- **Arrêter un travail IA** (Modifier avec une consigne, Effacer, Remplir…) affichait « JSONDecodeError », et le
  moteur continuait le calcul en arrière-plan : maintenant l'arrêt est propre et la carte graphique s'arrête
  vraiment (signalé par Christophe le 15/11/2026).

## À mettre à jour le jour de la publication

- [ ] Numéro de version (`pixane\__init__.py`) selon la règle A.B.C.
- [ ] README.md et README.en.md, liste « Ce que Pixane sait faire » (écrite à la main).
- [ ] Recopier le guide dans les README : `.venv\Scripts\python outils\readme.py`.
- [ ] FEUILLE_DE_ROUTE : ligne « Dernière version d'essai ».
- [ ] Notes de version (« ## Nouveautés », « ## Corrections ») à partir des listes ci-dessus, sans pied « Generated
      with Claude Code ».
- [ ] Installateur, push, release GitHub, ligne au JOURNAL ; puis vider ce carnet.
