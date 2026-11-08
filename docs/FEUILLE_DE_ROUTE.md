# Feuille de route de Chrypix

Liste des étapes décidées avec Christophe. Cocher quand c'est fait (et mettre à jour docs/GUIDE.md).

## Fait
- [x] Base : ouvrir / enregistrer, zoom, sélection (pinceau, gomme, rectangle, lasso), annuler.
- [x] IA : Effacer, Remplir, Agrandir (deux cadres : agrandir + bord abîmé), Upscale (Net / Rapide).
- [x] Interface moderne, couleur d'accent et thème de Windows, barre de progression, logo « C en pixels ».
- [x] Guide d'utilisation (docs/GUIDE.md).

## À faire (dans cet ordre, sauf décision contraire)
1. [ ] **Calques** — en cours (lancé le 08/11/2026).
   Panneau Calques (vignette, œil, nom, opacité, ordre, nouveau / dupliquer / supprimer / fusionner / aplatir) ;
   Effacer et Remplir créent un calque avec seulement la zone retouchée ; Agrandir décale les calques et met
   l'ajout dessous ; Upscale agrandit tous les calques ; l'IA voit l'image visible ; outil « Gomme de calque » ;
   format projet .ora (OpenRaster) pour garder les calques.
2. [ ] **Outils** : recadrer, pinceau de couleur, tampon (copier une zone sur une autre), texte.
3. [ ] **Réglages d'image** : luminosité, contraste, couleurs, netteté.
4. [ ] **PSD** : ouvrir et enregistrer les fichiers Photoshop avec leurs calques.
5. [ ] **Assistant d'installation** : installer Chrypix chez quelqu'un d'autre, et ComfyUI + modèles s'ils
   sont absents (indispensable pour publier).
6. [ ] **Publication** : guide complet, licences (Flux Fill dev = non commercial), dépôt public ou installateur.

## Idées notées en passant
- Nettoyer les images d'essai dans les dossiers de sortie de ComfyUI (proposé, pas encore fait).
