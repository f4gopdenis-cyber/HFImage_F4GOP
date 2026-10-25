# Historique des versions — HFImage F4GOP

## Version 1.57 — style Moderne : cartes, jauges, listes colorées (étape 3)

- Style Moderne : la colonne de gauche est présentée en **cartes** (bordure fine, marges) ; jauges **RX / SNR arrondies** dans la couleur d'accent ; voyants sans contour.
- Liste des stations : **●** devant les stations en ligne, **○** devant celles entendues seulement par radio.
- **Rx Ok** : chaque report est **coloré** selon sa valeur, avec les mêmes couleurs que la légende de la carte (vert foncé +5 dB et plus, vert clair, orange, rouge).
- Style Classique : inchangé (vérifié au pixel près).

## Version 1.56 — style Moderne : tuiles avec icônes (étape 2)

- Style Moderne : les 16 boutons de gauche deviennent des **tuiles avec une icône** au-dessus du texte (émission, relecture, FIX, BSR, accord, ID, texte, WAVE, écoute, texte inclus, log, QSL, image, hybride, réglages, dossier). La tuile **ÉMISSION** est dans la couleur d'accent ; une tuile active (Écoute, Hybride…) prend la couleur d'accent, l'attente est en orange et l'émission en rouge, icône comprise.
- Style Classique : boutons inchangés.

## Version 1.55 — style Moderne : ambiance « Vert EasyPal »

- Style Moderne : nouvelle ambiance **« Vert EasyPal »**, le vert vif d'EasyPal (barre du haut, bandeaux, barre d'état) et le vert clair, en version plate et moderne. C'est l'ambiance proposée par défaut quand on choisit le style Moderne ; Sombre, Clair et Vert radio restent au choix.

## Version 1.54 — style Moderne (étape 1 de la refonte)

- Réglages → Apparence → **Style** : **Classique (EasyPal)** (le look d'origine, par défaut) ou **Moderne**, avec trois **ambiances** : **Sombre**, **Clair**, **Vert radio**. Passage de l'un à l'autre à tout moment, sans redémarrer ; le style Classique revient exactement comme avant.
- Style Moderne : tout plat (plus de relief 3D sur les boutons, cadres, listes, journal), une couleur d'accent, police moderne (Segoe UI sous Windows), onglets RX / TX / Stations / Galerie en pastilles, listes et cases sobres, bouton **▶ Émettre** mis en valeur, boutons de la grille colorés selon leur état (actif, attente, émission).
- Nouvelle **barre du haut** (style Moderne) : indicatif, prénom et locator, **fréquence en grand** (clic : menu des fréquences), **état** (Réception, Attente, Émission), **stations en ligne** (clic : carte) et heure UTC.

## Version 1.53 — clic sur l'image TX : ouvrir une image comme avant

- Un clic sur l'image TX **à côté des textes et logos** ouvre de nouveau directement le choix d'une image, comme avant la 1.52. Un clic **sur** un texte ou un logo le sélectionne ; si un élément est sélectionné, le premier clic à côté enlève seulement la sélection.

## Version 1.52 — textes et logos directement sur l'image TX (demande de RK1AT)

- Édition directe sur l'image de l'onglet TX, comme dans le « GMSK controller » de JQ1HDR : **clic droit** → « Ajouter un texte… » (avec les phrases toutes prêtes), « Ajouter un logo / une image du PC… » (un PNG transparent devient un logo), « Ajouter l'image d'un correspondant ». **Clic** pour sélectionner (cadre jaune), **glisser** pour déplacer, **molette** pour agrandir / réduire, **Maj + molette** pour tourner un logo, **double-clic** pour modifier un texte, **Suppr** pour enlever. Le clic droit sur l'élément choisi donne aussi style, couleurs, forme, légende, « Remettre droit ». L'aperçu suit la souris ; l'image à émettre est recalculée au relâchement.
- Une fois une image ouverte, un clic sur l'image TX sélectionne au lieu d'ouvrir une autre image (bouton « Ouvrir une image… », glisser-déposer ou clic droit → « Ouvrir une autre image… »). Les fenêtres « Bulles… » et « Image du correspondant… » restent pour les réglages fins.
- La taille d'un texte peut maintenant se régler finement (molette), au-delà de Petite / Moyenne / Grande.

## Version 1.51 — grande photo en AVIF (mode hybride) préparée 5 fois plus vite

- Mode hybride avec le format **avif** (ou webp) et une grande photo : la meilleure qualité est cherchée sur un **échantillon** de la photo, puis la photo entière n'est compressée qu'une fois (au lieu d'une quinzaine de fois, quelques secondes chacune). Photo de téléphone de 12 Mpx en « originale / 3000 ko » : **environ 50 s → 10 s** sur la machine d'essai.
- Sous l'image, un conseil s'affiche dans ce cas : « AVIF sur une grande photo : choisissez jpg ou original pour une image prête tout de suite. »

## Version 1.50 — forme des images incrustées

- Fenêtre « Image du correspondant » : liste **« Forme »** pour chaque image incrustée : **Rectangle** (comme avant, par défaut), **Coins arrondis**, **Rond** (centre carré de l'image, comme un médaillon) ou **Ovale**. Le cadre blanc et l'ombre suivent la forme ; pour le rond et l'ovale, la légende est dans une pastille sous l'image. La forme découpe aussi un logo, et marche avec la rotation et la perspective. Retenue pour chaque emplacement.

## Version 1.49 — logo PNG transparent, hauteur des bandeaux de la carte QSL (demandes de RK1AT)

- Fenêtre « Image du correspondant » : case **« Logo (sans cadre, transparence gardée) »** pour chaque image incrustée : l'image est posée directement sur la photo, sans cadre, ombre ni légende, et le **fond transparent d'un PNG est gardé**. Cochée d'office quand on choisit un PNG à fond transparent avec « Image du PC… ». Réglette **Opacité** (20 à 100 %) pour un logo discret ; position, taille, rotation et perspective comme pour les autres images.
- Carte QSL : réglettes **« Hauteur du bandeau du haut »** et **« Hauteur du bandeau du bas »** (50 à 150 %) ; le texte suit la hauteur choisie (la ligne date / fréquence / report reste dans la carte). Réglage retenu avec le style.

## Version 1.48 — incruster une image du PC, légende libre

- Fenêtre « Image du correspondant » : bouton **« Image du PC… »** pour incruster n'importe quelle image de l'ordinateur (photo, logo, carte QSL… en JPEG, PNG, GIF, BMP, WebP, AVIF) dans l'image à émettre, avec les mêmes réglages que les images reçues (position, taille, souris, rotation, perspective). Une photo de téléphone est remise droite. Les 10 dernières images du PC restent proposées dans la liste (📁).
- Champ **« Légende »** : le texte de votre choix sous l'image incrustée. Vide : « de F4EMK — +12 dB » pour une image reçue, pas de légende pour une image du PC.
- La fenêtre s'ouvre maintenant même sans image reçue (pour incruster une image du PC).

## Version 1.47 — logo d'hommage à VK4AES

- Un clic sur « **En hommage à VK4AES** » (barre du bas, à côté du drapeau australien) ouvre maintenant une fenêtre avec le **logo d'hommage à Erik Sundstrup VK4AES** dessiné par Denis F4GOP, et la dédicace.

## Version 1.46 — images des correspondants tournées / en perspective (demande de M7WUV)

- Fenêtre « Image du correspondant » : pour chaque image incrustée, réglettes **Rotation** (−45° à +45°, ou **Maj + molette** sur l'image) et **Perspective** (l'image « penche » vers la gauche ou la droite, effet 3D). Le cadre et la légende tournent avec l'image ; les coins qui dépassent laissent voir la photo de fond, avec l'ombre. Bouton **« Remettre droit »**. Réglages retenus pour chaque emplacement.

## Version 1.45 — phrases toutes prêtes pour les bulles (demande de M7WUV)

- Fenêtre des bulles : bouton **« Phrases ▾ »** avec des phrases toutes prêtes (« Bonjour de {MOI} », « Merci pour l'image ! 73 de {MOI} », « Image bien reçue 5/5 »…), dans la langue du programme, à mettre dans la bulle d'un clic. **{MOI}**, **{PRENOM}** et **{LOC}** (ou {CALL}, {NAME}, {LOC}) sont remplacés par l'indicatif, le prénom et le locator.
- « **Enregistrer cette phrase** » ajoute le texte de la bulle à la liste ; « **Modifier la liste…** » pour retoucher, supprimer ou réordonner les phrases (une par ligne), avec « Liste d'origine ».
- Une nouvelle bulle reprend le **style, la taille et les couleurs de la dernière utilisée**, même sur une autre image et après avoir relancé le programme.

## Version 1.44 — image hybride préparée plus vite

- Ouvrir une grande photo pour l'émettre en mode hybride (HFImage ou EasyPal) est **2 à 3 fois plus rapide** quand elle doit être recompressée en JPEG (bandeau « Infos de ma station », bulles, rotation, taille maximale…) : la meilleure qualité est d'abord cherchée sur un échantillon de la photo, puis confirmée sur la photo entière (2 compressions au lieu d'une dizaine). L'image obtenue est exactement la même.

## Version 1.43 — listes Stations et Rx Ok : début des indicatifs toujours visible

- Correction (1.40) : la liste des stations pouvait rester décalée d'un caractère vers la droite (« 4VD274 » au lieu de « 14VD274 ») après un geste horizontal de la molette ou du pavé tactile. Le défilement horizontal des listes Stations et Rx Ok est maintenant bloqué : elles s'affichent toujours depuis le début de la ligne.

## Version 1.42 — mises à jour : secours quand GitHub limite les vérifications

- Quand GitHub refuse la vérification des mises à jour (« HTTP Error 403: rate limit exceeded » : 60 questions par heure au plus pour une même connexion Internet), HFImage lit la page « dernière version » du site GitHub, qui n'a pas cette limite, et trouve quand même la nouvelle version et son fichier (toujours sur la page officielle du projet ; taille vérifiée).
- Si tout échoue, un message clair et traduit : « GitHub limite le nombre de vérifications : réessayez dans une heure. »

## Version 1.41 — bulles sur un GIF animé reçu

- Répondre avec un **GIF animé** reçu (par exemple une image avec des émoticônes animées, « Renvoyer cette image ») en y ajoutant une **bulle** : la bulle est maintenant **dessinée sur chaque image du GIF** et l'animation d'origine est gardée. Avant, le GIF repartait tel quel, sans la bulle.
- Si la nouvelle bulle a elle aussi des émoticônes animées, elles bougent en même temps. Le GIF est réduit si besoin pour respecter la taille maximale réglée.

## Version 1.40 — listes Stations et Rx Ok stables (demande de SWLPete)

- Les listes **Stations** et **Rx Ok** ne « sautent » plus à chaque nouvelle information (station qui se connecte, change de fréquence, passe en émission…) : elles restent à l'endroit où on les a fait défiler, la station sélectionnée le reste, et rien n'est réécrit quand rien n'a changé (plus de clignotement). Seules les lignes qui changent sont mises à jour ; une station qui arrive s'insère à sa place alphabétique sans décaler la partie de la liste qu'on regarde.

## Version 1.39 — carte des stations : « Copier la carte », étiquettes plus lisibles

- Carte des stations : nouveau bouton **« Copier la carte »**. La carte affichée (avec la mention du fond de carte) part dans le presse-papiers, à coller avec **Ctrl+V** dans Teams, un forum, Facebook, un e-mail…
- Carte plus lisible quand les stations sont serrées (Angleterre, par exemple) : les **noms de villes et de pays** qui tomberaient sous un indicatif ou un point de station **ne sont plus écrits**, et les étiquettes des stations gardent un peu d'espace entre elles.

## Version 1.38 — copier une image dans le presse-papiers (VK6ATI)

- Galerie, clic droit sur une image : **« Copier l'image »**. Il suffit ensuite de la coller (**Ctrl+V**) dans MS Teams, un e-mail, WhatsApp, Word, Paint… par exemple pour une station qui ne l'a pas décodée. L'image est copiée en pleine qualité (PNG).
- Onglet RX, clic droit sur la grande image : « Copier l'image » et « Revenir à l'image entière » (après un zoom).
- Un GIF animé est copié comme image fixe (le presse-papiers ne garde pas l'animation). Sous Linux, la copie utilise xclip (`sudo apt install xclip`).

## Version 1.37 — commandes CAT personnalisées : changement de fréquence Icom (VK6NJP)

- Commandes CAT personnalisées avec un poste **Icom** (commandes CI-V « FEFE94E0… ») : HFImage trouve l'adresse du poste dans les commandes et **change la fréquence** quand on choisit une fréquence dans le menu (commande Icom standard) ; le mode du poste (LSB / USB, DATA) n'est pas touché. La fréquence choisie s'affiche dans le panneau.
- Avec d'autres postes en commandes personnalisées : plus de fenêtre d'erreur, un message dans le journal invite à changer la fréquence sur le poste.
- Les messages « ce pilote ne change pas la fréquence », etc. sont traduits.

## Version 1.36 — commandes CAT personnalisées : départ / sortie à chaque émission (VK6NJP)

- Commandes CAT personnalisées : comme dans EasyPal, les **chaînes de départ** partent maintenant **avant chaque émission** (avant PTT marche) et les **chaînes de sortie après** (après PTT arrêt), quelle que soit la méthode PTT. Pratique pour passer le poste en DATA ou changer le gain micro le temps de l'émission, puis tout remettre comme avant.
- Nouveau choix dans la fenêtre Radio : « Départ / Sortie : à chaque émission (comme EasyPal) » (par défaut) ou « au lancement et à la fermeture du programme » (l'ancien fonctionnement).

## Version 1.35 — commandes CAT personnalisées : plusieurs à la suite (VK6NJP)

- Commandes CAT personnalisées : une case peut contenir **plusieurs commandes à la suite**, écrites comme dans EasyPal (`\$FEFE94E0…FD\$FEFE94E0…FD\`). Elles sont envoyées l'une après l'autre, avec le délai réglé entre chacune. Avant, une case contenant plusieurs commandes était envoyée comme du texte et le poste ne la comprenait pas.

## Version 1.34 — texte libre sur l'image, dossier « envoyees » allégé (demandes de RK1AT)

- Bulles de texte : nouveau style **« Texte seul (sans bulle) »** : le texte est écrit directement sur l'image, bordé d'un contour (couleur « Fond ») pour rester lisible sur n'importe quelle photo ; blanc bordé de noir par défaut. Il se déplace à la souris, sur une ou plusieurs lignes, avec émoticônes (même animées).
- Dossier **« envoyees »** : une image renvoyée à l'identique n'est plus recopiée (elle remonte simplement en tête de la galerie). Nouveau réglage (Réglages → Dossier des images reçues) **« Images envoyées gardées »** : toutes (comme avant), les 20 dernières, ou **la dernière seulement** ; les plus anciennes sont effacées de ce dossier seulement (les images reçues ne sont jamais touchées).

## Version 1.33 — hommage à VK4AES

- Dans la barre du bas de la fenêtre principale, à gauche de l'horloge : un petit **drapeau australien** et « **En hommage à VK4AES** », pour Erik Sundstrup VK4AES (SK), créateur d'EasyPal, à qui HFImage est dédié. Un clic affiche la dédicace. Traduit dans les 5 langues ; le drapeau est dessiné par le programme.

## Version 1.32 — émoticônes animées dans les bulles

- Bulles de texte : nouvelle case **« Émoticônes animées (mode hybride : GIF animé) »**. Les émoticônes de la bulle bougent : le cœur bat, la main salue, le pouce se balance, l'étoile et le soleil tournent, le sourire fait un clin d'œil, la flamme danse, l'éclair clignote… L'aperçu de la fenêtre des bulles les montre en mouvement.
- En **mode hybride**, l'image part alors en **GIF animé** (12 images, environ 1 s, en boucle), que les stations HFImage voient bouger. Une photo y perd un peu en finesse (256 couleurs) ; la largeur est limitée à 800 px par défaut (réglage hybride « largeur max » sinon) et le GIF respecte la taille max des GIF animés. En **radio seule**, les émoticônes restent fixes.
- Les animations sont calculées par HFImage à partir des émoticônes Twemoji déjà présentes (même licence CC-BY 4.0) : rien de plus à télécharger.

## Version 1.31 — carte des stations plus lisible

- **Couleur selon le report** : le trait et le cadre de chaque station qui a reçu votre image ont la couleur de son report (vert foncé : +5 dB et plus, vert clair : 0 à +4, orange : -10 à -1, rouge : moins de -10 dB), avec une légende ; le report est écrit à côté de l'indicatif (« F6GIA +8 »).
- **Étiquettes rangées** : chacune près de son point, du côté où il y a de la place, avec un petit trait de rappel si elle doit s'écarter ; elles ne se chevauchent plus. Traits plus fins.
- **Souris sur une station** : une bulle donne prénom, locator, distance, direction, report et heure.
- **Bouton « Tout voir »** : cadre la carte sur toutes les stations. La barre du haut n'est plus coupée ; en bas : nombre de stations, la plus lointaine et l'aide souris.

## Version 1.30 — « Répondre » met toujours l'indicatif du correspondant

- Fenêtre des messages reçus, **Répondre…** : le message commence toujours par « F4EEH de F4GOP : », curseur juste après. Avant, rien n'était écrit si la case contenait encore le message envoyé précédemment. Si un message est en cours d'écriture (pas encore envoyé), le programme demande avant de le remplacer.
- Toujours le bon indicatif : le vôtre sans le prénom, celui du correspondant complet (même coupé par la radio ou suivi d'un prénom) ; expéditeur inconnu : « de F4GOP : ».

## Version 1.29 — SunSDR / ExpertSDR par TCI (demande de F4FRC, radio-club F8KLY)

- Nouveau choix **« SunSDR / ExpertSDR (TCI) »** dans Réglages → Poste radio… : HFImage parle directement à ExpertSDR par le **TCI** (réseau, port 40001), sans RadioSync ni port COM virtuel. Fréquence et mode lus en direct (ExpertSDR prévient de chaque changement), PTT par CAT, changement de fréquence (bouton Fréquence ▾), passage automatique en DIGL / DIGU avant d'émettre.
- Le son passe, comme avant, par les câbles audio virtuels (VAC) d'ExpertSDR. Dans ExpertSDR : Options → TCI, activer le serveur (port 40001). Marche aussi avec les autres logiciels SDR qui parlent TCI.

## Version 1.28 — Sites des stations (remplace Digi-Sites)

- Nouvelle fenêtre **Sites des stations** (Images → Sites des stations…, aussi dans Action et par clic droit sur la liste des stations) : comme Digi-Sites, qui n'est plus entretenu depuis le décès de W3WV, une vignette par station avec la **dernière image qu'elle a reçue** (son image1), l'heure de cette image et la distance. Les plus récentes en premier ; un clic l'agrandit ; clic droit : ouvrir la page de la station.
- Les stations HFImage qui mettent leurs images en ligne (Site web / Digi-Sites) annoncent maintenant l'adresse de leur image1 dans leur présence : elles apparaissent toutes seules. **« Ajouter une station… »** pour le site d'une station EasyPal (adresse de son image1, celle donnée à Digi-Sites).
- Les images ne sont relues que si elles ont changé (toutes les 2 minutes, seulement quand la fenêtre est ouverte). Sécurité : adresses http / https vers des serveurs publics seulement, 5 Mo au plus par image.

## Version 1.27 — vignette dans le panneau, adresse Digi-Sites

- **Panneau d'état** : la place libre à droite du tableau TX / RX montre maintenant la **vignette de la dernière image reçue**, avec l'indicatif, le prénom et la distance de la station (« F4EEH Jean — 312 km »). Elle se met à jour à chaque réception (aperçu compris) ; un clic l'affiche dans l'onglet RX. Au démarrage, elle montre la dernière image de la galerie. Elle prend la place disponible sans élargir le panneau.
- **Site web / Digi-Sites** : la fenêtre donne maintenant la bonne adresse pour Digi-Sites, celle du fichier **image1** (`https://www.qsl.net/f4gop/image1`, vérifié par F4GOP), et en dessous l'adresse de la page de vos images.

## Version 1.26 — Digi-Sites : images nommées comme EasyPal

- Site web / Digi-Sites : les images reçues sont mises en ligne sous le nom **« image1 », « image2 »… sans extension**, exactement comme EasyPal : c'est ce fichier que lit Digi-Sites. HFImage les nommait « image1.jpg » : Digi-Sites ne les trouvait pas et continuait d'afficher la dernière image déposée par EasyPal. La page hfimage.html les affiche toujours.
- Pour Digi-Sites, mettez le **dossier vide** (racine du site, comme EasyPal) dans Site web / Digi-Sites, puis « Envoyer la page maintenant » : les dernières images partent tout de suite. C'est maintenant le réglage par défaut.

## Version 1.25 — fichiers hybrides déposés tels quels (demande de RK1AT)

- En mode hybride, un **fichier** (vidéo MP4, son MP3, page HTML, PDF, AVI…) est maintenant déposé **tel quel, sous son nom d'origine** : `RK1AT_20261021_133402_TEST.mp4`. Le lien public s'ouvre directement dans un navigateur (la vidéo se lit, la page s'affiche). Avant, il était emballé par HFImage (compressé, nom en « .file ») et seul HFImage savait l'ouvrir.
- À la réception, le fichier est enregistré sous son nom d'origine dans le dossier « fichiers ». Les fichiers emballés des anciennes versions sont toujours compris. Une station restée sur une ancienne version reçoit le nouveau fichier complet, mais sous le nom « fichier.bin » : il suffit qu'elle se mette à jour.
- Hybride EasyPal : le fichier garde aussi son extension d'origine. Le ménage du serveur reconnaît ces nouveaux noms. Par radio seule, rien ne change (le fichier reste compressé pour gagner du temps d'émission).

## Version 1.24 — commandes CAT personnalisées, dépôt hybride d'avance (demandes de VK6NJP)

- **Commandes CAT personnalisées (comme EasyPal)** : nouveau choix dans Réglages → Poste radio…. On écrit soi-même les commandes envoyées au poste, en hexadécimal (Icom CI-V : `FEFE5EE01C0001FD`) ou en texte (Kenwood : `TX1;`) : Départ 1 et 2 (à l'ouverture du port), PTT marche / PTT arrêt (méthode PTT « CAT »), Sortie 1 et 2 (à la fermeture du programme), délai entre deux commandes. Les réglages d'EasyPal (`\$…\`) se collent tels quels. La fréquence du poste n'est pas lue dans ce mode.
- **Déposer l'image hybride d'avance** : nouveau bouton **⇪ Déposer** (onglet TX, mode hybride), comme l'ancien EasyPal. L'image part sur le serveur tout de suite ; à votre tour, **Émettre** envoie directement l'annonce radio. Pratique pour les groupes qui émettent chacun leur tour. Si l'image ou le serveur changent entre-temps, l'image est redéposée au moment d'émettre. Marche aussi en hybride EasyPal.

## Version 1.23 — HFImage pour Linux

- **Nouvelle version Linux** 64 bits : **HFImage_F4GOP_Linux.tar.gz** sur la page des versions (Ubuntu 22.04 et plus récents, Debian 12, Linux Mint 21…). Un seul fichier à lancer, même programme et mêmes modes que sous Windows (DATAC, EasyPal, hybride, présence, Rx Ok, galerie, site web…), compatible avec les stations Windows. Fabriquée et testée automatiquement par GitHub à chaque version, avec codec2 et HamDRM compilés depuis leurs sources.
- Linux : Hamlib vient du système (`sudo apt install libhamlib-utils`, le programme l'indique s'il manque) ; ports série /dev/ttyUSB… (message clair si le compte n'est pas dans le groupe « dialout ») ; polices libres équivalentes à celles de Windows ; entrée dans le menu des applications ; mises à jour automatiques comme sous Windows. OmniRig n'existe que sous Windows.
- Rappel 1.22 : le fichier journal complet s'ouvre par Réglages → Ouvrir le journal.

## Version 1.22 — journal à l'écran vidé automatiquement

- Le journal affiché dans la fenêtre ne garde plus que les **300 dernières lignes** : il se vide tout seul, le programme restant ouvert des jours. Tout reste enregistré dans le fichier journal (Fichiers → journal).

## Version 1.21 — photos de téléphone dans le bon sens (demande de G4GIM)

- Les téléphones enregistrent souvent la photo « couchée » avec une indication « à afficher tournée » : HFImage l'ignorait, la photo apparaissait et partait couchée. Elle est maintenant **remise droite automatiquement** à l'ouverture, comme dans Windows (message dans le journal).
- En mode « original », une photo remise droite part en **JPEG très haute qualité, déjà droite** (lisible partout, même par EasyPal).
- Nouveaux boutons **⟲ / ⟳** (en bas à droite de l'image, onglet TX) : tourner l'image d'un quart de tour à gauche ou à droite.
- Les images **reçues** qui portent cette indication s'affichent aussi dans le bon sens (fenêtre RX, galerie, site web).

## Version 1.20 — étiquette du site web sous l'image, heure UTC

- Site web / Digi-Sites : l'étiquette (indicatif, date, mode, bande) est maintenant **ajoutée sous l'image**, sur une bande noire. Avant, elle était posée sur le bas de la photo et cachait le bandeau de la station émettrice (les deux textes se mélangeaient).
- L'heure de l'étiquette est en **UTC** (« 19:28 UTC »), comme EasyPal : la même pour toutes les stations, quel que soit leur pays.
- Rappel : la liste des fichiers du serveur qsl.net affiche les heures de New York (6 h de moins que la France) ; ce n'est pas une erreur.

## Version 1.19 — « Envoyer la page maintenant » renvoie aussi les images

- Site web / Digi-Sites : le bouton **« Envoyer la page maintenant »** remet aussi en ligne les dernières images reçues (image1.jpg…) et émises (TX1.jpg…), prises dans la galerie. Après un changement de dossier ou de serveur, Digi-Sites trouve tout de suite les images, sans attendre la prochaine réception.

## Version 1.18 — bouton « Fréquence ▾ »

- Beaucoup d'utilisateurs ne trouvaient pas comment changer de fréquence (il fallait cliquer sur la fréquence affichée). Nouveau bouton **« Fréquence ▾ »** bien visible, à droite de « Attendre fréquence libre » : il ouvre le menu des fréquences image (3,733 – 7,058 – 14,233…).
- La fréquence du panneau porte une petite flèche **▾** pour montrer qu'elle se clique aussi, et une bulle d'aide « Cliquez pour changer de fréquence » apparaît au passage de la souris.

## Version 1.17 — l'émission hybride repart sans attendre

- 1.15 : le ménage des anciennes images sur le serveur se faisait **avant** l'émission. La première fois, des centaines d'anciennes images pouvaient être à effacer, une par une : l'émission mettait longtemps à partir. Le ménage se fait maintenant **en tâche de fond**, par une connexion à part, pendant que l'émission part.

## Version 1.16 — prénom dans Rx Ok seulement

- Le prénom n'est plus affiché dans la liste **Stations** (il prenait trop de place) ; il reste dans la liste **Rx Ok**, après le report. Le prénom complet s'affiche toujours dans le journal en cliquant sur une station.

## Version 1.15 — ménage sur le serveur (demande de RK1AT)

- Nouveau réglage **« Mes images gardées sur le serveur »** (Réglages → Mode hybride) : **les 3 dernières** (par défaut), **la dernière seulement** ou **toutes** (comme avant). Après chaque dépôt réussi, les anciennes images sont effacées du serveur FTP, en hybride HFImage comme en hybride EasyPal.
- Seuls les fichiers déposés par HFImage avec votre indicatif sont effacés (reconnus à leur nom) : les autres fichiers de votre site ne sont jamais touchés. Le journal indique combien d'images ont été effacées.

## Version 1.14 — prénoms longs

- Les prénoms longs (« Pierre-Marie ») élargissaient les listes : le report de Rx Ok et la fréquence de la liste Stations sortaient de la fenêtre. Le prénom est maintenant **en bout de ligne**, après le report ou la fréquence (qui restent toujours visibles et alignés), et coupé à 10 caractères (« Pierre-Ma. »). Le prénom complet reste visible dans le journal en cliquant sur la station.

## Version 1.13 — votre prénom sur votre propre ligne

- Dans la liste Rx Ok (et Stations), votre propre ligne affiche aussi votre prénom (« F4GOP Denis »), comme celles des autres stations.

## Version 1.12 — prénom à part, une seule ligne par station

- **Nouvelle case « Prénom »** (Réglages → Station) : il s'affiche à côté de l'indicatif dans la liste des stations des autres utilisateurs (« F4LTX Chris »), sans toucher à l'indicatif envoyé par radio.
- Beaucoup d'utilisateurs écrivaient leur prénom dans la case indicatif (« F4LTX CHRIS »). Par radio, l'indicatif est limité à 8 caractères : il arrivait coupé (« F4LTX CH ») et la même station apparaissait plusieurs fois dans les listes Stations et Rx Ok. Le prénom écrit derrière l'indicatif est maintenant rangé tout seul dans la case Prénom.
- **Une seule ligne par station** dans les listes, même si son indicatif arrive avec un prénom, coupé par la radio, ou depuis une ancienne version du programme.
- Pendant qu'on tape son indicatif, la présence Internet attend la fin de la frappe (3 s) au lieu de se reconnecter à chaque lettre (on voyait passer « F4LTX CH », « F4LTX CHR », « F4LTX CHRIS »…).

## Version 1.11 — contrôle général, programme ouvert des jours

- **Mémoire** : quand le programme restait ouvert très longtemps (des jours, beaucoup d'images reçues et envoyées), la mémoire utilisée grossissait petit à petit sans jamais redescendre : chaque image reçue gardait son décodeur, chaque image envoyée gardait son modem. Maintenant, une image reçue complète libère son décodeur, et le programme ne garde en mémoire que les 64 dernières images reçues et les 32 dernières envoyées (largement assez pour répondre aux demandes de complément). Les images enregistrées sur le disque ne sont pas touchées.
- Le bilan de la relecture d'un fichier WAV compte toujours toutes les images, même au-delà de 64.
- Nettoyage du code (importations inutilisées, ligne en double) ; aucun changement visible.

## Version 1.10 — le mode choisi à la main est gardé

- Après une image reçue en **EasyPal**, l'émission passe bien en EasyPal pour répondre à la station (case « suivre le mode reçu »). Mais si l'on choisissait ensuite **Auto** à la main (par exemple pour renvoyer l'image en DATAC), le programme remettait EasyPal quelques instants après, et l'image partait en EasyPal : l'état de la dernière réception EasyPal restait affiché et relançait le changement de mode à chaque rafraîchissement du panneau.
- Maintenant, le mode suit la station **une seule fois par émission reçue** ; un choix fait à la main ensuite est gardé jusqu'à la prochaine image reçue. Même règle pour les images DATAC (une fois par image).

## Version 1.09 — glisser-déposer réparé

- **Le programme se fermait** quand on glissait une image sur la fenêtre (1.08). Le glisser-déposer passe maintenant par **tkdnd** (paquet tkinterdnd2), l'extension de glisser-déposer reconnue pour Tk, au lieu d'une interception maison des messages de Windows. Une image glissée n'importe où sur la fenêtre s'ouvre dans l'onglet TX ; un autre fichier est proposé à l'envoi. Les chemins avec des espaces sont bien reconnus.
- Si l'extension ne peut pas se charger, le programme démarre normalement, sans glisser-déposer (message dans le journal).

## Version 1.08 — fichiers hybrides sans limite, glisser-déposer (demandes de RK1AT)

- **Fichiers en mode hybride** : plus de limite de taille ni de type, comme dans EasyPal. Les images hybrides partent telles quelles quelle que soit leur taille (plus de recompression au-delà de 7,5 Mo) ; un fichier de plus de 16 Mo part par l'annonce hybride normale (l'éclair est limité à 16 Mo). Par radio seule, la limite de 16 Mo reste (elle n'aurait pas de sens au-delà).
- **Réception** : nouveau réglage **« Fichiers hybrides reçus : taille max »** (Réglages → Mode hybride) : 8 Mo, 50 Mo, **200 Mo (par défaut)**, 1 Go ou **sans limite**. Avant, la limite était fixée à 8 Mo. Les autres protections restent (adresse publique seulement, contrôle de taille et de CRC).
- **Glisser-déposer** : une image glissée depuis l'Explorateur Windows n'importe où sur la fenêtre s'ouvre dans l'onglet TX ; un autre fichier est proposé à l'envoi.
- **Clic dans la fenêtre TX** : un clic dans la grande image ouvre le choix de l'image (un glisser pour se déplacer dans une image agrandie n'est pas un clic).

## Version 1.07 — émoticônes dans les bulles

- Fenêtre **Bulles de texte** : une palette de **30 émoticônes en couleur** (sourires, 👍 👋 🙏, ❤️ ⭐ 🎉, météo ☀️ 🌧️ ❄️ ⚡, 📻 📡 🎙️ 📷, ☕ 🍺 🎂 🏆…). Un clic l'ajoute dans le texte de la bulle, à l'endroit du curseur ; elle est dessinée en couleur dans l'image émise, à la taille du texte.
- Images Twemoji (licence CC-BY 4.0), fournies avec le programme : rien à installer, même rendu chez tout le monde.

## Version 1.06 — bulles de texte façon BD

- **💬 Bulles…** (onglet TX, ou menu Images → Bulles de texte…) : un texte dans une **bulle de bande dessinée** sur l'image émise.
  - Quatre styles : **parole** (bulle ronde avec une pointe), **pensée** (petits ronds), **cri** (contour en étoile), **cartouche** (rectangle, comme une légende).
  - Trois tailles de texte, relatives à l'image (lisible quelle que soit la taille d'émission) ; couleurs du fond et du texte au choix.
  - On **glisse la bulle** à la souris, et le rond rouge (la **pointe**) vers ce qu'elle montre. Plusieurs bulles possibles ; clic droit sur une bulle pour la supprimer.
- La bulle fait partie de l'image : tout le monde la voit, en radio comme en hybride, y compris les stations EasyPal / QSSTV. Elle s'ajoute aux incrustations (images des correspondants, conditions de trafic).
- Les bulles sont effacées quand on ouvre une autre image (elles étaient placées pour la précédente).

## Version 1.05 — plusieurs fréquences à la fois (profils)

- **Plusieurs HFImage ouverts en même temps**, chacun avec **ses propres réglages** : par exemple un sur 40 m, un sur 20 m et un sur 28,680 MHz, chacun branché sur son récepteur ou sur une bande d'un SDR (câbles audio virtuels type VB-Cable).
- **Réglages → Ouvrir une autre instance (profil)…** : on donne un nom (ex. « 20m ») ; HFImage le lance et propose un **raccourci sur le Bureau** (« HFImage 20m »). En ligne de commande : `HFImage_F4GOP.exe --profil 20m`.
- Chaque profil a son fichier de réglages, son dossier d'images (Documents\HFImage\20m) et son nom dans le titre de la fenêtre. Au premier lancement, il part des réglages habituels (indicatif, licence…) et l'assistant de démarrage permet de choisir son entrée audio.
- Stations en ligne : chaque instance a sa propre présence, avec sa fréquence.

## Version 1.04 — hybride en pleine qualité

- **Mode hybride** : l'image passe par Internet, il n'y a donc aucune raison de la dégrader. Elle part maintenant **en pleine qualité** par défaut : format **original** (le fichier tel quel, sans réduction ni recompression) et largeur **originale**. Avant, les réglages par défaut (640 px, 60 ko) rendaient l'image floue.
- Mise à jour : les réglages hybrides restés petits (60 ko…) passent en pleine qualité ; un réglage choisi plus grand est gardé.
- Une image de plus de **7,5 Mo** (les stations n'acceptent pas plus de 8 Mo) est recompressée à la même taille d'image, et réduite seulement si elle ne tient toujours pas.

## Version 1.03 — aide au réglage du serveur hybride

- **Tester le serveur** sans lien public (ou avec « ftp.… » à la place d'une adresse web) : au lieu d'échouer tout de suite, HFImage teste quand même le **dépôt FTP**, qui suffit pour l'**hybride EasyPal**, puis explique ce qu'est le lien public (l'adresse **web** du dossier, nécessaire pour l'hybride HFImage).
- **qsl.net** : HFImage propose le lien public probable (ex. **https://www.qsl.net/wasstv/easypal/**) et refait le test d'un clic.
- **Port 22** : c'est le port du SFTP (SSH), que ni HFImage ni EasyPal n'utilisent ; le message le dit clairement et indique le port 21 (FTP).
- Échec de connexion avec **FTPS** coché : le message conseille d'essayer sans FTPS, comme dans EasyPal.
- Messages du serveur hybride **traduits** dans les 5 langues (ils restaient en français).

## Version 1.02 — dédicace et transparence

- **Infos → À propos…**, mode d'emploi (français et anglais) et page GitHub : le programme est **dédié à Erik Sundstrup VK4AES (SK)**, créateur d'EasyPal, en hommage à son travail.
- Par honnêteté, ces mêmes endroits indiquent que HFImage a été conçu, choisi et testé sur l'air par Denis F4GOP, et que son code a été écrit en grande partie avec l'aide de l'**intelligence artificielle Claude** (Anthropic).

## Version 1.01 — changer de fréquence d'un clic (idée d'Allan G7VQV)

- **Clic sur la fréquence** affichée (panneau en haut à gauche, ou barre d'état en bas) : menu des fréquences image **3,733 – 7,058 – 14,233 – 21,340 – 28,680 MHz** ; un clic et le poste y va par CAT, comme dans WSJT-X. La fréquence actuelle est marquée d'un ●.
- **Bande latérale** de chaque fréquence (LSB en dessous de 10 MHz, USB au-dessus, modifiable) : le poste passe dessus, et s'il était en DATA il y reste (LSB-DATA / USB-DATA).
- **Action → Aller sur une fréquence** : le même menu, avec **Autre fréquence…** (saisie en MHz) et **Modifier la liste…** (une ligne par fréquence, ex. « 7.058 LSB », bouton « Liste d'origine »).
- **Clic droit dans la liste des stations → Aller sur la fréquence de cette station.**
- Tous les types de liaison CAT : Kenwood en direct (commande FA), Hamlib, FLRig, OmniRig. Jamais pendant une émission ; sans liaison CAT, le programme explique comment la régler. HFImage vérifie que le poste est bien arrivé sur la fréquence demandée.

## Version 1.00 — liste des stations toujours lisible

- **Liste des stations et Rx Ok** : le début des indicatifs pouvait être coupé (« 4FR79 » pour « 14FR79 », « A0041SWL » pour « PA0041SWL ») : un glisser à la souris décalait la liste vers la droite et elle restait décalée. Les deux listes reviennent maintenant toujours au début de la ligne, et le glisser ne les fait plus défiler sur le côté.
- **Indicatifs longs** (PA0041SWL, F4FRC/P…) : la colonne de l'indicatif prend la largeur du plus long, la fréquence et « HYB » restent alignés.
- Version **1.00** : merci à tous les utilisateurs pour leurs essais et leurs retours.

## Version 0.99 — écouteurs (SWL)

- **Identifiants d'écouteurs acceptés** dans l'assistant de démarrage : **PA0041SWL**, **F-12345**, **14VD274**, **ONL1234**… (la 0.98 n'acceptait que les indicatifs radioamateurs).
- **Un écouteur n'émet jamais** : avec un identifiant d'écouteur (se terminant par SWL, avec un tiret, commençant par deux chiffres, ou ONL + chiffres), HFImage reçoit tout normalement et envoie ses **reports par Internet** (Rx Ok, carte), mais ne passe jamais en émission : ni image, ni accusé (ACK), ni BSR automatiques par radio. Un clic sur ÉMISSION l'explique.
- **Indicatifs longs reçus par radio** : les trames radio ne portent que 8 caractères (« PA0041SWL » arrivait en « PA0041SW »). S'il n'y a qu'une station en ligne ou entendue dont l'indicatif complet commence ainsi, HFImage affiche l'indicatif complet.

## Version 0.98 — éclair par défaut, assistant de démarrage, moins de fausses alertes

- **Hybride éclair coché par défaut** : depuis la 0.93 l'annonce éclair (DATAC13) passe jusqu'à −7 dB, bien plus bas que l'annonce normale (DATAC3, vers 0 dB). La case **Éclair (9 s)** est donc cochée d'office (une seule fois à la mise à jour : si vous la décochez ensuite, votre choix est gardé). Elle ne change rien tant que le mode hybride n'est pas activé, et si le serveur des stations en ligne n'est pas joignable au moment d'émettre, l'annonce normale part toujours à la place.
- **Assistant de démarrage** : au premier lancement, une fenêtre en 3 étapes guide le réglage — **indicatif et locator**, **carte son du poste** (sortie / entrée, essai 1 kHz sans émettre), **poste radio** (CAT / PTT, installation de Hamlib proposée si besoin). On le retrouve par **Réglages → Assistant de démarrage…**. Une nouvelle installation n'a plus « F4GOP » comme indicatif par défaut : le champ est vide tant que l'utilisateur n'a pas mis le sien.
- **Attendre fréquence libre** : sur le bruit seul, le démodulateur croit parfois accrocher un signal pendant un instant (un bloc de 0,5 s, jamais plus dans nos mesures). Une accroche n'est maintenant prise en compte qu'au-delà de 0,7 s ; une trame décodée compte toujours tout de suite.

## Version 0.97 — menus et onglets rangés (rien n'est supprimé)

- **Onglet Simulation** : c'est un outil d'essai (canal HF simulé), pas de trafic. Il n'est plus affiché d'office : **Fichiers → Onglet Simulation (canal HF simulé)** l'affiche ou le cache (le choix est gardé). Il reste donc RX, TX, Stations et Galerie.
- **Menu Effacer** : déplacé en sous-menu de **Fichiers → Effacer** (mêmes commandes : historique des images, messages reçus, journal des stations, waterfall, journal à l'écran).
- **Fichiers → Décoder et analyser un fichier WAV…** remplace « Décoder un fichier WAV… » et « Analyser un enregistrement WAV… » : on choisit le fichier une seule fois, ses images sont décodées comme en réception et la fenêtre d'analyse (niveau, QRM, trames, SNR, mode conseillé) s'ouvre en même temps.

## Version 0.96 — le waterfall et l'analyseur connaissent le DATAC13

- **Waterfall** : la bande du **DATAC13** (annonce hybride éclair, 200 Hz autour de 1 500 Hz) a son repère dans l'échelle, et elle est encadrée en rose quand une annonce éclair est reçue, comme les autres modes.
- **Analyseur de fichiers WAV** : les trames DATAC13 sont reconnues et comptées (rond ou croix dans le graphique, couleur propre dans la légende), avec la mention « DATAC13 : annonce hybride éclair ». Le conseil de mode ne tient compte que des modes d'image (DATAC1X à DATAC4).

## Version 0.95 — attendre que la fréquence soit libre

- Nouvelle case **Attendre fréquence libre** sous les boutons, **cochée par défaut**. Si une autre station émet déjà quand vous cliquez sur ÉMISSION (ou ▶ Émettre, ou « Envoyer le texte seul »), HFImage n'émet pas par-dessus : le bouton devient **ATTENTE…** (orange), la barre d'état indique qui occupe la fréquence, et l'émission **part toute seule** dès que la fréquence se libère, après un petit délai tiré au hasard (2 à 6 s) pour que deux stations en attente ne repartent pas ensemble.
- La fréquence est considérée occupée :
  - **par radio** (écoute active) : un signal DATAC ou EasyPal est en cours de décodage, et encore 3 s après sa fin ;
  - **par Internet** : une station en ligne est en émission sur votre fréquence, à 3 kHz près (fréquence du poste lue par CAT).
- Pendant l'attente : **clic sur ÉMISSION** = annuler, **clic droit sur ÉMISSION** = émettre tout de suite.
- Au bout de **5 minutes** d'attente, HFImage demande s'il faut émettre quand même.
- Les **réponses automatiques** (ACK, BSR, FIX) n'attendent pas : elles sont courtes et partent juste après la fin de l'émission du correspondant.

## Version 0.94 — bouton « Répondre… » de retour

- Fenêtre **Message reçu** : depuis l'ajout de la case « Traduire » (0.91), la rangée du bas était trop longue et le bouton **Répondre…** sortait de la fenêtre. Les cases (Ouvrir à chaque message reçu, Bip, Traduire) sont maintenant sur une rangée et les boutons (**Répondre…**, Copier, Fermer) sur la rangée du dessous : tout reste visible, même fenêtre réduite au minimum.

## Version 0.93 — hybride éclair robuste (DATAC13) : passe dans le bruit et le QRM

- **Annonce hybride éclair en DATAC13** : la trame d'annonce (empreinte de l'image, 14 octets ; le lien passe par Internet) part maintenant **3 fois en DATAC13**, un mode codec2 très étroit (**200 Hz** au lieu de 500) fait pour les signaux faibles, puis 2 fois en DATAC0 pour les stations qui ont une version plus ancienne. Annonce de **9 s** au lieu de 4,5 s (case « Éclair (9 s) »).
- Mesuré au simulateur, part des annonces reçues :

  | Canal | S/B | Éclair DATAC0 (avant) | Éclair DATAC13 (0.93) |
  |---|---|---|---|
  | Calme | −5 dB | 15 % | 100 % |
  | Calme | −7 dB | 0 % | 100 % |
  | Fading moyen | −5 dB | 50 % | 100 % |
  | Fading moyen | −7 dB | 20 % | 80 % |
  | Fading fort | −5 dB | 35 % | 100 % |
  | Fading fort | −7 dB | 5 % | 90 % |

- HFImage **écoute le DATAC13 en permanence** (en plus des autres modes) ; une annonce reçue dans les deux modes n'est comptée qu'une fois.
- **Coupe-QRM** : son niveau de référence est maintenant pris sur les porteuses du mode seulement. Pour un mode aussi étroit que le DATAC13, l'ancien calcul prenait les porteuses du signal lui-même pour du QRM à fort S/B. Les autres modes ne changent pas (vérifié au simulateur).

## Version 0.92 — installation de Hamlib proposée au moment d'émettre

- **« PTT par CAT impossible : Hamlib n'est pas installé »** : au lieu d'un simple message d'erreur, HFImage propose maintenant **« L'installer maintenant ? »**. Oui : Hamlib est téléchargé depuis son site officiel (empreinte vérifiée, comme avec le bouton des réglages du poste) ; il suffit ensuite de relancer l'émission.
- Si `rigctld.exe` disparaît juste après l'installation, le programme indique que l'**antivirus** l'a probablement mis en quarantaine (cause fréquente quand Hamlib « disparaît » alors qu'il marchait avant).

## Version 0.91 — traduction des messages reçus

- **Traduction automatique** : un message reçu écrit dans une autre langue que celle choisie dans le programme est traduit à l'arrivée, par Internet (Google Traduction, MyMemory en secours ; service gratuit). Exemple : F4GOP écrit en français, M0JGM lit le message en anglais, et inversement.
  - Le message part par radio **tel qu'il a été écrit** : seule la station qui le reçoit le traduit, pour elle.
  - Fenêtre **Message reçu** : la traduction en premier, l'**original** en dessous, en gris. Cadre **Messages reçus** : une ligne bleue « ↳ traduction (EN → FR) : … ».
  - Sans Internet, ou si le service ne répond pas, le message s'affiche simplement tel quel. Les messages très courts (« 73 », un indicatif) ne sont pas envoyés au traducteur.
  - Nouvelle case **Traduire** dans la fenêtre « Message reçu » pour couper la traduction.

## Version 0.90 — retour du waterfall d'origine

- Le plancher du waterfall ajouté en 0.89 est retiré : le waterfall fonctionne exactement comme en 0.88. Tout le reste est inchangé.

## Version 0.89 — waterfall noir quand le poste est éteint

- **Waterfall** : poste éteint, le codec USB reste alimenté mais ne reçoit plus rien ; le réglage automatique du waterfall amplifiait alors son tout petit bruit et le ronflement secteur (raies verticales, peigne de pics dans le spectre). Un plancher a été ajouté : sous environ −76 dBFS de bruit d'entrée, le waterfall reste noir. En réception normale, rien ne change.

## Version 0.88 — interface plus réactive, changement de poste sans redémarrer

- **Onglet TX plus fluide** : la recherche de la taille et de la qualité de l'image (à l'ouverture d'une image et à chaque changement de Mode, Durée, Largeur, Format, incrustation…) se fait maintenant **en tâche de fond**. La fenêtre ne se fige plus : mesuré avec une photo de 12 Mpx, 0,3 s au pire au lieu de 2,5 à 3,3 s à chaque réglage. Pendant le calcul, l'onglet TX affiche « Calcul de l'image… » ; plusieurs réglages changés à la suite ne s'additionnent plus. Les résultats déjà calculés sont gardés : revenir à un réglage précédent est immédiat. « Émettre » pendant un calcul attend simplement qu'il se termine.
- **Changement de poste sans redémarrer** :
  - choisir une autre **Entrée (depuis le poste)** dans les Réglages relance tout de suite l'écoute sur cette entrée (avant, il fallait redémarrer le programme pour voir la réception) ;
  - **Actualiser** relit vraiment la liste des cartes son de Windows : un poste branché ou allumé après le démarrage de HFImage apparaît maintenant sans redémarrer ;
  - valider la fenêtre **Poste radio** relit aussi les cartes son (le codec USB d'un autre poste vient souvent d'être branché).

## Version 0.87 — indicatif du correspondant dans le panneau

- **L'indicatif de l'ancien correspondant restait affiché** : le panneau était rafraîchi avec l'indicatif de la dernière image DATAC, qui écrasait celui d'une annonce hybride ou d'une image EasyPal plus récente. Maintenant, **la réception la plus récente gagne**.
- **Pendant une image DATAC, l'indicatif n'arrive qu'en fin d'émission** (trame d'identification). En attendant, le panneau n'affiche plus l'indicatif précédent : s'il n'y a **qu'une seule station en ligne en émission sur votre fréquence** (à 3 kHz près), son indicatif est affiché tout de suite, suivi de « ? » (ex. « M0JGM ? ») ; sinon « — ». Le « ? » disparaît dès que l'identification est reçue.
- **Hybride éclair** : l'indicatif, reçu par Internet avec le lien, s'affiche maintenant dans le panneau.

## Version 0.86 — fenêtre Réglages utilisable sur les écrans moyens

- **Réglages** : sur un écran moyen (par exemple 1366×768), la fenêtre dépassait en bas de l'écran et l'on ne pouvait plus atteindre « Enregistrer les réglages » ni « Fermer ». La fenêtre s'ouvre maintenant à la taille de l'écran, son contenu **défile** (barre de défilement et molette de la souris), et les boutons **Enregistrer les réglages / Ouvrir le journal / Fermer** restent toujours visibles en bas.
- Texte d'aide des stations en ligne mis à jour : HFImage essaie tout seul les ports 8883, 8884 et 8000 si le 1883 est bloqué.

## Version 0.85 — licence en français (LICENCE.txt)

- Nouveau fichier **LICENCE.txt**, en français avec un résumé en anglais, à côté du texte officiel de la GPL v3 (LICENSE) : auteur, utilisation gratuite, partage et modification, **conditions complémentaires** permises par l'article 7 de la GPL v3 (garder la mention « Denis, F4GOP » et le lien officiel, marquer clairement une version modifiée, ne pas reprendre le nom « HFImage F4GOP » pour une version modifiée), **aucune garantie**, **limitation de responsabilité** (PTT, passage en DATA, émissions automatiques), **données personnelles** (ce qui part sur Internet, et quand), éléments d'autres auteurs, droit français.
- Menu **Infos → Licence (GNU GPL v3)** : ouvre LICENCE.txt (et copie le texte de la GPL à côté). La fenêtre À propos le mentionne.
- **Au premier démarrage**, la licence s'affiche : « J'accepte » pour continuer, « Je refuse » ferme le programme. Les utilisateurs actuels la voient **une seule fois** après cette mise à jour ; elle ne revient que si la licence change.

## Version 0.84 — dossier des images rangé : une copie par image, un dossier par jour, nettoyage

- **Une seule copie par image** : HFImage enregistrait chaque image reçue deux fois, l'original (AVIF, JPEG, WebP…) et une copie PNG pour l'afficher, souvent 5 à 10 fois plus lourde. Il affiche maintenant directement l'original : **deux fois moins de fichiers**, et beaucoup moins de place. Seuls les dessins SVG gardent un rendu PNG, rangé à part dans un sous-dossier caché « apercus ». Pour le plein format (double-clic), une image AVIF ou JPEG 2000 est convertie à la volée pour la visionneuse de Windows.
- **Un sous-dossier par jour** : les images et messages reçus vont dans `2026-10-18`, `2026-10-19`… (même chose pour les images envoyées, dans « envoyees »). Les fichiers reçus restent dans « fichiers ». La galerie et l'historique fonctionnent comme avant.
- **Nettoyage automatique** (Réglages, sous « Dossier des images reçues ») : les sous-dossiers par jour de plus de **30 jours** (réglable de 1 à 3650) sont effacés au démarrage puis toutes les 6 heures, avec une ligne dans le journal. Rien d'autre n'est jamais effacé : ni les fichiers reçus, ni les enregistrements, ni les images rangées à plat par les versions précédentes. Décochez la case pour tout garder.

## Version 0.83 — licence GNU GPL v3

- HFImage F4GOP est maintenant officiellement un **logiciel libre et gratuit**, sous licence **GNU GPL v3** (© 2026 Denis F4GOP) : chacun peut l'utiliser, le copier, le partager et le modifier ; une version modifiée distribuée doit rester sous la même licence, avec ses sources. C'est aussi la licence du modem EasyPal repris de QSSTV.
- Texte complet : fichier **LICENSE** du dépôt GitHub, et nouveau menu **Infos → Licence (GNU GPL v3)** dans le programme. La fenêtre **À propos** et les modes d'emploi le mentionnent.

## Version 0.82 — retrait de l'envoi de pages web

- La fonction « page web envoyée comme une image » de la version 0.81 est **retirée**, pour garder le programme simple. **Ouvrir une image…** n'accepte plus les fichiers .html ; le menu Images → Pages web disparaît. Tout le reste est identique à la 0.81.
- Pour envoyer une page web, faites-en une capture d'écran (touche Impr. écran ou Outil Capture de Windows) et ouvrez-la comme une image.

## Version 0.81 — envoyer une page web comme une image

- **Ouvrir une image…** accepte maintenant les **pages web** (.html, .htm, .mht). HFImage ouvre la page avec **Microsoft Edge** (présent dans Windows 10 et 11 ; sinon Google Chrome), attend quelques secondes que ses images se chargent (y compris celles qui viennent d'Internet), puis en fait une **capture** : elle s'affiche dans l'onglet TX et part comme une image normale. Tous les correspondants la voient telle quelle, **EasyPal et QSSTV compris**, sans avoir besoin d'Internet.
- Taille de la capture : menu **Images → Pages web : taille de la capture** (800×600, **1024×768** par défaut, 1280×960, 1280×720).
- Les animations (texte qui défile, GIF animés) sont figées à l'instant de la capture.
- Une page écrite en UTF-8 sans le déclarer (accents qui s'affichent « DÃ©partement ») est corrigée automatiquement.
- Le navigateur tourne avec un profil temporaire : il ne touche ni à votre navigateur ouvert, ni à son historique.

## Version 0.80 — contrôle DATA quel que soit le PTT, modes d'emploi à jour

- **Mode DATA vérifié dès que le CAT est relié, quelle que soit la méthode PTT** (CAT, RTS, DTR ou VOX). Avant, le contrôle ne se faisait qu'avec le PTT par CAT : avec un PTT par RTS ou VOX, on pouvait émettre en LSB ou en USB sans DATA sans le savoir. Avec un PTT par RTS / DTR / VOX, un échec du passage en DATA est signalé dans le journal sans bloquer l'émission. Choisissez « Avant / Micro » comme source audio si votre poste émet l'audio sans le mode DATA : HFImage ne touche alors pas à son mode (ce choix est maintenant possible aussi avec un PTT par RTS / DTR / VOX).
- **Modes d'emploi français et anglais mis à jour** (menu Infos) : passage automatique en LSB-DATA / USB-DATA, fenêtres séparées et menu Fenêtres, jusqu'à 4 images de correspondants (nouvelle capture), hybride éclair (avec les mesures), sécurité des téléchargements, ports COM, accès de secours au serveur des stations, problèmes fréquents complétés.

## Version 0.79 — sortie audio du TS-890 et journal du mode DATA

- **Sortie audio** : quand l'entrée et la sortie du codec USB du poste portent exactement le même nom dans Windows (par ex. renommées « TS-890 »), HFImage prenait parfois l'**entrée** à la place de la sortie : erreur « Invalid number of channels », puis message « … ne fonctionne pas ; … utilisée à la place » avec deux fois le même nom. HFImage choisit maintenant toujours un appareil du bon sens (sortie pour l'émission, entrée pour la réception).
- **Mode DATA** : si le réglage « Poste pas en DATA avant d'émettre » est sur « Émettre sans rien dire », le journal le dit maintenant, avec l'endroit où choisir le passage automatique en DATA.

## Version 0.78 — passage automatique en DATA, en LSB comme en USB

- **Poste pas en DATA avant d'émettre** : HFImage passe maintenant le poste en DATA **en gardant sa bande latérale** : **LSB → LSB-DATA**, **USB → USB-DATA**. Avant, il le mettait toujours en USB-DATA, ce qui changeait de bande latérale sur 40 et 80 m (où l'image numérique se trafique souvent en LSB, comme dans EasyPal).
- Réglage par défaut : **« Passer en DATA automatiquement (USB-DATA / LSB-DATA) »** (Réglages → Poste radio). Si vous aviez choisi « Demander » ou « Émettre sans rien dire », votre choix est gardé.
- Kenwood en direct (TS-990 : LSB-D1 / USB-D1 ; TS-890 et TS-590 / TS-480… : LSB ou USB puis DATA), Hamlib (PKTLSB / PKTUSB), FLRig et OmniRig (DIG-L / DIG-U).
- Rappel : les deux stations doivent être sur la même bande latérale.

## Version 0.77 — menu Fenêtres simplifié

- Le menu **Fenêtres** ne propose plus de séparer les onglets **RX**, **TX**, **Simulation** ni le **Journal** : ils restent toujours dans la fenêtre principale. On peut toujours séparer le panneau et les boutons, le waterfall, la liste des stations entendues, l'onglet Stations et la galerie.
- Si l'une de ces zones avait été séparée, elle revient d'elle-même dans la fenêtre principale.

## Version 0.76 — tous les ports COM, et stations en ligne derrière un pare-feu

- **Ports COM manquants** (signalé par RK1AT, merci !) : certains ports présents dans le Gestionnaire de périphériques n'apparaissaient pas dans les listes **Port série** et **PTT** (convertisseurs Prolific, CH340, Silicon Labs, ports virtuels…). HFImage lit maintenant aussi la liste des ports actifs de Windows (celle qu'utilisent la plupart des logiciels radio) : tous les ports apparaissent, classés COM1, COM2, COM3…
- On peut toujours **taper le nom d'un port** (ex. `COM9`) directement dans la case.
- **Stations en ligne** : si le serveur ne répond pas sur le port habituel (1883, souvent bloqué par un pare-feu ou un fournisseur d'accès), HFImage essaie tout seul les autres accès du même serveur (8883 chiffré, puis 8884 et 8000 par le web). Le journal indique le port qui a fonctionné.

## Version 0.75 — Historique et Messages reçus : affichés ou masqués

- Menu **Fenêtres** : **« Afficher l'historique (onglet RX) »** et **« Afficher les messages reçus (onglet RX) »**. Décochez-les pour masquer ces listes à droite de l'image reçue ; sans aucune des deux, l'**image reçue prend toute la largeur**. Le choix est gardé d'une session à l'autre.
- Les messages continuent d'arriver même quand la liste est masquée (fenêtre « Message reçu », menu Images).
- « Disposition d'origine des fenêtres » les réaffiche.

## Version 0.74 — fenêtres séparées toujours visibles

- **Correction** : un clic sur la fenêtre principale faisait passer les fenêtres séparées **derrière** elle, comme si elles avaient disparu. Les fenêtres séparées restent maintenant **toujours devant la fenêtre principale**, à l'endroit et à la taille où vous les avez mises. On peut cliquer et travailler dans n'importe quelle fenêtre sans que les autres bougent ou se cachent.
- Elles se réduisent et reviennent avec la fenêtre principale.

## Version 0.73 — fenêtres séparées : organisez l'écran comme vous voulez

- **Nouveau menu « Fenêtres »** : chaque zone du programme peut devenir une **fenêtre séparée**, à placer et dimensionner où vous voulez, y compris sur un **autre écran** :
  - Panneau et boutons, Waterfall, Stations entendues, Journal ;
  - les onglets **Réception (RX)**, **Émission (TX)**, **Stations**, **Simulation** et **Galerie**.
- Cochez une zone dans le menu pour la séparer, décochez-la (ou **fermez sa fenêtre**) pour la remettre à sa place dans la fenêtre principale. « Tout remettre dans la fenêtre principale » remet tout d'un coup, comme « Réglages → Disposition d'origine des fenêtres ».
- Tout continue de fonctionner dans les fenêtres séparées (waterfall, réception, émission, galerie…). Quand une image arrive et que l'onglet RX est séparé, il reste simplement affiché dans sa fenêtre ; les boutons qui ouvrent un onglet (Galerie, Log Station…) font passer sa fenêtre au premier plan.
- La disposition est **gardée** : au prochain lancement, les fenêtres séparées reviennent à leur place et à leur taille. Si un écran a été débranché entre-temps, la fenêtre revient près de la fenêtre principale.
- Quand le waterfall est séparé, la liste des stations prend toute la colonne de gauche.

## Version 0.72 — hybride éclair plus robuste (4,5 s)

- L'annonce **éclair** part maintenant en **5 copies** au lieu de 3 : **4,5 s** sur l'air au lieu de 3 s (toujours 2,5 fois plus court que l'annonce normale de 11 s). Une seule copie reçue suffit, et elles sont plus étalées dans le temps face au QSB.
- Mesuré au simulateur (20 essais par point) :

| Canal | SNR | Normale (11 s) | Éclair 0.71 (3 s) | Éclair 0.72 (4,5 s) |
|---|---|---|---|---|
| Calme | −4 dB | 100 % | 75 % | **100 %** |
| Fading moyen | −2 dB | 60 % | 70 % | **85 %** |
| Fading moyen | 0 dB | 85 % | 85 % | **100 %** |
| Fading fort | −2 dB | 55 % | 70 % | **90 %** |
| Fading fort | 0 dB | 95 % | 85 % | **100 %** |

- La case s'appelle maintenant « Éclair (5 s) ». Compatible avec la 0.71 (même trame).

## Version 0.71 — hybride éclair : annonce radio en 3 secondes

- **Nouveau : « Éclair (3 s) »**, à côté de « Mode hybride » dans l'onglet TX. L'annonce radio ne porte plus le lien de l'image, seulement son **empreinte** (SHA-256 abrégé), sa taille et son format : elle tient dans **une seule trame DATAC0** (500 Hz de large). Durée sur l'air : **3 s au lieu de 11 s**.
- Le lien part en même temps par le serveur des **stations en ligne**. La station qui entend l'annonce récupère le lien, télécharge l'image et vérifie qu'elle a **exactement l'empreinte reçue par radio** : un faux lien publié sur Internet ne peut pas faire passer une autre image.
- Robustesse mesurée au simulateur (20 essais par point, au moins une des 3 copies décodée) : comparable à l'annonce normale. Canal calme : 100 % dès −2 dB (normale : dès −4 dB). Fading moyen : 70 % à −2 dB et 85 % à 0 dB (normale : 60 % et 85 %).
- **Conditions** : les deux stations doivent avoir **« Stations en ligne »** activé et la version 0.71. Les versions précédentes ignorent simplement la trame. Si le serveur n'est pas joignable au moment d'émettre, HFImage envoie l'annonce normale (DATAC3) et le signale dans le journal.
- L'hybride normal et l'hybride EasyPal ne changent pas.

## Version 0.70 — plusieurs images de correspondants dans l'image émise

- **Image du correspondant : jusqu'à 4 images reçues** incrustées dans votre image, par exemple pour répondre à plusieurs stations d'un coup ou montrer les images d'un QSO à plusieurs.
- Fenêtre **Image du correspondant…** : liste **Images incrustées** avec les boutons **Ajouter une image** et **Retirer**. Chaque image a sa propre **position** et sa propre **taille** (coin, ou libre à la souris et à la molette). **Cliquez** sur une image dans l'aperçu pour la choisir (cadre jaune), faites-la glisser, la molette l'agrandit ou la réduit.
- Une nouvelle image se place d'elle-même dans un **coin libre**. La disposition de chaque image est gardée pour les émissions suivantes.
- **Galerie** (clic droit sur une image reçue) : nouveau choix **« Ajouter cette image à mon image TX »**, qui s'ajoute aux images déjà incrustées. « Répondre avec cette image » remplace toujours les incrustations par cette seule image, comme avant.

## Version 0.69 — réception plus sûre

- **Correction de sécurité : indicatif reçu dans le nom des fichiers.** L'indicatif d'une station (reçu par radio, en HFImage comme en EasyPal) sert à nommer l'image ou le fichier enregistré. Un indicatif piégé, contenant par exemple `\..\..\`, pouvait faire enregistrer un fichier **en dehors** du dossier de réception (dans Documents ou plus haut), avec une extension choisie par l'émetteur pour les fichiers. Seuls les lettres, chiffres et « - » de l'indicatif sont maintenant gardés (« / » devient « - » comme avant), et chaque fichier reçu est vérifié avant d'être écrit : il doit rester dans le dossier de réception. Les noms de fichiers ne changent pas pour les indicatifs normaux.
- **Hybride EasyPal : fichier limité à 8 Mo**, comme l'hybride HFImage. Une annonce pouvait faire télécharger un fichier de taille quelconque, jusqu'à faire planter le programme faute de mémoire.
- **Téléchargements hybrides (HFImage et EasyPal) : serveurs locaux refusés.** Le serveur indiqué dans une annonce radio ne peut plus désigner l'ordinateur lui-même ni une machine du réseau de la maison (box, NAS, imprimante…) : seules les adresses Internet publiques sont contactées, y compris après une redirection. Le test du serveur dans les Réglages n'est pas concerné (votre propre serveur peut être local).
- Tests automatiques de ces protections, lancés à chaque fabrication de l'exe (`tests/test_securite.py`).
- Petits nettoyages du code (variables inutilisées, banc d'essai `loopback.py`).

## Version 0.68 — mode d'emploi en anglais et mode d'emploi complété

- **Nouveau : mode d'emploi en anglais** (PDF, 15 pages, captures de l'interface en anglais), menu **Infos → Mode d'emploi en anglais (PDF)**. Il couvre tout le programme : modes HFImage, mode EasyPal / QSSTV, hybride, stations en ligne, messages, problèmes fréquents.
- **Mode d'emploi en français mis à jour** (il datait de la 0.50) : nouveau chapitre **Mode EasyPal (HamDRM)** (réglages, réglages conseillés, BSR / FIX, textes, hybride EasyPal, suivi du mode reçu), zoom à la souris, bascule automatique sur l'onglet RX, image du correspondant placée à la souris, cartes son sans doublons, problèmes fréquents complétés, crédits.

## Version 0.67 — image du correspondant placée et dimensionnée à la souris

- Fenêtre **Image du correspondant** : dans l'aperçu, **faites glisser** l'image du correspondant pour la placer **où vous voulez** dans votre image, et utilisez la **molette** pour l'**agrandir ou la réduire** (de 10 % à 90 % de la largeur). Position et taille passent alors sur « Libre » ; choisir un coin ou une taille dans les listes revient aux réglages habituels.
- Le réglage est gardé pour les émissions suivantes, et l'image émise est exactement celle de l'aperçu.

## Version 0.66 — zoom à la souris sur les images

- **Molette de la souris** sur l'image reçue (et sur l'image à émettre) : agrandit ou réduit autour du pointeur, jusqu'à ×16.
- **Clic gauche maintenu** : déplace l'image agrandie.
- **Clic droit** : retour à l'image entière. Le zoom revient aussi à l'image entière à chaque nouvelle image.
- Le double-clic ouvre toujours l'image en grand dans la visionneuse de Windows.

## Version 0.65 — le mode d'émission change dès le début de la réception

- Le passage automatique sur le mode reçu (EasyPal ↔ HFImage) se fait maintenant **dès que l'image commence à arriver**, et plus seulement quand elle est complète. Les réglages A / B / E et QAM d'EasyPal sont repris quand l'image est complète.
- Rappel : la réception décode toujours les deux modes, quel que soit le mode d'émission choisi. Si l'image HFImage reste incomplète, le BSR part automatiquement (en DATAC0) à la fin de l'émission du correspondant, même en mode EasyPal ; c'est le FIX du correspondant qui complète l'image.

## Version 0.64 — bascule automatique sur l'onglet Réception

- Quand une image commence à arriver (HFImage ou EasyPal) alors que l'onglet **Émission** est affiché, HFImage passe **tout de suite** sur l'onglet **Réception** pour la montrer, comme EasyPal, sans attendre la fin de l'image. Si vous revenez sur l'onglet Émission pendant la réception, le programme vous y laisse jusqu'à la fin de l'image. Rien ne bascule pendant vos propres émissions.

## Version 0.63 — l'émission suit le mode reçu

- Quel que soit le mode choisi pour l'émission, HFImage **décode toujours les deux** : les images et messages EasyPal **et** ceux de HFImage (DATAC).
- **Nouveau** : quand une image ou un message arrive dans l'autre mode, l'émission **passe automatiquement sur ce mode** pour répondre à la station dans le mode qu'elle écoute :
  - réception EasyPal → mode **EasyPal**, avec le même mode A / B / E, la même largeur (2,2 / 2,4) et la même QAM que la station reçue (sauf hybride, toujours en E / QAM4) ;
  - réception HFImage alors qu'on est en EasyPal → mode **Auto**.
  Le changement est indiqué dans le journal. Option dans l'onglet **Stations** : « Passer en émission sur le mode reçu » (cochée par défaut). Rien ne change pendant une émission ni lors du décodage d'un fichier WAV.
- La ligne des réglages EasyPal apparaît / disparaît correctement même si l'onglet Émission n'est pas affiché au moment du changement.

## Version 0.62 — EasyPal plus robuste dans le bruit

- **Réception EasyPal** : le décodeur calcule maintenant la fiabilité de chaque bit de façon exacte (distances au carré) : environ **0,5 dB de mieux en QAM16**, identique en QAM4. Rien ne change pour les autres stations.
- **Émission EasyPal** : **Reed-Solomon RS2 par défaut** (le réglage « Aucun » existant passe à RS2 une seule fois, vous pouvez le remettre). Avec un peu de QSB, quelques segments se perdent toujours et l'image restait incomplète ; avec RS2, elle est reconstruite sans attendre de BSR/FIX. Mesuré au simulateur en mode B / QAM16 avec QSB léger : image complète **dès 14 dB au lieu de 17 à 20 dB**, pour une émission environ 18 % plus longue. RS est lu par EasyPal et QSSTV : le signal reste 100 % compatible.
- Le signal émis reste celui d'EasyPal (on ne peut pas changer le format sans perdre la compatibilité) ; le niveau moyen avait déjà été relevé de 4 dB en 0.59.

## Version 0.61 — listes de cartes son sans doublons

- **Sortie vers le poste / Entrée depuis le poste** : chaque appareil n'apparaît plus qu'**une fois**, avec son nom complet. Windows présente chaque carte son plusieurs fois (MME, DirectSound, WASAPI…) ; HFImage choisit lui-même l'interface la plus sûre et, si elle échoue, essaie toujours automatiquement les autres pour le même appareil.
- Les entrées virtuelles de Windows (« Mappeur de sons Microsoft », « Pilote de son principal »…) ne sont plus proposées.
- Votre réglage actuel est conservé, même s'il désignait l'un des anciens doublons.

## Version 0.60 — report Rx Ok en hybride EasyPal

- **Rx Ok en hybride EasyPal** : la station qui reçoit une image hybride EasyPal renvoie maintenant son **report** (S/B mesuré sur l'annonce radio) avec sa confirmation ; seul l'indicatif apparaissait. Il faut que la station qui reçoit ait la version 0.60.

## Version 0.59 — mode EasyPal : signal plus fort, largeurs et Rx Ok

- **Signal EasyPal plus fort de 4 dB** : à réglage égal, l'émission EasyPal partait 5,6 dB plus faible que les modes DATAC (signal OFDM aux crêtes très marquées) : trame à peine visible chez le correspondant, et l'image en mode B / QAM16 ne passait pas alors que l'annonce hybride (mode E, robuste) passait. Les crêtes rares sont maintenant écrêtées en douceur : l'image passe avec 4 à 5 dB de bruit en plus au simulateur, et le signal reste lu à l'identique par le récepteur de QSSTV dans les 9 modes. Pensez à revérifier le niveau d'émission (ALC) en mode EasyPal.
- **Largeurs affichées comme dans EasyPal : 2,2 / 2,4 kHz** (QSSTV disait 2,3 / 2,5 ; c'est le même signal). Vos réglages sont convertis automatiquement.
- **Waterfall** : les repères de bande suivent la largeur réelle du mode EasyPal reçu ou émis (A, B ou E ; 2,2 ou 2,4 kHz), mesurée sur le signal.
- **Rx Ok en hybride EasyPal** : l'image déposée est maintenant reconnue comme la vôtre, et les stations HFImage qui la reçoivent apparaissent dans Rx Ok avec leur report.
- **Hybride EasyPal : mode E automatique** : en cochant « Mode hybride » en mode EasyPal, les réglages passent sur E / QAM4 (ceux de l'annonce, comme EasyPal) ; ils reviennent à leurs valeurs précédentes quand on décoche.

## Version 0.58 — panneau d'état en mode EasyPal

- **Panneau de gauche en réception EasyPal** : il affiche maintenant l'indicatif de la station, le S/B, le mode (« EP B/16 » = EasyPal mode B, QAM16), la largeur, le débit, le nombre de segments reçus et la progression, comme pour les modes DATAC. Les voyants Sync, Trame, Image et BSR suivent la réception EasyPal.
- Après la fin du signal, le panneau garde les dernières valeurs valides (mode, S/B) au lieu d'afficher le bruit.
- En émission EasyPal, la colonne TX indique aussi le mode, la largeur et le débit.

## Version 0.57 — indicatif des messages texte plus fiable

- **Messages texte** : la trame d'identification, qui porte l'indicatif de l'expéditeur, part maintenant **deux fois** à la fin du message. Avec un signal faible ou du QSB, le message passait souvent alors que cette unique trame était perdue, et la fenêtre « Message reçu » restait sur « (indicatif à venir) ». Au simulateur (QSB faible, 6 dB), l'indicatif manquait sur 7 messages sur 39 ; il ne manque plus que sur 1. Compatible avec les versions précédentes.
- Si l'indicatif n'arrive vraiment pas, la fenêtre affiche « (indicatif non reçu) » au bout de 30 s au lieu d'attendre indéfiniment.
- L'amélioration porte sur l'émission : elle profite pleinement quand l'expéditeur a aussi la version 0.57.

## Version 0.56 — correction des fermetures du programme en mode EasyPal

- **Correction de fermetures brutales du programme** dues au modem EasyPal (code repris de QSSTV), trouvées en faisant écouter au modem 40 minutes de bruit et de signaux abîmés sous un détecteur d'erreurs mémoire :
  - réception en **mode E** (donc aussi chaque **annonce hybride EasyPal**) : écriture en dehors d'un tableau ;
  - réception d'une image avec **Reed-Solomon** : mémoire libérée deux fois ;
  - envoi d'un **texte court avec Reed-Solomon** : écriture après la fin d'un tampon.
- Le signal émis est inchangé (identique à QSSTV, compatible EasyPal).

## Version 0.55 — mode EasyPal plus fiable

- Correction de plusieurs erreurs mémoire dans le modem EasyPal (hérité de QSSTV), qui pouvaient **fermer le programme sans message** sous Windows, notamment pendant la réception (indicatif de la station écrit un caractère trop loin) et à l'envoi de texte.
- Le décodage des paramètres EasyPal (FAC) utilise maintenant le bon motif de poinçonnage lors de son deuxième passage.
- Le signal émis est inchangé : toujours identique à celui de QSSTV, donc compatible EasyPal.

## Version 0.54 — envoi de texte en mode EasyPal

- **Envoi de texte en mode EasyPal** : le bouton d'envoi de texte fonctionne maintenant aussi en mode EasyPal. Le message part comme dans EasyPal et QSSTV (petit fichier texte en HamDRM, avec vos réglages EasyPal), accents compris.
- **Réception des messages texte d'EasyPal / QSSTV** : ils s'affichent dans la fenêtre des messages, comme les messages HFImage, au lieu d'arriver comme un fichier.

## Version 0.53 — mode hybride EasyPal

- **Mode hybride façon EasyPal / QSSTV** : en mode EasyPal, cochez « Mode hybride » comme d'habitude. L'image est déposée par FTP dans le dossier `HybridFiles1` de votre serveur, puis une courte annonce (~20 s, mode E / QAM4) part par radio. Les stations EasyPal, QSSTV et HFImage téléchargent alors l'image en pleine qualité.
- **Réception automatique des images hybrides EasyPal / QSSTV** : quand une station EasyPal émet en hybride, HFImage décode l'annonce et télécharge l'image tout seul (case « Télécharger automatiquement » de l'onglet Réglages). L'image arrive comme les autres, marquée « EasyPal-HYB ».
- La liste **Mode** reste disponible en mode hybride : « EasyPal » pour l'hybride façon EasyPal, les autres modes pour l'hybride HFImage habituel.
- En hybride EasyPal, l'image part en JPEG (EasyPal n'affiche ni AVIF, ni WebP).
- **Attention** : comme dans EasyPal, l'identifiant et le mot de passe FTP sont transmis dans l'annonce (simplement brouillés). Utilisez un **compte FTP dédié**, limité à un dossier. Ils ne doivent contenir ni accents ni caractères spéciaux.
- Les fichiers émis en mode EasyPal portent maintenant le nom de la photo.

## Version 0.52 — correction : blocage après une émission en mode EasyPal

- Correction : après une émission en mode EasyPal (terminée ou arrêtée), le waterfall et les boutons restaient bloqués. C'est réparé.
- Plus sûr pour tous les modes : une erreur dans une mise à jour de la fenêtre est maintenant notée dans le journal, sans plus jamais figer le programme.

## Version 0.51 — mode EasyPal (expérimental) : échange d'images avec EasyPal et QSSTV

- Nouveau mode **EasyPal** dans la liste des modes d'émission : HFImage parle maintenant le mode image d'**EasyPal** et de **QSSTV** (HamDRM : 2,3 ou 2,5 kHz, modes A / B / E, QAM 4 / 16 / 64). On peut envoyer des images aux stations qui utilisent encore EasyPal, et recevoir les leurs.
- **Réception automatique** : les images EasyPal sont décodées en même temps que les modes DATAC, sans rien régler. Elles arrivent dans la fenêtre RX et la galerie comme les autres, avec l'indicatif et le mode (ex. « EasyPal B/2.5/Hi/16/Long »).
- Réglages du mode EasyPal dans l'onglet TX : mode A / B / E, QAM, largeur, protection (HI / LO) et **Reed-Solomon** RS1 à RS4, comme dans EasyPal. Image en **JPEG 2000** (le format d'EasyPal), taille choisie pour tenir dans la durée demandée.
- **BSR / FIX** compatibles EasyPal : bouton BSR pour demander les segments manquants d'une image EasyPal incomplète ; quand une station EasyPal demande des segments de votre image, le bouton FIX les renvoie (ou automatiquement, comme pour les modes DATAC).
- Images EasyPal aussi décodées par « Décoder un fichier WAV » et « Relire RX ».
- Mode **expérimental** : il reprend le modem de QSSTV, compatible avec EasyPal, mais n'a pas encore été essayé sur l'air avec des stations EasyPal. Merci de signaler vos essais !

## Version 0.50 — taille du texte en points, séparateur Stations / Rx Ok

- Taille du texte en points : 8, 9 (normale), 10, 11, 12, 13, 14 (menu Réglages → Police et taille du texte, et Réglages → Apparence). Les anciens réglages sont convertis (Petite 8, Normale 9, Grande 11, Très grande 13).
- Séparateur réglable à la souris entre la liste Stations et la liste Rx Ok ; la position est gardée d'une session à l'autre (« Disposition d'origine des fenêtres » la remet par défaut).
- La barre de défilement de la liste Stations et la légende restent toujours visibles.

## Version 0.49 — texte en gras, taille dans le menu, « HYB » dans la liste des stations

- Nouveau menu **Réglages → Police et taille du texte** : « Texte en gras » et taille (Petite, Normale, Grande, Très grande), appliqués tout de suite à tout le programme. Case « Gras » aussi dans Réglages → Apparence. Le choix est gardé.
- Liste des stations : « F1ABL 7.058 HYB » (fréquence avec un point, puis HYB pour le mode hybride) ; légende « HYB = mode hybride ».

## Version 0.48 — carte : seulement les stations qui ont reçu l'image

- La carte des stations montre maintenant par défaut **seulement les stations qui ont reçu votre dernière image** (en vert, avec le trait depuis votre station) ; les stations simplement en ligne ou entendues n'y sont plus.
- Nouvelle case « Aussi les autres stations (en jaune) » pour les rajouter ; le choix est gardé.
- La carte se base sur votre dernière image émise, même si une image reçue entre-temps a changé la liste Rx Ok.
- « Coller la carte dans la fenêtre TX » envoie donc une carte avec uniquement les stations qui vous ont reçu.

## Version 0.47 — fréquence devant le H dans le panneau Stations

- La fréquence est maintenant toujours affichée devant le H (« F1BAL 14,230H »), sur la largeur d'origine de la liste.
- Une station en ligne qui ne publie pas sa fréquence (CAT non branché chez elle) montre la fréquence où on l'a entendue par radio, au lieu de « — ».

## Version 0.46 — les stations voient qui est en mode hybride

- La présence Internet indique maintenant si « Mode hybride » est coché ; c'est republié dès qu'on coche ou décoche.
- Panneau Stations : **H** et couleur bleue pour une station en mode hybride (présence Internet, ou annonce / image hybride entendue par radio dans la dernière demi-heure). Légende sous la liste : « * = en émission    H = mode hybride ».
- Le double-clic sur une station et la carte indiquent « en mode hybride (image par Internet) ».
- Les correspondants doivent avoir la version 0.46 pour voir votre mode hybride par Internet.

## Version 0.45 — passage hybride ↔ normal corrigé

- Le format est maintenant mémorisé séparément pour la radio et pour l'hybride : « original » choisi en hybride (photo pleine qualité, GIF animé) ne reste plus en radio, où une grosse photo demandait des heures et laissait l'aperçu vide.
- Le bouton « Répéter l'annonce » de l'hybride redevient « Compléter » en mode normal.
- Cocher ou décocher « Mode hybride » pendant une émission est pris en compte à la fin de l'émission : l'émission suivante part bien dans le mode coché.
- Une photo ouverte en radio après un SVG repasse en avif au lieu de rester en « original ».
- Message plus clair quand l'image n'est pas prête à émettre.

## Version 0.44 — version pour Windows 7 et 8

- Nouveau fichier **HFImage_F4GOP_Win7.exe** dans chaque version, pour **Windows 7 SP1 et Windows 8 (64 bits)**. La version normale (HFImage_F4GOP.exe, Windows 8.1 / 10 / 11) ne change pas.
- Même programme, compilé avec Python 3.8 et des bibliothèques compatibles ; la CRT universelle de Windows est embarquée.
- La version Windows 7 se met à jour toute seule avec HFImage_F4GOP_Win7.exe (jamais avec l'exe normal) ; Infos → À propos indique « (Windows 7 / 8) ».
- Seule différence : les images SVG reçues ne s'affichent pas (elles sont enregistrées).
- Chaque fabrication vérifie qu'aucune DLL n'appelle de fonction propre à Windows 8 ou plus récent, puis lance l'autotest.

## Version 0.43 — accusé de réception des messages

- Un message texte seul bien reçu est maintenant confirmé à l'émetteur, comme une image : ACK radio en DATAC0 (si « ACK auto » est coché) et confirmation par Internet (si le réseau est actif).
- Fenêtre Envoi texte : nouvelle liste **Messages envoyés — reçus par** : « ✓ F1BAL (+8 dB) 11:00 » en vert, « en attente de l'accusé… » en orange, « pas d'accusé de réception » en rouge après 3 minutes.
- Ligne verte « ✓ F1BAL a bien reçu votre message » dans le cadre Messages reçus et dans le journal des stations.
- La fenêtre Envoi texte reste ouverte après « Envoyer le texte seul » pour suivre l'accusé.
- Le texte joint à une image est confirmé avec l'image.

## Version 0.42 — heure de Windows dans tout le programme

- Toutes les heures affichées suivent maintenant l'heure de Windows (heure d'été comprise) : journal des stations, liste des stations entendues, messages, bandeau « Mes conditions de trafic », cartes QSL, Digi-Sites.
- Un clic sur l'horloge permet toujours de passer en UTC ; le choix vaut alors pour tout le programme (heures suivies de « UTC »).
- Le fichier stations.csv reste en UTC.

## Version 0.41 — horloge à l'heure de Windows

- L'horloge du programme affiche maintenant l'heure de Windows (heure locale, heure d'été comprise).
- Un clic sur l'horloge passe à « heure de Windows + UTC », puis « UTC seule » ; le choix est gardé.
- Les messages reçus sont horodatés à l'heure de Windows (avec l'UTC entre parenthèses dans la fenêtre Message reçu).
- Le journal des stations et les cartes QSL restent en UTC.

## Version 0.40 — fenêtre « Message reçu »

- Quand un correspondant envoie un message (texte seul ou joint à une image), une fenêtre s'ouvre au premier plan, avec un bip et le clignotement de la barre des tâches.
- Indicatif (complété dès que l'identification arrive), heure UTC, mode, SNR, texte en grand, vignette de l'image jointe.
- Flèches pour revoir les messages de la session ; boutons Répondre… (envoi de texte prérempli), Copier, Fermer.
- Options « Ouvrir à chaque message reçu » et « Bip » ; menu Action → Messages reçus…, ou double-clic dans le cadre des messages.

## Version 0.39 — police et couleurs du bandeau « Mes conditions de trafic »

- Choix de la police (toutes les polices installées sur Windows), gras, italique.
- Couleur du texte, couleur à part pour l'indicatif, couleur du contour (ou sans contour), couleur et opacité du fond, filet de couleur au bord du bandeau.
- Modèles tout prêts : classique, jaune et rouge, vert radio, noir sur blanc, sans fond.

## Version 0.38 — image du correspondant dans l'image TX

- Comme EasyPal, on peut répondre avec l'image reçue du correspondant incrustée dans la sienne, avec le report :
  - Galerie → clic droit → **Répondre avec cette image** ;
  - ou case **Image du correspondant** dans l'onglet TX, et bouton « … » pour choisir l'image reçue, le coin, la taille.
- Cadre blanc, ombre, légende « de F4EMK — +12 dB » (le SNR mesuré en recevant sa station ; affichage du report au choix).
- Se combine avec « Mes conditions de trafic ». Le report est maintenant aussi gardé dans la galerie.

## Version 0.37 — mes conditions de trafic sur l'image

- Case **Mes conditions de trafic** dans l'onglet TX (et bouton « … », ou menu Images → Mes conditions de trafic…) : un bandeau est incrusté sur l'image émise.
- Contenu au choix : indicatif, locator, QTH, poste (lu par CAT si le champ est vide), puissance, antenne, fréquence (CAT), date et heure UTC, texte libre.
- Position en bas ou en haut, trois tailles de texte, aperçu en direct. Le bandeau fait partie de l'image : visible chez tous les correspondants.

## Version 0.36 — ménage

- Vérification des commandes en double : aucune fonction définie deux fois ; les doublons restants sont voulus (même action dans un menu et sur un bouton, comme dans EasyPal).
- 4 traductions présentes deux fois supprimées (« Annonce hybride » avait même deux traductions allemandes différentes).
- Mode d'emploi : l'enregistrement d'une réception se fait par WAVE → « ● Enregistrer RX » (le bouton WAVE ouvre la fenêtre des fichiers WAV).

## Version 0.35 — image dans le waterfall

- Comme EasyPal, une **image** (photo, logo, carte QSL) peut être dessinée dans le waterfall du correspondant : Action → Texte waterfall… → bouton **Image…** (« Texte » pour revenir au texte).
- Niveaux de gris rendus en dB (comme l'affichent les waterfalls), contraste automatique, option Négatif ; 96 colonnes sur 400–2600 Hz, environ 12 à 16 s pour une image.
- « Émission » l'envoie tout de suite ; « Sauve » en fait un WAV, proposé comme **begin.wav** joué avant chaque émission.

## Version 0.34 — envoi de fichiers

- Bouton **Envoyer un fichier…** (onglet TX, et menu Images) : n'importe quel fichier (texte, PDF, ZIP, journal ADIF…).
  - Compressé automatiquement quand il y gagne (un texte de 29 ko part en 9 ko).
  - Même protection que les images : code fontaine, robustesse Auto, BSR / FIX, ACK et Rx Ok.
  - La taille et la durée d'émission sont annoncées avant d'émettre (conseil du mode hybride au-delà de 10 minutes).
  - Avec le **mode hybride** coché, le fichier passe par Internet et seul le lien passe par radio.
- À la réception : le fichier est rangé sous son nom d'origine dans le sous-dossier **fichiers** du dossier des images reçues, signalé dans « Messages reçus », et s'ouvre par un double-clic dans l'historique.
- Les deux stations doivent avoir la version 0.34 ou plus récente.
- Mode d'emploi complété.

## Version 0.33 — mode d'emploi à jour

- Mode d'emploi (Infos → Mode d'emploi) mis à jour : reports en vrais dB et plafonds (+15 dB DATAC3 / DATAC0, +21 dB DATAC1X / DATAC1), réglage Site web / Digi-Sites (dossier vide = racine, exemple qsl.net).

## Version 0.32 — Site web / Digi-Sites : réglage plus simple

- « Dossier sur le serveur » vide = **racine du site**, comme EasyPal (ex. qsl.net : dossier vide, lien https://www.qsl.net/indicatif).
- Si une adresse web est collée par erreur dans « Dossier sur le serveur », elle est déplacée dans « Lien public » et le dossier remis à la racine, avec un message pour vérifier.
- « Envoyer la page maintenant » demande le lien public s'il manque.

## Version 0.31 — reports plafonnés là où la mesure sature

- Sur un signal fort, l'estimation de SNR des modes étroits (DATAC3, et DATAC0 des BSR / ACK) sature : quelques dixièmes de dB d'écart donnaient des reports exagérés (jusqu'à +25 dB en mode hybride, dont l'annonce passe en DATAC3, alors que le même lien donnait +12 dB en DATAC1).
- Les reports sont maintenant plafonnés au dernier point fiable de chaque mode : **+15 dB** en DATAC3 / DATAC0 (= 15 dB ou plus), +21 dB en DATAC1X / DATAC1 / DATAC4.

## Version 0.30 — reports en vrais dB

L'estimation de SNR du modem codec2 est comprimée : un signal à 12 dB réels était affiché vers 8,5 dB en DATAC1X et vers 6 dB en DATAC3, et elle sature sur les bons signaux. Les reports n'étaient donc pas comparables d'un mode à l'autre et sous-estimaient les bonnes liaisons.

- Chaque mode est maintenant **étalonné** (mesures au simulateur : sans évanouissement, CCIR bon et moyen). Le panneau, les reports (ACK, Rx Ok, Internet), la carte QSL, l'historique des stations et l'analyseur donnent le **SNR réel sur 3 kHz**.
- Exemples : DATAC1X 8,5 dB estimés → 11,6 dB ; DATAC1 4 dB → 5,4 dB ; DATAC3 6 dB → 11,9 dB.
- Le mode Auto reprend des seuils en vrais dB : **DATAC1X dès 9 dB, DATAC1 dès 5 dB**, DATAC3 en dessous ; robustesse 15 % avec 4 dB de marge, 25 % avec 2 dB, sinon 40 %.
- Les stations encore en 0.29 ou avant envoient des reports plus bas (estimation brute) : le mode Auto reste prudent avec elles, le temps qu'elles se mettent à jour.
- Mode d'emploi mis à jour.

## Version 0.29 — mode d'emploi PDF

- Menu **Infos → Mode d'emploi (PDF)** : un guide de 13 pages, en français, avec captures d'écran :
  installation et mises à jour, premier réglage (station, audio, poste radio), réception, envoi d'images, mode Auto et robustesse, tableau des modes, stations en ligne et carte, mode hybride et Digi-Sites, bruit / QSB / QRM et analyseur, problèmes fréquents.
- Le PDF est aussi sur GitHub : `docs/HFImage_mode_emploi.pdf`.

## Version 0.28 — analyseur de réception, mode Auto mieux calé

- **Fichiers → Analyser un enregistrement WAV…** : on relit un enregistrement (bouton WAVE) et HFImage dit ce qui s'est passé :
  - niveau d'entrée (écrêtage, trop faible) ;
  - brouillage étroit (porteuse, CW, RTTY) : fréquence et part du temps ;
  - pour chaque mode : trames justes / perdues, SNR médian, mini / maxi, décalage de fréquence entre les postes ;
  - pertes groupées (QSB) ou isolées ;
  - ce que le coupe-QRM a sauvé (comparaison avec / sans) ;
  - le mode conseillé pour ce lien.
  Graphique du SNR de chaque trame (juste / perdue) avec les seuils des modes. « Copier le rapport » pour l'envoyer par message.
- **Mode Auto recalé** : le SNR affiché par le modem (reports, panneau) est une estimation qui sous-estime nettement les bons signaux (12 dB réels → environ 8,5 dB affichés). Les seuils du mode Auto sont maintenant exprimés dans cette même échelle : DATAC1X dès 6,5 dB affichés (au lieu de 10), DATAC1 dès 3,5 dB (au lieu de 5). Résultat : DATAC1X, donc des images plus nettes, est choisi beaucoup plus souvent quand le lien le permet.

## Version 0.27 — couleur du texte

- Réglages → Apparence → **Couleur du texte** : « Choisir… » pour prendre n'importe quelle couleur, « Couleur du thème » pour revenir à l'origine.
- La couleur s'applique aux textes de toutes les fenêtres (panneau, boutons, listes, journal, onglets, réglages) et se combine avec tous les thèmes, y compris Nuit. Les textes colorés exprès (alertes en rouge, textes blancs sur les bandeaux) gardent leur couleur.
- Après une mise à jour, l'explorateur Windows est prévenu : la nouvelle icône s'affiche sans redémarrer.

## Version 0.26 — nouvelle icône

- Nouvelle icône : une photo avec des ondes radio sur fond vert, et l'indicatif **F4GOP** sur les grandes tailles (bureau, explorateur). Les petites tailles (barre des tâches, barre de titre) gardent seulement le dessin, pour rester lisibles.
- L'icône apparaît sur l'exe, dans la barre de titre, la barre des tâches et toutes les fenêtres du programme.

## Version 0.25 — images en ligne sur votre site (Digi-Sites)

Comme EasyPal, HFImage peut mettre vos images en ligne sur votre site web, pour qu'elles apparaissent dans **Digi-Sites** et sur votre page.

- Menu **Images → Site web / Digi-Sites…** (ou bouton dans Réglages → Mode hybride).
- Chaque image reçue est envoyée par FTP sous le nom **image1.jpg** ; les précédentes glissent d'un cran (image2, image3… jusqu'au nombre choisi : 10, 20, 30 ou 50).
- Vos images émises vont dans **TX1.jpg … TX5.jpg** (option).
- Chaque image porte une étiquette : indicatif, date et heure UTC, mode, bande.
- Une page **hfimage.html** (rafraîchie toutes les 5 minutes) présente les images reçues et émises, et **list.txt** donne les 10 dernières stations.
- Liste d'indicatifs à ne pas mettre en ligne. Vos propres images entendues en retour ne sont pas publiées.
- Utilise le serveur FTP déjà réglé pour le mode hybride, dans un dossier à part (par défaut `dsstv`).
- Dans Digi-Sites : Setup → Edit site, et donnez l'adresse de la page (affichée dans la fenêtre).
- Envoi en tâche de fond : la réception n'est jamais ralentie ; en cas de coupure Internet, l'erreur est notée dans le journal.

## Version 0.24 — images à nouveau nettes en mode Auto

En 0.22/0.23, sans report, le mode Auto prenait DATAC1 avec 40 % de redondance : l'image était deux fois plus petite qu'avant (environ 8 ko au lieu de 16 ko en 2 minutes), donc nettement moins nette.

- Sans report, le mode Auto reprend **DATAC1X**, le mode rapide des images nettes. Il ne descend en DATAC1 ou DATAC3 que si les reports des stations sont faibles.
- Nouvelle robustesse **« Auto (selon les reports) »**, par défaut : la redondance s'adapte à la marge entre le report le plus faible et le seuil du mode :
  - lien confortable (4 dB de marge ou plus) ou pas de report : 15 % ;
  - lien juste (2 à 4 dB de marge) : 25 % ;
  - lien à la limite : 40 %.
- Exemple en 2 minutes (photo 800×600, aperçu rapide compris) : sans report ou à +16 dB, 12,9 ko (q38) au lieu de 8,4 ko en 0.23 ; à +11 dB, 10,1 ko avec 40 % de redondance.
- Les réglages fixes (Faible, Normale, Forte, Très forte) restent disponibles.

## Version 0.23 — coupe-QRM à la réception

Constat au simulateur : une simple porteuse (CW, « birdie ») aussi forte que le signal, du RTTY dans la bande, ou une BLU forte juste à côté faisaient perdre **toutes** les trames, quel que soit le mode.

- Nouveau **coupe-QRM** devant chaque démodulateur (Réglages → Audio, activé par défaut) :
  - tout ce qui est hors de la bande du mode est effacé (BLU voisine, signaux forts à côté) ;
  - dans la bande, les raies qui dépassent le signal OFDM de plus de 10 dB sont effacées (porteuses, CW, RTTY). Les porteuses touchées deviennent des « trous » que le code correcteur répare.
- Mesures (SNR 12 dB, 24 trames) : porteuse +15 dB 0 % → 88-100 % ; BLU voisine +20 dB 0 % → 88-96 % ; CW +10 dB 0 % → 70-90 % ; RTTY +6 dB 0 % → 60-70 %. Sans QRM, quasiment aucune perte.
- Fonctionne avec toutes les versions de l'émetteur (rien ne change à l'émission). Peu gourmand (~2 % d'un processeur).

## Version 0.22 — meilleure tenue au bruit et au QSB

Mesures au simulateur (évanouissement « moyen ») : DATAC1X a besoin d'environ 9-10 dB, DATAC1 de 5 dB, DATAC3 tient vers 0 dB. Avec seulement 10 % de redondance, une image ne passait pas en une fois dès que le QSB faisait perdre plus d'une trame sur dix.

- **Mode « Auto »** (nouveau réglage par défaut) : le mode est choisi d'après le **report le plus faible** des stations qui ont reçu vos images ces 45 dernières minutes (Rx Ok) :
  - 10 dB et plus : DATAC1X (rapide) ;
  - de 5 à 10 dB : DATAC1 ;
  - moins de 5 dB : DATAC3.
  Sans report, HFImage prend le SNR des stations entendues, sinon DATAC1. Le choix et sa raison sont affichés sous l'image (« Mode Auto → DATAC1 (report le plus faible +7 dB) »). Si les reports changent avant l'émission, l'image est refaite pour le bon mode.
- **Robustesse** (remplace « Redondance % ») : Faible 15 %, **Normale 40 %** (défaut), Forte 70 %, Très forte 100 %. Plus de trames de secours : l'image passe en un seul coup malgré le QSB, un peu moins détaillée pour la même durée.
- Les anciens réglages DATAC1X et 10 % passent automatiquement en Auto et Normale (40 %). On peut toujours choisir un mode fixe.

## Version 0.21 — poste radio comme WSJT-X

Nouvelle fenêtre **Réglages → Poste radio…** (aussi dans le menu Réglages), sur le modèle de l'onglet Radio de WSJT-X :

- **Liste de tous les postes connus** : plus de 300 modèles (Icom, Yaesu, Kenwood, Elecraft, Xiegu, FlexRadio, Ten-Tec…), avec une case de recherche.
- Liaisons possibles :
  - **Kenwood en direct** (TS-990S, TS-890S, TS-590, TS-2000, TS-480 : rien à installer) ;
  - **Hamlib** pour tous les autres postes. HFImage lance Hamlib (`rigctld`) en arrière-plan. Hamlib 4.6.5 est téléchargé une seule fois depuis GitHub (3 Mo, empreinte SHA-256 vérifiée) avec le bouton « Installer Hamlib ». Celui de WSJT-X ou de JTDX est utilisé s'il est déjà là ;
  - **OmniRig** (Rig 1 / Rig 2), pour partager le poste avec d'autres logiciels ;
  - **FLRig** ;
  - **Hamlib NET rigctl** (serveur rigctld déjà lancé) ;
  - **Aucun** (pas de CAT).
- **Port série complet** : vitesse, bits de données, bits de stop, contrôle de flux (aucun, XON/XOFF, matériel), DTR / RTS forcés.
- **PTT** : VOX, CAT, DTR ou RTS. DTR / RTS peuvent être sur un **autre port COM** (interface à côté du poste).
- **Source audio en émission** : arrière / data (audio USB, ACC) ou avant / micro. Pour les Kenwood, cela remplace la commande `TX1;` / `TX0;`.
- **Mode** mis par CAT avant chaque émission : Aucun, USB ou Data / Pkt.
- **Intervalle d'interrogation** du poste (fréquence et mode).
- Boutons **Tester le CAT** et **Tester le PTT** : vert si ça marche, rouge sinon, avec le message d'erreur.
- Les réglages des versions précédentes (Kenwood, PTT CAT / RTS / DTR) sont repris automatiquement.

Nouvel onglet **Galerie** (comme « 30 dernières Rx / TX » d'EZPix) :

- mosaïque des **dernières images reçues** (« de F4EMK ») et des **dernières images envoyées** (30, 60 ou 100) ;
- clic : l'image s'affiche dans l'onglet RX ; double-clic : plein format ; clic droit : renvoyer l'image (onglet TX), voir la station sur la carte, ouvrir le dossier, retirer de la galerie ;
- les images reçues avant cette version sont reprises automatiquement ; les images envoyées sont gardées dans le sous-dossier `envoyees`.

Mise à jour automatique : HFImage revérifie GitHub toutes les 3 heures quand il reste ouvert, et note dans le journal si la vérification échoue (pare-feu, antivirus, pas d'Internet).

## Version 0.20 — mise à jour automatique

- Au démarrage, HFImage regarde sur GitHub (page « Releases » du projet) s'il existe une version plus récente.
- Si oui, un **bandeau orange** apparaît en haut de la fenêtre : « Nouvelle version … disponible — cliquez ici pour mettre à jour ».
- Au clic :
  - affichage des nouveautés et confirmation ;
  - téléchargement avec progression dans le bandeau ;
  - **vérification de la taille et de l'empreinte SHA-256** (un fichier abîmé est refusé, l'exe en place n'est pas touché) ;
  - remplacement de l'exe et **redémarrage automatique**. L'ancien exe est effacé au démarrage suivant.
- Le ✕ ferme le bandeau pour la session. Menu Infos → « Rechercher une mise à jour » et « Page du programme sur GitHub ».
- Réglages → Internet : case « Vérifier les mises à jour au démarrage (GitHub) ».
- Seuls les fichiers publiés dans les Releases de `f4gopdenis-cyber/HFImage_F4GOP` sont acceptés.
- Lancé depuis les sources Python, le bandeau ouvre simplement la page de la nouvelle version.

## Version 0.19 — message « poste pas en mode DATA »

Avec la commande PTT **TX1;** (DATA SEND), un Kenwood n'émet l'audio USB qu'en mode DATA : HFImage vérifie le mode avant d'émettre. Le message ne revient plus à chaque émission :

- **Trois choix** :
  - **Passer en USB-DATA et émettre** : le programme met le poste en USB-DATA1 par CAT et relit le mode pour vérifier (TS-990 : `OM0D;` ; TS-890 : `OM02;` + `DA1;` ; autres Kenwood : `MD2;` + `DA1;`) ;
  - **Émettre quand même** ;
  - **Annuler**.
- Case **« Ne plus me demander »** : le choix est retenu.
- Réglages → PTT → « Poste pas en DATA avant d'émettre » (Demander / Passer en USB-DATA automatiquement / Émettre sans rien dire) pour changer ce choix.
- Poste réglé pour émettre l'audio USB **sans** le mode DATA : choisissez la commande **TX0;**. La vérification n'est alors plus faite.

## Version 0.18 — style de la carte QSL

Dans la fenêtre **Carte QSL** (bouton IMG/QSL), nouvelle partie « Style de la carte », avec un **aperçu en direct** à droite :

- **Police** : Arial, Arial Black, Segoe UI, Verdana, Tahoma, Trebuchet MS, Georgia, Times New Roman, Impact, Comic Sans MS, Courier New, Consolas.
- **Couleurs**, chacune à cliquer pour ouvrir le nuancier : indicatif, texte, locator / correspondant, bandeaux.
- **Taille de l'indicatif** et **opacité des bandeaux** (de transparent à opaque), réglées par curseur.
- « Style d'origine » pour revenir au style de départ.
- Le style choisi est gardé pour les cartes suivantes.

## Version 0.17 — couleurs et police au choix

Réglages → **Apparence**. Les changements s'appliquent tout de suite, sans redémarrer, et sont gardés pour la prochaine ouverture.

- **Couleurs** :
  - thèmes Vert EasyPal (d'origine), Bleu, Gris, Sable, Bordeaux, Violet ;
  - **Nuit** : fond sombre et texte clair, moins éblouissant pour le trafic de nuit. L'image et le waterfall restent sur fond noir ;
  - **Couleur personnalisée…** : n'importe quelle couleur, choisie dans le nuancier Windows ; toutes les nuances du programme en sont dérivées.
- **Police** : celle de Windows par défaut, ou Segoe UI, Arial, Tahoma, Verdana, Calibri, Trebuchet MS, Times New Roman, Georgia, Consolas, Courier New. Seules les polices présentes sur le PC sont proposées.
- **Taille** : Petite, Normale, Grande, Très grande. Avec une police plus grande, la colonne de gauche s'élargit d'elle-même pour que les boutons restent lisibles.
- Les listes Stations / Rx Ok gardent une police à chasse fixe, pour que les colonnes restent alignées.

## Version 0.16 — fenêtre et zones réglables

- La fenêtre principale s'agrandit, se réduit (jusqu'à 900×600) ou se met en plein écran.
- **Séparateurs à faire glisser à la souris**, comme dans EasyPal :
  - entre la colonne verte de gauche et l'image ;
  - entre le waterfall et les listes Stations / Rx Ok ;
  - entre l'image reçue et la colonne Historique / Messages ;
  - entre l'Historique et les Messages ;
  - au-dessus du journal.
- Le waterfall, le panneau et les listes suivent la taille choisie.
- La taille de la fenêtre et des zones est **retrouvée à la prochaine ouverture**, y compris le plein écran.
- Réglages → « Disposition d'origine des fenêtres » pour revenir à la présentation de départ.

## Version 0.15 — reports visibles aussi en réception (Rx Ok comme EasyPal)

- La liste **Rx Ok** montre les stations qui ont reçu **l'image en cours**, avec leur report, **chez toutes les stations** :
  - chez l'émetteur : les reports en dB de tous ceux qui ont reçu son image (par Internet et par ACK radio) ;
  - chez une station qui reçoit : **son propre report**, plus ceux des autres stations qui ont reçu la même image.
- Les confirmations sont diffusées à toutes les stations en ligne ; chacune les classe d'après le numéro de l'image. Ça marche même si l'indicatif de l'émetteur n'est pas encore arrivé.
- La liste repart à zéro à chaque nouvelle image émise ou reçue.
- Compatible avec la 0.14 côté émetteur. Pour voir les reports en réception, il faut la 0.15.

## Version 0.14 — stations en ligne par Internet (comme EasyPal)

- **Dès l'ouverture du programme**, chaque HFImage se signale sur Internet avec son indicatif, son locator et sa fréquence (lue par CAT). Toutes les stations qui ont HFImage ouvert apparaissent aussitôt dans la liste « Stations », avec leur fréquence, sans rien émettre par radio.
- Une station en train d'émettre est affichée **en rouge avec une « * »**. À la fermeture du programme, elle disparaît de la liste (même en cas de plantage, au bout de quelques minutes au plus).
- Les stations seulement entendues par radio restent dans la liste, en gris-vert.
- **Rx Ok par Internet** : quand une station a reçu votre image, elle vous le confirme aussi par Internet, avec son report. La liste Rx Ok se remplit même si l'ACK radio est perdu, et même si la trame d'identification n'est pas arrivée chez elle : l'image est reconnue à son numéro.
- La carte des stations montre aussi toutes les stations en ligne, avec leur locator.
- Le serveur est un serveur **MQTT public** (`broker.hivemq.com`, port 1883), sans inscription ni mot de passe :
  - seuls l'indicatif, le locator, la fréquence et l'état réception/émission sont partagés ;
  - réglages : Réglages → « Internet : stations en ligne » (activer/désactiver, serveur, port, état de la connexion) ;
  - si un pare-feu bloque le port 1883 : 8883 (chiffré) ou 8000 (web) ;
  - **toutes les stations doivent utiliser le même serveur** (et la version 0.14).
- L'autotest (`--selftest`) indique si le serveur de présence est joignable depuis votre PC.

## Version 0.13 — carte des stations (façon « Digi-Sites » d'EasyPal)

- **Double-clic sur une station** dans les listes « Stations » ou « Rx Ok » : la carte s'ouvre, centrée sur vous et sur elle. Accès aussi par le menu Action → « Carte des stations… » ou un clic droit sur les listes.
- **Votre station** : étiquette blanche, placée d'après le locator des Réglages.
- **Stations qui ont reçu votre image** : étiquettes vertes, reliées à vous par un trait (arc de grand cercle).
- **Stations seulement entendues** : étiquettes jaunes. Case « Stations entendues aussi » pour les afficher ou non.
- Clic sur une station : locator, distance, azimut, report, heure et fréquence, en bas de la fenêtre.
- Vues : Toutes les stations, Europe, France, Monde, Amérique du Nord, Atlantique Nord, Asie, Océanie.
- Bouton gauche maintenu pour déplacer la carte, molette pour zoomer.
- **« Coller la carte dans la fenêtre TX »** : la carte devient l'image à émettre, comme dans EasyPal.
- **Positions des stations** :
  - l'ACK transporte maintenant le carré de locator (4 caractères), la trame d'identification de fin d'image et la présence QRV le locator complet ;
  - les locators reçus sont gardés d'une session à l'autre (`Documents\HFImage\locators.json`).
- Fond de carte dessiné par le programme à partir de **Natural Earth** (domaine public) : pays, frontières, lacs, villes, méridiens. Fichier `carte.bin` de 144 Ko, généré par `build_map.py`.

## Version 0.12 — listes « Stations » et « Rx Ok » (façon EasyPal)

En bas de la colonne verte de gauche, toujours visibles :

- **Stations (n) - fréquence** : les stations entendues qui utilisent HFImage, avec la fréquence du poste au moment où on les a entendues (lue par CAT, sinon « — »).
  - Elles sont repérées à chaque image, annonce hybride, BSR, ACK ou présence reçus.
  - Classement alphabétique ; en vert vif si entendue depuis moins de 2 min, en gris après 30 min ; retirée au bout de 2 h.
  - Double-clic : détails dans le journal (locator, heure, SNR, dernier événement).
- **Rx Ok (n)** : les stations qui ont bien reçu **votre** image, avec leur **report** (SNR mesuré chez elles). La liste repart à zéro à chaque nouvelle image.
- L'**ACK** automatique contient maintenant le report du correspondant. Il est aussi envoyé après une image **hybride** téléchargée, une fois l'annonce terminée.
- Nouvelle trame de **présence (QRV)**, environ 2 s en DATAC0 : indicatif + locator, pour apparaître dans les listes des autres sans envoyer d'image. Menu Action → « Signaler ma présence (QRV) », ou clic droit sur les listes.
- Toutes les stations doivent avoir la 0.12 pour le report dans l'ACK et la présence QRV. Les versions précédentes reçoivent toujours les images.

## Version 0.11 — GIF animés en hybride, format png retiré

- **Formats** : avif, webp, **jpg**, original. Le png a été retiré de la liste ; une ancienne configuration en png repasse en avif.
- **GIF animés en mode hybride** :
  - ouvrez un .gif animé et cochez « Mode hybride » : le GIF est déposé tel quel sur votre serveur, l'animation est conservée ;
  - seul le lien passe par radio (annonce DATAC3 d'environ 11 s) ;
  - réglage « GIF animé : taille max (ko) » (2000 par défaut, onglet Réglages → Hybride). Un GIF plus lourd est réduit automatiquement en gardant l'animation : moins de couleurs, plus petit, puis une image sur deux si besoin ;
  - l'animation est jouée dans l'aperçu d'émission, et chez le correspondant dans la fenêtre de réception et dans l'historique ;
  - un double-clic ouvre le .gif dans la visionneuse Windows ;
  - sans le mode hybride, seule la première image du GIF part par radio (le journal le signale).

## Version 0.10 — images nettes en un temps raisonnable (façon EasyPal)

- **Nouveau mode DATAC1X (rapide)**, ajouté à libcodec2 (`hfi_modes.c`) :
  - même structure que DATAC1 (QPSK, pilotes, rafales), mais 35 porteuses (2,2 kHz de large, comme EasyPal) et un code LDPC long DVB-S2 de rendement 0,6 ;
  - **1 420 bit/s utiles, 1,6 × DATAC1** ;
  - sur canal simulé : 100 % des trames reçues dès 9 dB (évanouissements « good ») et dès 12 dB (« moderate ») ; environ 3 dB de plus que DATAC1 ;
  - quand les conditions sont mauvaises, revenir à DATAC1. La réception écoute tous les modes à la fois.
- **Nouveaux réglages par défaut : DATAC1X, 2 min.**
  - Une photo arrive en 800×600 nette, environ 13 Ko avec l'aperçu, 16 Ko sans.
  - Avant : DATAC1, 60 s, soit 480×360 en 4 Ko.
  - Une ancienne configuration restée sur DATAC1 / 60 s passe automatiquement aux nouveaux réglages.
- **Formats** : avif, webp, **jpg**, original.
- Recherche plus fine de la qualité : le temps d'émission est mieux rempli.
- **Important** : les deux stations doivent avoir la version 0.10 pour le mode DATAC1X.

## Version 0.9 — JPEG / JPG et SVG

- **Ouvrir** accepte JPG / JPEG, PNG, **SVG / SVGZ**, GIF, WEBP, AVIF, BMP, TIFF.
- **Format d'émission** (onglet TX) :
  - **avif** : le plus compact, idéal en HF ;
  - **webp** ;
  - **jpeg** : lisible partout, mais demande nettement plus d'octets que l'AVIF pour la même image ;
  - **original** : le fichier part **tel quel**, sans recompression. Un JPG reste un .jpg identique octet pour octet chez le correspondant.
- **SVG** :
  - le dessin vectoriel est envoyé en texte, nettoyé et compressé (souvent quelques centaines d'octets : une carte QSL simple ≈ 490 octets, 25 s en DATAC3) ;
  - la station qui reçoit enregistre le .svg et l'affiche redessiné en 1280 px, net ;
  - à l'ouverture d'un SVG, le format « original » est choisi automatiquement. On peut aussi l'envoyer converti en avif / jpeg.
- En **hybride**, le SVG est déposé en clair sur le serveur, lisible directement dans un navigateur.
- Le fond de la carte QSL peut être un SVG.
- Fichiers reçus : la bonne extension (.jpg, .svg, .png…), plus un .png pour l'affichage.

## Version 0.8 — texte dans le waterfall, begin.wav / end.wav

- Le bouton **WAVE** ouvre la fenêtre **Lire fichier Wave**. Elle liste les WAV du dossier `Documents\HFImage\wav` et propose :
  - Mettre comme / Retirer « begin.wav » et « end.wav » ;
  - ÉMISSION, SORTIE, Effacer, Renommer, Importer, Dossier ;
  - Enregistrer RX.
- **begin.wav** part avant chaque émission (image, texte, hybride). **end.wav** part après. Ni l'un ni l'autre n'est envoyé avec les FIX.
- La fenêtre **Texte waterfall** (bouton dans WAVE, ou menu Action) contient :
  - le texte sur plusieurs lignes et un aperçu de ce qui s'affichera chez le correspondant ;
  - Wav Volume, la fonte et Négatif ;
  - **Émission** (envoi direct) et **Sauve**, qui enregistre le WAV et propose de le mettre comme begin.wav.
- Le texte occupe 400–2600 Hz, soit toute la bande SSB utile. Une ligne de pixels dure 0,2 s, ce qui donne des lettres hautes ; « F4GOP / IN98QR » dure environ 8 s.
- Pour qu'il soit bien visible chez le correspondant, chaque pixel a une puissance constante. Le signal est légèrement écrêté (+3 à +4 dB de puissance moyenne), puis filtré : rien ne sort de la bande.
- Un begin.wav fait avec une version précédente doit être refait : Texte waterfall → Sauve.

## Version 0.7 — langues, fréquence du poste, report QSL

- **Langues** : français, English, Deutsch, Español, Italiano (Réglages → Station →
  « Langue / Language »). Changement immédiat, sans redémarrer ; au premier lancement, la
  langue de Windows est prise. Menus, boutons, panneau, messages du journal, fenêtres et
  carte QSL sont traduits.
- **Fréquence du poste** (lecture CAT `FA;` chaque seconde, mode par `SF0;`/`OM0;`) : affichée
  en haut du panneau (ex. 14.233.000, USB-DATA1 · 20 m) et dans la barre d'état ; notée dans
  le journal des stations. Case « Afficher la fréquence du poste (CAT) » dans Réglages → PTT.
  La même liaison sert au PTT : le port COM n'est ouvert qu'une fois.
- **Carte QSL** : le report est rempli automatiquement avec le SNR mesuré sur la dernière
  image reçue de la station (« SNR -4 dB »), la fréquence avec celle du poste ; changer
  l'indicatif du correspondant met le report à jour.

## Version 0.6 — disposition façon EasyPal

- **Barre de menus** : Réglages, Hybride, Action, Images, Fichiers, Effacer, Infos.
- **Colonne verte à gauche** : panneau d'état (indicatif, RX/SNR, TX/RX, voyants), grille de
  boutons (ÉMISSION/STOP, Relire RX, FIX, BSR, Accord, ID, Envoi Texte, WAVE, Écoute,
  Txt inclus, Log Station, IMG/QSL, Image…, Hybride, Réglages, Dossier), puis spectre et
  waterfall sur toute la hauteur.
- **À droite** : onglets **RX** (dernière image en grand, historique, messages) et **TX**
  (réglages d'émission sur deux lignes, image à émettre en grand, infos et boutons en bas),
  **Stations**, **Simulation** ; journal et barre d'état avec l'heure UTC en bas.
- **Réglages** (station, audio, PTT, serveur hybride, dossier) dans une fenêtre séparée ;
  **Envoi Texte** aussi.
- L'écoute démarre toute seule au lancement si l'entrée audio est réglée ; l'onglet RX
  s'affiche à chaque image reçue, l'onglet TX pendant une émission.

## Version 0.5 — fonctions façon EasyPal

### Grand format
- Largeur jusqu'à **1920 px** (ou « originale »), durée max jusqu'à **60 min** ; en « auto »,
  le programme prend la plus grande largeur qui garde une qualité correcte (q ≥ 30).
- Si la qualité est faible, il indique la durée nécessaire pour une bonne qualité à cette taille.
- **Aperçu rapide d'abord** (émissions de plus de 2 min) : une petite image (~1 ko) part en
  premier, les autres la voient au bout de ~20 s en DATAC1, puis l'image complète la remplace.
- Ordres de grandeur DATAC1 : 20 ko ≈ 4 min, 60 ko ≈ 10 min, 200 ko ≈ 33 min. En **hybride**,
  la taille ne compte plus (jusqu'à 2560 px / 5 Mo) : annonce radio de 11 s.
- Émission en flux : le son est fabriqué au fur et à mesure (pas des centaines de Mo en mémoire).
- Double-clic sur une image reçue : ouverture en plein format.

### BSR / FIX / ACK (onglet Stations)
- En réception, si une image est incomplète quand l'émetteur a fini, un **BSR** part
  automatiquement en DATAC0 (~2 s) avec le nombre de symboles manquants.
- L'émetteur (qui se remet à l'écoute après chaque émission) répond par un **FIX** :
  seulement des symboles nouveaux, utiles à toutes les stations (il regroupe les BSR reçus
  pendant 5 s et envoie le maximum demandé).
- Image complète → **ACK** : l'émetteur voit qui a reçu.
- Chaque automatisme se désactive (cases de l'onglet Stations) ; boutons **BSR** (Réception) et
  **FIX** (Stations) pour le faire à la main. Délai aléatoire avant BSR/ACK pour éviter les collisions.
- Journal des stations (heure UTC, indicatif, événement, mode, SNR) à l'écran et dans
  `Documents\HFImage\stations.csv`.

### Panneau d'état (onglet Réception)
Indicatif reçu, barres **RX** (dBFS) et **SNR**, colonnes **TX / RX** (mode, bande, débit, total,
segments OK, position), voyants **Signal / Sync / Trame / Image / BSR**.

### Texte
- **Envoyer le texte seul** : message court (~10 s en DATAC3), affiché dans « Messages reçus ».
- **Texte inclus avec l'image** : le texte voyage dans le même fichier que l'image.
- Les messages sont aussi enregistrés en `.txt` dans le dossier des images.

### Outils station
- **Accord (10 s)** : porteuse 1500 Hz à la crête du signal modem, pour régler l'ALC.
- **ID morse** (bouton, ou case « en fin d'émission ») : « DE indicatif » à 20 mots/min sur 1500 Hz.
- **● WAVE** : enregistre le son reçu (8 kHz) dans `Documents\HFImage\enregistrements`.
- **Relire RX** : redécode les 15 dernières minutes reçues (résultats dans « relecture »).
- **Carte QSL…** : carte 960×600 (photo de fond ou dégradé, indicatif, locator, correspondant,
  date UTC, fréquence, report, message), prête à émettre. Renseignez le **Locator** en haut.

### Essais réalisés
Deux stations réelles sous Windows (cartes son virtuelles) : image DATAC3 avec 2 trames perdues
→ BSR auto → FIX auto de 4 à 7 symboles → image + texte reçus → ACK reçu par l'émetteur.
Image DATAC1 de 4 min avec aperçu : aperçu à 20 s, image complète, ACK.


## Versions 0.1 à 0.4

- Prototype : modem OFDM codec2 (DATAC1 / DATAC3 / DATAC4), code fontaine GF(256), images AVIF / WebP, réception multi-modes.
- Exécutable Windows unique (PyInstaller).
- Sortie son fiable sur les codecs USB des Kenwood (lecture en mode « callback », repli MME → WASAPI → DirectSound).
- Waterfall.
- Mode hybride : image par FTP sur son hébergement web, seul le lien passe par radio.
