# Historique des versions — HFImage F4GOP

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
