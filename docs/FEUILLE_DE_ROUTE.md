# Feuille de route de Chrypix

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
   format .chr (textes modifiables). Guide chapitre 7.
3. [ ] **Outils** : recadrer, pinceau de couleur, tampon (copier une zone sur une autre).
4. [ ] **Réglages d'image** : luminosité, contraste, couleurs, netteté.
5. [ ] **PSD** : ouvrir et enregistrer les fichiers Photoshop avec leurs calques.
6. [ ] **Installateur** (même présentation que TwinPanel, Inno Setup 7) :
   - [x] images (validées le 08/11/2026) ;
   - [x] partie 1 (08/11/2026, à essayer par Christophe) : langue, pour moi / pour tous, dossier, vérification du PC
     (carte NVIDIA, place, ComfyUI trouvé ou dossier à indiquer), Python inclus, association .chr ;
     construire-installateur.bat -> publication\installateur\Chrypix-Setup-x.y.z.exe ;
   - [x] partie 2 (08/11/2026, à essayer par Christophe) : page « Moteur IA » si ComfyUI absent (liste taille /
     site / licence, case licence FLUX.1 [dev] obligatoire, Flux Schnell facultatif), téléchargeur
     chrypix\installation_moteur.py (reprise après coupure, SHA-256, ComfyUI portable 0.44 selon le pilote,
     extensions, gguf, modèles GGUF Q8 sans compte Hugging Face), menu IA > Installer le moteur IA ;
     désinstalleur : propose de supprimer le moteur installé par Chrypix et les réglages ;
     vrai téléchargement complet (~19 Go) pas encore essayé ;
   - [x] licence de Chrypix : « Licence Chrypix 1.1 » (gratuit, code ouvert, non commercial ; modifications et forks
     permis s'ils restent gratuits et sous la même licence ; nom de l'auteur obligatoire ; texte français qui fait
     foi, droit belge, présentation comme TwinPanel), page dans l'installateur ;
   - [ ] essai sur un Windows vierge (Bac à sable Windows), avec le vrai téléchargement du moteur.
7. [ ] **Publication** : guide complet, licences (Flux Fill dev = non commercial), dépôt public ou installateur.

## Idées notées en passant
- Nettoyer les images d'essai dans les dossiers de sortie de ComfyUI (proposé, pas encore fait).
