# Chrypix

**Français** · [English](README.en.md)

Éditeur photo gratuit pour Windows, avec retouche par intelligence artificielle **sur votre PC** : pas d'abonnement, aucune photo envoyée sur Internet. Interface en français et en anglais.

- **Effacer** un objet : on peint dessus, l'IA le fait disparaître et reconstruit le fond
- **Remplir** une zone : l'IA invente ce qui va le mieux à cet endroit
- **Agrandir** l'image au-delà de ses bords (outpaint) : l'IA prolonge le décor
- **Upscale** : augmenter la définition (×1,5 à ×4), en version rapide ou plus nette
- Plusieurs propositions à chaque fois : on choisit la meilleure, comme dans Photoshop
- Calques : visibilité, opacité, verrou, ordre, fusion ; chaque résultat de l'IA arrive dans son propre calque
- Sélection au rectangle, au lasso ou au pinceau ; couper, copier, coller, supprimer
- Outils de retouche : recadrer, pinceau de couleur, tampon, gomme de calque, déplacer
- Texte modifiable : police, taille, couleur, contour, ombre, fond, rotation
- JPG, PNG, TIFF, WebP, BMP, et `.chr` / `.ora` pour garder les calques ; informations EXIF et profil couleur conservés
- Annuler / Rétablir (30 dernières étapes)
- Thème clair ou sombre, couleur d'accent de Windows
- Installateur qui vérifie le PC et télécharge lui-même le moteur IA (ComfyUI et les modèles), avec reprise après coupure

## Télécharger

**[Chrypix pour Windows](../../releases/latest)** (installateur 64 bits, `Chrypix-Setup-<version>-64bits.exe`).

**Il faut :**
- Windows 10 ou 11, 64 bits ;
- une carte graphique **NVIDIA** avec **8 Go** de mémoire (testé sur une RTX 3060 Ti) ; sans elle, Chrypix s'ouvre et retouche, mais les actions IA ne marchent pas ;
- environ **30 Go** de place pour le moteur IA (19,4 Go à télécharger), 41 Go avec l'option « Upscale net ».

L'installateur vérifie la carte graphique et la place libre, puis propose de télécharger le moteur IA depuis les sites officiels (GitHub, Hugging Face). Le modèle Flux Fill est sous licence **FLUX.1 [dev] non commerciale** : il faut l'accepter pour l'installer.

> **Message « Windows a protégé votre ordinateur » :** Chrypix est gratuit et n'est pas signé, car un certificat de signature est payant chaque année. Windows affiche donc ce message tant que le programme n'est pas assez connu. Cliquez sur **Informations complémentaires**, puis sur **Exécuter quand même**. Vérifiez que le fichier vient bien de cette page ; son empreinte SHA-256 est donnée avec chaque version.

Pour demander une fonction ou signaler un problème : ouvrez une [« Issue »](../../issues) sur la page GitHub de Chrypix.

## À l'origine de ce projet (Pourquoi et comment ?)

J'utilisais Photoshop et j'appréciais beaucoup son IA générative : effacer un objet, remplir une zone, agrandir une image… Elle réussissait presque à chaque fois. Mais je ne voulais plus payer l'abonnement.

J'ai essayé les solutions gratuites, comme Krita avec son extension d'IA : les résultats étaient très aléatoires, l'inverse de ce que j'avais connu. J'ai donc créé **Chrypix**, d'abord pour mon usage personnel : un éditeur simple, avec des réglages de l'IA choisis et testés pour réussir au premier essai, qui tourne entièrement sur le PC.

### Une totale transparence avec vous :

Je tiens à être 100 % honnête avec tout le monde : **je n'y connais absolument rien en programmation et je ne parle pas d'autre langue que le français**.

**Chrypix** a pu voir le jour, être entièrement codé et traduit en anglais grâce à l'aide de l'intelligence artificielle **Claude Code**. L'IA m'a accompagné pas à pas pour traduire mes besoins en lignes de code et pour générer la version anglaise du logiciel afin qu'il soit accessible au plus grand nombre.

Le programme est partagé ici tel quel, de bon cœur, dans le seul but d'être utile. Il est entièrement gratuit, mais comme vous pourrez le lire dans la section Licence ci-dessous, il reste protégé pour garantir qu'il ne soit jamais commercialisé.

Bienvenue à tous les futurs utilisateurs de Chrypix !

## Guide

Ce qui suit est le guide complet. C'est le même texte que le fichier `docs\GUIDE.md` livré avec le programme (menu **Aide**, touche **F1** pour les raccourcis).

<!-- guide -->
## 1. La fenêtre

| Zone | Rôle |
|---|---|
| **Barre du haut** | Ouvrir, Enregistrer, Annuler / Rétablir, réglages de l'outil choisi (taille, Nouvelle / Ajouter / Retirer…), zoom |
| **Outils (à gauche)** | Main, Déplacer, outils de sélection, outils de retouche, Recadrer, Texte. Un petit triangle sur un bouton = plusieurs outils : **clic droit** (ou clic maintenu) pour choisir |
| **Panneau « Texte » (à gauche)** | Réglages du texte, visible avec l'outil Texte (voir chapitre 7) |
| **Photo (au centre)** | La photo ; la zone sélectionnée apparaît en rouge transparent |
| **Panneau « Intelligence artificielle » (à droite)** | Effacer, Remplir, Agrandir l'image, Upscale |
| **Panneau « Calques » (à droite, en dessous)** | Les calques de l'image (voir chapitre 6) |
| **Barre d'état (en bas)** | État du moteur IA (point de couleur), taille de la photo |

**Couleurs** : Chrypix prend la couleur d'accent choisie dans Windows (Paramètres > Personnalisation > Couleurs)
et suit le mode clair / sombre de Windows. Menu **Affichage > Thème** : *Comme Windows*, *Clair* ou *Sombre*.
Le bouton soleil / lune de la barre du haut bascule aussi entre clair et sombre.

**Langue** : Chrypix existe en **français** et en **anglais**. Par défaut, il prend la langue de Windows
(français si Windows est en français, anglais sinon). Menu **Affichage > Langue** : *Comme Windows*, *Français*
ou *English* ; Chrypix propose alors de redémarrer pour appliquer la langue (le moteur IA redémarre aussi,
environ 20 secondes). Les boutons standard (Oui / Non / Annuler, menu clic droit) suivent la même langue.
Les noms de calques déjà créés gardent leur langue d'origine. Guide en anglais : `docs\GUIDE_en.md`.

**Moteur IA** : au démarrage, Chrypix lance l'IA (ComfyUI) en arrière-plan, sans fenêtre. Comptez environ
20 secondes. Le point en bas à gauche passe au vert quand le moteur est prêt ; les actions IA sont grisées avant.

---

## 2. Ouvrir et enregistrer

- **Fichier > Ouvrir** (Ctrl+O) : JPG, PNG, TIFF, WebP, BMP, et les projets à calques **.chr** et **.ora**.
  La photo est redressée selon son orientation d'appareil.
- **Enregistrer** (Ctrl+S), **Enregistrer sous** (Ctrl+Maj+S) :
  - **.chr** (projet Chrypix) : le format de Chrypix. Garde **tout** : calques (noms, ordre, visibilité, opacité,
    verrou) et **textes modifiables**. Proposé d'office quand l'image a plusieurs calques ou un texte.
  - **.ora** (OpenRaster) : pour **partager avec Krita ou GIMP** (format ouvert). Garde les calques, mais les
    textes y deviennent des images.
  - Bon à savoir : un .chr est construit comme un .ora ; renommé en .ora, il s'ouvre aussi dans Krita ou GIMP.
  - **Photoshop** n'ouvre pas les .ora : l'enregistrement en PSD (calques) est prévu dans une prochaine étape.
    En attendant, enregistrez en PNG ou TIFF (image à plat).
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
| Déplacer **un calque** | Outil **Déplacer** (V) : seul le calque choisi bouge (la Main, elle, ne déplace que la vue) |

---

## 4. Sélectionner (dire à l'IA où travailler)

La zone sélectionnée apparaît en **rouge transparent**. Il n'est pas nécessaire d'« entourer » un objet :
on peut simplement **peindre dessus**.

Les quatre outils de sélection sont rangés sous **un seul bouton** de la barre de gauche (petit triangle) :
**clic droit** dessus, ou clic maintenu, pour choisir ; ou directement leur touche.

| Outil | Touche | Usage |
|---|---|---|
| **Rectangle** | M | Sélection rectangulaire |
| **Lasso** | L | Tracer un contour à main levée, bouton appuyé ; la forme est fermée automatiquement |
| **Pinceau de sélection** | B | Peindre la zone. Idéal pour un objet, un texte, un fil… |
| **Gomme de sélection** | E | Retirer de la sélection en peignant |

- **Rectangle et lasso**, comme dans Photoshop : une nouvelle sélection **remplace** l'ancienne. Maintenir **Maj** en
  commençant le tracé **ajoute** à la sélection, **Alt** **retire**. Un simple clic sans tracer **désélectionne**.
  Les pastilles **Nouvelle / Ajouter / Retirer** de la barre du haut choisissent le mode sans touche.
- **Pinceau de sélection** : il ajoute toujours à la sélection ; pastille **Retirer** ou **Alt** maintenu : il retire
  (comme la gomme de sélection).
- **Taille du pinceau** : curseur « Taille » de la barre du haut, ou touches `[` et `]`.
- Menu **Sélection** : *Tout sélectionner* (Ctrl+A), *Désélectionner* (Ctrl+D), *Inverser* (Ctrl+Maj+I).

### Couper, copier, coller, supprimer (menu Édition)
Ils agissent sur le **calque choisi** dans le panneau Calques :
- **Copier** (Ctrl+C) : copie ce qui est sélectionné (tout le calque s'il n'y a pas de sélection). La copie garde sa
  transparence ; on peut aussi la coller dans un autre logiciel.
- **Couper** (Ctrl+X) : copie, puis efface la zone sélectionnée (elle devient transparente).
- **Coller** (Ctrl+V) : met l'image copiée dans un **nouveau calque**, à **la même place** si elle vient de Chrypix,
  au centre si elle vient d'ailleurs (capture d'écran, autre logiciel…). Bougez-la ensuite avec l'outil Déplacer (V).
- **Supprimer la sélection** (Suppr) : efface la zone sélectionnée du calque (transparente).

Un calque **verrouillé** est protégé ; un **texte** coupé ou supprimé devient une image. Ctrl+Z annule tout.

Les autres outils : **Déplacer** (V) bouge le contenu du **calque choisi** (un texte déplacé reste modifiable ; ce qui
sort de l'image est coupé ; refusé sur un calque verrouillé). La **Gomme de calque** (G) efface **pour de vrai** les
pixels du calque choisi (voir chapitre 6) ; elle est rangée avec le pinceau de couleur et le tampon.

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
- **Garder ce résultat** : applique la version choisie (annulable par Ctrl+Z). La sélection (pinceau, lasso,
  rectangle) disparaît alors ; Ctrl+Z la fait revenir avec la photo d'avant.

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
| **Cadenas** (à droite du nom) | Verrouille le calque pour le protéger : il ne peut plus être gommé, supprimé ni fusionné, et son opacité est bloquée ; Aplatir est désactivé tant qu'un calque est verrouillé. Les actions IA sont refusées avec un message : Effacer et Remplir si le calque choisi est verrouillé, Agrandir et Upscale si un calque quelconque est verrouillé (ils changent la taille de tous les calques). On peut toujours le masquer, le renommer et le monter / descendre. Le cadenas ouvert est discret, le cadenas fermé bien visible. Le verrou est gardé dans les fichiers .chr et .ora |

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

## 7. Le texte

Outil **Texte** (touche **T**, icône « T » dans la barre d'outils). Le panneau **Texte** s'ouvre à gauche.

### Écrire, déplacer, tourner
- **Cliquer sur la photo** : un nouveau texte « Texte » apparaît à cet endroit, sur **son propre calque**.
  Tapez directement : le mot proposé est remplacé. La case du panneau accepte plusieurs lignes (Entrée).
- **Cliquer sur un texte existant** : il est choisi et ses réglages s'affichent ; on peut le modifier à tout
  moment, même après avoir enregistré en **.chr** et rouvert.
- Le texte s'applique **au fur et à mesure** : rien à valider.
- **Glisser le texte** : le déplacer (aussi avec l'outil Déplacer, V). Un cadre en pointillés entoure le texte choisi.
- **Poignée ronde** au-dessus du cadre : tourner le texte (**Maj** : par pas de 15°), ou case *Rotation*.
- Le nom du calque suit la première ligne du texte (tant qu'on ne l'a pas renommé à la main).
- Sans texte choisi, les réglages du panneau servent pour le **prochain** texte ; Chrypix retient aussi le
  dernier style utilisé (police, couleur, effets…). La taille du nouveau texte est calculée d'après la photo.

### Réglages du panneau
| Réglage | Effet |
|---|---|
| **Police** | Toutes les polices installées dans Windows |
| **Taille** | Hauteur des lettres, en pixels de la photo |
| **Couleur** (pastille) | Couleur des lettres, avec la transparence (canal alpha) |
| **G / I / S / B** | Gras, italique, souligné, barré |
| **Alignement** | À gauche, centré, à droite (pour plusieurs lignes) |
| **Lettres** | Espace ajouté entre les lettres, en % de la taille (négatif = lettres serrées) |
| **Lignes** | Écart entre les lignes, × la taille des lettres |
| **Rotation** | Angle en degrés |
| **Courbe** | Texte en arc : positif = en voûte, négatif = en creux, 360° = cercle complet |
| **Contour** | Trait autour des lettres : couleur et épaisseur |
| **Ombre portée** | Couleur, distance, direction (0° = vers la droite, 90° = vers le bas) et flou |
| **Fond** | Rectangle coloré derrière le texte : couleur, marge et arrondi des coins |

Les tailles des effets (épaisseur, distance, flou, marge, arrondi) sont en **% de la taille des lettres** :
ils restent proportionnés quand on change la taille du texte.
**Transparence** du texte entier : curseur **Opacité** du panneau Calques.

### Bon à savoir
- Toutes les modifications s'annulent avec Ctrl+Z ; une saisie de plusieurs lettres s'annule d'un seul coup.
- **Agrandir** et **Upscale** gardent les textes modifiables : ils sont décalés ou redessinés nets à la nouvelle taille.
- La **Gomme de calque** sur un texte le transforme en image (un message le signale ; Ctrl+Z pour revenir).
  **Fusionner** ou **Aplatir** aussi.
- Un texte sur un calque **verrouillé** ne peut être ni déplacé ni modifié.
- Pour garder les textes modifiables, enregistrez en **.chr** (dans un .ora, ils deviennent des images).

---

## 8. Recadrer, peindre, tamponner

Trois outils de retouche à la main, comme dans Photoshop. Tout s'annule par **Ctrl+Z** ; un calque **verrouillé**
est protégé.

### Recadrer (C)
1. Tirez un cadre sur la photo : la partie gardée reste claire, le reste est assombri, une grille des tiers aide à
   placer le sujet. La taille du résultat s'affiche sous le cadre.
2. Ajustez-le : les **poignées** (coins et milieux des côtés) changent sa taille, glisser **dans** le cadre le
   déplace. Le cadre ne sort jamais de la photo (pour l'agrandir, voir *Agrandir l'image*).
3. **Proportions** (barre du haut) : *Libre*, *Comme la photo*, 1:1, 4:3, 3:2, 16:9, et les mêmes en hauteur.
4. **Entrée**, double-clic dans le cadre ou bouton **Recadrer** : c'est fait. **Échap** ou **Annuler** : le cadre
   disparaît sans rien changer.

Tous les calques sont recadrés ensemble ; les textes restent modifiables. Menu **Sélection > Recadrer à la
sélection** : garde le plus petit rectangle qui contient la sélection.

### Pinceau de couleur (P)
Peint sur le **calque choisi** dans le panneau Calques (astuce : un calque vide au-dessus de la photo permet de
corriger sans toucher à la photo).
- **Couleur** : pastille de la barre du haut. **Alt+clic** sur la photo prend la couleur à cet endroit (pipette).
- **Taille** (ou `[` et `]`), **Opacité** (100 % couvre tout, moins laisse voir dessous) et **Dureté** (100 % bord
  net, 0 % bord très doux).
- Repasser au même endroit pendant un même coup ne fonce pas la couleur ; un nouveau coup, si.

### Tampon (S)
Recopie une partie de la photo sur une autre : pour effacer un petit défaut à la main, dupliquer une texture…
1. **Alt+clic** sur l'endroit à copier (une croix le marque).
2. Peignez là où il doit être recopié : la croix suit, à la même distance.
3. Les coups suivants gardent ce même décalage (comme l'option « Aligné » de Photoshop). Un nouvel Alt+clic choisit
   un autre endroit.

Le tampon copie la photo **telle qu'on la voit** (tous les calques visibles) et peint sur le calque choisi. Taille,
opacité et dureté comme le pinceau.

Un **texte** retouché au pinceau ou au tampon devient une image (un message le rappelle ; Ctrl+Z pour revenir).

---

## 9. Raccourcis

| Touche | Action |
|---|---|
| H, V, M, L, B, E, G, T | Main, Déplacer, Rectangle, Lasso, Pinceau, Gomme de sélection, Gomme de calque, Texte |
| C, P, S | Recadrer, Pinceau de couleur, Tampon |
| Alt+clic | (Pinceau de couleur) prendre une couleur ; (Tampon) endroit à copier |
| `[` / `]` | Pinceau plus petit / plus grand |
| Espace (maintenu) | Déplacer la vue |
| Maj / Alt (en commençant un rectangle ou un lasso) | Ajouter / Retirer |
| Alt (maintenu, pinceau de sélection) | Retirer le temps d'un geste |
| Maj+E, Maj+R, Maj+A, Maj+U | Effacer, Remplir, Agrandir, Upscale |
| Ctrl+Z, Ctrl+Y | Annuler, Rétablir |
| Ctrl+A, Ctrl+D, Ctrl+Maj+I | Tout sélectionner, Désélectionner, Inverser |
| Ctrl+X, Ctrl+C, Ctrl+V, Suppr | Couper, Copier, Coller (nouveau calque), Supprimer la sélection |
| Clic droit sur un outil à petit triangle | Choisir un autre outil du groupe |
| Ctrl+0, Ctrl+1 | Ajuster, 100 % |
| Entrée / Échap | (Agrandir) Lancer / Annuler ; (Recadrer) Valider / Annuler |
| Maj (en tournant un texte) | Rotation par pas de 15° |
| F1 | Liste des raccourcis |

---

## 10. Matériel et licences

**Installation** : lancer `Chrypix-Setup-<version>-64bits.exe`.
1. Langue de l'installation (ce sera aussi la langue de Chrypix, modifiable ensuite dans Affichage > Langue).
2. Pour moi seulement (par défaut, sans droits administrateur) ou pour tous les utilisateurs.
3. Dossier d'installation.
4. **Vérification du PC** : carte graphique NVIDIA et sa mémoire (8 Go conseillés), place libre, moteur IA
   (ComfyUI) trouvé ou non. Si ComfyUI est installé ailleurs, bouton **Parcourir…** pour indiquer son dossier.
   Sans ComfyUI, Chrypix ouvre, retouche (calques, texte) et enregistre, mais les actions IA ne marchent pas.
5. **Moteur IA** (seulement si ComfyUI n'est pas trouvé) : liste de ce qui sera téléchargé, avec taille, site et
   licence (19,4 Go à télécharger, environ 28 Go sur le disque) ; dossier du moteur (par défaut
   `%LOCALAPPDATA%\Chrypix\moteur`) ; case facultative **Flux Schnell** pour « Upscale net » (11,8 Go de plus) ;
   case **J'accepte la licence FLUX.1 [dev]** (usage non commercial) obligatoire pour installer le moteur.
   On peut aussi décocher : Chrypix s'installe sans moteur.
6. Options : icône sur le Bureau ; ouvrir les fichiers .chr avec Chrypix.
7. À la fin, la fenêtre **Installer le moteur IA** télécharge et installe tout (ComfyUI portable, ses extensions,
   les modèles). Elle montre l'avancement, la vitesse et le temps restant. **Arrêter** est possible à tout moment :
   le téléchargement reprendra plus tard là où il s'était arrêté (même après une coupure). Chaque fichier est
   vérifié (empreinte SHA-256).

La même fenêtre s'ouvre par le menu **IA > Installer le moteur IA…** (par exemple pour ajouter Flux Schnell plus
tard), et Chrypix la propose au démarrage s'il ne trouve pas de moteur. Si un ComfyUI installé autrement est déjà
là, Chrypix l'utilise et n'installe rien.

Une nouvelle version s'installe par-dessus l'ancienne (réglages gardés). Désinstaller : Paramètres de Windows >
Applications. Le désinstalleur pose deux questions (réponse « Non » par défaut) :
- supprimer aussi le **moteur IA installé par Chrypix** (ComfyUI, extensions, modèles) ? Un ComfyUI installé
  autrement, par exemple ComfyUI Desktop, n'est jamais touché ;
- supprimer aussi les **réglages** (langue, thème, dernier dossier, style de texte, dossier du moteur) et les
  journaux ?


- Chrypix : Licence Chrypix 1.1, © 2026 Georges Christophe (chrypox) : gratuit, modifiable et partageable,
  nom de l'auteur obligatoire, aucune vente (ni de Chrypix ni d'une version modifiée) ; fichier `LICENSE`.
  Éléments tiers : `docs\LICENCES_TIERS.md`.
- Testé sur une carte graphique NVIDIA de 8 Go (RTX 3060 Ti). Les durées indiquées viennent de ce PC.
- Modèles utilisés : Flux.1 Fill dev (**usage non commercial** ; version GGUF Q8 si installé par Chrypix, même
  qualité), Flux.1 Schnell (Apache-2.0), LaMa (Apache-2.0), RealESRGAN x4plus (BSD-3).
- Moteur : ComfyUI (GPL-3.0) et ses extensions Inpaint nodes, Inpaint Crop and Stitch, Ultimate SD Upscale
  (GPL-3.0), ComfyUI-GGUF (Apache-2.0).
<!-- /guide -->

## Questions fréquentes

### Mes photos sont-elles envoyées sur Internet ?
Non. L'IA tourne sur votre PC. Internet ne sert qu'une fois, pour télécharger le moteur IA et les modèles.

### Pourquoi l'IA est-elle lente ?
Les modèles d'IA sont gros (Flux Fill : 12 Go). Sur une carte de 8 Go, comptez environ une minute par proposition. Chrypix ne traite que la zone autour de la sélection, pas toute la photo, pour aller plus vite.

### J'ai une carte AMD ou Intel. Est-ce que ça marche ?
Chrypix s'ouvre et retouche (calques, texte, recadrage…), mais les actions IA demandent une carte NVIDIA.

### J'ai déjà ComfyUI. Faut-il tout retélécharger ?
Non : l'installateur le cherche, et le bouton **Parcourir…** permet d'indiquer son dossier. Chrypix l'utilise alors tel quel.

### Comment changer la langue ?
Menu **Affichage > Langue**. Chrypix redémarre pour l'appliquer.

### Puis-je l'utiliser au travail ?
Oui, gratuitement, aussi en entreprise. Il est seulement interdit de le vendre, le louer ou l'intégrer dans une offre payante. Attention : le modèle **Flux Fill** (Effacer, Remplir, Agrandir) est sous licence non commerciale ; vérifiez qu'elle convient à votre usage.

### Comment le désinstaller ?
Paramètres de Windows > Applications > Chrypix. Le désinstalleur demande s'il faut aussi supprimer le moteur IA et les réglages.

## Développer

Il faut Python 3.11 et [uv](https://github.com/astral-sh/uv).

- `uv venv` puis `uv pip install -e .` : prépare l'environnement.
- `Chrypix.bat` (ou `.venv\Scripts\python -m chrypix photo.jpg`) : lance Chrypix.
- `construire-installateur.bat` : fabrique l'installateur (il faut [Inno Setup 7](https://jrsoftware.org/isdl.php)).
- `tests\essai_*.py` : essais automatiques (ils ne touchent pas à vos réglages).
- `outils\readme.py` : recopie le guide (`docs\GUIDE.md`, `docs\GUIDE_en.md`) dans les README.

| Dossier | Rôle |
|---|---|
| `chrypix` | Le programme (PySide6) : fenêtre, canevas, calques, texte, recettes d'IA, liaison avec ComfyUI |
| `installateur` | Installateur Inno Setup |
| `docs` | Guides, feuille de route, licences des éléments tiers |
| `tests` | Essais automatiques |

## Licence

Chrypix est publié sous la **Licence Chrypix 1.1** — © 2026 Georges Christophe (chrypox). Le texte complet, seul à faire foi, est dans le fichier [`LICENSE`](LICENSE) (traduction anglaise : [`LICENSE.en.txt`](LICENSE.en.txt)). En résumé :

- **Gratuit** : utilisation libre et gratuite, aussi en entreprise et en interne ; interdit de le vendre, le louer ou l'intégrer dans une offre payante.
- **Partage** : copie et partage gratuits, avec la licence et le nom de l'auteur.
- **Modifications permises** : chacun peut modifier Chrypix, publier sa version modifiée (« fork ») ou réutiliser son code, à condition de garder le nom de l'auteur, d'indiquer que la version est modifiée, et de la publier sous la même licence : elle reste donc gratuite et non commerciale.
- **Corrections** : proposées par une « Issue » (ticket) ou une demande de fusion ; l'auteur les intègre, en créditant leur auteur.
- **Droits d'autrui** : un élément qui ne respecterait pas une licence ou vos droits ? Écrivez à admin@chrypox.be.

Le moteur IA (ComfyUI) et les modèles d'IA ne sont pas inclus dans Chrypix : ils restent sous leur propre licence, et le modèle **Flux.1 Fill [dev]** est sous licence non commerciale. Liste complète : [`docs/LICENCES_TIERS.md`](docs/LICENCES_TIERS.md).
