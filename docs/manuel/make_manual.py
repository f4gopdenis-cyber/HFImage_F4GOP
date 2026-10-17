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
    p = os.path.join(D, name)
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
    c.drawImage(os.path.join(D, "icone.png"), w / 2 - 32 * mm, h - 92 * mm, 64 * mm, 64 * mm, mask="auto")
    c.setFillColor(colors.white)
    c.setFont("DVB", 30)
    c.drawCentredString(w / 2, h - 108 * mm, "HFImage F4GOP")
    c.setFillColor(DARK)
    c.setFont("DVB", 20)
    c.drawCentredString(w / 2, h - 140 * mm, "Mode d'emploi")
    c.setFont("DV", 12)
    c.setFillColor(GREY)
    c.drawCentredString(w / 2, h - 150 * mm, "Images numériques en HF, façon EasyPal — sans SSTV")
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
s.append(P("HFImage F4GOP envoie et reçoit des <b>photos numériques par radio en HF</b>, comme EasyPal, mais avec "
           "un modem moderne (OFDM de codec2) et une correction d'erreurs par <b>code fontaine</b>. L'image reçue est "
           "<b>identique bit à bit</b> à l'image envoyée, ou elle n'est pas affichée : jamais d'image abîmée."))
s += B(["Photo 800×600 nette en environ 2 minutes (mode rapide DATAC1X, 2,2 kHz de large).",
        "Mode <b>Auto</b> : le mode et la robustesse s'adaptent aux reports des stations.",
        "<b>Coupe-QRM</b> à la réception : porteuses, CW, RTTY et BLU voisines effacées.",
        "Liste des <b>stations en ligne</b>, <b>Rx Ok</b> avec reports en dB, <b>carte</b> des stations.",
        "Mode <b>hybride</b> (image par Internet, lien par radio), GIF animés, carte <b>QSL</b>, texte dans le waterfall.",
        "Plus de 300 postes pilotés (Hamlib), Kenwood en direct, OmniRig, FLRig.",
        "<b>Galerie</b>, mise en ligne sur votre site (<b>Digi-Sites</b>), <b>analyseur</b> de réception.",
        "Mise à jour automatique, 5 langues."])
s += tip("les deux stations doivent utiliser HFImage. Le mode DATAC1X n'existe que dans HFImage.", "Important")
s.append(img("fenetre_principale.png", 170, "La fenêtre principale : panneau d'état et boutons à gauche, "
                                           "waterfall, liste des stations, image reçue, historique et messages."))

# ------------------------------------------------------------------ 2
s.append(PageBreak())
s.append(P("2. Installation et mises à jour", "h1"))
s.append(P("Installation", "h2"))
s += N(["Téléchargez <b>HFImage_F4GOP.exe</b> sur la page <i>Releases</i> du projet GitHub.",
        "Placez-le dans un dossier à vous, par exemple <b>C:\\Prg-Radio\\HFImage</b> (évitez « Program Files »).",
        "Au premier lancement, Windows SmartScreen peut afficher un avertissement : « Informations "
        "complémentaires », puis « Exécuter quand même »."])
s.append(P("Rien d'autre à installer : un seul fichier, Windows 10 / 11 64 bits."))
s.append(P("Mises à jour automatiques", "h2"))
s.append(P("Au démarrage (puis toutes les 3 heures), HFImage regarde sur GitHub s'il existe une version plus "
           "récente. Si oui, un <b>bandeau orange</b> apparaît en haut de la fenêtre : un clic, « Oui », et le "
           "programme se met à jour et redémarre tout seul. Menu <b>Infos → Rechercher une mise à jour</b> pour "
           "vérifier à tout moment."))
s += tip("après une mise à jour, si l'explorateur Windows affiche encore l'ancienne icône, redémarrez le PC "
         "(Windows garde les icônes en mémoire).")

# ------------------------------------------------------------------ 3
s.append(P("3. Premier réglage", "h1"))
s.append(P("Ouvrez <b>Réglages</b> (bouton ou menu). Les réglages sont enregistrés automatiquement."))
s.append(img("reglages.png", 165, "La fenêtre des réglages."))
s.append(P("Station", "h2"))
s.append(P("Indicatif et <b>locator</b> (6 caractères, ex. IN98QR) : ils servent aux annonces, à la carte "
           "des stations et à la carte QSL. Langue de l'interface : français, English, Deutsch, Español, Italiano."))
s.append(P("Audio", "h2"))
s += B(["<b>Sortie (vers le poste)</b> et <b>Entrée (depuis le poste)</b> : avec un Kenwood TS-890 / TS-990, "
        "« Haut-parleurs (USB Audio CODEC) » et « Microphone (USB Audio CODEC) », de préférence en [MME].",
        "<b>Tester la sortie (1 kHz)</b> : tonalité de 2 s sans PTT, pour vérifier la carte son.",
        "<b>Niveau d'émission</b> : réglez-le pour que l'<b>ALC ne bouge pas</b>. Un signal OFDM surmodulé "
        "devient illisible.",
        "<b>Coupe-QRM à la réception</b> : laissez-le coché (voir chapitre 8)."])
s.append(P("Poste radio (CAT / PTT)", "h2"))
s.append(P("Bouton <b>Poste radio…</b> : la fenêtre reprend l'onglet Radio de WSJT-X."))
s.append(img("poste_radio.png", 150, "Réglages du poste : poste, liaison CAT, PTT, source audio, mode, tests."))
s += B(["<b>Poste</b> : tapez une partie du nom dans « Rechercher » (ex. 7300, FT-991, TS-990). "
        "Kenwood TS-990S / TS-890S / TS-590 / TS-2000 / TS-480 : pilotés en direct, rien à installer. "
        "Autres postes : Hamlib, téléchargé une fois (bouton « Installer Hamlib », 3 Mo).",
        "<b>OmniRig</b> (Rig 1 / Rig 2) ou <b>FLRig</b> : pour partager le poste avec d'autres logiciels "
        "(logger, WSJT-X…).",
        "<b>Port série</b> et vitesse ; paramètres avancés si besoin (bits, stop, contrôle de flux, DTR/RTS forcés).",
        "<b>Méthode PTT</b> : CAT (recommandé), DTR ou RTS (y compris sur le port d'une interface à côté du poste), "
        "ou VOX.",
        "<b>Source audio en émission</b> : « Arrière / Data » (audio USB, ACC) ou « Avant / Micro ».",
        "<b>Mode</b> : « Data / Pkt » met le poste en USB-DATA avant chaque émission.",
        "<b>Tester le CAT</b> lit la fréquence ; <b>Tester le PTT</b> émet 1,5 s. Vert = OK, rouge = erreur "
        "affichée en dessous."])
s += tip("Kenwood TS-890 / TS-990 : poste en <b>USB-DATA</b>, source audio DATA = USB Audio, <b>DATA VOX sur "
         "OFF</b>, PTT CAT sur le port COM virtuel du poste à 115200 bauds, source « Arrière / Data ». "
         "Le port doit être libre : fermez ARCP ou le logger, ou passez par OmniRig.", "Kenwood")

# ------------------------------------------------------------------ 4
s.append(PageBreak())
s.append(P("4. Recevoir des images", "h1"))
s.append(P("L'écoute démarre toute seule si l'entrée audio est réglée (bouton <b>Écoute</b> pour arrêter / "
           "reprendre). Rien à choisir : <b>tous les modes</b> sont décodés en même temps."))
s += B(["<b>Panneau d'état</b> (en haut à gauche) : indicatif de la station reçue, fréquence et mode du poste, "
        "niveau RX, SNR, mode, débit, segments reçus, voyants Signal / Sync / Trame / Image / BSR.",
        "<b>Aperçu rapide</b> : une petite image arrive en ~20 s, puis l'image complète la remplace.",
        "<b>Historique</b> à droite : clic pour réafficher, double-clic pour le plein format.",
        "<b>BSR / ACK automatiques</b> : s'il manque des morceaux à la fin, HFImage les demande (BSR) ; "
        "l'émetteur ne renvoie que ce qui manque (FIX). Une fois l'image complète, un accusé (ACK) avec "
        "votre report part vers l'émetteur.",
        "Les images sont rangées dans le dossier choisi (Réglages → Dossier des images reçues), bouton "
        "<b>Dossier</b> pour l'ouvrir.",
        "<b>Relire RX</b> : redécode les 15 dernières minutes (si une image a été manquée)."])
s.append(P("Galerie", "h2"))
s.append(P("Onglet <b>Galerie</b> : les 30, 60 ou 100 dernières images reçues (« de F4EMK ») ou envoyées. Clic : "
           "afficher ; double-clic : plein format ; clic droit : renvoyer l'image, voir la station sur la carte, "
           "ouvrir le dossier, retirer de la galerie."))
s.append(img("galerie.png", 160, "La galerie des dernières images reçues."))

# ------------------------------------------------------------------ 5
s.append(PageBreak())
s.append(P("5. Envoyer une image", "h1"))
s += N(["Onglet <b>TX</b> → <b>Ouvrir une image…</b> (JPG, PNG, GIF, WebP, AVIF, SVG, BMP…).",
        "Choisissez le <b>Mode</b> (Auto conseillé), la <b>Durée max</b> (120 s par défaut), la <b>Largeur</b> "
        "(auto), le <b>Format</b> (avif conseillé) et la <b>Robustesse</b> (Auto conseillé).",
        "HFImage calcule tout seul la taille et la qualité qui tiennent dans la durée : l'image compressée "
        "s'affiche avec sa taille et sa qualité.",
        "<b>▶ Émettre</b> (ou bouton ÉMISSION). La barre de progression suit l'émission.",
        "Si des stations demandent des morceaux (BSR), <b>+ Compléter</b> / FIX envoie seulement ce qui manque."])
s.append(img("tx.png", 165, "L'onglet TX : mode Auto, robustesse, image compressée et durée d'émission."))
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
s.append(P("Envoyer un fichier", "h2"))
s.append(P("Bouton <b>Envoyer un fichier…</b> (onglet TX) ou menu Images : n'importe quel fichier (texte, PDF, ZIP, "
           "journal ADIF…). Il est compressé s'il y gagne, protégé par le même code fontaine que les images (BSR / FIX "
           "et ACK compris), et la durée d'émission est annoncée avant d'émettre. Avec le <b>mode hybride</b> coché, "
           "le fichier passe par Internet et seul le lien passe par radio (~11 s) : idéal pour les gros fichiers. "
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
        "police et couleurs au choix."])

# ------------------------------------------------------------------ 6
s.append(PageBreak())
s.append(P("6. Stations en ligne, Rx Ok et carte", "h1"))
s.append(P("Avec <b>Réglages → Internet</b> coché, chaque HFImage ouvert se signale sur un serveur public "
           "(indicatif, locator, fréquence, émission / réception) : la liste <b>Stations</b> montre tout de suite "
           "les stations qui ont HFImage ouvert, avec leur fréquence. Aucune autre donnée n'est partagée."))
s += B(["<b>Rx Ok</b> : les stations qui ont bien reçu l'image, avec leur <b>report en dB</b>, visibles par tous "
        "(par radio et par Internet).",
        "Clic sur une station : la <b>carte des stations</b> (comme Digi-Sites), avec le trajet et la distance. "
        "« Coller la carte dans la fenêtre TX » pour l'envoyer en image.",
        "Pare-feu qui bloque le port 1883 : essayez 8883 (chiffré) ou 8000 (web)."])
s.append(img("carte_stations.png", 150, "La carte des stations qui ont reçu l'image."))

# ------------------------------------------------------------------ 7
s.append(P("7. Mode hybride et site web", "h1"))
s.append(P("Mode hybride", "h2"))
s.append(P("L'image passe par votre <b>hébergement web</b> (FTP) ; seul le <b>lien</b> passe par radio "
           "(~11 s en DATAC3). Les stations la téléchargent automatiquement. Idéal pour les grandes images et les "
           "<b>GIF animés</b>. Réglages → Mode hybride : serveur FTP, identifiant, mot de passe, dossier et "
           "<b>lien public</b> de ce dossier ; « Tester le serveur » vérifie tout. Seul le lien passe par radio, "
           "jamais le mot de passe."))
s.append(P("Site web / Digi-Sites", "h2"))
s.append(P("Menu <b>Images → Site web / Digi-Sites…</b> : comme EasyPal, chaque image reçue est mise en ligne "
           "sous le nom <b>image1.jpg</b> (les précédentes glissent : image2, image3…), avec indicatif, date, mode "
           "et bande. Vos images émises vont dans TX1.jpg … TX5.jpg. Une page <b>hfimage.html</b> les présente "
           "(rafraîchie toutes les 5 minutes). Dans Digi-Sites : Setup → Edit site, et donnez l'adresse de la page."))
s += B(["<b>Dossier sur le serveur</b> : le dossier FTP, pas une adresse web. <b>Vide = racine du site</b>, comme EasyPal.",
        "<b>Lien public</b> : l'adresse web de ce dossier.",
        "Exemple qsl.net : serveur <b>ftp.qsl.net</b>, identifiant = votre indicatif (Réglages → Mode hybride), "
        "dossier <b>vide</b>, lien <b>https://www.qsl.net/f4gop</b> → page à donner à Digi-Sites : "
        "<b>https://www.qsl.net/f4gop/hfimage.html</b>."])
s.append(img("webdlg.png", 110, "Réglages de la mise en ligne (serveur FTP du mode hybride)."))

# ------------------------------------------------------------------ 8
s.append(PageBreak())
s.append(P("8. Bruit, QSB et QRM", "h1"))
s += B(["<b>Bruit et QSB</b> : mode Auto + robustesse Auto. Si les pertes viennent par groupes, choisissez la "
        "robustesse « Forte ».",
        "<b>QRM</b> : le <b>coupe-QRM</b> (Réglages → Audio) efface avant la démodulation tout ce qui est hors de "
        "la bande du mode (BLU voisine) et, dans la bande, les raies étroites (porteuse, CW, RTTY). Sans lui, "
        "une simple porteuse aussi forte que le signal suffisait à tout bloquer.",
        "Un brouilleur <b>large posé sur le signal</b> (autre BLU sur la même fréquence) ne peut pas être effacé : "
        "décalez la fréquence."])
s.append(P("Analyseur de réception", "h2"))
s.append(P("Pour comprendre une réception ratée : bouton <b>WAVE</b> → <b>● Enregistrer RX</b> (ou menu "
           "Fichiers → Enregistrement WAVE marche / arrêt) pendant la réception, puis "
           "<b>Fichiers → Analyser un enregistrement WAV…</b>. HFImage indique le niveau d'entrée (écrêtage, trop "
           "faible), le brouillage étroit et sa fréquence, pour chaque mode les trames justes / perdues, le SNR, "
           "le décalage de fréquence entre les postes, le type de pertes (QSB ou isolées), ce que le coupe-QRM a "
           "sauvé, et le mode conseillé. « Copier le rapport » pour l'envoyer par message."))
s.append(img("analyse.png", 160, "L'analyseur : diagnostic en clair et SNR de chaque trame."))

# ------------------------------------------------------------------ 9
s.append(PageBreak())
s.append(P("9. Problèmes fréquents", "h1"))
s.append(table([["Symptôme", "Cause probable", "Que faire"],
                ["Le poste ne passe pas en émission", "PTT mal réglé, port COM occupé",
                 "Poste radio… → Tester le PTT ; fermer les logiciels qui tiennent le port ou passer par OmniRig"],
                ["Le poste émet mais sans puissance", "Poste pas en USB-DATA, mauvaise source audio, niveau trop faible",
                 "Mode « Data / Pkt » ou réglage « Poste pas en DATA » ; source « Arrière / Data » ; monter le niveau"],
                ["Rien n'est reçu", "Mauvaise entrée audio, volume Windows coupé",
                 "Réglages → Audio ; vérifier que le waterfall bouge ; analyser un enregistrement WAVE"],
                ["Trames détectées mais perdues", "Signal faible, QSB, QRM, écrêtage",
                 "Analyseur WAV ; mode Auto / robustesse Forte ; baisser le niveau d'entrée"],
                ["Images peu nettes", "Mode lent ou robustesse forte, durée courte",
                 "Robustesse Auto ; durée 3 min ; DATAC1X si les reports le permettent"],
                ["« Poste pas en mode DATA »", "Kenwood en USB avec audio arrière",
                 "« Passer en USB-DATA » (mémorisable) ou source « Avant / Micro »"],
                ["Pas de stations en ligne", "Internet décoché ou port 1883 bloqué",
                 "Réglages → Internet ; essayer le port 8883 ou 8000"],
                ["Mode hybride : échec FTP", "Identifiants, dossier ou lien public",
                 "Réglages → Mode hybride → Tester le serveur"]],
               [45, 55, 70]))
s.append(Spacer(1, 8))
s.append(P("Diagnostic complet : <b>HFImage_F4GOP.exe --selftest rapport.txt</b> (modems, carte, Internet, "
           "cartes son, ports COM, poste radio). Journal : Réglages → Ouvrir le journal."))
s.append(P("Contact", "h2"))
s.append(P("F4GOP — Denis — f4gop.denis@gmail.com<br/>Page du programme : "
           "github.com/f4gopdenis-cyber/HFImage_F4GOP (versions, nouveautés, sources).<br/>73 !"))

doc = Doc(OUT, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=20 * mm, bottomMargin=18 * mm,
          title="HFImage F4GOP — Mode d'emploi", author="F4GOP", subject=f"Version {VERSION}")
doc.multiBuild(s, onFirstPage=cover, onLaterPages=page_deco)
print(OUT, os.path.getsize(OUT))
