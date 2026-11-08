# Feuille de route de Chrypix

Liste des étapes décidées avec Christophe. Cocher quand c'est fait (et mettre à jour docs/GUIDE.md).

## Fait
- [x] Base : ouvrir / enregistrer, zoom, sélection (pinceau, gomme, rectangle, lasso), annuler.
- [x] IA : Effacer, Remplir, Agrandir (deux cadres : agrandir + bord abîmé), Upscale (Net / Rapide).
- [x] Interface moderne, couleur d'accent et thème de Windows, barre de progression, logo « C en pixels ».
- [x] Guide d'utilisation (docs/GUIDE.md).

## À faire (dans cet ordre, sauf décision contraire)
1. [ ] **Calques** — en cours (lancé le 08/11/2026). Fait : panneau, IA sur calques, gomme de calque, .ora.
   Reste : validation par Christophe.
   Panneau Calques (vignette, œil, nom, opacité, ordre, nouveau / dupliquer / supprimer / fusionner / aplatir) ;
   Effacer et Remplir créent un calque avec seulement la zone retouchée ; Agrandir décale les calques et met l'ajout
   (seulement les nouveaux pixels) dans un calque au-dessus ; Upscale agrandit tous les calques ; l'IA voit l'image visible ; outil « Gomme de calque » ;
   format projet .ora (OpenRaster) pour garder les calques.
2. [ ] **Français / anglais** (demandé le 08/11/2026) : tout le programme dans les deux langues ; par défaut la
   langue de Windows (choisie aussi par l'installateur), changeable dans le menu ; guide en anglais aussi.
   Déjà fait : les fenêtres standard de Qt (Oui / Non / Annuler, clic droit…) sont en français.
3. [ ] **Outils** : recadrer, pinceau de couleur, tampon (copier une zone sur une autre), texte.
4. [ ] **Réglages d'image** : luminosité, contraste, couleurs, netteté.
5. [ ] **PSD** : ouvrir et enregistrer les fichiers Photoshop avec leurs calques.
6. [ ] **Assistant d'installation** : installer Chrypix chez quelqu'un d'autre, et ComfyUI + modèles s'ils
   sont absents (indispensable pour publier).
7. [ ] **Publication** : guide complet, licences (Flux Fill dev = non commercial), dépôt public ou installateur.

## Idées notées en passant
- Nettoyer les images d'essai dans les dossiers de sortie de ComfyUI (proposé, pas encore fait).
