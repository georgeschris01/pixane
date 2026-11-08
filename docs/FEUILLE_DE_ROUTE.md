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
2. [ ] **Toutes les fonctions de texte** (demandé le 08/11/2026, avant de reprendre la suite) : à préciser avec
   Christophe avant de commencer.
3. [ ] **Outils** : recadrer, pinceau de couleur, tampon (copier une zone sur une autre).
4. [ ] **Réglages d'image** : luminosité, contraste, couleurs, netteté.
5. [ ] **PSD** : ouvrir et enregistrer les fichiers Photoshop avec leurs calques.
6. [ ] **Assistant d'installation** : installer Chrypix chez quelqu'un d'autre, et ComfyUI + modèles s'ils
   sont absents (indispensable pour publier).
7. [ ] **Publication** : guide complet, licences (Flux Fill dev = non commercial), dépôt public ou installateur.

## Idées notées en passant
- Nettoyer les images d'essai dans les dossiers de sortie de ComfyUI (proposé, pas encore fait).
