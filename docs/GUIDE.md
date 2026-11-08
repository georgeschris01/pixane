# Guide d'utilisation de Chrypix

Chrypix est un éditeur photo pour Windows qui retouche les images avec une IA qui tourne **sur votre PC**
(pas d'abonnement, pas d'envoi de photos sur Internet).
Ce guide explique chaque outil et chaque réglage. Il est complété à chaque nouvelle fonction.

---

## 1. La fenêtre

| Zone | Rôle |
|---|---|
| **Barre du haut** | Ouvrir, Enregistrer, Annuler / Rétablir, taille du pinceau, Ajouter / Retirer, zoom, thème clair / sombre |
| **Outils (à gauche)** | Main, Rectangle, Lasso, Pinceau, Gomme |
| **Photo (au centre)** | La photo ; la zone sélectionnée apparaît en rouge transparent |
| **Panneau « Intelligence artificielle » (à droite)** | Effacer, Remplir, Agrandir l'image, Upscale |
| **Panneau « Calques » (à droite, en dessous)** | Les calques de l'image (voir chapitre 6) |
| **Barre d'état (en bas)** | État du moteur IA (point de couleur), taille de la photo |

**Couleurs** : Chrypix prend la couleur d'accent choisie dans Windows (Paramètres > Personnalisation > Couleurs)
et suit le mode clair / sombre de Windows. Menu **Affichage > Thème** : *Comme Windows*, *Clair* ou *Sombre*.
Le bouton soleil / lune de la barre du haut bascule aussi entre clair et sombre.

**Moteur IA** : au démarrage, Chrypix lance l'IA (ComfyUI) en arrière-plan, sans fenêtre. Comptez environ
20 secondes. Le point en bas à gauche passe au vert quand le moteur est prêt ; les actions IA sont grisées avant.

---

## 2. Ouvrir et enregistrer

- **Fichier > Ouvrir** (Ctrl+O) : JPG, PNG, TIFF, WebP, BMP, et les projets à calques **.ora**.
  La photo est redressée selon son orientation d'appareil.
- **Enregistrer** (Ctrl+S), **Enregistrer sous** (Ctrl+Maj+S) :
  - **.ora** (OpenRaster) : garde **tous les calques** (noms, ordre, visibilité, opacité). Format ouvert, lisible
    aussi par Krita, GIMP et MyPaint. Proposé d'office quand l'image a plusieurs calques.
  - **JPG** (qualité 95), **PNG**, **TIFF**, **WebP** : l'image **à plat** (ce que vous voyez, calques fusionnés).
    Un message le rappelle si l'image a plusieurs calques.
  Les informations de l'appareil (EXIF) et le profil de couleur sont conservés.
- **Annuler** (Ctrl+Z) / **Rétablir** (Ctrl+Y ou Ctrl+Maj+Z) : chaque retouche et chaque sélection peut être annulée
  (30 étapes).

---

## 3. Se déplacer dans la photo

| Action | Comment |
|---|---|
| Zoomer | Molette (autour du curseur), Ctrl++ / Ctrl+-, boutons loupe |
| Ajuster à la fenêtre | Ctrl+0 |
| Taille réelle (100 %) | Ctrl+1 |
| Déplacer la vue | Outil **Main** (H), ou maintenir **Espace** et glisser, ou glisser avec le **bouton du milieu** |

---

## 4. Sélectionner (dire à l'IA où travailler)

La zone sélectionnée apparaît en **rouge transparent**. Il n'est pas nécessaire d'« entourer » un objet :
on peut simplement **peindre dessus**.

| Outil | Touche | Usage |
|---|---|---|
| **Pinceau** | B | Peindre la zone. Idéal pour un objet, un texte, un fil… |
| **Gomme** | E | Retirer de la sélection en peignant |
| **Gomme de calque** | G | Efface **pour de vrai** les pixels du calque choisi (voir chapitre 6) |
| **Rectangle** | M | Sélection rectangulaire |
| **Lasso** | L | Tracer un contour à main levée ; la forme est fermée automatiquement |

- **Taille du pinceau** : curseur « Taille » de la barre du haut, ou touches `[` et `]`.
- **Ajouter / Retirer** (pastilles de la barre du haut) : avec *Retirer*, Rectangle, Lasso et Pinceau enlèvent de la
  sélection au lieu d'ajouter. Maintenir **Alt** inverse le mode le temps d'un geste.
- Menu **Sélection** : *Tout sélectionner* (Ctrl+A), *Désélectionner* (Ctrl+D), *Inverser* (Ctrl+Maj+I).

**Conseil (texte, cursive, objet fin)** : couvrez bien chaque lettre, bords compris, avec un pinceau un peu plus large
que le trait ; n'oubliez pas l'ombre ou le contour s'il y en a. Chrypix élargit déjà un peu la zone (environ 16 px)
pour attraper les bords flous.

---

## 5. Les actions IA

Chaque action propose **plusieurs résultats** : on choisit le meilleur, comme dans Photoshop.
Le résultat gardé arrive sur un **nouveau calque** (« Effacer 1 », « Remplir 2 »…) : la photo d'origine n'est
jamais abîmée. L'IA travaille toujours sur l'image **telle qu'on la voit** (tous les calques visibles ensemble).

### Fenêtre de choix du résultat
- Cliquez sur une vignette pour la voir en grand.
- **Maintenir pour voir l'original** : tant que le bouton est enfoncé, la photo d'avant s'affiche.
- **Autres propositions** : relance l'IA pour de nouvelles versions (elles s'ajoutent aux précédentes).
- **Garder ce résultat** : applique la version choisie (annulable par Ctrl+Z).

### Pendant le calcul
Une fenêtre affiche l'étape en cours, une **barre de progression**, le temps écoulé et le **temps restant estimé**.
**Annuler** arrête le calcul.

### Effacer (Maj+E)
Enlève ce qui est peint en rouge et reconstruit le fond.
- Deux méthodes combinées : **LaMa** (rapide, efface proprement) puis une finition par **Flux Fill** (plus réaliste).
- Résultats proposés : 2 versions Flux + la version « LaMa seul ».
- Durée indicative : environ 2 minutes (carte graphique 8 Go).

### Remplir (Maj+R)
Redessine la zone peinte en rouge.
- **Sans texte** (recommandé) : l'IA invente ce qui va bien avec le reste de la photo.
- **Avec un texte** (champ « Texte facultatif », en anglais de préférence) : décrit ce qu'on veut voir à la place.
- 3 propositions, environ 1 minute chacune.

### Agrandir l'image (Maj+A)
Étend la photo au-delà de ses bords : l'IA invente la suite du décor.

Deux cadres apparaissent sur la photo :

| Cadre | Aspect | Rôle |
|---|---|---|
| **Cadre d'agrandissement** | pointillés blancs, **poignées carrées** couleur d'accent | Tirez-le **vers l'extérieur** : la zone ajoutée s'affiche en damier gris |
| **Cadre « bord abîmé »** | pointillés **rouges**, **poignées rondes** rouges | Tirez-le **vers l'intérieur** : la bande hachurée rouge est un bord abîmé (liseré, trait, flou, coin déchiré…) qui sera **jeté puis redessiné** par l'IA |

- Quand les deux cadres sont l'un sur l'autre (au départ), le **sens du geste** décide : vers l'extérieur = agrandir,
  vers l'intérieur = bord abîmé.
- **Maj** en tirant : le côté opposé bouge pareil (agrandir à gauche et à droite en même temps, par exemple).
- **Détection automatique** : à l'ouverture, Chrypix repère les liserés clairs ou foncés (1 à 8 px) que beaucoup
  d'images ont sur leurs bords, et place déjà le cadre rouge dessus. Vous pouvez l'ajuster ou le remettre à 0.
- **Barre en haut de la photo** :
  - ligne **Agrandir** : ce qui est ajouté de chaque côté, en % de la photo (0 à 200 %) ;
  - ligne **Bord abîmé** : la bande à refaire de chaque côté, en pixels ;
  - **taille finale** de l'image ;
  - **Lancer** (ou Entrée) / **Annuler** (ou Échap).
  Les cases et les cadres se suivent : modifier l'un met l'autre à jour.
- **Taille finale** = photo d'origine + agrandissement. Le bord abîmé ne réduit pas l'image : il est remplacé.
- Le raccord entre la photo et l'ajout est fait par Chrypix : la photo d'origine est gardée **au pixel près**, avec un
  fondu progressif et un accord des couleurs, pour qu'aucune ligne ne soit visible.
- 3 propositions, environ 1 minute chacune.
- **Calques** : tous les calques sont décalés sur la nouvelle toile ; un calque « Agrandir 1 » contient l'ajout
  et le bord refait (seulement les pixels nouveaux).
- Si la photo contient du texte, l'IA invente parfois des lettres sans sens dans l'ajout : utilisez
  « Autres propositions ».

### Upscale (Maj+U)
Augmente la définition (nombre de pixels) de la photo.

| Réglage | Valeurs | Effet |
|---|---|---|
| **Net** | par défaut | RealESRGAN agrandit, puis **Flux redessine les détails** morceau par morceau. Plus lent (environ 20 à 30 s par morceau de 1024 px) mais net |
| **Rapide** | | RealESRGAN seul : quelques secondes, mais peut donner un aspect lissé (« plastique ») |
| **Facteur** | ×1,5 à ×4 (×2 par défaut) | Combien de fois plus grand |
| **Force** (mode Net) | 0,10 à 0,60 (0,35 par défaut) | Liberté laissée à Flux : bas = fidèle à l'original, haut = plus de détails inventés |

La fenêtre indique la taille finale avant de lancer ; pendant le calcul, la progression compte les morceaux.

**Calques** : tous les calques sont agrandis (lissage simple) et le résultat de l'IA arrive, complet, sur un
calque « Upscale 1 » au-dessus.

---

## 6. Les calques

Une image peut avoir plusieurs **calques**, empilés comme des feuilles transparentes : celui du haut passe
devant. Une photo ouverte a un seul calque, « Arrière-plan ».

### Le panneau Calques
| Élément | Rôle |
|---|---|
| **Liste** | Le calque du haut est en haut. Cliquez sur un calque pour le choisir (il est surligné) |
| **Œil** | Afficher / masquer le calque (pratique pour comparer avant / après une retouche IA) |
| **Vignette** | Aperçu du calque ; le damier gris montre les parties transparentes |
| **Nom** | Double-clic pour renommer |
| **Opacité** | Transparence du calque choisi, de 0 % (invisible) à 100 % ; affichée sous le nom quand < 100 % |
| **Cadenas** (à droite du nom) | Verrouille le calque pour le protéger : il ne peut plus être gommé, supprimé ni fusionné, et son opacité est bloquée ; Aplatir est désactivé tant qu'un calque est verrouillé. On peut toujours le masquer, le renommer et le monter / descendre. Agrandir et Upscale le redimensionnent avec toute l'image. Le cadenas ouvert est discret, le cadenas fermé bien visible. Le verrou est gardé dans les fichiers .ora |

### Les boutons (de gauche à droite)
| Bouton | Action |
|---|---|
| **Nouveau calque** | Ajoute un calque vide au-dessus du calque choisi |
| **Dupliquer** | Copie le calque choisi |
| **Monter / Descendre** | Change la place du calque dans la pile |
| **Fusionner** | Réunit le calque choisi avec celui du dessous (l'opacité est appliquée) |
| **Aplatir** | Réunit tous les calques visibles en un seul « Arrière-plan » |
| **Supprimer** | Supprime le calque choisi (le dernier calque ne peut pas être supprimé) |

### Gomme de calque (G)
Efface les pixels du **calque choisi** avec le pinceau rond (taille : curseur « Taille » ou `[` `]`).
Exemple : une retouche IA réussie sauf sur un bord → choisissez son calque et gommez ce bord ; la photo
d'origine réapparaît dessous. Les zones effacées d'un calque seul apparaissent en damier.
À ne pas confondre avec la **Gomme de sélection** (E), qui ne touche qu'au rouge de la sélection.
Sur un calque verrouillé, la gomme ne fait rien et un message en bas de la fenêtre l'indique.

Toutes les actions sur les calques s'annulent avec Ctrl+Z (changer de calque choisi ne compte pas).

---

## 7. Raccourcis

| Touche | Action |
|---|---|
| H, M, L, B, E, G | Main, Rectangle, Lasso, Pinceau, Gomme de sélection, Gomme de calque |
| `[` / `]` | Pinceau plus petit / plus grand |
| Espace (maintenu) | Déplacer la vue |
| Alt (maintenu) | Inverser Ajouter / Retirer le temps d'un geste |
| Maj+E, Maj+R, Maj+A, Maj+U | Effacer, Remplir, Agrandir, Upscale |
| Ctrl+Z, Ctrl+Y | Annuler, Rétablir |
| Ctrl+A, Ctrl+D, Ctrl+Maj+I | Tout sélectionner, Désélectionner, Inverser |
| Ctrl+0, Ctrl+1 | Ajuster, 100 % |
| Entrée / Échap | (Agrandir) Lancer / Annuler |
| F1 | Liste des raccourcis |

---

## 8. Matériel et licences

- Testé sur une carte graphique NVIDIA de 8 Go (RTX 3060 Ti). Les durées indiquées viennent de ce PC.
- Modèles utilisés : Flux.1 Fill dev (**usage non commercial**), Flux.1 Schnell (Apache-2.0),
  LaMa (Apache-2.0), RealESRGAN x4plus (BSD-3).
