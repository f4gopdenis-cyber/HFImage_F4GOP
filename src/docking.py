"""Fenêtres séparées : chaque zone de la fenêtre principale (waterfall, onglets RX / TX…,
journal, liste des stations, panneau de commandes) peut devenir une fenêtre à part,
que l'on place où l'on veut (y compris sur un autre écran), puis revenir à sa place.

Mécanisme Tk « wm manage » / « wm forget » : la zone (un cadre) devient une fenêtre
indépendante sans être reconstruite ; tout ce qu'elle contient continue de fonctionner.
Fermer la fenêtre séparée remet la zone dans la fenêtre principale.
"""
import re
import tkinter as tk

MIN_W, MIN_H = 220, 120


class Dock:
    def __init__(self, root, title_prefix="HFImage", on_change=lambda: None, tr=lambda s: s):
        self.root, self.prefix, self.on_change, self.tr = root, title_prefix, on_change, tr
        self.zones = {}           # nom -> description
        self.order = []           # ordre d'ajout (menu)
        self.geom = {}            # nom -> dernière géométrie de la fenêtre séparée

    # ------------------------------------------------------------------ zones
    def _zone(self, name, title, frame, kind, **kw):
        self.zones[name] = dict(kw, name=name, title=title, frame=frame, kind=kind, detached=False)
        self.order.append(name)

    def add_pane(self, name, title, frame, pw, siblings, **opts):
        """Zone d'un séparateur (PanedWindow). siblings : les cadres du séparateur dans l'ordre."""
        self._zone(name, title, frame, "pane", pw=pw, siblings=siblings, opts=opts)

    def add_tab(self, name, title, frame, nb, text, siblings):
        """Onglet d'un ttk.Notebook. siblings : les cadres des onglets dans l'ordre."""
        self._zone(name, title, frame, "tab", nb=nb, text=text, siblings=siblings)

    def add_pack(self, name, title, frame, siblings, **opts):
        """Cadre placé par pack. siblings : les cadres du même parent dans l'ordre."""
        self._zone(name, title, frame, "pack", siblings=siblings, opts=opts)

    # ------------------------------------------------------------------ état
    def detached(self, name):
        z = self.zones.get(name)
        return bool(z and z["detached"])

    def saved(self):
        """{nom: géométrie} des zones séparées (pour les réglages)."""
        out = {}
        for n, z in self.zones.items():
            if z["detached"]:
                try:
                    out[n] = self._wm("geometry", z["frame"])
                except tk.TclError:
                    out[n] = self.geom.get(n, "")
        return out

    def _wm(self, *args):
        return self.root.tk.call("wm", args[0], args[1], *args[2:])

    # ------------------------------------------------------------------ séparer / remettre
    def detach(self, name, geometry=None):
        z = self.zones.get(name)
        if z is None or z["detached"]:
            return
        f = z["frame"]
        self.root.update_idletasks()
        w, h = max(MIN_W, f.winfo_width()), max(MIN_H, f.winfo_height())
        x, y = f.winfo_rootx() + 30, f.winfo_rooty() + 30
        if z["kind"] == "pane":
            z["pw"].forget(f)
            self._restretch(z["pw"])
        elif z["kind"] == "tab":
            z["text"] = z["nb"].tab(f, "text")         # texte de l'onglet dans la langue choisie
            z["nb"].forget(f)
        else:
            f.pack_forget()
        self._wm("manage", f)
        self._wm("title", f, f"{self.prefix} — {self.tr(z['title'])}")
        self._wm("protocol", f, "WM_DELETE_WINDOW", self.root.register(lambda n=name: self.attach(n)))
        self._wm("minsize", f, MIN_W, MIN_H)
        geometry = geometry or self.geom.get(name) or f"{w}x{h}+{x}+{y}"
        if not _on_screen(self.root, geometry):
            geometry = f"{w}x{h}+{self.root.winfo_rootx() + 60}+{self.root.winfo_rooty() + 60}"
        self._wm("geometry", f, geometry)
        z["detached"] = True
        self.on_change()

    def attach(self, name):
        z = self.zones.get(name)
        if z is None or not z["detached"]:
            return
        f = z["frame"]
        try:
            self.geom[name] = self._wm("geometry", f)
        except tk.TclError:
            pass
        self._wm("forget", f)
        z["detached"] = False
        sib = z["siblings"]
        later = sib[sib.index(f) + 1:] if f in sib else []
        if z["kind"] == "pane":
            present = {str(p) for p in z["pw"].panes()}
            nxt = next((s for s in later if str(s) in present), None)
            if nxt is not None:
                z["pw"].add(f, before=nxt, **z["opts"])
            else:
                z["pw"].add(f, **z["opts"])
            self._restretch(z["pw"])
        elif z["kind"] == "tab":
            nb = z["nb"]
            tabs = [str(t) for t in nb.tabs()]
            nxt = next((s for s in later if str(s) in tabs), None)
            nb.insert(tabs.index(str(nxt)) if nxt is not None else "end", f, text=z["text"])
        else:
            nxt = next((s for s in later if s.winfo_manager() == "pack"), None)
            if nxt is not None:
                f.pack(before=nxt, **z["opts"])
            else:
                f.pack(**z["opts"])
        self.on_change()

    def _restretch(self, pw):
        """Une zone seule dans son séparateur prend toute la place ; sinon réglage d'origine."""
        panes = [str(p) for p in pw.panes()]
        for z in self.zones.values():
            if z["kind"] == "pane" and z["pw"] is pw and str(z["frame"]) in panes:
                stretch = "always" if len(panes) == 1 else z["opts"].get("stretch", "always")
                try:
                    pw.paneconfigure(z["frame"], stretch=stretch)
                except tk.TclError:
                    pass

    def toggle(self, name):
        (self.attach if self.detached(name) else self.detach)(name)

    def attach_all(self):
        for n in list(self.order):
            self.attach(n)

    def restore(self, saved):
        """Au démarrage : sépare les zones qui l'étaient, à leur place."""
        for n, g in (saved or {}).items():
            if n in self.zones and isinstance(g, str):
                try:
                    self.detach(n, g or None)
                except tk.TclError:
                    pass

    def show(self, name):
        """Fait apparaître une zone séparée (au premier plan)."""
        z = self.zones.get(name)
        if z and z["detached"]:
            try:
                self._wm("deiconify", z["frame"])
                self.root.tk.call("raise", z["frame"])
            except tk.TclError:
                pass


def _on_screen(root, geometry):
    """La fenêtre serait-elle visible (écran débranché depuis la dernière fois) ?"""
    m = re.match(r"(\d+)x(\d+)([+-]-?\d+)([+-]-?\d+)", geometry or "")
    if not m:
        return False
    w, h, x, y = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
    try:
        vx, vy = root.winfo_vrootx(), root.winfo_vrooty()
        vw = max(root.winfo_vrootwidth(), root.winfo_screenwidth())
        vh = max(root.winfo_vrootheight(), root.winfo_screenheight())
    except tk.TclError:
        return True
    # Windows : plusieurs écrans -> on ne connaît que l'écran principal ; on accepte les
    # positions raisonnables (jusqu'à 3 écrans de large)
    return x + w > vx + 40 - 2 * vw and x < vx + 3 * vw - 40 and y + h > vy + 40 - vh and y < vy + 2 * vh - 40
