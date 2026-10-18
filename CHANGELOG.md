# Historique des versions — HFImage F4GOP

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
