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
- **Flèches du clavier** avec l'outil Déplacer : poussent le calque choisi ou le texte (1 px, Maj : 10 px), aussi
  après un clic dans le panneau Calques, et le cadre de Transformer.
- **Aperçus** dans Taille de l'image (centre à 100 %, avant / après), Taille de la zone de travail (feuille, partie
  rognée), Nouvelle image (feuille, fond, repères).
- **Trouver une police semblable** (menu Sélection, ou bouton de la Sélection de texte) : parmi les polices
  installées, les plus proches des lettres sélectionnées, écrites avec ces lettres ; appliquer au texte choisi ou
  créer un texte avec la police. Option à l'installation (case cochée par défaut) et dans Affichage.
- **Agrandir** : détection des bords abîmés élargie (cadre, bord flou, bande unie, jusqu'à 4 % du côté).
- **Installateur** : la case « Lancer Pixane » est aussi proposée à la fin d'une installation neuve (avec le
  téléchargement du traducteur ou du moteur, Pixane démarre une fois ceux-ci terminés).

## Corrections

- **Vignettes du panneau Calques** : à la forme de l'image (une image large n'a plus de bandes vides en haut et
  en bas).
- **Agrandir** : plus de partie plus claire ni de bandes dans les fonds unis ajoutés (« effet fantôme ») ; l'accord
  des couleurs va jusqu'au bord de l'image, et il est refait après « Pleine définition » (qui, en redessinant
  l'ajout, le rendait de nouveau plus clair par endroits).
- **Texte** : en passant d'un calque de texte à un autre, le nouveau texte pouvait prendre la police du
  précédent (aperçu de police du panneau Texte).

## À mettre à jour le jour de la publication

- [ ] Numéro de version (`pixane\__init__.py`) selon la règle A.B.C.
- [ ] README.md et README.en.md, liste « Ce que Pixane sait faire » (écrite à la main).
- [ ] Recopier le guide dans les README : `.venv\Scripts\python outils\readme.py`.
- [ ] FEUILLE_DE_ROUTE : ligne « Dernière version d'essai ».
- [ ] Notes de version (« ## Nouveautés », « ## Corrections ») à partir des listes ci-dessus, sans pied « Generated
      with Claude Code ».
- [ ] Installateur, push, release GitHub, ligne au JOURNAL ; puis vider ce carnet.
