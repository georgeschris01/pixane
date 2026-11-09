# Feuille de route de Pixane

Liste des étapes décidées avec Christophe. Cocher quand c'est fait (et mettre à jour docs/GUIDE.md).

## Fait
- [x] Base : ouvrir / enregistrer, zoom, sélection (pinceau, gomme, rectangle, lasso), annuler.
- [x] IA : Effacer, Remplir, Agrandir (deux cadres : agrandir + bord abîmé), Upscale (Net / Rapide).
- [x] Interface moderne, couleur d'accent et thème de Windows, barre de progression, logo « C en pixels ».
- [x] Guide d'utilisation (docs/GUIDE.md).
- [x] **Calques** (validé par Christophe le 08/11/2026) : panneau (œil, nom, opacité, cadenas, ordre, nouveau /
  dupliquer / supprimer / fusionner / aplatir), IA sur calques, gomme de calque, format .ora.

## À faire (dans cet ordre, sauf décision contraire)
1. [ ] **Français / anglais** — fait le 08/11/2026, à valider par Christophe : tout le programme dans les deux langues ; par défaut la
   langue de Windows (choisie aussi par l'installateur), changeable dans le menu ; guide en anglais aussi.
   Fait : langue.py + langues\en.json, menu Affichage > Langue, Qt traduit, guide docs\GUIDE_en.md.
2. [ ] **Toutes les fonctions de texte** — fait le 08/11/2026, à valider par Christophe : outil T, police, taille,
   couleur, gras / italique / souligné / barré, alignement, espacement, rotation, courbe, contour, ombre, fond ;
   format .pixane (textes modifiables). Guide chapitre 7.
3. [x] **Outils** (08/11/2026, à essayer par Christophe) : recadrer (C, proportions, Recadrer à la sélection), pinceau de couleur (P, opacité, dureté, pipette Alt+clic), tampon (S, Alt+clic = source, aligné).
4. [x] **Réglages d'image** (08/11/2026, à essayer par Christophe) : menu Image > Réglages de l'image (Ctrl+U) : luminosité, contraste, saturation, teinte, température, netteté ; calque choisi, dans la sélection s'il y en a une ; aperçu en direct calculé en arrière-plan.
5. [x] **PSD** (08/11/2026, à essayer par Christophe dans Photoshop) : ouvrir et enregistrer avec les calques, sans bibliothèque en plus (pixane/psd.py) ; lu : RVB / gris 8-16 bits, groupes, masques de calque ; signalé : modes de fusion, styles, calques de réglage, écrêtage ; CMJN ouvert aplati.
   - [x] **En plus** (08/11/2026, à essayer par Christophe) : menu Image (taille, pivoter, retourner, redresser),
     transformer un calque (Ctrl+T), modifier la sélection (agrandir, réduire, adoucir), sélectionner le sujet et
     supprimer l'arrière-plan (BiRefNet), fichiers récents, nouvelle image (vide ou presse-papiers), panneau
     Historique, bouton Auto des réglages, À propos, recherche de mise à jour (sur demande ou option).
   - [x] **Sélections automatiques** (08/11/2026, à essayer par Christophe) : sélection d'objet (O) et sélection rapide (Q) avec SAM 3.1, baguette magique (W).
   - [x] **Styles de calque** (08/11/2026, à essayer par Christophe) : ombres (dont réaliste et au sol), lueurs, contours multiples, biseau, incrustations, 14 styles tout prêts, styles enregistrés, menu Calque.
5b. [x] **Bloc « comme Photoshop »** (09/11/2026, version 0.3.0, à essayer par Christophe ; tout sauf le
   remplacement du ciel) : pinceau Supprimer (J) ; masques de calque ; groupes ; modes de fusion ; calques de
   réglage ; Niveaux, Courbes, Balance des couleurs, Noir et blanc, Vibrance ; filtres (flous, bruit, netteté,
   vignette) ; dégradé (D), pot de peinture (K), formes (U), pinceau correcteur (R) ; PSD : modes, groupes et masques
   lus et écrits, styles lus (modifiables) ; onglets (plusieurs photos) ; enregistrement automatique et récupération ; règles, repères,
   grille, magnétisme ; Améliorer le contour ; Exporter pour le web ; Traitement par lot ; IA : Réduire le bruit
   (SCUNet), Netteté (RealESRGAN), Restaurer une vieille photo (Flux Kontext, facultatif).
   - [ ] Plus tard (exclu de ce bloc) : remplacement du ciel.
6. [ ] **Installateur** (même présentation que TwinPanel, Inno Setup 7) :
   - [x] images (validées le 08/11/2026) ;
   - [x] partie 1 (08/11/2026, à essayer par Christophe) : langue, pour moi / pour tous, dossier, vérification du PC
     (carte NVIDIA, place, ComfyUI trouvé ou dossier à indiquer), Python inclus, association .pixane ;
     construire-installateur.bat -> publication\installateur\Pixane-Setup-x.y.z-64bits.exe ;
   - [x] partie 2 (08/11/2026, à essayer par Christophe) : page « Moteur IA » si ComfyUI absent (liste taille /
     site / licence, case licence FLUX.1 [dev] obligatoire, Flux Schnell facultatif), téléchargeur
     pixane\installation_moteur.py (reprise après coupure, SHA-256, ComfyUI portable 0.44 selon le pilote,
     extensions, gguf, modèles GGUF Q8 sans compte Hugging Face), menu IA > Installer le moteur IA ;
     désinstalleur : propose de supprimer le moteur installé par Pixane et les réglages ;
     vrai téléchargement complet (~19 Go) pas encore essayé ;
   - [x] licence de Pixane : « Licence Pixane 1.1 » (gratuit, code ouvert, non commercial ; modifications et forks
     permis s'ils restent gratuits et sous la même licence ; nom de l'auteur obligatoire ; texte français qui fait
     foi, droit belge, présentation comme TwinPanel), page dans l'installateur ;
   - [ ] essai sur un Windows vierge (Bac à sable Windows), avec le vrai téléchargement du moteur.
7. [ ] **Publication** : guide complet, licences (Flux Fill dev = non commercial), dépôt public ou installateur.

## Numérotation des versions (décidée le 08/11/2026)
A.B.C : A = 0 tant que Pixane n'est pas fini (1.0.0 = première version finie) ; B = +1 pour un lot de nouvelles fonctions (C repart à 0) ; C = +1 pour des corrections seulement. Le numéro se change dans pixane\__init__.py avant de fabriquer l'installateur. Dernière version d'essai : 0.10.0 (ComfyUI déjà installé : Pixane ne télécharge que ce qui lui manque, fenêtre Compléter le moteur IA ; 0.9.0 : Agrandir en pleine définition : l'ajout redessiné à la vraie taille par morceaux, avec le grain de la photo ; rotation au degré près : cases Largeur / Hauteur / Angle dans Transformer, Image > Pivoter selon un angle ; 0.8.0 : plusieurs calques choisis avec Ctrl+clic / Maj+clic, fusion des calques choisis, menu du clic droit sur les calques, aperçu de la police sur le texte de la photo, icône plus grande, « Pour qui ? » ; 0.7.0 : vrais calques : les pixels hors de la feuille sont gardés, Image > Tout faire apparaître ; 0.6.1 : fond et mode gardés dans les formats enregistrés ; 0.6.0 : cadre à poignées de l'outil Déplacer, Exporter sous, flèches pour bouger la sélection, polices avec aperçu du texte ; 0.5.0 : Nouvelle image avec formats tout prêts, unités, résolution, mode, fond perdu ; taille de la zone de travail ; niveaux de gris ; export CMJN et aperçu de l'impression).

## Idées notées en passant
- Nettoyer les images d'essai dans les dossiers de sortie de ComfyUI (proposé, pas encore fait).
- **Nom du programme** (09/11/2026) : fait. « Chrypix » devient **Pixane** (projets **.pixane**, logo « P en pixels »), version 0.4.0. Les réglages, le dossier %LOCALAPPDATA% et le moteur de Chrypix sont repris au premier démarrage (pixane\ancien_nom.py) ; l'installateur remplace une installation de Chrypix.
- **16 et 32 bits par couche** (09/11/2026, demandé par Christophe : « il faudra à un moment pouvoir travailler en 16 et 32 bits si on veut que des connaisseurs utilisent le programme ») : aujourd'hui tout le moteur (calques, filtres, styles, IA) travaille en 8 bits. À faire : images internes en 16 bits (numpy uint16 / float32), lecture et écriture 16 bits (PSD, TIFF, PNG), puis 32 bits flottants (HDR, EXR). Gros chantier, à prévoir avant ou juste après la 1.0.0.
- **Vrai mode CMJN** (travailler directement en CMJN) : pas prévu ; Pixane exporte en CMJN depuis la 0.5.0.
- **Cartes AMD** (09/11/2026) : pas prévues pour l'instant (moteur et réglages faits pour NVIDIA / CUDA). Possible plus tard avec ComfyUI + ROCm sous Windows (Radeon RX 7000 / 9000), mais il faudrait une carte AMD pour tout essayer.
