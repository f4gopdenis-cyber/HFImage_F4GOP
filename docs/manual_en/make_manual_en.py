"""HFImage F4GOP user manual in English (PDF)."""
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
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(D, "HFImage_user_manual_EN.pdf")

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
               os.path.join(D, "..", "manuel", name)) if os.path.exists(q)), name)
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


def tip(text, title="Tip"):
    t = Table([[Paragraph(f"<b>{title}:</b> {text}", st["tip"])]], colWidths=[170 * mm])
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
        c.drawString(20 * mm, h - 12 * mm, f"HFImage F4GOP {VERSION} — user manual")
        c.drawRightString(w - 20 * mm, 10 * mm, f"{doc.page}")
        c.drawString(20 * mm, 10 * mm, "github.com/f4gopdenis-cyber/HFImage_F4GOP")
    c.restoreState()


def cover(c, doc):
    w, h = A4
    c.saveState()
    c.setFillColor(DARK)
    c.rect(0, h - 120 * mm, w, 120 * mm, fill=1, stroke=0)
    c.drawImage(os.path.join(D, "..", "images", "icone.png"), w / 2 - 32 * mm, h - 92 * mm, 64 * mm, 64 * mm, mask="auto")
    c.setFillColor(colors.white)
    c.setFont("DVB", 30)
    c.drawCentredString(w / 2, h - 108 * mm, "HFImage F4GOP")
    c.setFillColor(DARK)
    c.setFont("DVB", 20)
    c.drawCentredString(w / 2, h - 140 * mm, "User manual")
    c.setFont("DV", 12)
    c.setFillColor(GREY)
    c.drawCentredString(w / 2, h - 150 * mm, "Digital images over HF — HFImage modes and EasyPal / QSSTV (HamDRM)")
    c.drawCentredString(w / 2, h - 158 * mm, f"Version {VERSION}")
    c.setFont("DV", 10)
    c.drawCentredString(w / 2, 30 * mm, "F4GOP — Denis — IN98QR — f4gop.denis@gmail.com")
    c.drawCentredString(w / 2, 24 * mm, "github.com/f4gopdenis-cyber/HFImage_F4GOP")
    c.restoreState()


s = []
s.append(PageBreak())
s.append(Paragraph("Contents", ParagraphStyle("toct", parent=st["h1"])))
toc = TableOfContents()
toc.levelStyles = [ParagraphStyle("t1", fontName="DVB", fontSize=10.5, leading=15, leftIndent=0),
                   ParagraphStyle("t2", fontName="DV", fontSize=9.5, leading=12.5, leftIndent=12, textColor=GREY)]
s.append(toc)
s.append(PageBreak())

# ------------------------------------------------------------------ 1
s.append(P("1. Overview", "h1"))
s.append(P("<i>Dedicated to Erik Sundstrup VK4AES (SK), creator of EasyPal, in tribute to his work. HFImage was designed "
           "by Denis F4GOP, who chose each of its features, tested it on the air and improved it with users' feedback; "
           "the code was written largely with the help of the artificial intelligence Claude (Anthropic).</i>"))
s.append(P("HFImage F4GOP sends and receives <b>digital pictures over HF radio</b>. One program covers two families "
           "of modes, and it <b>always listens to both at the same time</b>:"))
s += B(["<b>HFImage modes (DATAC)</b>: a modern OFDM modem (codec2) with <b>fountain-code</b> error correction. "
        "The received picture is <b>bit-for-bit identical</b> to the one sent, or it is not shown at all: never a "
        "damaged picture. Both stations must run HFImage.",
        "<b>EasyPal mode (HamDRM)</b>: the digital SSTV mode used by <b>EasyPal</b> and <b>QSSTV</b>. HFImage "
        "exchanges pictures, texts and hybrid pictures with stations running those programs, so this mode can live "
        "on now that EasyPal is no longer updated since the death of its author, Erik Sundstrup VK4AES."])
s.append(P("Main features", "h2"))
s += B(["Sharp 800×600 photo in about 2 minutes (fast DATAC1X mode, 2.2 kHz wide).",
        "<b>Auto</b> mode: mode and robustness adapt to the reports of the stations.",
        "EasyPal / QSSTV compatible mode: modes A / B / E, QAM4 / 16 / 64, 2.2 or 2.4 kHz, Reed-Solomon, BSR / FIX, "
        "hybrid mode.",
        "Transmission <b>follows the received mode</b>: answer each station in the mode it uses.",
        "<b>QRM cutter</b> on receive: carriers, CW, RTTY and adjacent SSB signals removed.",
        "<b>Stations online</b> list, <b>Rx Ok</b> with reports in dB, <b>map</b> of stations.",
        "<b>Hybrid</b> mode (picture via the Internet, link over the air), including <b>flash hybrid</b>: a robust 9 s "
        "announcement over the air.",
        "Up to <b>4 correspondents' pictures</b> inserted into yours, animated GIFs, <b>QSL</b> card, text in the waterfall.",
        "<b>Separate windows</b>: waterfall, gallery, station list… placed where you want, even on another screen.",
        "More than 300 radios controlled (Hamlib), Kenwood direct, OmniRig, FLRig.",
        "<b>Gallery</b>, upload to your website (<b>Digi-Sites</b>), reception <b>analyser</b>.",
        "Automatic updates, 5 languages (English, French, German, Spanish, Italian)."])
s.append(img("en_main.png", 170, "Main window: status panel and buttons on the left, waterfall, stations and Rx Ok "
                                 "lists, received picture, history and received messages."))

# ------------------------------------------------------------------ 2
s.append(PageBreak())
s.append(P("2. Installation and updates", "h1"))
s.append(P("Installation", "h2"))
s += N(["Download <b>HFImage_F4GOP.exe</b> from the <i>Releases</i> page of the GitHub project.",
        "Put it in a folder of your own, for example <b>C:\\Radio\\HFImage</b> (avoid “Program Files”).",
        "On first start, Windows SmartScreen may show a warning: click “More info”, then “Run anyway”.",
        "On first start, the <b>licence</b> is shown (free software, GNU GPL v3; French text with an English summary at "
        "the end): read it and click “<b>I accept</b>”. Read it again any time: Info → Licence."])
s.append(P("Nothing else to install: a single file, Windows 8.1 / 10 / 11 64-bit. For <b>Windows 7 SP1 or 8</b> "
           "(64-bit), take <b>HFImage_F4GOP_Win7.exe</b> from the same page: same program, updated with its own "
           "version; only SVG pictures cannot be displayed there."))
s.append(P("Linux", "h2"))
s.append(P("Since version 1.23, HFImage is also available for 64-bit <b>Linux</b> (Ubuntu 22.04 and newer, Debian 12, "
           "Linux Mint 21, etc.): same program, same modes, compatible with Windows stations."))
s += N(["Download <b>HFImage_F4GOP_Linux.tar.gz</b> from the same GitHub page and open it (double-click, or "
        "<b>tar xzf HFImage_F4GOP_Linux.tar.gz</b>): it holds a single file, <b>HFImage_F4GOP_Linux</b>.",
        "Put it in a folder of your own (for example <b>~/HFImage</b>) and start it with a double-click. On first start it "
        "adds itself to the applications menu (Ham Radio section).",
        "To control the radio through Hamlib: <b>sudo apt install libhamlib-utils</b>. Direct Kenwood control, FLRig and "
        "serial-port PTT need nothing else; OmniRig only exists on Windows.",
        "Serial ports (/dev/ttyUSB0…): your account must be in the <b>dialout</b> group: "
        "<b>sudo usermod -aG dialout $USER</b>, then log out and back in."])
s.append(P("Updates work as on Windows (orange banner). The FTP password is kept in the settings file, readable by your "
           "account only."))
s.append(P("Automatic updates", "h2"))
s.append(P("At start-up (then every 3 hours), HFImage checks GitHub for a newer version. If there is one, an "
           "<b>orange banner</b> appears at the top of the window: one click, “Yes”, and the program updates itself "
           "and restarts. Menu <b>Info → Check for updates</b> to check at any time. The list of changes of every "
           "version is on the GitHub page (CHANGELOG)."))
s += tip("after an update, if Windows Explorer still shows the old icon, restart the PC (Windows caches icons).")

# ------------------------------------------------------------------ 3
s.append(P("3. First setup", "h1"))
s.append(P("On first start, the <b>setup assistant</b> opens by itself, in 3 steps: callsign and locator, radio "
           "sound card (output and input, with a 1 kHz test without transmitting), then the radio (CAT / PTT, with "
           "Hamlib installation if needed). It is also in <b>Settings → Setup assistant…</b>. Everything else is in "
           "<b>Settings</b>."))
s.append(P("<b>Listeners (SWL)</b>: enter your listener ID instead of a callsign (e.g. <b>F-12345</b>, "
           "<b>PA0041SWL</b>, <b>14VD274</b>). HFImage receives everything as usual and sends your reports <b>via the "
           "Internet</b> (Rx Ok, station map), but <b>never</b> transmits: no picture, no ACK, no BSR over the air."))
s.append(P("Open <b>Settings</b> (button or menu). Settings are saved automatically."))
s.append(img("en_settings.png", 165, "The Settings window."))
s.append(P("Station", "h2"))
s.append(P("Callsign and <b>locator</b> (6 characters, e.g. IN98QR): used in the announcements, the station map "
           "and the QSL card. Interface language: English, Français, Deutsch, Español, Italiano."))
s.append(P("<b>First name</b>: shown next to your callsign in the other users' Rx Ok list "
           "(“F4GOP  +5 dB  Denis”). Do not type it in the <b>Callsign</b> box: over the air the callsign is limited "
           "to 8 characters, and “M7WUV ANDY” arrived cut to “M7WUV AN” (the same station appeared twice). "
           "Since version 1.12, a name typed after the callsign is moved to the First name box automatically."))
s.append(P("Audio", "h2"))
s += B(["<b>Output (to radio)</b> and <b>Input (from radio)</b>: with a Kenwood TS-890 / TS-990, "
        "“Speakers (USB Audio CODEC)” and “Microphone (USB Audio CODEC)”. Each sound card appears only once, "
        "with its full name: HFImage picks the most reliable Windows interface itself and tries the others "
        "automatically if it fails.",
        "<b>Test output (1 kHz)</b>: 2 s tone without PTT, to check the sound card.",
        "<b>Transmit level</b>: set it so that the <b>ALC does not move</b>. An over-driven OFDM signal becomes "
        "unreadable.",
        "<b>QRM cutter on receive</b>: keep it ticked (see chapter 10)."])
s.append(P("Radio (CAT / PTT)", "h2"))
s.append(P("<b>Radio…</b> button: the window follows the Radio tab of WSJT-X."))
s.append(img("poste_radio.png", 140, "Radio settings: rig, CAT link, PTT, audio source, mode, tests "
                                      "(screenshot of the French interface)."))
s += B(["<b>Radio</b>: type part of the name in “Search” (e.g. 7300, FT-991, TS-990). "
        "Kenwood TS-990S / TS-890S / TS-590 / TS-2000 / TS-480 are driven directly, nothing to install. "
        "Other radios: Hamlib, downloaded once (“Install Hamlib” button, 3 MB).",
        "<b>OmniRig</b> (Rig 1 / Rig 2) or <b>FLRig</b>: to share the radio with other programs (logger, WSJT-X…).",
        "<b>SunSDR / ExpertSDR (TCI)</b>: HFImage talks directly to ExpertSDR through TCI (Options → TCI in ExpertSDR, "
        "port 40001; “Network server” 127.0.0.1:40001, or the address of the PC running ExpertSDR): frequency, mode "
        "(DIGL / DIGU) and PTT “CAT”, without RadioSync or a virtual COM port. Audio goes through ExpertSDR's virtual "
        "audio cables (VAC). Also works with other SDRs that speak TCI.",
        "<b>Custom CAT commands (as in EasyPal)</b>: you write the commands sent to the radio yourself, in hexadecimal "
        "(Icom CI-V: FEFE5EE01C0001FD) or as text (Kenwood: TX1;): <b>Initial</b> strings 1 and 2 (when the port opens), "
        "<b>PTT ON</b> / <b>PTT OFF</b> (with PTT method “CAT”), <b>Exit</b> strings 1 and 2 (when the program closes) and "
        "the delay between commands. EasyPal settings (“\\$…\\”) can be pasted as they are. In this mode the radio "
        "frequency is not read.",
        "<b>Serial port</b> and speed; advanced parameters if needed (bits, stop, flow control, forced DTR / RTS). "
        "The list shows every active Windows port (Prolific, CH340, Silicon Labs and virtual ports included); you can "
        "also type the port name, e.g. COM9.",
        "<b>PTT method</b>: CAT (recommended), DTR or RTS (also on the port of an interface next to the radio), "
        "or VOX.",
        "<b>Transmit audio source</b>: “Rear / Data” (USB audio, ACC) or “Front / Mic”. Choose “Front / Mic” if your "
        "radio transmits USB audio without DATA mode: HFImage then leaves its mode alone.",
        "<b>Mode</b>: “Data / Pkt” puts the radio in DATA before each transmission, keeping its sideband "
        "(LSB → LSB-DATA, USB → USB-DATA).",
        "<b>Test CAT</b> reads the frequency; <b>Test PTT</b> transmits for 1.5 s. Green = OK, red = error shown "
        "below."])
s.append(P("Radio not in DATA before transmitting", "h2"))
s.append(P("As soon as CAT is connected, HFImage reads the radio's mode before each transmission, <b>whatever the PTT "
           "method</b> (CAT, RTS, DTR or VOX). If it is not in DATA, the setting “<b>Radio not in DATA before "
           "transmitting</b>” (Settings, below the radio buttons) decides:"))
s += B(["<b>Switch to DATA automatically (USB-DATA / LSB-DATA)</b>: the default. The radio goes to DATA <b>keeping "
        "its sideband</b>: in LSB (40 and 80 m, as in EasyPal) it goes to <b>LSB-DATA</b>, in USB to <b>USB-DATA</b>. "
        "The log shows it (“TS-890S switched to LSB-DATA1 by CAT”).",
        "<b>Ask</b>: a window offers to switch to DATA, transmit anyway or cancel.",
        "<b>Transmit without asking</b>: the radio stays in its mode; the log reminds you at each transmission."])
s.append(P("Kenwood TS-990: a single command (LSB-D1 or USB-D1). TS-890, TS-590, TS-480: LSB or USB, then DATA. Other "
           "radios: PKTLSB / PKTUSB (Hamlib), DIG-L / DIG-U (OmniRig), FLRig's DATA mode. With RTS, DTR or VOX PTT, a "
           "failed switch to DATA is only reported in the log and does not block the transmission."))
s += tip("Kenwood TS-890 / TS-990: DATA audio source = USB Audio, <b>DATA VOX OFF</b>, CAT PTT on the radio's virtual "
         "COM port at 115200 baud, source “Rear / Data”. The radio switches to LSB-DATA or USB-DATA by itself. The "
         "port must be free: close ARCP or your logger, or go through OmniRig. If the input and output of the USB codec "
         "have the same name in Windows, HFImage always picks the right one.", "Kenwood")
s.append(P("Layout: separate windows", "h2"))
s.append(P("Menu <b>Windows</b>: tick an area to turn it into a <b>separate window</b>, placed and sized wherever you want, "
           "even on another screen: <b>panel and buttons</b>, <b>waterfall</b>, <b>stations heard</b>, <b>Stations</b> tab and "
           "<b>gallery</b>. The RX and TX tabs and the log stay in the main window. The <b>Simulation</b> tab (simulated HF channel, to try without a radio) is shown with Files → Simulation tab."))
s += B(["Separate windows always stay <b>in front of</b> the main window and are minimised with it.",
        "Untick the area, or close its window, to put it back. “Put everything back in the main window” gathers "
        "everything; “Settings → Original window layout” too.",
        "The layout is kept from one session to the next.",
        "<b>Show the history</b> and <b>Show received messages</b> (RX tab) hide these lists: without both, the received "
        "picture uses the whole width."])

# ------------------------------------------------------------------ 4
s.append(P("Changing frequency", "h2"))
s.append(P("With a CAT link, the <b>“Frequency ▾”</b> button (right of “Wait for clear frequency”), or a <b>click on the "
           "frequency</b> shown (panel at the top left, marked ▾, or the status bar) opens the "
           "picture-frequency menu: <b>3.733 – 7.058 – 14.233 – 21.340 – 28.680 MHz</b>. One click and the radio goes "
           "there, with that frequency's sideband (LSB below 10 MHz, USB above); if it was in DATA, it stays in DATA. "
           "Same menu in <b>Action → Go to a frequency</b>, with “Other frequency…” and “Edit the list…” (one line per "
           "frequency, e.g. “7.058 LSB”). Right-click in the station list: <b>Go to this station's frequency</b>. "
           "Never during a transmission. (Idea from Allan G7VQV.)"))
s.append(P("Several frequencies at once (profiles)", "h2"))
s.append(P("One HFImage listens to one frequency (one audio input). To monitor e.g. 40 m, 20 m and 28.680 MHz at the "
           "same time, you need one receiver per frequency (often an <b>SDR</b> with several bands, each sent to a "
           "virtual audio cable such as VB-Cable) and one HFImage per frequency: <b>Settings → Open another instance "
           "(profile)…</b>, give a name (e.g. “20m”). Each profile has its <b>own settings</b> (audio input, radio, "
           "picture folder, in Documents\\HFImage\\20m); on first start it copies your usual settings and the setup "
           "assistant lets you choose its audio input. HFImage offers to create a desktop shortcut (“HFImage 20m”) that "
           "runs <b>HFImage_F4GOP.exe --profil 20m</b>. The profile name is shown in the window title."))
s.append(P("4. Receiving pictures", "h1"))
s.append(P("Listening starts by itself when the audio input is set (<b>Receive</b> button to stop / resume). "
           "Nothing to choose: <b>all modes are decoded at the same time</b> — DATAC1X, DATAC1, DATAC3, DATAC4 "
           "<b>and</b> EasyPal (HamDRM), whatever mode is selected for transmission."))
s += B(["<b>Status panel</b> (top left): callsign of the station received, radio frequency and mode, RX level, "
        "SNR, mode, bandwidth, data rate, segments received, Signal / Sync / Frame / Image / BSR lights. Right of the "
        "table, a <b>thumbnail of the last picture received</b>, with the callsign, first name and distance of the "
        "station; a click shows it in the RX tab.",
        "When a picture starts to arrive while the <b>TX tab</b> is displayed, HFImage switches to the <b>RX tab</b> "
        "so that you see it come in (except during your own transmissions).",
        "<b>Quick preview</b> (HFImage modes): a small picture arrives in ~20 s, then the full picture replaces it.",
        "<b>History</b> on the right: click to show again, double-click for full size (can be hidden, menu Windows).",
        "<b>Zoom</b>: mouse wheel on the picture to enlarge / reduce around the pointer (up to ×16), hold the left "
        "button to move the enlarged picture, right-click to return to the whole picture.",
        "<b>Automatic BSR / ACK</b> (HFImage modes): if pieces are missing at the end, HFImage asks for them (BSR); "
        "the sender sends only what is missing (FIX). Once the picture is complete, an acknowledgement (ACK) with "
        "your report goes back to the sender.",
        "Pictures are stored in the chosen folder (Settings → Received images folder), in a <b>sub-folder per day</b> "
        "(2026-10-18…), <b>one copy per picture</b> (the received AVIF, JPEG… file); <b>Folder</b> button to open it. "
        "Received files stay in the “fichiers” sub-folder.",
        "<b>Automatic cleaning</b> (Settings, below the folder): day folders older than <b>30 days</b> (adjustable) are "
        "deleted, sent pictures included. Nothing else is ever deleted: received files, recordings and pictures from "
        "older versions are kept. Untick the box to keep everything.",
        "<b>Replay RX</b>: decodes the last 15 minutes again (if a picture was missed)."])
s.append(P("Gallery", "h2"))
s.append(P("<b>Gallery</b> tab: the last 30, 60 or 100 pictures received (“from F4EMK”) or sent. Click: show; "
           "double-click: full size; right-click: send the picture again, reply with this picture, show the station "
           "on the map, open the folder, remove from the gallery."))
s.append(img("en_gallery.png", 150, "The gallery of the last pictures received."))

# ------------------------------------------------------------------ 5
s.append(PageBreak())
s.append(P("5. Sending a picture (HFImage modes)", "h1"))
s += N(["<b>TX</b> tab → <b>Open image…</b> (JPG, PNG, GIF, WebP, AVIF, SVG, BMP…).",
        "Choose the <b>Mode</b> (Auto recommended), <b>Max duration</b> (120 s by default), <b>Width</b> (auto), "
        "<b>Format</b> (avif recommended) and <b>Robustness</b> (Auto recommended).",
        "HFImage computes the size and quality that fit in the duration: the compressed picture is shown with its "
        "size and quality.",
        "<b>▶ Transmit</b> (or TRANSMIT button). The progress bar follows the transmission. If another station is "
        "already transmitting (signal being received, or online station transmitting on your frequency), the button "
        "turns to <b>WAITING…</b> and the transmission starts by itself 2 to 6 s after the other one ends (box "
        "<b>Wait for clear frequency</b> under the buttons, ticked by default). Click TRANSMIT: cancel; right-click: "
        "transmit now. Automatic replies (ACK, BSR, FIX) do not wait.",
        "If stations ask for missing pieces (BSR), <b>FIX</b> sends only what is missing (automatically by default)."])
s.append(P("<b>Opening a picture</b>: one click in the large picture of the TX tab opens the file chooser; you can also "
           "<b>drag a picture</b> from Windows Explorer anywhere onto the window (another file type is offered for "
           "sending)."))
s.append(P("<b>Phone pictures</b>: a picture saved “lying on its side” by the phone is turned the right way up "
           "automatically when opened, as in Windows. The <b>⟲</b> and <b>⟳</b> buttons (bottom right of the picture, "
           "TX tab) rotate it a quarter turn left or right if needed. A rotated picture is sent as a very high quality "
           "JPEG, already upright, even in “original” mode."))
s.append(P("Speech bubbles", "h2"))
s.append(P("<b>Bubbles…</b> button (TX tab) or <b>Images → Speech bubbles…</b>: type a text and it appears in a "
           "comic-strip bubble on the transmitted picture. Four styles: <b>speech</b> (round bubble with a tail), "
           "<b>thought</b> (small circles), <b>shout</b> (star outline), <b>caption</b> (rectangle); three text sizes; "
           "background and text colours of your choice; <b>30 colour emoticons</b> to add to the text with one click. <b>Drag the bubble</b> with the mouse, and the <b>red dot</b> "
           "(the tail) towards what it points at; several bubbles are possible, right-click a bubble to delete it. The "
           "bubble is part of the picture: everyone sees it, over the air or in hybrid mode, EasyPal stations too. "
           "Bubbles are cleared when you open another picture."))
s.append(P("Auto mode and robustness", "h2"))
s.append(P("In <b>Auto</b> mode, HFImage chooses the mode from the <b>weakest report</b> of the stations that "
           "received your pictures during the last 45 minutes (Rx Ok list). Without reports it uses the SNR of the "
           "stations heard, otherwise DATAC1X. The reason for the choice is shown under the picture."))
s.append(table([["SNR shown (report)", "Mode chosen", "Pictures"],
                ["9 dB and more", "DATAC1X", "sharpest"],
                ["5 to 9 dB", "DATAC1", "medium"],
                ["below 5 dB", "DATAC3", "small but very robust"]], [55, 45, 70]))
s.append(Spacer(1, 6))
s.append(P("<b>Robustness</b> is the share of spare frames (fountain code): they replace the frames lost in QSB. "
           "In “Auto”: 15 % if the link has margin, 25 % if it is tight, 40 % if it is at the limit. More robustness = "
           "slightly less detail for the same duration, but the picture gets through in one go."))
s += tip("reports and SNR are the <b>real SNR over 3 kHz</b>, comparable from one mode to another. On a very strong "
         "signal the measurement saturates: reports are capped at +15 dB in DATAC3 / DATAC0 and +21 dB in DATAC1X / "
         "DATAC1. For a sharper picture, the most effective is a longer duration (3 min in DATAC1X ≈ 50 % more bytes).")
s.append(P("The HFImage modes", "h2"))
s.append(table([["Mode", "Width", "Net rate", "In 2 min", "Use"],
                ["DATAC1X", "2.2 kHz", "~1,500 bit/s", "~13-16 kB", "Good conditions: sharp pictures (HFImage only)"],
                ["DATAC1", "1.7 kHz", "~980 bit/s", "~8-10 kB", "Average conditions"],
                ["DATAC3", "0.6 kHz", "~320 bit/s", "~2.5-3 kB", "Weak signals, QSB"],
                ["DATAC4", "0.25 kHz", "~85 bit/s", "~1 kB", "Very weak signals"],
                ["DATAC0", "0.6 kHz", "—", "—", "BSR, ACK, presence (automatic)"]],
               [20, 20, 25, 22, 83]))

# ------------------------------------------------------------------ 6
s.append(PageBreak())
s.append(P("6. EasyPal mode (HamDRM) — EasyPal / QSSTV compatible", "h1"))
s.append(P("Choose <b>Mode: EasyPal</b> in the TX tab. A second row appears with the EasyPal settings, the same as "
           "in EasyPal. The signal is the HamDRM signal of EasyPal and QSSTV (DRM OFDM): those stations decode your "
           "pictures, and HFImage decodes theirs."))
s.append(img("en_tx.png", 170, "TX tab in EasyPal mode: EasyPal settings row, compressed picture (JPEG 2000) "
                               "and exact transmission time."))
s.append(P("EasyPal settings", "h2"))
s.append(table([["Setting", "Values", "Meaning"],
                ["EasyPal mode", "A, B, E", "Robustness of the OFDM signal. A: fastest, good conditions. B: usual HF "
                                             "mode. E: most robust (long paths, strong QSB)."],
                ["QAM", "QAM4, QAM16, QAM64", "Modulation: QAM4 robust and slow, QAM64 fast but needs a strong signal."],
                ["Width", "2.2 kHz, 2.4 kHz", "Bandwidth, labelled as in EasyPal (2.3 / 2.5 kHz in QSSTV, same "
                                              "signal). Use 2.2 kHz with a narrow filter."],
                ["Protection", "High (HI), Normal (LO)", "Code rate of the error correction. HI is more robust."],
                ["Reed-Solomon", "None, RS1 … RS4", "Extra redundancy: the picture is rebuilt even when segments are "
                                                    "lost. <b>RS2 by default</b>. Read by EasyPal and QSSTV."]],
               [32, 42, 96]))
s.append(Spacer(1, 6))
s.append(P("Pictures are sent in <b>JPEG 2000</b> (the usual EasyPal format) or JPEG, sized to fit the chosen "
           "duration; the exact transmission time is computed before transmitting. The waterfall marks the exact "
           "band of the mode received (A / B / E, 2.2 / 2.4 kHz)."))
s.append(P("Recommended settings", "h2"))
s.append(table([["Conditions", "Settings", "SNR needed (about)"],
                ["Good propagation, strong signal", "A / QAM64", "15 dB"],
                ["Usual HF (most common)", "B / QAM16 / RS2", "10 dB without QSB, 14 dB with light QSB"],
                ["Difficult propagation, QSB", "B or E / QAM4 / RS3 or RS4", "6 dB without QSB, about 12 dB with "
                                                                           "average QSB"]],
               [55, 55, 60]))
s.append(Spacer(1, 4))
s.append(P("Measured in the simulator: with light QSB, B / QAM16 with <b>RS2</b> gives a complete picture from "
           "about 14 dB instead of 17-20 dB without Reed-Solomon, for a transmission about 18 % longer. "
           "HFImage also transmits the EasyPal signal with a reduced crest factor (+4 dB average level for the same "
           "peak power) and decodes it with an improved bit-reliability estimate (about +0.5 dB in QAM16) — "
           "the signal remains 100 % EasyPal compatible."))
s.append(P("Receiving EasyPal pictures", "h2"))
s += B(["The status panel shows the callsign, “EP B/16” (EasyPal mode / QAM), bandwidth, data rate, total and "
        "received segments, position, and the Sync / Frame / Image / BSR lights.",
        "If a picture remains incomplete, the BSR light turns amber and the log tells you to click <b>BSR</b>: "
        "the EasyPal BSR asks the sender for the missing segments.",
        "Texts sent by EasyPal / QSSTV (.txt files) appear in the received messages window with the callsign."])
s.append(P("Answering BSR (FIX)", "h2"))
s.append(P("When an EasyPal or QSSTV station asks for missing segments of your last picture (BSR), HFImage answers "
           "<b>automatically</b> with a FIX containing only those segments (option in the Stations tab), or "
           "manually with the <b>FIX</b> button."))
s.append(P("Texts in EasyPal mode", "h2"))
s.append(P("<b>Send Text</b> in EasyPal mode sends the message as a .txt file, readable by EasyPal and QSSTV."))
s.append(P("Hybrid EasyPal", "h2"))
s.append(P("With <b>Hybrid mode</b> ticked in EasyPal mode, HFImage works like EasyPal: the picture is uploaded by "
           "FTP to <b>&lt;folder&gt;/HybridFiles1/de_CALL-n-name.jpg</b>, and only a short announcement is sent over "
           "the air, in mode <b>E / QAM4</b> (set automatically, and restored when you untick hybrid mode). EasyPal, "
           "QSSTV and HFImage stations that receive it download the picture automatically and send their Rx Ok "
           "with report."))
s += tip("as in EasyPal, the announcement contains the FTP server, user name and password <b>scrambled, not "
         "encrypted</b>: any station receiving it can read them. Use a <b>dedicated FTP account</b> limited to one "
         "folder. Only plain ASCII characters are allowed in these fields.", "Important")
s.append(P("Following the received mode", "h2"))
s.append(P("With “<b>Switch transmission to the received mode</b>” ticked (Stations tab, on by default), the "
           "transmission mode changes as soon as a picture or message starts to arrive in the other family of modes:"))
s += B(["EasyPal received → mode <b>EasyPal</b>; when the picture is complete, the A / B / E mode, width and QAM of "
        "the station received are also taken over (except for hybrid announcements, always E / QAM4);",
        "HFImage (DATAC) received while in EasyPal → mode <b>Auto</b>.",
        "Nothing changes during your own transmissions or when decoding a WAV file. Each change is written in the log."])

# ------------------------------------------------------------------ 7
s.append(P("7. Adding to your picture", "h1"))
s.append(P("Correspondent's picture", "h2"))
s.append(P("To answer as in EasyPal: right-click a picture in the <b>Gallery</b> → “Reply with this image (inserted into my TX image)”, or tick "
           "<b>Correspondent's image</b> in the TX tab and click <b>…</b>. Received pictures are inserted into yours with "
           "the caption “from F4EMK — +12 dB”: the <b>report</b> is the SNR you measured when receiving them. <b>Up to 4 "
           "pictures</b> at once, for example to answer several stations together."))
s += B(["<b>Inserted images</b> list: <b>Add an image</b> (it goes to a free corner) and <b>Remove</b>. The “Image "
        "received” list changes the picture of the selected line.",
        "Each picture has its own <b>position</b> and <b>size</b>: a corner and a size in the lists, or with the mouse "
        "in the preview. <b>Click</b> a picture to select it (yellow frame), <b>drag</b> it to place it, the <b>mouse "
        "wheel</b> enlarges or reduces it (10 % to 90 % of the width).",
        "Gallery, right-click: “<b>Reply with this image</b>” replaces the insets with this picture only; “<b>Add this "
        "image to my TX image</b>” adds it to the others.",
        "The layout is kept; the picture transmitted is exactly the preview."])
s.append(img("en_pip.png", 125, "Correspondent's image: three pictures inserted, ON4QZ's selected (yellow frame)."))
s.append(P("My station info", "h2"))
s.append(P("Tick <b>My station info</b> (TX tab) and click <b>…</b> next to it (or Images menu): a banner is inserted "
           "at the bottom or top of the transmitted picture, with your callsign, locator, QTH, radio (read by CAT if "
           "the field is empty), power, antenna, frequency, UTC date and time, and free text. Each item can be ticked "
           "or not; the preview updates live. The banner is part of the picture, so every correspondent sees it, "
           "whatever program they use. The <b>Font and colours</b> frame sets the font, bold / italic, text colour, "
           "callsign colour, outline, background and its opacity, and a coloured border; <b>Presets…</b> offers "
           "ready-made styles."))
s.append(P("Other transmissions", "h2"))
s += B(["<b>Incl. text</b>: a message attached to the picture, shown in “Received messages”.",
        "<b>Send Text</b>: message alone.",
        "<b>Send a file…</b> (HFImage modes): any file (text, PDF, ZIP, ADIF log…), compressed when useful and "
        "protected by the same fountain code (BSR / FIX and ACK included); with hybrid mode, the file goes via the "
        "Internet and only the link goes over the air. Received files are stored under their original name in the "
        "<b>fichiers</b> subfolder.",
        "<b>Tune</b> (10 s): carrier to adjust the amplifier / tuner. <b>ID</b>: callsign in Morse.",
        "<b>WAVE</b> / waterfall text: begin.wav / end.wav files, <b>text or picture</b> drawn in the correspondent's "
        "waterfall (Action → Waterfall text…); “Save” makes it a begin.wav played before each transmission, as in "
        "EasyPal.",
        "<b>IMG/QSL</b>: QSL card with background photo, callsign, locator and report filled in automatically, "
        "font and colours of your choice."])

# ------------------------------------------------------------------ 8
s.append(PageBreak())
s.append(P("8. Messages", "h1"))
s.append(P("When a correspondent sends a message (text alone, or text attached to a picture), the <b>Message "
           "received</b> window opens in front with a beep: callsign, UTC time, mode, SNR, the text in large print "
           "and the thumbnail of the picture if there is one (click = full size). The ◀ ▶ arrows browse the messages "
           "of the session. <b>Reply…</b> opens the text window pre-filled with “F1BAL de F4GOP: ”. The sender's "
           "callsign is also written above each message in the “Received messages” frame. That frame can be hidden "
           "(menu Windows): messages still arrive in the “Message received” window."))
s.append(P("<b>Automatic translation</b>: a message written in another language than the program's is translated "
           "on arrival (via the Internet, free service). The translation is shown first, the original below in grey; "
           "in the “Received messages” frame a blue line “↳ translation (FR → EN)” is added. The message goes over the "
           "air exactly as it was written: everyone reads it translated into their own language. Without Internet, "
           "the message is simply shown as is. The <b>Translate</b> box in the “Message received” window turns "
           "translation off."))
s.append(P("<b>Did my correspondent receive my message?</b> As soon as a message is received, the correspondent's "
           "program sends an acknowledgement, over the air (ACK in DATAC0) and via the Internet (if the network is "
           "on). In the <b>Send Text</b> window, the list “Sent messages — received by” shows “✓ F1BAL (+8 dB)” in "
           "green when it arrived, “waiting for acknowledgement…” in orange, then “no acknowledgement” in red after "
           "3 minutes."))

# ------------------------------------------------------------------ 9
s.append(P("9. Stations online, Rx Ok and map", "h1"))
s.append(P("With <b>Settings → Internet</b> ticked, each running HFImage announces itself on a public server "
           "(callsign, locator, frequency, transmitting / receiving): the <b>Stations</b> list immediately shows the "
           "stations that have HFImage open, with their frequency. No other data is shared."))
s += B(["In the list, <b>*</b> marks a station transmitting (red) and <b>HYB</b> a station in hybrid mode (blue). "
        "Double-click a station for details in the log.",
        "<b>Rx Ok</b>: the stations that received your picture, with their <b>report in dB</b>, visible to everyone "
        "(over the air and via the Internet). Also works for EasyPal pictures and hybrid EasyPal pictures received "
        "by HFImage stations.",
        "Click a station: the <b>station map</b> (like Digi-Sites), with path and distance; “Paste the map into the TX "
        "window” to send it as a picture.",
        "Firewall or Internet provider blocking port 1883: HFImage tries the other accesses of the same server by itself "
        "(8883 encrypted, then 8884 and 8000 via the web); the log shows which one worked."])
s.append(img("en_stations.png", 160, "Stations tab: BSR / FIX options, mode following, and the station log."))
s.append(P("Hybrid mode (HFImage) and website", "h2"))
s.append(P("In the HFImage modes, hybrid mode sends the picture through your <b>web hosting</b> (FTP); only the "
           "<b>link</b> goes over the air (~11 s in DATAC3). Stations download it automatically. Ideal for large "
           "pictures and <b>animated GIFs</b>. Settings → Hybrid mode: FTP server, user name, password, folder and "
           "<b>public link</b> of this folder; “Test server” checks everything. Only the link goes over the air, never "
           "the password. By default the picture goes in <b>full quality</b> (“original” format: the file as it is, "
           "not reduced), whatever its size. <b>Files</b> (Images → Send a file…, or dragged onto the window) also go "
           "<b>with no size or type limit</b> in hybrid mode, as in EasyPal (over the air: 16 MB at most). Since 1.25, a "
           "file is uploaded <b>as it is, under its original name</b> (e.g. RK1AT_20261021_133402_TEST.mp4): the public "
           "link opens directly in a web browser."))
s.append(P("<b>Upload in advance</b>: in hybrid mode, the <b>⇪ Upload</b> button (TX tab, right of WAV…) puts the "
           "picture on the server right away, as the old EasyPal did. When it is your turn, <b>Transmit</b> sends the "
           "radio announcement at once, without waiting for the upload. If the picture or the server change in the "
           "meantime, the picture is uploaded again when transmitting."))
s.append(P("<b>Flash hybrid</b>: tick <b>Flash (9 s)</b> next to “Hybrid mode” (TX tab), <b>ticked by default</b> since 0.98. The announcement no longer carries "
           "the link, only the picture's <b>fingerprint</b> (shortened SHA-256), size and format, in a 14-byte frame. Since "
           "version 0.93 it is sent <b>3 times in DATAC13</b> (a very narrow 200 Hz mode made to get through noise and QRM), "
           "then twice in DATAC0 (500 Hz) for stations with an older version: 9 s in all. The link goes at the same time through the online-stations "
           "server; the receiving station downloads the picture and checks it has <b>exactly the fingerprint received over "
           "the air</b>. Simulated at −5 dB: 100 % of DATAC13 announcements received (calm, moderate or strong fading) "
           "against 15 to 50 % for the DATAC0 flash announcement; at −7 dB, 80 to 100 % against 0 to 20 %. Both stations need “<b>Stations online</b>” (Settings → Internet) and version 0.71 or later; if "
           "the server is unreachable, HFImage sends the normal announcement."))
s.append(P("<b>My pictures on the server</b>: each picture sent in hybrid mode is uploaded to your FTP server under a "
           "new name. Settings → Hybrid mode → “<b>My images kept on the server</b>”: <b>the last 3</b> (default), <b>the last "
           "one only</b> or <b>all</b>. After each upload, the older ones are deleted. Only the files uploaded by HFImage "
           "with your callsign are concerned (HFImage hybrid and EasyPal hybrid): the other files of your site are never "
           "touched. With “the last one only”, a station still downloading the previous picture will no longer find it."))
s.append(P("<b>Download safety</b>: an announcement received over the air can only fetch a file up to the <b>maximum size you chose</b> (Settings → Hybrid mode → “Received hybrid files: max size”, 200 MB by default, or no limit), and "
           "only from a public Internet address (never the computer itself or a machine on your home network). Received "
           "pictures and files always stay in the reception folder, whatever the announced callsign."))
s.append(P("Menu <b>Images → Website / Digi-Sites…</b>: as in EasyPal, each received picture is uploaded as "
           "<b>image1</b>, with no extension as in EasyPal: this is the file Digi-Sites reads (the previous ones move to "
           "image2, image3…), with callsign, date, mode and band; your "
           "transmitted pictures go to TX1.jpg … TX5.jpg, and a <b>hfimage.html</b> page shows them. Example with "
           "qsl.net: server <b>ftp.qsl.net</b>, empty folder, link <b>https://www.qsl.net/yourcall</b>, address for "
           "Digi-Sites (Setup → Edit site) <b>https://www.qsl.net/yourcall/image1</b>; page of your pictures: "
           "https://www.qsl.net/yourcall/hfimage.html."))
s.append(P("<b>Station sites</b>: menu <b>Images → Station sites…</b> (or Action, or right-click on the station list): "
           "like Digi-Sites, which is no longer maintained, one thumbnail per station with the <b>last picture it "
           "received</b> (its image1), the time of that picture and the distance. Online HFImage stations that upload "
           "their pictures appear by themselves; “<b>Add a station…</b>” for an EasyPal station (address of its image1, "
           "the one given to Digi-Sites). Read every 2 minutes, only if the picture changed; a click enlarges it, "
           "right-click: the station's page."))

# ------------------------------------------------------------------ 10
s.append(P("10. Noise, QSB and QRM", "h1"))
s += B(["<b>Noise and QSB</b> (HFImage modes): Auto mode + Auto robustness. If losses come in groups, choose the "
        "“Strong (70 %)” robustness.",
        "<b>Noise and QSB</b> (EasyPal mode): keep Reed-Solomon (RS2 or more), lower the QAM (QAM4) or use mode E. "
        "An incomplete picture can be completed with BSR / FIX.",
        "<b>QRM</b>: the <b>QRM cutter</b> (Settings → Audio) removes, before demodulation, everything outside the band "
        "of the mode (adjacent SSB) and, inside the band, narrow lines (carrier, CW, RTTY).",
        "A <b>wide interferer on top of the signal</b> (another SSB station on the same frequency) cannot be removed: "
        "move the frequency."])
s.append(P("Reception analyser", "h2"))
s.append(P("To understand a failed reception: <b>WAVE</b> button → <b>● Record RX</b> during the reception, then "
           "<b>Files → Decode and analyse a WAV file…</b> (the pictures in the file are decoded and the report opens). HFImage reports the input level (clipping, too low), narrow "
           "interference and its frequency, the frames received / lost in each mode, SNR, frequency offset between "
           "the radios, the type of losses (QSB or isolated), what the QRM cutter saved, and the recommended mode. "
           "The same command decodes HFImage and EasyPal pictures."))
s.append(img("analyse.png", 150, "The analyser: plain-language diagnosis and SNR of each frame "
                                  "(screenshot of the French interface)."))

# ------------------------------------------------------------------ 11
s.append(PageBreak())
s.append(P("11. Common problems", "h1"))
s.append(table([["Symptom", "Probable cause", "What to do"],
                ["The radio does not transmit", "PTT badly set, COM port busy",
                 "Radio… → Test PTT; close the programs holding the port or use OmniRig"],
                ["The radio transmits without power", "Radio not in DATA, wrong audio source, level too low",
                 "“Switch to DATA automatically”; source “Rear / Data”; raise the level (ALC must not move)"],
                ["“Radio not in DATA” and it does not switch", "Setting “Transmit without asking” or “Ask”",
                 "Settings → “Radio not in DATA before transmitting” → “Switch to DATA automatically”"],
                ["COM port missing from the list", "Driver not seen, or device unplugged",
                 "Version 0.76 or later; type the port name (COM9); check Windows Device Manager"],
                ["Nothing is received", "Wrong audio input, Windows volume muted",
                 "Settings → Audio; check that the waterfall moves; analyse a WAVE recording"],
                ["Frames detected but lost", "Weak signal, QSB, QRM, clipping",
                 "WAV analyser; Auto mode / Strong robustness; lower the input level"],
                ["EasyPal picture incomplete", "QSB, segments lost",
                 "Click BSR; ask the sender to use RS2 or more, QAM4 or mode E"],
                ["HFImage picture incomplete", "BSR not heard or no FIX",
                 "Check “Send BSR” on your side and “answer BSR with a FIX” on the sender's side (Stations tab)"],
                ["Pictures not sharp", "Slow mode or strong robustness, short duration",
                 "Auto robustness; 3 min duration; DATAC1X or EasyPal B/QAM16 if reports allow"],
                ["No stations online", "Internet unticked or server blocked",
                 "Settings → Internet; HFImage tries ports 8883, 8884, 8000 by itself; see the log"],
                ["Flash hybrid: picture not downloaded", "“Stations online” off at the sender or receiver",
                 "Enable Internet on both sides, or untick “Flash (5 s)”"],
                ["Hybrid mode: FTP failure", "Credentials, folder or public link",
                 "Settings → Hybrid mode → Test server"]],
               [45, 55, 70]))
s.append(Spacer(1, 8))
s.append(P("Full diagnosis: <b>HFImage_F4GOP.exe --selftest report.txt</b> (modems including EasyPal, map, Internet, "
           "sound cards, COM ports, radio). Log: <b>Documents\\HFImage\\journal.txt</b>."))
s.append(P("Credits and licence", "h2"))
s.append(P("HFImage F4GOP — © 2026 Denis F4GOP — is <b>free software</b>, at no cost, under the <b>GNU GPL v3</b>: you may "
           "use, copy, share and modify it; a modified version you distribute must keep the same licence, with its "
           "sources. Full text: menu <b>Info → Licence (GNU GPL v3)</b>, or the LICENSE file on the program's GitHub page."))
s.append(P("The EasyPal (HamDRM) modem comes from <b>QSSTV</b> (Johan Maes ON4QZ), itself derived from <b>Dream</b> "
           "(Volker Fischer, TU Darmstadt) and <b>RXAMADRM</b> (Ties Bos PA0MBO), GNU GPL v3. The DATAC modes use "
           "<b>codec2</b> (David Rowe VK5DGR and contributors). Tribute to <b>Erik Sundstrup VK4AES</b>, author of "
           "EasyPal."))
s.append(P("Contact", "h2"))
s.append(P("F4GOP — Denis — f4gop.denis@gmail.com<br/>Program page: github.com/f4gopdenis-cyber/HFImage_F4GOP "
           "(versions, changes, sources).<br/>73!"))

doc = Doc(OUT, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=20 * mm, bottomMargin=18 * mm,
          title="HFImage F4GOP — User manual", author="F4GOP", subject=f"Version {VERSION}")
doc.multiBuild(s, onFirstPage=cover, onLaterPages=page_deco)
print(OUT, os.path.getsize(OUT))
