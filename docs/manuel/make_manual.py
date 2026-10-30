"""Mode d'emploi HFImage F4GOP (PDF)."""
import io
import os
import sys

from PIL import Image as PImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

D = os.path.dirname(os.path.abspath(__file__))
VERSION = sys.argv[1] if len(sys.argv) > 1 else "0.29"
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(D, "HFImage_mode_emploi.pdf")

F = "/usr/share/fonts/truetype/dejavu/"
pdfmetrics.registerFont(TTFont("DV", F + "DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DVB", F + "DejaVuSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("DVI", F + "DejaVuSans-Oblique.ttf"))
pdfmetrics.registerFont(TTFont("DVM", F + "DejaVuSansMono.ttf"))
from reportlab.pdfbase.pdfmetrics import registerFontFamily
registerFontFamily("DV", normal="DV", bold="DVB", italic="DVI", boldItalic="DVB")

GREEN = colors.HexColor("#1c8f1c")
DARK = colors.HexColor("#0d3b0d")
LIGHT = colors.HexColor("#e9f7e9")
GREY = colors.HexColor("#555555")

st = {
    "body": ParagraphStyle("body", fontName="DV", fontSize=10, leading=14.5, spaceAfter=5),
    "small": ParagraphStyle("small", fontName="DV", fontSize=8.5, leading=11, textColor=GREY),
    "cap": ParagraphStyle("cap", fontName="DVI", fontSize=8.5, leading=11, textColor=GREY, alignment=TA_CENTER,
                          spaceAfter=10),
    "h1": ParagraphStyle("h1", fontName="DVB", fontSize=17, leading=21, textColor=DARK, spaceBefore=4,
                         spaceAfter=8),
    "h2": ParagraphStyle("h2", fontName="DVB", fontSize=12.5, leading=16, textColor=GREEN, spaceBefore=10,
                         spaceAfter=4),
    "bul": ParagraphStyle("bul", fontName="DV", fontSize=10, leading=14, leftIndent=14, bulletIndent=3,
                          spaceAfter=2),
    "num": ParagraphStyle("num", fontName="DV", fontSize=10, leading=14, leftIndent=18, bulletIndent=2,
                          spaceAfter=2),
    "cell": ParagraphStyle("cell", fontName="DV", fontSize=9, leading=12),
    "cellb": ParagraphStyle("cellb", fontName="DVB", fontSize=9, leading=12, textColor=colors.white),
    "tip": ParagraphStyle("tip", fontName="DV", fontSize=9.5, leading=13.5),
}


class Doc(SimpleDocTemplate):
    def afterFlowable(self, f):
        if isinstance(f, Paragraph) and f.style.name == "h1":
            self.notify("TOCEntry", (0, f.getPlainText(), self.page))
        elif isinstance(f, Paragraph) and f.style.name == "h2":
            self.notify("TOCEntry", (1, f.getPlainText(), self.page))


def P(t, s="body"):
    return Paragraph(t, st[s])


def B(items):
    return [Paragraph(i, st["bul"], bulletText="•") for i in items]


def N(items):
    return [Paragraph(i, st["num"], bulletText=f"{k}.") for k, i in enumerate(items, 1)]


def img(name, width_mm, caption=None):
    p = next((q for q in (os.path.join(D, name), os.path.join(D, "..", "images", name),
               os.path.join(D, "..", "manual_en", name)) if os.path.exists(q)), os.path.join(D, name))
    im = PImage.open(p).convert("RGB")
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=82, optimize=True)
    buf.seek(0)
    w = width_mm * mm
    h = w * im.height / im.width
    out = [Image(buf, width=w, height=h)]
    if caption:
        out.append(Paragraph(caption, st["cap"]))
    return KeepTogether(out)


def table(rows, widths, head=True):
    data = [[Paragraph(str(c), st["cellb"] if (head and r == 0) else st["cell"]) for c in row]
            for r, row in enumerate(rows)]
    t = Table(data, colWidths=[w * mm for w in widths], repeatRows=1 if head else 0)
    style = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#b8d8b8")),
             ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if head:
        style += [("BACKGROUND", (0, 0), (-1, 0), GREEN)]
        for r in range(1, len(rows)):
            if r % 2 == 0:
                style.append(("BACKGROUND", (0, r), (-1, r), LIGHT))
    t.setStyle(TableStyle(style))
    return t


def tip(text, title="Conseil"):
    t = Table([[Paragraph(f"<b>{title} :</b> {text}", st["tip"])]], colWidths=[170 * mm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), LIGHT),
                           ("BOX", (0, 0), (-1, -1), 0.8, GREEN),
                           ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                           ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    return [Spacer(1, 4), t, Spacer(1, 6)]


def page_deco(c, doc):
    c.saveState()
    w, h = A4
    if doc.page > 1:
        c.setStrokeColor(GREEN)
        c.setLineWidth(1.2)
        c.line(20 * mm, h - 14 * mm, w - 20 * mm, h - 14 * mm)
        c.setFont("DV", 8)
        c.setFillColor(GREY)
        c.drawString(20 * mm, h - 12 * mm, f"HFImage F4GOP {VERSION} — mode d'emploi")
        c.drawRightString(w - 20 * mm, 10 * mm, f"{doc.page}")
        c.drawString(20 * mm, 10 * mm, "github.com/f4gopdenis-cyber/HFImage_F4GOP")
    c.restoreState()


def cover(c, doc):
    w, h = A4
    c.saveState()
    c.setFillColor(DARK)
    c.rect(0, h - 120 * mm, w, 120 * mm, fill=1, stroke=0)
    c.drawImage(next(q for q in (os.path.join(D, "icone.png"), os.path.join(D, "..", "images", "icone.png")) if os.path.exists(q)), w / 2 - 32 * mm, h - 92 * mm, 64 * mm, 64 * mm, mask="auto")
    c.setFillColor(colors.white)
    c.setFont("DVB", 30)
    c.drawCentredString(w / 2, h - 108 * mm, "HFImage F4GOP")
    c.setFillColor(DARK)
    c.setFont("DVB", 20)
    c.drawCentredString(w / 2, h - 140 * mm, "Mode d'emploi")
    c.setFont("DV", 12)
    c.setFillColor(GREY)
    c.drawCentredString(w / 2, h - 150 * mm, "Images numériques en HF — modes HFImage et EasyPal / QSSTV (HamDRM)")
    c.drawCentredString(w / 2, h - 158 * mm, f"Version {VERSION}")
    c.setFont("DV", 10)
    c.drawCentredString(w / 2, 30 * mm, "F4GOP — Denis — IN98QR — f4gop.denis@gmail.com")
    c.drawCentredString(w / 2, 24 * mm, "github.com/f4gopdenis-cyber/HFImage_F4GOP")
    c.restoreState()


s = []
s.append(PageBreak())
s.append(Paragraph("Sommaire", ParagraphStyle("toct", parent=st["h1"])))
toc = TableOfContents()
toc.levelStyles = [ParagraphStyle("t1", fontName="DVB", fontSize=10.5, leading=15, leftIndent=0),
                   ParagraphStyle("t2", fontName="DV", fontSize=9.5, leading=12.5, leftIndent=12, textColor=GREY)]
s.append(toc)
s.append(PageBreak())

# ------------------------------------------------------------------ 1
s.append(P("1. Présentation", "h1"))
s.append(P("<i>Programme dédié à Erik Sundstrup VK4AES (SK), créateur d'EasyPal, en hommage à son travail. "
           "HFImage a été conçu par Denis F4GOP, qui en a choisi chaque fonction, l'a testé sur l'air et l'a fait évoluer "
           "avec les retours des utilisateurs ; le code a été écrit en grande partie avec l'aide de l'intelligence "
           "artificielle Claude (Anthropic).</i>"))
s.append(P("HFImage F4GOP envoie et reçoit des <b>photos numériques par radio en HF</b>, comme EasyPal, mais avec "
           "un modem moderne (OFDM de codec2) et une correction d'erreurs par <b>code fontaine</b>. L'image reçue est "
           "<b>identique bit à bit</b> à l'image envoyée, ou elle n'est pas affichée : jamais d'image abîmée."))
s.append(P("Le programme réunit deux familles de modes et <b>écoute toujours les deux en même temps</b> : les "
           "<b>modes HFImage (DATAC)</b> ci-dessus, et le <b>mode EasyPal (HamDRM)</b>, celui d'<b>EasyPal</b> et de "
           "<b>QSSTV</b> : HFImage échange images, textes et images hybrides avec les stations qui utilisent ces "
           "logiciels, pour faire vivre ce mode depuis la disparition d'Erik Sundstrup VK4AES, l'auteur d'EasyPal."))
s += B(["Photo 800×600 nette en environ 2 minutes (mode rapide DATAC1X, 2,2 kHz de large).",
        "Mode <b>EasyPal</b> compatible EasyPal / QSSTV : modes A / B / E, QAM4 / 16 / 64, 2,2 ou 2,4 kHz, "
        "Reed-Solomon, BSR / FIX, mode hybride.",
        "L'émission <b>suit le mode reçu</b> : on répond à chaque station dans le mode qu'elle utilise.",
        "Mode <b>Auto</b> : le mode et la robustesse s'adaptent aux reports des stations.",
        "<b>Coupe-QRM</b> à la réception : porteuses, CW, RTTY et BLU voisines effacées.",
        "Liste des <b>stations en ligne</b>, <b>Rx Ok</b> avec reports en dB, <b>carte</b> des stations.",
        "Mode <b>hybride</b> (image par Internet, lien par radio), dont l'<b>hybride éclair</b> : annonce radio robuste de 9 s (DATAC13, passe jusqu'à −7 dB).",
        "Jusqu'à <b>4 images de correspondants</b> incrustées dans la vôtre, GIF animés, carte <b>QSL</b>, texte dans le waterfall.",
        "<b>Fenêtres séparées</b> : waterfall, galerie, liste des stations… placés où vous voulez, même sur un autre écran.",
        "Plus de 300 postes pilotés (Hamlib), Kenwood en direct, OmniRig, FLRig.",
        "<b>Galerie</b>, mise en ligne sur votre site (<b>Digi-Sites</b>), <b>analyseur</b> de réception.",
        "Mise à jour automatique, 5 langues."])
s += tip("en modes HFImage (DATAC), les deux stations doivent utiliser HFImage. Pour trafiquer avec EasyPal ou "
         "QSSTV, choisissez le mode EasyPal (chapitre 6).", "Important")
s.append(img("fenetre_principale.png", 170, "La fenêtre principale : panneau d'état et boutons à gauche, "
                                           "waterfall, liste des stations, image reçue, historique et messages."))

# ------------------------------------------------------------------ 2
s.append(PageBreak())
s.append(P("2. Installation et mises à jour", "h1"))
s.append(P("Installation", "h2"))
s += N(["Téléchargez <b>HFImage_F4GOP.exe</b> sur la page <i>Releases</i> du projet GitHub.",
        "Placez-le dans un dossier à vous, par exemple <b>C:\\Prg-Radio\\HFImage</b> (évitez « Program Files »).",
        "Au premier lancement, Windows SmartScreen peut afficher un avertissement : « Informations "
        "complémentaires », puis « Exécuter quand même ».",
        "Au premier démarrage, la <b>licence</b> s'affiche (logiciel libre et gratuit, GNU GPL v3) : lisez-la et "
        "cliquez « <b>J'accepte</b> ». On la relit à tout moment par Infos → Licence."])
s.append(P("Rien d'autre à installer : un seul fichier, Windows 8.1 / 10 / 11 64 bits. Pour <b>Windows 7 SP1 ou 8</b> "
           "(64 bits), prenez <b>HFImage_F4GOP_Win7.exe</b> sur la même page GitHub : même programme, qui se met à jour "
           "avec sa propre version ; seules les images SVG ne s'y affichent pas."))
s.append(P("Linux", "h2"))
s.append(P("Depuis la version 1.23, HFImage existe aussi pour <b>Linux</b> 64 bits (Ubuntu 22.04 et plus récents, "
           "Debian 12, Linux Mint 21, etc.) : même programme, mêmes modes, compatible avec les stations Windows."))
s += N(["Téléchargez <b>HFImage_F4GOP_Linux.tar.gz</b> sur la même page GitHub et ouvrez-le (double-clic, ou "
        "<b>tar xzf HFImage_F4GOP_Linux.tar.gz</b>) : il contient un seul fichier, <b>HFImage_F4GOP_Linux</b>.",
        "Placez-le dans un dossier à vous (par exemple <b>~/HFImage</b>) et lancez-le par un double-clic. Au premier "
        "lancement, il s'ajoute au menu des applications (rubrique Radioamateur).",
        "Pour piloter le poste par Hamlib : <b>sudo apt install libhamlib-utils</b>. Le pilotage Kenwood direct, FLRig et le "
        "PTT par le port série n'ont besoin de rien d'autre ; OmniRig n'existe que sous Windows.",
        "Ports série (/dev/ttyUSB0…) : votre compte doit être dans le groupe <b>dialout</b> : "
        "<b>sudo usermod -aG dialout $USER</b>, puis fermez la session et reconnectez-vous."])
s.append(P("Les mises à jour se font comme sous Windows (bandeau orange). Le mot de passe FTP est gardé dans le fichier "
           "de réglages, lisible par votre seul compte."))
s.append(P("Mises à jour automatiques", "h2"))
s.append(P("Au démarrage (puis toutes les 3 heures), HFImage regarde sur GitHub s'il existe une version plus "
           "récente. Si oui, un <b>bandeau orange</b> apparaît en haut de la fenêtre : un clic, « Oui », et le "
           "programme se met à jour et redémarre tout seul. Menu <b>Infos → Rechercher une mise à jour</b> pour "
           "vérifier à tout moment."))
s.append(P("Mode d'emploi en anglais", "h2"))
s.append(P("Menu <b>Infos → Mode d'emploi en anglais (PDF)</b> : le même mode d'emploi en anglais, à donner aux "
           "correspondants étrangers."))
s += tip("après une mise à jour, si l'explorateur Windows affiche encore l'ancienne icône, redémarrez le PC "
         "(Windows garde les icônes en mémoire).")

# ------------------------------------------------------------------ 3
s.append(P("3. Premier réglage", "h1"))
s.append(P("Au premier démarrage, l'<b>assistant de démarrage</b> s'ouvre tout seul, en 3 étapes : indicatif et "
           "locator, carte son du poste (sortie et entrée, avec un essai à 1 kHz sans émettre), puis poste radio "
           "(CAT / PTT, avec l'installation de Hamlib si besoin). On le retrouve par <b>Réglages → Assistant de "
           "démarrage…</b>. Ensuite, tout se règle dans <b>Réglages</b>."))
s.append(P("<b>Écouteurs (SWL)</b> : mettez votre identifiant d'écouteur à la place de l'indicatif (ex. "
           "<b>F-12345</b>, <b>PA0041SWL</b>, <b>14VD274</b>). HFImage reçoit tout normalement et envoie vos "
           "reports <b>par Internet</b> (Rx Ok, carte des stations), mais n'émet <b>jamais</b> : ni image, ni accusé "
           "(ACK), ni BSR par radio."))
s.append(P("Ouvrez <b>Réglages</b> (bouton ou menu). Les réglages sont enregistrés automatiquement."))
s.append(img("reglages.png", 165, "La fenêtre des réglages."))
s.append(P("Station", "h2"))
s.append(P("Indicatif et <b>locator</b> (6 caractères, ex. IN98QR) : ils servent aux annonces, à la carte "
           "des stations et à la carte QSL. Langue de l'interface : français, English, Deutsch, Español, Italiano, chinois simplifié (traduit par Yang BH2RMX et BD4QXR), russe (traduit par Yuri)."))
s.append(P("<b>Prénom</b> : affiché à côté de votre indicatif dans la liste Rx Ok des autres "
           "utilisateurs (« F4GOP  +5 dB  Denis »). Ne l'écrivez pas dans la case <b>Indicatif</b> : par radio, "
           "l'indicatif est limité à 8 caractères, et « F4LTX CHRIS » arrivait coupé en « F4LTX CH » "
           "(la même station apparaissait deux fois). Depuis la version 1.12, un prénom écrit derrière "
           "l'indicatif est rangé tout seul dans la case Prénom."))
s.append(P("Audio", "h2"))
s += B(["<b>Sortie (vers le poste)</b> et <b>Entrée (depuis le poste)</b> : avec un Kenwood TS-890 / TS-990, "
        "« Haut-parleurs (USB Audio CODEC) » et « Microphone (USB Audio CODEC) », de préférence en [MME].",
        "<b>Tester la sortie (1 kHz)</b> : tonalité de 2 s sans PTT, pour vérifier la carte son.",
        "<b>Niveau d'émission</b> : réglez-le pour que l'<b>ALC ne bouge pas</b>. Un signal OFDM surmodulé "
        "devient illisible.",
        "<b>Coupe-QRM à la réception</b> : laissez-le coché (voir chapitre 9).",
        "Chaque carte son n'apparaît qu'<b>une fois</b>, avec son nom complet : HFImage choisit lui-même "
        "l'interface Windows la plus sûre (MME, DirectSound, WASAPI) et essaie automatiquement les autres si elle échoue."])
s.append(P("Poste radio (CAT / PTT)", "h2"))
s.append(P("Bouton <b>Poste radio…</b> : la fenêtre reprend l'onglet Radio de WSJT-X."))
s.append(img("poste_radio.png", 150, "Réglages du poste : poste, liaison CAT, PTT, source audio, mode, tests."))
s += B(["<b>Poste</b> : tapez une partie du nom dans « Rechercher » (ex. 7300, FT-991, TS-990). "
        "Kenwood TS-990S / TS-890S / TS-590 / TS-2000 / TS-480 : pilotés en direct, rien à installer. "
        "Autres postes : Hamlib, téléchargé une fois (bouton « Installer Hamlib », 3 Mo).",
        "<b>OmniRig</b> (Rig 1 / Rig 2) ou <b>FLRig</b> : pour partager le poste avec d'autres logiciels "
        "(logger, WSJT-X…).",
        "<b>SunSDR / ExpertSDR (TCI)</b> : HFImage parle directement à ExpertSDR par le TCI (Options → TCI dans "
        "ExpertSDR, port 40001 ; « Serveur réseau » 127.0.0.1:40001, ou l'adresse du PC qui fait tourner ExpertSDR) : "
        "fréquence, mode (DIGL / DIGU) et PTT « CAT », sans RadioSync ni port COM virtuel. Le son passe par les câbles "
        "audio virtuels (VAC) d'ExpertSDR. Marche aussi avec les autres SDR qui parlent TCI.",
        "<b>Commandes CAT personnalisées (comme EasyPal)</b> : on écrit soi-même les commandes envoyées au poste, en "
        "hexadécimal (Icom CI-V : FEFE5EE01C0001FD) ou en texte (Kenwood : TX1;) : <b>Départ</b> 1 et 2, "
        "<b>PTT marche</b> / <b>PTT arrêt</b> (avec la méthode PTT « CAT »), <b>Sortie</b> 1 et 2 "
        "et le délai entre deux commandes. Comme dans EasyPal, les chaînes de départ partent <b>avant chaque émission</b> (avant PTT marche) et les chaînes de sortie <b>après</b> (après PTT arrêt), quelle que soit la méthode PTT ; on peut choisir à la place de les envoyer une seule fois, au lancement et à la fermeture du programme. Les réglages d'EasyPal (« \\$…\\ ») se collent tels quels, même plusieurs commandes à la suite (« \\$…\\$…\\ ») : elles partent l'une après l'autre, avec le délai entre chacune. "
        "Dans ce mode, la fréquence du poste n'est pas lue. Avec des commandes Icom (CI-V, « FEFE94E0… »), HFImage "
        "trouve l'adresse du poste dans vos commandes et sait quand même <b>changer la fréquence</b> (menu des fréquences) ; "
        "le mode du poste n'est pas touché. Avec d'autres postes, changez la fréquence sur le poste.",
        "<b>Port série</b> et vitesse ; paramètres avancés si besoin (bits, stop, contrôle de flux, DTR/RTS forcés). "
        "La liste montre tous les ports actifs de Windows (Prolific, CH340, Silicon Labs, ports virtuels compris), "
        "<b>avec leur description</b> : utile quand le poste crée deux ports COM (TS-890/990, IC-7610, IC-7300MK2…) ; "
        "on peut aussi taper le nom du port, par exemple COM9. Avec un PTT par DTR ou RTS sur le port du CAT, "
        "la ligne reste basse à l'ouverture du port (le poste ne passe pas en émission au lancement).",
        "<b>Adresse CI-V (Icom)</b> : vide = l'adresse du modèle (IC-7300 : 94, IC-7300MK2 : B6, IC-7610 : 98). "
        "À remplir seulement si l'adresse a été changée dans le poste (Set → Connectors → CI-V). L'<b>IC-7300MK2</b> "
        "est dans la liste (Hamlib 4.7.2) ; avec un Hamlib plus ancien (Linux), HFImage le pilote comme un IC-7300 "
        "à l'adresse B6. Si le poste ne répond pas : « CI-V USB Port » sur « Unlink from [REMOTE] », ou essayez "
        "l'autre port COM du poste.",
        "<b>Partager le poste avec d'autres logiciels</b> (WSJT-X, JTDX, logger…) : un port COM ne sert qu'à un seul "
        "programme à la fois. Case cochée, HFImage garde le port du poste et l'ouvre aux autres logiciels du PC : "
        "dans WSJT-X ou le logger, choisissez le poste <b>« Hamlib NET rigctl »</b>, serveur <b>127.0.0.1:4532</b>. "
        "Tous lisent et changent la fréquence et passent en émission en même temps. <b>Lancez HFImage en premier.</b> "
        "Pour les postes de la liste Hamlib et les Kenwood (choisir le modèle exact) ; pas pour les commandes CAT "
        "personnalisées ni le TCI (qui accepte déjà plusieurs logiciels).",
        "<b>Afficher le S-mètre du poste</b> (coché par défaut) : à droite de l'indicatif, le S-mètre du poste "
        "(S1 à S9+60), lu par CAT avec la fréquence, en réception seulement (figé et grisé pendant l'émission). "
        "La fréquence, le mode et la bande restent en haut de la fenêtre. Si le poste ne donne pas son S-mètre "
        "(OmniRig, FLRig, TCI, CAT personnalisé…), la fréquence reste affichée à sa place. Chaque marque a sa propre "
        "échelle : la valeur est proche de celle du poste, pas toujours au point près.",
        "<b>Préréglages</b> (en haut à droite, depuis la 1.83) : pour passer d'un poste à l'autre (FT-857D, "
        "IC-7300, IC-9700…). <b>Enregistrer sous…</b> garde tout le réglage du poste de la fenêtre, plus les cartes son "
        "(Réglages → Audio) et le niveau d'émission actuels. Choisir un préréglage dans la liste remplit la fenêtre ; "
        "<b>OK</b> l'applique, cartes son comprises (l'écoute repart sur la carte son de ce poste).",
        "<b>Méthode PTT</b> : CAT (recommandé), DTR ou RTS (y compris sur le port d'une interface à côté du poste), "
        "ou VOX.",
        "<b>Source audio en émission</b> : « Arrière / Data » (audio USB, ACC) ou « Avant / Micro ». Choisissez "
        "« Avant / Micro » si votre poste émet l'audio USB sans le mode DATA : HFImage ne touche alors pas à son mode.",
        "<b>Mode</b> : « Data / Pkt » met le poste en DATA avant chaque émission, en gardant sa bande latérale "
        "(LSB → LSB-DATA, USB → USB-DATA).",
        "<b>Tester le CAT</b> lit la fréquence ; <b>Tester le PTT</b> émet 1,5 s. Vert = OK, rouge = erreur "
        "affichée en dessous."])
s.append(P("Poste pas en DATA avant d'émettre", "h2"))
s.append(P("Dès que le CAT est relié, HFImage lit le mode du poste avant chaque émission, <b>quelle que soit la méthode "
           "PTT</b> (CAT, RTS, DTR ou VOX). S'il n'est pas en DATA, le réglage « <b>Poste pas en DATA avant d'émettre</b> » "
           "(Réglages, sous les boutons du poste) décide :"))
s += B(["<b>Passer en DATA automatiquement (USB-DATA / LSB-DATA)</b> : le réglage par défaut. Le poste passe en DATA "
        "<b>en gardant sa bande latérale</b> : en LSB (40 et 80 m, comme EasyPal) il passe en <b>LSB-DATA</b>, en USB "
        "en <b>USB-DATA</b>. Le journal l'indique (« TS-890S passé en LSB-DATA1 par CAT »).",
        "<b>Demander</b> : une fenêtre propose de passer en DATA, d'émettre quand même ou d'annuler.",
        "<b>Émettre sans rien dire</b> : le poste reste dans son mode ; le journal le rappelle à chaque émission."])
s.append(P("Kenwood TS-990 : une seule commande (LSB-D1 ou USB-D1). TS-890 : commande SF (fréquence et mode d'un coup, comme Hamlib). TS-590, TS-480 : LSB ou USB, puis DATA. "
           "Autres postes : PKTLSB / PKTUSB (Hamlib), DIG-L / DIG-U (OmniRig), mode DATA de FLRig. Avec un PTT par RTS, "
           "DTR ou VOX, un échec du passage en DATA est seulement signalé dans le journal, sans bloquer l'émission."))
s += tip("Kenwood TS-890 / TS-990 : source audio DATA = USB Audio, <b>DATA VOX sur OFF</b>, PTT CAT sur le port COM "
         "virtuel du poste à 115200 bauds, source « Arrière / Data ». Le poste passe tout seul en LSB-DATA ou USB-DATA. "
         "Le port doit être libre : fermez ARCP ou le logger, ou passez par OmniRig. Si l'entrée et la sortie du codec "
         "USB portent le même nom dans Windows, HFImage prend toujours la bonne.", "Kenwood")
s.append(P("Bouton « DATA auto » : image en DATA, commentaire en phonie", "h2"))
s.append(P("Le bouton <b>DATA auto</b>, à côté de « Émettre » (onglet TX), est vert quand il est actif. À chaque émission, "
           "le poste passe de <b>LSB à LSB-DATA</b> (ou de USB à USB-DATA), envoie l'image, puis <b>revient tout seul en "
           "LSB</b> (ou USB) à la fin, ou si l'on arrête l'émission : on peut aussitôt commenter l'image au micro. "
           "Il faut une liaison CAT qui lit le mode (Kenwood, Icom et autres par Hamlib, FLRig, OmniRig, TCI) ; "
           "pas avec les commandes CAT personnalisées. Si le poste est déjà en DATA, ou dans un autre mode (FM, CW…), "
           "HFImage n'y touche pas. Bouton éteint : rien ne change."))
s.append(P("Disposition : fenêtres séparées", "h2"))
s.append(P("Menu <b>Fenêtres</b> : cochez une zone pour en faire une <b>fenêtre séparée</b>, à placer et dimensionner où vous "
           "voulez, même sur un autre écran : <b>panneau et boutons</b>, <b>waterfall</b>, <b>stations entendues</b>, onglet "
           "<b>Stations</b> et <b>galerie</b>. Les onglets RX, TX et le journal restent dans la fenêtre principale. L'onglet <b>Simulation</b> (canal HF simulé, pour essayer sans poste) s'affiche par Fichiers → Onglet Simulation."))
s += B(["Les fenêtres séparées restent <b>toujours devant</b> la fenêtre principale et se réduisent avec elle.",
        "Décochez la zone, ou fermez sa fenêtre, pour la remettre à sa place. « Tout remettre dans la fenêtre "
        "principale » rassemble tout ; « Réglages → Disposition d'origine des fenêtres » aussi.",
        "La disposition est gardée d'une session à l'autre.",
        "Les cases <b>Afficher l'historique</b> et <b>Afficher les messages reçus</b> (onglet RX) masquent ces listes : "
        "sans les deux, l'image reçue prend toute la largeur."])

# ------------------------------------------------------------------ 4
s.append(PageBreak())
s.append(P("Changer de fréquence", "h2"))
s.append(P("Avec une liaison CAT, le bouton <b>« Fréquence ▾ »</b> (à droite de « Attendre fréquence libre »), ou un "
           "<b>clic sur la fréquence</b> affichée (panneau en haut à gauche, marquée ▾, ou barre d'état en bas) ouvre le menu des fréquences image : <b>3,733 – 7,058 – 14,233 – 21,340 – 28,680 MHz</b>. Un clic, et le "
           "poste y va, avec la bande latérale de la fréquence (LSB en dessous de 10 MHz, USB au-dessus) ; s'il était en "
           "DATA, il y reste. Même menu dans <b>Action → Aller sur une fréquence</b>, avec « Autre fréquence… » et "
           "« Modifier la liste… » (une ligne par fréquence, ex. « 7.058 LSB »). Clic droit dans la liste des stations : "
           "<b>Aller sur la fréquence de cette station</b>. Jamais pendant une émission. (Idée d'Allan G7VQV.)"))
s.append(P("Plusieurs fréquences à la fois (profils)", "h2"))
s.append(P("Un HFImage écoute une fréquence (une entrée audio). Pour surveiller par exemple le 40 m, le 20 m et le "
           "28,680 MHz en même temps, il faut un récepteur par fréquence (souvent un <b>SDR</b> avec plusieurs bandes, "
           "chacune envoyée vers un câble audio virtuel comme VB-Cable) et un HFImage par fréquence : <b>Réglages → "
           "Ouvrir une autre instance (profil)…</b>, donnez un nom (ex. « 20m »). Chaque profil a ses <b>propres "
           "réglages</b> (entrée audio, poste, dossier des images, dans Documents\\HFImage\\20m) ; au premier "
           "lancement, il part des réglages habituels et l'assistant permet de choisir son entrée audio. HFImage "
           "propose de créer un raccourci sur le Bureau (« HFImage 20m »), qui lance <b>HFImage_F4GOP.exe --profil "
           "20m</b>. Le nom du profil s'affiche dans le titre de la fenêtre."))
s.append(P("4. Recevoir des images", "h1"))
s.append(P("L'écoute démarre toute seule si l'entrée audio est réglée (bouton <b>Écoute</b> pour arrêter / "
           "reprendre). Rien à choisir : <b>tous les modes</b> sont décodés en même temps — DATAC1X, DATAC1, DATAC3, "
           "DATAC4 <b>et</b> EasyPal (HamDRM), quel que soit le mode choisi pour l'émission."))
s += B(["<b>Panneau d'état</b> (en haut à gauche) : indicatif de la station reçue, fréquence et mode du poste, "
        "niveau RX, SNR, mode, débit, segments reçus, voyants Signal / Sync / Trame / Image / BSR. À droite du "
        "tableau, la <b>vignette de la dernière image reçue</b>, avec l'indicatif, le prénom et la distance de la "
        "station ; un clic l'affiche dans l'onglet RX.",
        "Quand une image commence à arriver alors que l'<b>onglet TX</b> est affiché, HFImage passe sur l'<b>onglet RX</b> "
        "pour la montrer (sauf pendant vos propres émissions).",
        "<b>Aperçu rapide</b> (modes HFImage) : une petite image arrive en ~20 s, puis l'image complète la remplace.",
        "<b>Zoom</b> : molette de la souris sur l'image pour l'agrandir / la réduire autour du pointeur (jusqu'à ×16), "
        "clic gauche maintenu pour la déplacer. <b>Clic droit</b> : « <b>Copier l'image</b> » (à coller avec Ctrl+V dans "
        "Teams, un e-mail, WhatsApp… pour une station qui ne l'a pas décodée) et « Revenir à l'image entière ».",
        "<b>Historique</b> à droite : clic pour réafficher, double-clic pour le plein format (masquable par le menu Fenêtres).",
        "<b>BSR / ACK automatiques</b> : s'il manque des morceaux à la fin, HFImage les demande (BSR) ; "
        "l'émetteur ne renvoie que ce qui manque (FIX). Une fois l'image complète, un accusé (ACK) avec "
        "votre report part vers l'émetteur.",
        "Les images sont rangées dans le dossier choisi (Réglages → Dossier des images reçues), dans un "
        "<b>sous-dossier par jour</b> (2026-10-18…), <b>une seule copie par image</b> (le fichier reçu, AVIF, JPEG…). "
        "Bouton <b>Dossier</b> pour l'ouvrir. Les fichiers reçus restent dans le sous-dossier « fichiers ».",
        "<b>Nettoyage automatique</b> (Réglages, sous le dossier) : les sous-dossiers par jour de plus de <b>30 jours</b> "
        "(réglable) sont effacés, images envoyées comprises. Rien d'autre n'est jamais effacé : ni les fichiers reçus, "
        "ni les enregistrements, ni les images des versions précédentes. Décochez la case pour tout garder.",
        "<b>Relire RX</b> : redécode les 15 dernières minutes (si une image a été manquée)."])
s.append(P("Galerie", "h2"))
s.append(P("Onglet <b>Galerie</b> : les 30, 60 ou 100 dernières images reçues (« de F4EMK ») ou envoyées. Clic : "
           "afficher ; double-clic : plein format ; clic droit : <b>copier l'image</b> (à coller avec Ctrl+V dans Teams, "
           "un e-mail… ; un GIF animé est copié comme image fixe), renvoyer l'image, voir la station sur la carte, "
           "ouvrir le dossier, retirer de la galerie. Sous Linux, la copie demande xclip (sudo apt install xclip)."))
s.append(img("galerie.png", 160, "La galerie des dernières images reçues."))

# ------------------------------------------------------------------ 5
s.append(PageBreak())
s.append(P("5. Envoyer une image (modes HFImage)", "h1"))
s += N(["Onglet <b>TX</b> → <b>Ouvrir une image…</b> (JPG, PNG, GIF, WebP, AVIF, SVG, BMP…).",
        "Choisissez le <b>Mode</b> (Auto conseillé), la <b>Durée max</b> (120 s par défaut), la <b>Largeur</b> "
        "(auto), le <b>Format</b> (avif conseillé) et la <b>Robustesse</b> (Auto conseillé).",
        "HFImage calcule tout seul la taille et la qualité qui tiennent dans la durée : l'image compressée "
        "s'affiche avec sa taille et sa qualité.",
        "<b>▶ Émettre</b> (ou bouton ÉMISSION). La barre de progression suit l'émission. Si une autre station "
        "émet déjà (signal reçu, ou station en ligne en émission sur votre fréquence), le bouton devient "
        "<b>ATTENTE…</b> et l'émission part toute seule 2 à 6 s après la fin de l'autre (case <b>Attendre "
        "fréquence libre</b> sous les boutons, cochée par défaut). Clic sur ÉMISSION : annuler ; clic droit : "
        "émettre tout de suite. Les réponses automatiques (ACK, BSR, FIX) n'attendent pas.",
        "Si des stations demandent des morceaux (BSR), <b>+ Compléter</b> / FIX envoie seulement ce qui manque."])
s.append(img("tx.png", 165, "L'onglet TX : mode Auto, robustesse, image compressée et durée d'émission."))
s.append(P("<b>Ouvrir une image</b> : un clic dans la grande image de l'onglet TX ouvre le choix du fichier ; on peut "
           "aussi <b>glisser une image</b> depuis l'Explorateur Windows n'importe où sur la fenêtre (un autre type de "
           "fichier est proposé à l'envoi). Image trouvée sur Internet : dans le navigateur, clic droit sur l'image → "
           "« Copier l'image », puis <b>Ctrl+V</b> dans HFImage (onglet TX) ou clic droit sur l'image TX → "
           "<b>« Coller l'image »</b> (aussi dans le menu Images). Une capture d'écran se colle de la même façon ; "
           "l'image collée est enregistrée dans le dossier « collées » des images."))
s.append(P("<b>Photos de téléphone</b> : une photo enregistrée « couchée » par le téléphone est remise droite "
           "toute seule à l'ouverture, comme dans Windows. Les boutons <b>⟲</b> et <b>⟳</b> (en bas à droite de l'image, "
           "onglet TX) la tournent d'un quart de tour à gauche ou à droite si besoin. Une photo tournée part en JPEG "
           "très haute qualité, déjà droite, même en mode « original »."))
s.append(P("Textes et logos directement sur l'image TX", "h2"))
s.append(P("Une fois l'image ouverte dans l'onglet TX, tout se fait <b>sur l'image elle-même</b> : <b>clic droit</b> → "
           "« Ajouter un texte… », « Ajouter un logo / une image du PC… » (un PNG à fond transparent devient un logo), "
           "« Ajouter l'image d'un correspondant ». <b>Clic</b> sur un texte ou un logo : il est sélectionné (cadre "
           "jaune) ; <b>glisser</b> pour le déplacer (le rond rouge : la pointe d'une bulle) ; <b>molette</b> pour "
           "l'agrandir ou le réduire ; <b>Maj + molette</b> pour tourner un logo ou une image ; <b>double-clic</b> sur "
           "un texte pour le modifier ; touche <b>Suppr</b> pour l'enlever. Le clic droit sur l'élément choisi donne "
           "aussi son style, ses couleurs, sa forme, sa légende. Les fenêtres « Bulles… » et « Image du "
           "correspondant… » restent là pour les réglages fins. Un <b>clic à côté</b> des textes et logos ouvre une "
           "autre image, comme avant (s'il y a une sélection, le premier clic l'enlève)."))
s.append(P("Bulles de texte (BD)", "h2"))
s.append(P("Bouton <b>Bulles…</b> (onglet TX) ou menu <b>Images → Bulles de texte…</b> : on écrit un texte, il "
           "apparaît dans une bulle de bande dessinée sur l'image émise. Cinq styles : <b>parole</b> (bulle ronde "
           "avec une pointe), <b>pensée</b> (petits ronds), <b>cri</b> (contour en étoile), <b>cartouche</b> "
           "(rectangle, comme une légende), <b>texte seul</b> (sans bulle : le texte directement sur l'image, bordé de la "
           "couleur de « fond » pour rester lisible) ; trois tailles de texte ; couleurs du fond et du texte au choix ; "
           "<b>30 émoticônes</b> en couleur (sourires, pouce levé, poste radio, soleil, cœur…) à ajouter d'un clic dans le texte ; "
           "case « <b>Émoticônes animées</b> » : en mode hybride, elles bougent (le cœur bat, la main salue, l'étoile tourne, "
           "clin d'œil…) et l'image part en GIF animé (une photo y perd un peu en finesse : 256 couleurs) ; en radio seule, "
           "elles restent fixes. Sur un <b>GIF animé</b> reçu (« Renvoyer cette image »), les bulles sont dessinées sur "
           "chaque image et l'animation d'origine est gardée. "
           "Bouton <b>Phrases ▾</b> : des phrases toutes prêtes (« Bonjour de {MOI} », « Merci pour l'image ! 73 de "
           "{MOI} »…) à mettre dans la bulle d'un clic ; {MOI}, {PRENOM} et {LOC} sont remplacés par votre indicatif, "
           "votre prénom et votre locator. « Enregistrer cette phrase » ajoute le texte de la bulle à la liste, "
           "« Modifier la liste… » permet de la retoucher. Une nouvelle bulle reprend le style, la taille et les "
           "couleurs de la dernière utilisée. "
           "<b>Glissez la bulle</b> à la souris, et le <b>rond rouge</b> (la pointe) vers ce qu'elle doit montrer ; "
           "plusieurs bulles possibles, clic droit sur une bulle pour la supprimer. La bulle fait partie de l'image : "
           "tout le monde la voit, en radio comme en hybride, y compris les stations EasyPal. Les bulles sont effacées "
           "quand on ouvre une autre image."))
s.append(P("Mode Auto et robustesse", "h2"))
s.append(P("En mode <b>Auto</b>, HFImage choisit le mode d'après le <b>report le plus faible</b> des stations "
           "qui ont reçu vos images ces 45 dernières minutes (liste Rx Ok). Sans report, il prend le SNR des "
           "stations entendues, sinon DATAC1X. La raison du choix est affichée sous l'image."))
s.append(table([["SNR affiché (report)", "Mode choisi", "Images"],
                ["9 dB et plus", "DATAC1X", "les plus nettes"],
                ["de 5 à 9 dB", "DATAC1", "moyennes"],
                ["moins de 5 dB", "DATAC3", "petites mais très robustes"]], [55, 45, 70]))
s.append(Spacer(1, 6))
s.append(P("La <b>robustesse</b> est la part de trames de secours (code fontaine) : elles remplacent les trames "
           "perdues dans le QSB. En « Auto » : 15 % si le lien a de la marge, 25 % s'il est juste, 40 % s'il est "
           "à la limite. Plus de robustesse = image un peu moins détaillée pour la même durée, mais qui passe "
           "en une fois."))
s += tip("les reports et le SNR affichés sont le <b>SNR réel sur 3 kHz</b> (étalonné depuis la version 0.30), "
         "comparable d'un mode à l'autre. Les stations encore en version 0.29 ou plus ancienne envoient des reports "
         "plus bas (estimation brute du modem). Sur un signal très fort, la mesure sature : les reports sont plafonnés "
         "à +15 dB en DATAC3 / DATAC0 (annonce hybride, BSR, ACK) et +21 dB en DATAC1X / DATAC1. Pour une image plus nette, le plus efficace est d'allonger la durée "
         "(3 min en DATAC1X ≈ 50 % d'octets en plus).")
s.append(P("Les modes", "h2"))
s.append(table([["Mode", "Largeur", "Débit utile", "En 2 min", "Usage"],
                ["DATAC1X", "2,2 kHz", "~1 500 bit/s", "~13-16 ko", "Bonnes conditions : images nettes (HFImage uniquement)"],
                ["DATAC1", "1,7 kHz", "~980 bit/s", "~8-10 ko", "Conditions moyennes"],
                ["DATAC3", "0,6 kHz", "~320 bit/s", "~2,5-3 ko", "Signaux faibles, QSB"],
                ["DATAC4", "0,25 kHz", "~85 bit/s", "~1 ko", "Très faibles signaux"],
                ["DATAC0", "0,6 kHz", "—", "—", "BSR, ACK, présence (automatique)"]],
               [20, 20, 25, 22, 83]))
s.append(P("Mes conditions de trafic", "h2"))
s.append(P("Case <b>Mes conditions de trafic</b> (onglet TX) et bouton <b>…</b> à côté (ou menu Images) : un bandeau est "
           "incrusté en bas ou en haut de l'image émise, avec votre indicatif, locator, QTH, poste (lu par CAT si le "
           "champ est vide), puissance, antenne, fréquence, date et heure UTC, et un texte libre. Chaque élément "
           "peut être coché ou non ; l'aperçu se met à jour en direct. Le bandeau passe avec l'image, il est donc "
           "visible chez tous les correspondants, quelle que soit leur version."))
s.append(P("Le cadre <b>Police et couleurs</b> permet de choisir la police (toutes celles installées sur Windows), "
           "le gras et l'italique, la couleur du texte, une couleur à part pour l'<b>indicatif</b>, la couleur du "
           "contour des lettres (✕ = sans contour), la couleur du fond et son opacité (0 % = pas de fond), et un filet "
           "de couleur au bord du bandeau. La liste <b>Modèles…</b> propose des réglages tout prêts."))
s.append(P("Image du correspondant", "h2"))
s.append(P("Pour répondre comme dans EasyPal : clic droit sur une image de la <b>Galerie</b> → « Répondre avec cette image », "
           "ou case <b>Image du correspondant</b> (onglet TX) et bouton <b>…</b>. Les images reçues sont incrustées dans la "
           "vôtre avec la légende « de F4EMK — +12 dB » : le <b>report</b> est le SNR que vous avez mesuré en les recevant. "
           "<b>Jusqu'à 4 images</b> à la fois, par exemple pour répondre à plusieurs stations d'un coup. Se combine avec "
           "« Mes conditions de trafic »."))
s += B(["Liste <b>Images incrustées</b> : <b>Ajouter une image</b> (elle se place dans un coin libre) et <b>Retirer</b>. "
        "La liste « Image reçue » change l'image de la ligne choisie.",
        "Chaque image a sa <b>position</b> et sa <b>taille</b> : un coin et une taille dans les listes, ou à la souris "
        "dans l'aperçu. <b>Cliquez</b> sur une image pour la choisir (cadre jaune), <b>faites-la glisser</b> pour la "
        "placer, la <b>molette</b> l'agrandit ou la réduit (10 % à 90 % de la largeur). Réglettes <b>Rotation</b> "
        "(−45° à +45°, ou Maj + molette sur l'image) et <b>Perspective</b> (l'image « penche » vers la gauche ou la droite, "
        "effet 3D) pour chaque image incrustée ; les coins qui dépassent laissent voir votre photo ; « Remettre droit » "
        "annule les deux. Bouton <b>« Image du PC… »</b> : n'importe quelle image de l'ordinateur (photo, logo, "
        "carte QSL…) s'incruste de la même façon ; champ <b>Légende</b> pour écrire le texte de votre choix sous "
        "l'image (vide : « de F4EMK — +12 dB » pour une image reçue, rien pour une image du PC). Case "
        "<b>« Logo »</b> : l'image est posée sans cadre, sans ombre ni légende, et la transparence d'un PNG est "
        "gardée (cochée d'office pour un PNG à fond transparent) ; réglette <b>Opacité</b> pour un logo discret. "
        "Liste <b>Forme</b> : rectangle (habituel), coins arrondis, rond ou ovale ; le cadre blanc et l'ombre suivent "
        "la forme, la légende est dans une pastille dessous (rond, ovale), et la forme découpe aussi un logo.",
        "Galerie, clic droit : « <b>Répondre avec cette image</b> » remplace les incrustations par cette seule image ; "
        "« <b>Ajouter cette image à mon image TX</b> » l'ajoute aux autres.",
        "La disposition est gardée ; l'image émise est exactement celle de l'aperçu."])
s.append(img("pip.png", 130, "Image du correspondant : trois images incrustées, celle d'ON4QZ choisie (cadre jaune)."))
s.append(P("Messages reçus", "h2"))
s.append(P("Quand un correspondant envoie un message (texte seul, ou texte joint à son image), la fenêtre <b>Message reçu</b> "
           "s'ouvre au premier plan avec un bip : indicatif, heure UTC, mode, SNR, le texte en grand et la vignette de "
           "l'image s'il y en a une (clic = plein format). Les flèches ◀ ▶ parcourent les messages de la session. "
           "<b>Répondre…</b> ouvre l'envoi de texte prérempli « F1BAL de F4GOP : ». L'indicatif de l'expéditeur est aussi "
           "écrit au-dessus de chaque message dans le cadre « Messages reçus ». Les cases du bas permettent de ne "
           "plus l'ouvrir automatiquement ou de couper le bip ; on la rouvre par Action → Messages reçus… ou par un "
           "double-clic dans le cadre « Messages reçus ». Le cadre peut être masqué (menu Fenêtres) : les messages "
           "arrivent toujours dans la fenêtre « Message reçu »."))
s.append(P("<b>Traduction automatique</b> : un message écrit dans une autre langue que celle du programme est "
           "traduit à l'arrivée (par Internet, service gratuit). La traduction s'affiche en premier, l'original en "
           "dessous, en gris ; dans le cadre « Messages reçus », une ligne bleue « ↳ traduction (EN → FR) » s'ajoute. "
           "Le message part par radio tel que vous l'avez écrit : chacun le lit traduit dans sa propre langue. "
           "Sans Internet, le message s'affiche simplement tel quel. La case <b>Traduire</b> de la fenêtre "
           "« Message reçu » coupe la traduction."))
s.append(P("<b>Le correspondant a-t-il reçu mon message ?</b>"))
s.append(P("Dès qu'un message est bien reçu, le programme du correspondant renvoie un accusé de réception, par radio "
           "(ACK en DATAC0, si « ACK auto » est coché chez lui) et par Internet (si le réseau est actif). Dans la fenêtre "
           "<b>Envoi texte</b>, la liste <b>Messages envoyés — reçus par</b> montre pour chaque message : « ✓ F1BAL (+8 dB) » "
           "en vert quand il est arrivé, « en attente de l'accusé… » en orange, puis « pas d'accusé de réception » en rouge "
           "au bout de 3 minutes. Une ligne verte « ✓ F1BAL a bien reçu votre message » s'ajoute aussi dans le cadre "
           "« Messages reçus » et dans le journal des stations. Le correspondant doit avoir la version 0.43 ou plus récente "
           "pour les messages texte seuls ; un texte joint à une image est confirmé avec l'image."))
s.append(P("Police, taille et gras", "h2"))
s.append(P("Menu <b>Réglages → Police et taille du texte</b> : « Texte en gras » et la taille, de 8 à 14 points "
           "(9 = normale), appliqués tout de suite à tout le programme, listes comprises. Le choix de la police et des "
           "couleurs est dans Réglages → Apparence (case « Gras » aussi)."))
s.append(P("Style Classique ou Moderne", "h2"))
s.append(P("Réglages → Apparence → <b>Style</b> : <b>Classique (EasyPal)</b>, le look d'origine avec ses couleurs, ou "
           "<b>Moderne</b> : tout plat (sans relief), police moderne, onglets en pastilles, bouton « ▶ Émettre » mis en "
           "valeur, boutons de gauche plats et compacts (ÉMISSION dans la couleur d'accent), colonne de gauche en "
           "<b>cartes</b> (jauges RX / SNR arrondies, voyants sans contour), stations marquées ● (en ligne) ou ○ (entendues "
           "par radio), Rx Ok coloré selon le report (mêmes couleurs que la carte), et une <b>barre du haut</b> avec l'indicatif, la fréquence en grand (clic : menu des fréquences), "
           "l'état (réception, émission), les stations en ligne (clic : carte) et l'heure UTC. Cinq <b>ambiances</b> : "
           "Vert EasyPal (par défaut), Sombre, Clair, Vert radio, et <b>Personnalisée</b> : bouton « Couleur… » à côté de "
           "l'ambiance, on choisit une seule couleur et HFImage en tire tout le reste (barres dans cette couleur, fonds très "
           "clairs de la même teinte, accent plus foncé, texte noir ou blanc selon ce qui se lit le mieux). On passe de l'un "
           "à l'autre à tout moment, sans redémarrer."))
s.append(P("Horloge", "h2"))
s.append(P("L'horloge en bas à droite affiche l'heure de Windows (heure d'été comprise). Un clic dessus passe à "
           "« heure de Windows + UTC », puis « UTC seule », puis revient. Ce choix vaut pour tout le programme : "
           "journal des stations, messages, bandeau « Mes conditions de trafic », cartes QSL, Digi-Sites. En mode "
           "« UTC seule », les heures sont suivies de « UTC »."))
s.append(P("Envoyer un fichier", "h2"))
s.append(P("Bouton <b>Envoyer un fichier…</b> (onglet TX) ou menu Images : n'importe quel fichier (texte, PDF, ZIP, "
           "journal ADIF…). Il est compressé s'il y gagne, protégé par le même code fontaine que les images (BSR / FIX "
           "et ACK compris), et la durée d'émission est annoncée avant d'émettre. Avec le <b>mode hybride</b> coché, "
           "le fichier passe par Internet et seul le lien passe par radio (~11 s, ou 9 s en éclair) : idéal pour les gros fichiers. "
           "À la réception, il est rangé sous son nom d'origine dans le sous-dossier <b>fichiers</b> du dossier des "
           "images reçues ; double-clic dans l'historique pour l'ouvrir."))
s += tip("ordre de grandeur en DATAC1X : environ 8 ko par minute. Un fichier texte de 30 ko compressé à 9 ko "
         "passe en un peu plus d'une minute.")
s.append(P("Autres envois", "h2"))
s += B(["<b>Texte inclus</b> : un message joint à l'image, affiché dans « Messages reçus ».",
        "<b>Envoi Texte</b> : message seul.",
        "<b>Accord</b> (10 s) : porteuse pour régler l'ampli / la boîte d'accord. <b>ID</b> : indicatif en morse.",
        "<b>WAVE</b> / texte waterfall : fichiers begin.wav / end.wav, <b>texte ou image</b> dessinés dans le "
        "waterfall du correspondant (Action → Texte waterfall… → « Image… » pour une photo, un logo, votre QSL) ; "
        "« Sauve » en fait un begin.wav joué avant chaque émission, comme EasyPal.",
        "<b>IMG/QSL</b> : carte QSL avec photo de fond, indicatif, locator et report remplis automatiquement, "
        "police et couleurs au choix, <b>hauteur des bandeaux</b> du haut et du bas réglable (50 à 150 %, le texte "
        "suit). Les <b>textes se déplacent à la souris</b> dans l'aperçu (indicatif, locator, correspondant, "
        "date / fréquence / report, message) : cadre jaune au survol, place gardée pour les cartes suivantes, bouton "
        "« Textes à leur place d'origine »."])

# ------------------------------------------------------------------ 6 EasyPal
s.append(PageBreak())
s.append(P("6. Mode EasyPal (HamDRM) — compatible EasyPal / QSSTV", "h1"))
s.append(P("Choisissez <b>Mode : EasyPal</b> dans l'onglet TX. Une deuxième ligne apparaît avec les réglages "
           "d'EasyPal. Le signal est le signal HamDRM d'EasyPal et de QSSTV (OFDM DRM) : ces stations décodent vos "
           "images, et HFImage décode les leurs."))
s.append(img("en_tx.png", 165, "L'onglet TX en mode EasyPal (capture de l'interface en anglais) : ligne des réglages "
                               "EasyPal, image compressée en JPEG 2000 et durée d'émission exacte."))
s.append(P("Réglages EasyPal", "h2"))
s.append(table([["Réglage", "Valeurs", "Rôle"],
                ["Mode EasyPal", "A, B, E", "Robustesse du signal OFDM. A : le plus rapide, bonnes conditions. B : le mode "
                                            "HF habituel. E : le plus robuste (grandes distances, fort QSB)."],
                ["QAM", "QAM4, QAM16, QAM64", "Modulation : QAM4 robuste et lente, QAM64 rapide mais demande un signal fort."],
                ["Largeur", "2,2 kHz, 2,4 kHz", "Largeur de bande, notée comme dans EasyPal (2,3 / 2,5 kHz dans QSSTV, même "
                                                "signal). 2,2 kHz avec un filtre étroit."],
                ["Erreur (protection)", "Haute (HI), Normale (LO)", "Rendement de la correction d'erreurs. HI est plus robuste."],
                ["Reed-Solomon", "Aucun, RS1 … RS4", "Redondance en plus : l'image est reconstruite même avec des segments "
                                                    "perdus. <b>RS2 par défaut</b>. Lu par EasyPal et QSSTV."]],
               [32, 42, 96]))
s.append(Spacer(1, 6))
s.append(P("Les images partent en <b>JPEG 2000</b> (format habituel d'EasyPal) ou en JPEG, à la taille qui tient dans "
           "la durée choisie ; la durée exacte est calculée avant d'émettre. Le waterfall marque la bande exacte du mode "
           "reçu (A / B / E, 2,2 / 2,4 kHz)."))
s.append(P("Réglages conseillés", "h2"))
s.append(table([["Conditions", "Réglages", "S/B nécessaire (environ)"],
                ["Bonne propagation, signal fort", "A / QAM64", "15 dB"],
                ["HF habituelle (le plus courant)", "B / QAM16 / RS2", "10 dB sans QSB, 14 dB avec un QSB léger"],
                ["Propagation difficile, QSB", "B ou E / QAM4 / RS3 ou RS4", "6 dB sans QSB, une douzaine de dB avec un QSB moyen"]],
               [55, 55, 60]))
s.append(Spacer(1, 4))
s.append(P("Mesuré au simulateur : avec un QSB léger, B / QAM16 avec <b>RS2</b> donne une image complète dès 14 dB environ "
           "au lieu de 17 à 20 dB sans Reed-Solomon, pour une émission environ 18 % plus longue. HFImage émet aussi le "
           "signal EasyPal avec un facteur de crête réduit (+4 dB de niveau moyen pour la même puissance crête) et le "
           "décode avec une meilleure estimation de la fiabilité des bits (environ +0,5 dB en QAM16) : le signal reste "
           "100 % compatible EasyPal."))
s.append(P("Recevoir des images EasyPal", "h2"))
s += B(["Le panneau d'état affiche l'indicatif, « EP B/16 » (mode EasyPal / QAM), la largeur, le débit, les segments "
        "reçus et attendus, la position et les voyants Sync / Trame / Image / BSR.",
        "Si une image reste incomplète, le voyant BSR passe à l'orange et le journal vous invite à cliquer sur <b>BSR</b> : "
        "le BSR EasyPal demande à l'émetteur les segments manquants.",
        "Les textes envoyés par EasyPal / QSSTV (fichiers .txt) s'affichent dans les messages reçus avec l'indicatif."])
s.append(P("Répondre aux BSR (FIX)", "h2"))
s.append(P("Quand une station EasyPal ou QSSTV demande les segments manquants de votre dernière image (BSR), HFImage "
           "répond <b>automatiquement</b> par un FIX qui ne contient que ces segments (option de l'onglet Stations), ou "
           "à la main avec le bouton <b>FIX</b>."))
s.append(P("Textes en mode EasyPal", "h2"))
s.append(P("<b>Envoi Texte</b> en mode EasyPal envoie le message sous forme de fichier .txt, lisible par EasyPal et QSSTV."))
s.append(P("Hybride EasyPal", "h2"))
s.append(P("Avec <b>Mode hybride</b> coché en mode EasyPal, HFImage fait comme EasyPal : l'image est déposée par FTP dans "
           "<b>&lt;dossier&gt;/HybridFiles1/de_INDICATIF-n-nom.jpg</b>, et seule une courte annonce passe par radio, en "
           "mode <b>E / QAM4</b> (réglé automatiquement, et remis comme avant quand on décoche le mode hybride). Les "
           "stations EasyPal, QSSTV et HFImage qui la reçoivent téléchargent l'image et renvoient leur Rx Ok avec report."))
s += tip("comme dans EasyPal, l'annonce contient le serveur, l'identifiant et le mot de passe FTP <b>brouillés, pas "
         "chiffrés</b> : toute station qui la reçoit peut les relire. Utilisez un <b>compte FTP dédié</b>, limité à un "
         "seul dossier, et uniquement des caractères sans accents dans ces champs.", "Important")
s.append(P("Suivre le mode reçu", "h2"))
s.append(P("Avec « <b>Passer en émission sur le mode reçu</b> » coché (onglet Stations, coché par défaut), le mode "
           "d'émission change dès qu'une image ou un message commence à arriver dans l'autre famille de modes :"))
s += B(["réception EasyPal → mode <b>EasyPal</b> ; quand l'image est complète, le mode A / B / E, la largeur et la QAM "
        "de la station reçue sont repris aussi (sauf annonce hybride, toujours en E / QAM4) ;",
        "réception HFImage (DATAC) alors qu'on est en EasyPal → mode <b>Auto</b>.",
        "Rien ne change pendant vos émissions ni lors du décodage d'un fichier WAV. Chaque changement est noté dans le journal.",
        "Un mode <b>choisi à la main</b> dans l'onglet TX est gardé <b>10 minutes</b>, même si d'autres images arrivent "
        "dans l'autre famille de modes. Pour choisir toujours soi-même : décochez l'option."])

# ------------------------------------------------------------------ 6
s.append(PageBreak())
s.append(P("7. Stations en ligne, Rx Ok et carte", "h1"))
s.append(P("Avec <b>Réglages → Internet</b> coché, chaque HFImage ouvert se signale sur un serveur public "
           "(indicatif, locator, fréquence, émission / réception) : la liste <b>Stations</b> montre tout de suite "
           "les stations qui ont HFImage ouvert, avec leur fréquence. Aucune autre donnée n'est partagée."))
s.append(P("Dans la liste, <b>*</b> signale une station en émission (en rouge) et <b>HYB</b> une station en <b>mode "
           "hybride</b> (en bleu) : coché chez elle, ou annonce hybride entendue par radio dans la dernière demi-heure. "
           "Vos correspondants vous voient de même quand vous cochez « Mode hybride » (version 0.46 ou plus récente). "
           "Double-clic sur une station : le détail s'affiche dans le journal. Le séparateur entre la liste "
           "Stations et la liste Rx Ok se déplace à la souris ; sa position est gardée."))
s += B(["<b>Rx Ok</b> : les stations qui ont bien reçu l'image, avec leur <b>report en dB</b>, visibles par tous "
        "(par radio et par Internet).",
        "Clic sur une station : la <b>carte des stations</b> (comme Digi-Sites), avec le trajet et la distance. "
        "Elle montre en vert, avec un trait, les stations qui ont reçu <b>votre dernière image</b> ; la case "
        "« Aussi les autres stations (en jaune) » ajoute les stations en ligne ou entendues. "
        "« Coller la carte dans la fenêtre TX » pour l'envoyer en image. Le trait et le cadre de chaque station ont la "
        "<b>couleur de son report</b> (vert foncé : +5 dB et plus, vert clair, orange, rouge : moins de -10 dB ; "
        "légende en bas à gauche), et le report est écrit à côté de l'indicatif. Souris sur une station : prénom, "
        "locator, distance, report et heure. « <b>Tout voir</b> » cadre la carte sur toutes les stations. "
        "« <b>Copier la carte</b> » la met dans le presse-papiers, à coller (Ctrl+V) dans Teams, un forum, un e-mail… "
        "Les noms de villes et de pays qui tomberaient sous une station ne sont pas écrits, pour que les indicatifs "
        "restent lisibles quand les stations sont serrées.",
        "Pare-feu ou fournisseur d'accès qui bloque le port 1883 : HFImage essaie tout seul les autres accès du même "
        "serveur (8883 chiffré, puis 8884 et 8000 par le web) ; le journal indique celui qui a fonctionné."])
s.append(img("carte_stations.png", 150, "La carte des stations qui ont reçu l'image."))

# ------------------------------------------------------------------ 7
s.append(P("8. Mode hybride (modes HFImage) et site web", "h1"))
s.append(P("Mode hybride", "h2"))
s.append(P("L'image passe par votre <b>hébergement web</b> (FTP) ; seul le <b>lien</b> passe par radio "
           "(~11 s en DATAC3). Les stations la téléchargent automatiquement. Idéal pour les grandes images et les "
           "<b>GIF animés</b>. Réglages → Mode hybride : serveur FTP, identifiant, mot de passe, dossier et "
           "<b>lien public</b> de ce dossier ; « Tester le serveur » vérifie tout. Seul le lien passe par radio, "
           "jamais le mot de passe. Par défaut, l'image part en <b>pleine qualité</b> (format « original » : le "
           "fichier tel quel, sans réduction), quelle que soit sa taille. Les <b>fichiers</b> (Images → Envoyer un "
           "fichier…, ou glissés sur la fenêtre) partent aussi <b>sans limite de taille ni de type</b> en hybride, comme "
           "dans EasyPal (par radio : 16 Mo au plus). Depuis la 1.25, un fichier est déposé <b>tel quel, sous son nom "
           "d'origine</b> (ex. RK1AT_20261021_133402_TEST.mp4) : le lien public s'ouvre directement dans un navigateur."))
s.append(P("<b>Déposer d'avance</b> : en mode hybride, le bouton <b>⇪ Déposer</b> (onglet TX, à droite de WAV…) met "
           "l'image sur le serveur tout de suite, comme l'ancien EasyPal. Quand vient votre tour, <b>Émettre</b> envoie "
           "directement l'annonce radio, sans attendre le dépôt. Si l'image ou le serveur changent entre-temps, "
           "l'image est redéposée au moment d'émettre."))
s.append(P("Hybride éclair", "h2"))
s.append(P("Case <b>Éclair (9 s)</b>, à côté de « Mode hybride » (onglet TX), <b>cochée par défaut</b> depuis la 0.98. L'annonce radio ne porte plus le lien, seulement "
           "l'<b>empreinte</b> de l'image (SHA-256 abrégé), sa taille et son format, dans une trame de 14 octets. Depuis la "
           "version 0.93, cette trame part <b>3 fois en DATAC13</b> (mode très étroit de 200 Hz, fait pour passer dans le "
           "bruit et le QRM), puis 2 fois en DATAC0 (500 Hz) pour les stations qui ont une version plus ancienne : 9 s en tout. "
           "Le lien part en même temps par le serveur des stations en ligne ; la station qui entend l'annonce télécharge "
           "l'image et vérifie qu'elle a <b>exactement l'empreinte reçue par radio</b>."))
s.append(table([["Canal simulé", "S/B", "Éclair DATAC0 (avant 0.93)", "Éclair DATAC13 (0.93)"],
                ["Calme", "−5 dB", "15 %", "100 %"],
                ["Calme", "−7 dB", "0 %", "100 %"],
                ["Fading moyen", "−5 dB", "50 %", "100 %"],
                ["Fading moyen", "−7 dB", "20 %", "80 %"],
                ["Fading fort", "−5 dB", "35 %", "100 %"],
                ["Fading fort", "−7 dB", "5 %", "90 %"]], [40, 22, 55, 55]))
s.append(Spacer(1, 4))
s += B(["Les deux stations doivent avoir « <b>Stations en ligne</b> » activé (Réglages → Internet) et la version 0.71 ou plus récente.",
        "Si le serveur n'est pas joignable au moment d'émettre, HFImage envoie l'annonce normale (DATAC3) et le note dans "
        "le journal."])
s.append(P("Mes images sur le serveur", "h2"))
s.append(P("Chaque image envoyée en hybride est déposée sur votre serveur FTP sous un nom différent. Réglages → Mode "
           "hybride → « <b>Mes images gardées sur le serveur</b> » : <b>les 3 dernières</b> (par défaut), <b>la dernière "
           "seulement</b> ou <b>toutes</b>. Après chaque dépôt, les plus anciennes sont effacées. Seuls les fichiers déposés "
           "par HFImage avec votre indicatif sont concernés (hybride HFImage et hybride EasyPal) : les autres fichiers de "
           "votre site ne sont jamais touchés. Avec « la dernière seulement », une station qui télécharge encore l'image "
           "précédente ne la trouvera plus."))
s.append(P("Réception EZ Pix (W3WVG)", "h2"))
s.append(P("Depuis la 1.84, HFImage reconnaît le signal d'<b>EZ Pix</b> (GMSK 250 bauds autour de 1 500 Hz, ~5 s, "
           "toujours le même). EZ Pix dépose l'image sous le nom <b>EZPix/image1</b> sur le site de l'expéditeur, au moment d'émettre : "
           "HFImage lit la liste publique des stations EZ Pix (EZPixOnAir), cherche l'image déposée au moment du signal, la "
           "télécharge et l'affiche avec l'indicatif (« EZPix-HYB »). Il faut « Télécharger automatiquement les images "
           "hybrides reçues » coché ; les indicatifs bloqués et la taille maximale s'appliquent. Aucun accusé radio "
           "n'est émis vers une station EZ Pix."))
s.append(P("<b>Émission EZ Pix</b> (1.89) : choisissez le mode « <b>EZ Pix</b> » dans l'onglet TX (le mode hybride se coche "
           "tout seul). À l'émission, l'image est déposée dans <b>EZPix/image1</b> sur votre site (serveur FTP du mode hybride, "
           "à la racine du compte), vérifiée à l'adresse de votre fiche EZ Pix, puis le signal EZ Pix (5,4 s) part. Votre "
           "indicatif doit figurer dans la liste EZPixOnAir (lancez une fois EZ Pix avec ce site pour vous y inscrire)."))
s.append(P("Sécurité des téléchargements", "h2"))
s.append(P("<b>Indicatifs bloqués</b> (Réglages → Mode hybride, depuis la 1.82) : les images des indicatifs de cette "
           "liste (séparés par des virgules) ne sont ni affichées, ni enregistrées, ni téléchargées en hybride ; F4ABC "
           "bloque aussi F4ABC/P. Pour ne recevoir que par radio, décochez « Télécharger automatiquement les images "
           "hybrides reçues ». Rappel : sur l'air, n'importe qui peut émettre ; chaque opérateur est responsable de ce "
           "qu'il émet."))
s.append(P("Une annonce reçue par radio ne peut faire télécharger qu'un fichier de la <b>taille maximale choisie</b> (Réglages → Mode hybride → « Fichiers hybrides reçus : taille max », 200 Mo par défaut, ou sans limite), et seulement depuis "
           "une adresse Internet publique : l'ordinateur lui-même et les machines du réseau de la maison (box, NAS…) sont "
           "refusés, y compris après une redirection. Le test de votre propre serveur dans les Réglages n'est pas concerné. "
           "Les images et fichiers reçus restent toujours dans le dossier de réception, quel que soit l'indicatif annoncé."))
s.append(P("Site web / Digi-Sites", "h2"))
s.append(P("Menu <b>Images → Site web / Digi-Sites…</b> : comme EasyPal, chaque image reçue est mise en ligne "
           "sous le nom <b>image1</b>, sans extension comme EasyPal : c'est ce fichier que lit Digi-Sites (les précédentes "
           "glissent : image2, image3…), avec indicatif, date, mode "
           "et bande. Vos images émises vont dans TX1.jpg … TX5.jpg. Une page <b>hfimage.html</b> les présente "
           "(rafraîchie toutes les 5 minutes). Dans Digi-Sites : Setup → Edit site, et donnez l'adresse du fichier "
           "<b>image1</b> (affichée en vert dans la fenêtre). Par défaut, les images partent sur le serveur FTP du mode "
           "hybride ; avec <b>« Autre serveur FTP pour le site »</b>, elles partent sur un serveur à part (le mur d'un "
           "club, par exemple), comme le « FTP Upload » d'EasyPal, pendant que l'hybride reste sur le sien. Bouton "
           "<b>« Tester le serveur »</b> : dépôt d'un petit fichier et relecture par le lien public."))
s.append(P("Sites des stations", "h2"))
s.append(P("Menu <b>Images → Sites des stations…</b> (ou Action, ou clic droit sur la liste des stations) : comme "
           "Digi-Sites, qui n'est plus entretenu, une vignette par station avec la <b>dernière image qu'elle a reçue</b> "
           "(son image1), l'heure de cette image et la distance. Les stations HFImage en ligne qui mettent leurs images "
           "sur leur site y apparaissent toutes seules ; « <b>Ajouter une station…</b> » pour une station EasyPal (adresse "
           "de son image1, celle donnée à Digi-Sites). Relu toutes les 2 minutes, seulement si l'image a changé ; un clic "
           "l'agrandit, clic droit : page de la station."))
s += B(["<b>Dossier sur le serveur</b> : le dossier FTP, pas une adresse web. <b>Vide = racine du site</b>, comme EasyPal.",
        "<b>Lien public</b> : l'adresse web de ce dossier.",
        "Exemple qsl.net : serveur <b>ftp.qsl.net</b>, identifiant = votre indicatif (Réglages → Mode hybride), "
        "dossier <b>vide</b>, lien <b>https://www.qsl.net/f4gop</b> → adresse à donner à Digi-Sites : "
        "<b>https://www.qsl.net/f4gop/image1</b> ; page de vos images : https://www.qsl.net/f4gop/hfimage.html."])
s.append(img("webdlg.png", 110, "Réglages de la mise en ligne (serveur FTP du mode hybride)."))

# ------------------------------------------------------------------ 8
s.append(PageBreak())
s.append(P("9. Bruit, QSB et QRM", "h1"))
s += B(["<b>Bruit et QSB</b> : mode Auto + robustesse Auto. Si les pertes viennent par groupes, choisissez la "
        "robustesse « Forte ».",
        "<b>Bruit et QSB en mode EasyPal</b> : gardez Reed-Solomon (RS2 ou plus), baissez la QAM (QAM4) ou passez en "
        "mode E. Une image incomplète se complète par BSR / FIX.",
        "<b>QRM</b> : le <b>coupe-QRM</b> (Réglages → Audio) efface avant la démodulation tout ce qui est hors de "
        "la bande du mode (BLU voisine) et, dans la bande, les raies étroites (porteuse, CW, RTTY). Sans lui, "
        "une simple porteuse aussi forte que le signal suffisait à tout bloquer.",
        "Un brouilleur <b>large posé sur le signal</b> (autre BLU sur la même fréquence) ne peut pas être effacé : "
        "décalez la fréquence."])
s.append(P("Analyseur de réception", "h2"))
s.append(P("Pour comprendre une réception ratée : bouton <b>WAVE</b> → <b>● Enregistrer RX</b> (ou menu "
           "Fichiers → Enregistrement WAVE marche / arrêt) pendant la réception, puis "
           "<b>Fichiers → Décoder et analyser un fichier WAV…</b> (les images du fichier sont décodées et le rapport s'ouvre). HFImage indique le niveau d'entrée (écrêtage, trop "
           "faible), le brouillage étroit et sa fréquence, pour chaque mode les trames justes / perdues, le SNR, "
           "le décalage de fréquence entre les postes, le type de pertes (QSB ou isolées), ce que le coupe-QRM a "
           "sauvé, et le mode conseillé. « Copier le rapport » pour l'envoyer par message."))
s.append(img("analyse.png", 160, "L'analyseur : diagnostic en clair et SNR de chaque trame."))

# ------------------------------------------------------------------ 9
s.append(PageBreak())
s.append(P("10. Problèmes fréquents", "h1"))
s.append(table([["Symptôme", "Cause probable", "Que faire"],
                ["Le poste ne passe pas en émission", "PTT mal réglé, port COM occupé",
                 "Poste radio… → Tester le PTT ; fermer les logiciels qui tiennent le port ou passer par OmniRig"],
                ["Le poste émet mais sans puissance", "Poste pas en USB-DATA, mauvaise source audio, niveau trop faible",
                 "Mode « Data / Pkt » ou réglage « Poste pas en DATA » ; source « Arrière / Data » ; monter le niveau"],
                ["Rien n'est reçu", "Mauvaise entrée audio, volume Windows coupé",
                 "Réglages → Audio ; vérifier que le waterfall bouge ; analyser un enregistrement WAVE"],
                ["Trames détectées mais perdues", "Signal faible, QSB, QRM, écrêtage",
                 "Analyseur WAV ; mode Auto / robustesse Forte ; baisser le niveau d'entrée"],
                ["Image EasyPal incomplète", "QSB, segments perdus",
                 "Cliquer sur BSR ; demander à l'émetteur RS2 ou plus, QAM4 ou le mode E"],
                ["Image HFImage incomplète", "BSR pas entendu ou pas de FIX",
                 "Vérifier « envoyer un BSR » chez vous et « répondre aux BSR par un FIX » chez l'émetteur (onglet Stations)"],
                ["Images peu nettes", "Mode lent ou robustesse forte, durée courte",
                 "Robustesse Auto ; durée 3 min ; DATAC1X si les reports le permettent"],
                ["« Poste pas en mode DATA » et il ne bascule pas", "Réglage « Émettre sans rien dire » ou « Demander »",
                 "Réglages → « Poste pas en DATA avant d'émettre » → « Passer en DATA automatiquement » ; "
                 "le journal indique le réglage utilisé"],
                ["Le poste passe en USB-DATA au lieu de LSB-DATA", "Poste en USB avant l'émission",
                 "Mettre le poste en LSB : HFImage garde la bande latérale ; les deux stations doivent être sur la même"],
                ["Port COM absent de la liste", "Pilote non vu par Windows ou appareil débranché",
                 "Version 0.76 ou plus récente ; taper le nom du port (COM9) ; vérifier le Gestionnaire de périphériques"],
                ["Pas de stations en ligne", "Internet décoché ou serveur bloqué",
                 "Réglages → Internet ; HFImage essaie seul les ports 8883, 8884, 8000 ; voir le journal"],
                ["Hybride éclair : image non téléchargée", "« Stations en ligne » désactivé chez l'émetteur ou le récepteur",
                 "Activer Internet des deux côtés ; sinon décocher « Éclair (5 s) »"],
                ["Mode hybride : échec FTP", "Identifiants, dossier ou lien public",
                 "Réglages → Mode hybride → Tester le serveur"]],
               [45, 55, 70]))
s.append(Spacer(1, 8))
s.append(P("Diagnostic complet : <b>HFImage_F4GOP.exe --selftest rapport.txt</b> (modems dont EasyPal, carte, Internet, "
           "cartes son, ports COM, poste radio). Journal : Réglages → Ouvrir le journal."))
s.append(P("Crédits et licence", "h2"))
s.append(P("HFImage F4GOP — © 2026 Denis F4GOP — est un <b>logiciel libre et gratuit</b>, sous licence <b>GNU GPL v3</b> : "
           "vous pouvez l'utiliser, le copier, le partager et le modifier ; une version modifiée que vous distribuez doit "
           "rester sous la même licence, avec ses sources. Texte complet : menu <b>Infos → Licence (GNU GPL v3)</b>, ou "
           "fichier LICENSE sur la page GitHub du programme."))
s.append(P("Le modem EasyPal (HamDRM) provient de <b>QSSTV</b> (Johan Maes ON4QZ), lui-même issu de <b>Dream</b> "
           "(Volker Fischer, TU Darmstadt) et de <b>RXAMADRM</b> (Ties Bos PA0MBO), licence GNU GPL v3. Les modes DATAC "
           "utilisent <b>codec2</b> (David Rowe VK5DGR et contributeurs). Hommage à <b>Erik Sundstrup VK4AES</b>, "
           "auteur d'EasyPal."))
s.append(P("Contact", "h2"))
s.append(P("F4GOP — Denis — f4gop.denis@gmail.com<br/>Page du programme : "
           "github.com/f4gopdenis-cyber/HFImage_F4GOP (versions, nouveautés, sources).<br/>73 !"))

doc = Doc(OUT, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=20 * mm, bottomMargin=18 * mm,
          title="HFImage F4GOP — Mode d'emploi", author="F4GOP", subject=f"Version {VERSION}")
doc.multiBuild(s, onFirstPage=cover, onLaterPages=page_deco)
print(OUT, os.path.getsize(OUT))
