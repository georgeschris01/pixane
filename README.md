# Chrypix

**Français** · [English](README.en.md)

Éditeur photo gratuit pour Windows, avec retouche par intelligence artificielle **sur votre PC** : pas d'abonnement, aucune photo envoyée sur Internet. Interface en français et en anglais.

- **Effacer** un objet : on peint dessus, l'IA le fait disparaître et reconstruit le fond
- **Remplir** une zone : l'IA invente ce qui va le mieux à cet endroit
- **Agrandir** l'image au-delà de ses bords (outpaint) : l'IA prolonge le décor
- **Upscale** : augmenter la définition (×1,5 à ×4), en version rapide ou plus nette
- Plusieurs propositions à chaque fois : on choisit la meilleure, comme dans Photoshop
- Calques : visibilité, opacité, verrou, ordre, fusion ; chaque résultat de l'IA arrive dans son propre calque
- Sélection au rectangle, au lasso ou au pinceau ; sélection d'objet et sélection rapide par IA (SAM 3.1) ; baguette magique réglable en glissant ; couper, copier, coller, supprimer
- Outils de retouche : recadrer, pinceau de couleur, tampon, gomme de calque, déplacer
- Texte modifiable : police, taille, couleur, contour, ombre, fond, rotation
- JPG, PNG, TIFF, WebP, BMP, et `.chr` / `.ora` pour garder les calques ; informations EXIF et profil couleur conservés
- Taille de l'image, pivoter, retourner, redresser ; transformer un calque (taille, rotation)
- Supprimer l'arrière-plan ou sélectionner le sujet en un clic (IA)
- Réglages de l'image avec bouton Auto ; agrandir, réduire, adoucir une sélection
- Annuler / Rétablir (30 dernières étapes) avec panneau Historique ; fichiers récents
- Thème clair ou sombre, couleur d'accent de Windows
- Installateur qui vérifie le PC et télécharge lui-même le moteur IA (ComfyUI et les modèles), avec reprise après coupure

## Télécharger

**[Chrypix pour Windows](../../releases/latest)** (installateur 64 bits, `Chrypix-Setup-<version>-64bits.exe`).

**Il faut :**
- Windows 10 ou 11, 64 bits ;
- une carte graphique **NVIDIA** avec **8 Go** de mémoire (testé sur une RTX 3060 Ti) ; sans elle, Chrypix s'ouvre et retouche, mais les actions IA ne marchent pas ;
- environ **32 Go** de place pour le moteur IA (21,4 Go à télécharger), 44 Go avec l'option « Upscale net ».

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

Ce qui suit est le guide complet. C'est le même texte que le fichier `docs\GUIDE.md` livré avec le programme et affiché dans sa fenêtre **Aide > Guide de Chrypix** (avec une recherche ; **F1** l'ouvre sur les raccourcis).

<!-- guide -->
## 1. La fenêtre

| Zone | Rôle |
|---|---|
| **Barre du haut** | Ouvrir, Enregistrer, Annuler / Rétablir, réglages de l'outil choisi (taille, Nouvelle / Ajouter / Retirer…), zoom |
| **Outils (à gauche)** | Main, Déplacer, outils de sélection, outils de retouche, Recadrer, Texte. Un petit triangle sur un bouton = plusieurs outils : **clic droit** (ou clic maintenu) pour choisir |
| **Panneau « Texte » (à gauche)** | Réglages du texte, visible avec l'outil Texte (voir chapitre 7) |
| **Photo (au centre)** | La photo ; la zone sélectionnée apparaît en rouge transparent |
| **Panneau « Intelligence artificielle » (à droite)** | Effacer, Remplir, Agrandir l'image, Upscale |
| **Panneau « Calques » (à droite, en dessous)** | Les calques de l'image (voir chapitre 6) ; onglet **Historique** à côté |
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

- **Fichier > Ouvrir** (Ctrl+O) : JPG, PNG, TIFF, WebP, BMP, et les fichiers à calques **.chr**, **.ora** et
  **.psd** (Photoshop).
  La photo est redressée selon son orientation d'appareil.
- **Enregistrer** (Ctrl+S), **Enregistrer sous** (Ctrl+Maj+S) :
  - **.chr** (projet Chrypix) : le format de Chrypix. Garde **tout** : calques (noms, ordre, visibilité, opacité,
    verrou) et **textes modifiables**. Proposé d'office quand l'image a plusieurs calques ou un texte.
  - **.ora** (OpenRaster) : pour **partager avec Krita ou GIMP** (format ouvert). Garde les calques, mais les
    textes y deviennent des images.
  - Bon à savoir : un .chr est construit comme un .ora ; renommé en .ora, il s'ouvre aussi dans Krita ou GIMP.
  - **.psd** (Photoshop) : pour **travailler avec Photoshop**. Garde les calques (noms, ordre, visibilité,
    opacité, verrou) ; les textes y deviennent des images. Une photo ouverte depuis un PSD est proposée en PSD.
  - **PSD ouverts dans Chrypix** : RVB ou niveaux de gris, 8 ou 16 bits, avec les calques, les groupes (un groupe
    masqué masque ses calques) et les masques de calque. Chrypix ne reproduit pas les modes de fusion autres que
    *Normal*, les styles (ombre, contour…), les calques de réglage ni les masques d'écrêtage : un message le
    signale à l'ouverture, car l'aspect peut alors différer de Photoshop. Un PSD en CMJN s'ouvre aplati (un seul
    calque). Les grands documents .psb ne sont pas pris en charge.
  - **JPG** (qualité 95), **PNG**, **TIFF**, **WebP** : l'image **à plat** (ce que vous voyez, calques fusionnés).
    Un message le rappelle si l'image a plusieurs calques.
  Les informations de l'appareil (EXIF) et le profil de couleur sont conservés.
- **Annuler** (Ctrl+Z) / **Rétablir** (Ctrl+Y ou Ctrl+Maj+Z) : chaque retouche et chaque sélection peut être annulée
  (30 étapes).
- **Panneau Historique** (onglet à côté de « Calques ») : la liste des étapes. Un clic sur une étape revient à ce
  moment-là ; un clic sur une étape plus bas refait les suivantes. Une nouvelle retouche efface les étapes « en avance ».
- **Fichier > Fichiers récents** : les 10 dernières images ouvertes ou enregistrées (*Effacer la liste* pour la vider).
- **Fichier > Nouvelle image…** (Ctrl+N) : image vide, taille au choix, fond blanc, noir ou transparent.
- **Fichier > Nouvelle image depuis le presse-papiers** (Ctrl+Alt+V) : ouvre l'image copiée (capture d'écran, autre
  logiciel…). **Ctrl+V** sans photo ouverte fait la même chose.

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

Les outils de sélection sont rangés sous **deux boutons** de la barre de gauche (petit triangle) : les outils
« à la main » et les outils « automatiques ». **Clic droit** sur le bouton, ou clic maintenu, pour choisir ; ou
directement leur touche.

| Outil | Touche | Usage |
|---|---|---|
| **Rectangle** | M | Sélection rectangulaire |
| **Lasso** | L | Tracer un contour à main levée, bouton appuyé ; la forme est fermée automatiquement |
| **Pinceau de sélection** | B | Peindre la zone. Idéal pour un objet, un texte, un fil… |
| **Gomme de sélection** | E | Retirer de la sélection en peignant |
| **Sélection d'objet** (IA) | O | Tirer un cadre autour d'un objet, ou cliquer dessus : l'IA le détoure |
| **Sélection rapide** (IA) | Q | Peindre grossièrement sur l'objet : l'IA trouve ses contours |
| **Baguette magique** | W | Un clic sur une couleur : toute la zone de couleur proche (sans IA) |

- **Rectangle et lasso**, comme dans Photoshop : une nouvelle sélection **remplace** l'ancienne. Maintenir **Maj** en
  commençant le tracé **ajoute** à la sélection, **Alt** **retire**. Un simple clic sans tracer **désélectionne**.
  Les pastilles **Nouvelle / Ajouter / Retirer** de la barre du haut choisissent le mode sans touche.
- **Pinceau de sélection** : il ajoute toujours à la sélection ; pastille **Retirer** ou **Alt** maintenu : il retire
  (comme la gomme de sélection).
- **Taille du pinceau** : curseur « Taille » de la barre du haut, ou touches `[` et `]`.
- Menu **Sélection** : *Tout sélectionner* (Ctrl+A), *Désélectionner* (Ctrl+D), *Inverser* (Ctrl+Maj+I).
- **Sélection > Modifier la sélection** : *Agrandir…* ou *Réduire…* d'un nombre de pixels, *Adoucir les bords…*
  (bord progressif, utile pour les réglages de l'image).
- **Sélection > Sélectionner le sujet (IA)** (Ctrl+Alt+S) : l'IA trouve le sujet principal (personne, animal,
  objet) et le sélectionne. Voir chapitre 5, « Sujet et arrière-plan ».

### Sélection d'objet et sélection rapide (IA)
Elles utilisent le modèle **SAM 3.1** de Meta (1,6 Go, installé avec le moteur IA). L'IA comprend l'**objet entier**
(une personne, une voiture, un meuble…), même quand ses couleurs varient, et suit ses vrais contours. Environ une
seconde par demande (quelques secondes la première fois).
- **Sélection d'objet (O)** : tirer un **cadre** autour de l'objet, ou **cliquer** dessus. Comme le rectangle : la
  nouvelle sélection remplace l'ancienne ; **Maj** ajoute, **Alt** retire (ou les pastilles Nouvelle / Ajouter /
  Retirer).
- **Sélection rapide (Q)** : **peindre** grossièrement sur l'objet (dessus, ou en
  suivant son contour). Comme dans Photoshop, chaque trait trouve **son** objet, qui s'**ajoute** à la sélection : un
  trait sur un titre puis un trait autour d'une personne donnent le titre + la personne entière. Des points verts
  montrent ce que l'IA doit garder. **Alt + peindre** sur une partie à enlever (points rouges) : l'IA corrige les
  objets déjà trouvés. Une sélection vidée (Ctrl+D) ou changée par un autre outil fait repartir de zéro ; **Échap**
  aussi.
- Ctrl+Z annule chaque étape. Le résultat se règle ensuite avec *Modifier la sélection* (agrandir, adoucir…).

### Baguette magique (W)
Un clic sur une couleur sélectionne la zone de couleur proche. Sans IA, instantané.
- **Régler en glissant** : après le clic, **garder le bouton appuyé et glisser à droite** (plus large) **ou à gauche**
  (plus étroit) : la sélection suit en direct. La tolérance trouvée reste pour le clic suivant.
- **Tolérance** (0 à 255, 32 par défaut) : écart de couleur accepté. Les couleurs sont comparées comme l'œil les
  voit, et la couleur de départ est prise sur 3 × 3 pixels : le bruit d'une photo gêne moins.
- **Contiguë** (coché) : seulement la zone touchée ; décoché : toutes les couleurs proches de l'image.
- **Bords doux** (coché) : bord progressif, sans escalier.
- **Boucher les trous** : ajoute ce qui est entièrement entouré (oiseaux dans un ciel, reflets sur un objet…).
- **Image visible** ou **Calque choisi** : sur quoi les couleurs sont comparées.
- Maj ajoute, Alt retire, comme le rectangle.

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
- Marche aussi sur une sélection fine (lettres prises à la baguette magique) : tout pixel touché par la sélection est
  effacé, même sur un bord adouci.
- Durée indicative : environ 2 minutes (carte graphique 8 Go).

### Remplir (Maj+R)
Redessine la zone peinte en rouge.
- **Sans texte** (recommandé) : l'IA invente ce qui va bien avec le reste de la photo. Elle part du fond nettoyé
  par LaMa : même près d'un titre, elle ne réinvente pas de lettres.
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

### Sujet et arrière-plan
Modèle **BiRefNet** (MIT, 444 Mo, installé avec le moteur IA ; s'il manque, menu **IA > Installer le moteur IA…**
l'ajoute). Quelques secondes.
- **Supprimer l'arrière-plan** (Maj+B, panneau IA ou menu IA) : le fond du **calque choisi** devient transparent,
  le sujet reste. Enregistrez en PNG, PSD ou .chr pour garder la transparence. Ctrl+Z annule.
- **Sélectionner le sujet** (Ctrl+Alt+S, menu Sélection) : sélectionne le sujet sans rien effacer, par exemple
  pour le régler (Ctrl+U), ou *Inverser* (Ctrl+Maj+I) pour travailler le fond.

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

## 9. Réglages de l'image

Menu **Image > Réglages de l'image…** (Ctrl+U) : corriger la lumière, les couleurs et la netteté.

| Réglage | De … à | Effet |
|---|---|---|
| **Luminosité** | -100 à +100 | Éclaircit ou assombrit, en gardant le noir et le blanc |
| **Contraste** | -100 à +100 | Écarte ou rapproche les clairs et les sombres |
| **Saturation** | -100 à +100 | Couleurs plus vives ou plus ternes ; -100 = noir et blanc |
| **Teinte** | -180° à +180° | Fait tourner toutes les couleurs (le rouge devient orange, vert…) |
| **Température** | -100 à +100 | Plus chaud (orangé) ou plus froid (bleuté) |
| **Netteté** | 0 à 200 % | Renforce les détails |

- Le réglage s'applique au **calque choisi** dans le panneau Calques ; s'il y a une **sélection**, seulement à
  l'intérieur (avec ses bords doux). La fenêtre le rappelle en haut.
- **Aperçu sur la photo** : on voit le résultat en direct en bougeant les curseurs (sur une grande photo, il
  arrive après une fraction de seconde). Décochez pour comparer avec l'original.
- **Réinitialiser** remet tout à zéro, **Appliquer** garde le résultat, **Annuler** (ou Échap) laisse la photo
  comme avant. Après Appliquer, Ctrl+Z annule le réglage.
- **Auto** : propose d'office une luminosité, un contraste et une température (d'après la photo, ou la sélection) ;
  les curseurs restent ajustables ensuite.
- Un calque **verrouillé** est protégé ; un **texte** réglé devient une image.

---

## 10. Menu Image : taille, rotation, transformer

- **Taille de l'image…** (Ctrl+Alt+I) : en pixels ou en %, proportions gardées (case à décocher), boutons rapides
  (par exemple 1920 px pour l'écran et Internet). Sans IA : pour agrandir avec plus de détails, préférez Upscale.
- **Pivoter** de 90° à droite, à gauche ou de 180°, **Retourner** horizontalement ou verticalement : toute l'image,
  tous les calques, sans perte. Les textes retournés deviennent des images ; pivotés, ils restent modifiables.
- **Redresser…** : tourner d'un petit angle (-45° à +45°) avec une grille pour aligner l'horizon ou un mur.
  *Recadrer pour enlever les coins vides* (coché par défaut) ; décoché, l'image s'agrandit et les coins sont
  transparents.
- **Édition > Transformer le calque** (Ctrl+T) : un cadre entoure le **calque choisi**.
  - **coin** : taille, proportions gardées (Maj : libre) ; **bord** : largeur ou hauteur seule ;
  - **dedans** : déplacer ; **dehors** (le curseur devient une flèche ronde) : tourner (Maj : par 15°) ;
  - la barre du haut affiche largeur, hauteur et angle ; **Entrée**, double-clic ou **Valider** pour garder,
    **Échap** ou **Annuler** pour revenir. Changer d'outil valide aussi.
  Un texte transformé devient une image (pour garder un texte modifiable, utilisez l'outil Texte).

Tout s'annule par Ctrl+Z.

---

## 11. Raccourcis

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
| Ctrl+U | Réglages de l'image |
| Ctrl+N, Ctrl+Alt+V | Nouvelle image, Nouvelle image depuis le presse-papiers |
| Ctrl+Alt+I | Taille de l'image |
| Ctrl+T | Transformer le calque (Entrée valider, Échap annuler) |
| Ctrl+Alt+S, Maj+B | Sélectionner le sujet, Supprimer l'arrière-plan (IA) |
| O, Q, W | Sélection d'objet (IA), Sélection rapide (IA), Baguette magique |
| Glisser après un clic de baguette | Régler la tolérance en direct |
| Clic droit sur un outil à petit triangle | Choisir un autre outil du groupe |
| Ctrl+0, Ctrl+1 | Ajuster, 100 % |
| Entrée / Échap | (Agrandir) Lancer / Annuler ; (Recadrer) Valider / Annuler |
| Maj (en tournant un texte) | Rotation par pas de 15° |
| F1 | Guide, ouvert sur les raccourcis (menu Aide > Guide de Chrypix : tout le guide, avec une recherche) |

---

## 12. Matériel et licences

**Installation** : lancer `Chrypix-Setup-<version>-64bits.exe`.
1. Langue de l'installation (ce sera aussi la langue de Chrypix, modifiable ensuite dans Affichage > Langue).
2. Pour moi seulement (par défaut, sans droits administrateur) ou pour tous les utilisateurs.
3. Dossier d'installation.
4. **Vérification du PC** : carte graphique NVIDIA et sa mémoire (8 Go conseillés), place libre, moteur IA
   (ComfyUI) trouvé ou non. Si ComfyUI est installé ailleurs, bouton **Parcourir…** pour indiquer son dossier.
   Sans ComfyUI, Chrypix ouvre, retouche (calques, texte) et enregistre, mais les actions IA ne marchent pas.
5. **Moteur IA** (seulement si ComfyUI n'est pas trouvé) : liste de ce qui sera téléchargé, avec taille, site et
   licence (21,4 Go à télécharger, environ 31 Go sur le disque) ; dossier du moteur (par défaut
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

**Mises à jour du moteur IA** : les versions de ComfyUI, des extensions et des modèles sont choisies et essayées
avec chaque version de Chrypix ; rien ne change tout seul. Quand une nouvelle version de Chrypix demande d'autres
versions, Chrypix le propose une fois au démarrage (liste et taille à télécharger), et la fenêtre **Installer le
moteur IA** montre l'état de chaque élément (*à jour*, *nouvelle version*) avec le bouton **Mettre à jour**.
Seul ce qui a changé est téléchargé. ComfyUI est remplacé en gardant ses modèles, ses extensions et ses réglages ;
un ancien modèle remplacé est effacé. Le moteur est arrêté pendant la mise à jour et relancé après. Un ComfyUI
installé autrement (par exemple ComfyUI Desktop) se met à jour de son côté : Chrypix n'y touche pas.

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
  qualité), Flux.1 Schnell (Apache-2.0), LaMa (Apache-2.0), RealESRGAN x4plus (BSD-3), BiRefNet (MIT), SAM 3.1 (SAM License de Meta).
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
