"""Édition directe sur l'image de l'onglet TX (demande de RK1AT, comme le « GMSK controller » de
JQ1HDR) : textes (bulles) et logos / images incrustées se choisissent, se déplacent, se
redimensionnent et se tournent à la souris sur l'image elle-même ; un clic droit ouvre un menu
pour en ajouter, les modifier ou les supprimer.

- clic : sélectionner (cadre jaune) ; glisser : déplacer (le rond rouge d'une bulle : sa pointe) ;
- molette : agrandir / réduire ; Maj + molette : tourner (logos et images) ;
- double-clic sur un texte : le modifier ; touche Suppr : supprimer l'élément choisi.

Les textes sont les bulles (app.bubbles), les logos et images sont les incrustations (app.pips) :
mêmes réglages que dans les fenêtres « Bulles de texte » et « Image du correspondant ».
Pendant un déplacement, un aperçu rapide (image réduite) suit la souris ; l'image à émettre est
recalculée quand on relâche."""
import os

import bubbles
import trafic

STYLES = ("parole", "pensée", "cri", "cartouche", "texte")
STYLE_NAMES = {"parole": "Parole", "pensée": "Pensée", "cri": "Cri", "cartouche": "Cartouche",
               "texte": "Texte seul (sans bulle)"}
SHAPE_NAMES = {"rect": "Rectangle", "arrondi": "Coins arrondis", "rond": "Rond", "ovale": "Ovale"}


class TxEditor:
    def __init__(self, app, view):
        self.app, self.view = app, view
        self.sel = None              # ("b", indice de bulle) ou ("p", indice d'incrustation)
        self.drag = None             # (type, indice, partie, décalage x, décalage y)
        self._job = None
        self.preview_img = None      # aperçu en cours (pendant un déplacement)
        view.after_draw = self.draw_selection
        view.wheel_cb = self.wheel
        view.menu_cb = self.menu
        view.bind("<ButtonPress-1>", self.press, add="+")
        view.bind("<B1-Motion>", self.motion, add="+")
        view.bind("<ButtonRelease-1>", self.release, add="+")
        view.bind("<Double-Button-1>", self.double, add="+")
        view.bind("<Delete>", lambda e: self.delete())
        view.bind("<Shift-MouseWheel>", lambda e: self.wheel(e, 1 if e.delta > 0 else -1, rotate=True))
        view.bind("<Shift-Button-4>", lambda e: self.wheel(e, 1, rotate=True))
        view.bind("<Shift-Button-5>", lambda e: self.wheel(e, -1, rotate=True))

    # ------------------------------------------------------------------ géométrie
    def active(self):
        """Édition possible : une image ouverte, rien en cours d'émission, image entière (pas de zoom)."""
        a = self.app
        return a.src_img is not None and not a.tx_busy and self.view.image_box() is not None

    def _local(self, e):
        box = self.view.image_box()
        if box is None:
            return None
        ox, oy, dw, dh = box
        return e.x - ox, e.y - oy, dw, dh

    def _pip_rect(self, i, dw, dh):
        a = self.app
        p = a.pips[i]
        try:
            th = a._pip_thumb(p["path"])
        except Exception:
            return None
        logo = bool(p.get("logo"))
        th_size = th.size if (p.get("shape") or "rect") != "rond" else (min(th.size),) * 2
        return trafic.pip_layout((dw, dh), th_size, "" if logo else a._pip_caption(p),
                                 p.get("corner", "haut-droite"), p.get("size", "moyenne"), p.get("pos"),
                                 p.get("scale"), logo, p.get("shape") or "rect")[:4]

    def hit(self, e):
        """Élément sous la souris -> (type, indice, partie) ou None. Les textes sont au-dessus."""
        loc = self._local(e)
        if loc is None:
            return None
        x, y, dw, dh = loc
        a = self.app
        h = bubbles.hit(dw, dh, [b for b in a.bubbles], x, y, grab=10)
        if h is not None and (a.bubbles[h[0]].get("text") or "").strip():
            return "b", h[0], h[1]
        if a.conf.get("pip_on"):
            for i in range(len(a.pips) - 1, -1, -1):
                r = self._pip_rect(i, dw, dh)
                if r and r[0] <= x <= r[0] + r[2] and r[1] <= y <= r[1] + r[3]:
                    return "p", i, "pip"
        return None

    # ------------------------------------------------------------------ souris
    def press(self, e):
        self.view.focus_set()
        if not self.active():
            return
        h = self.hit(e)
        if h is None:
            # à côté : enlève la sélection s'il y en a une ; sinon le clic ouvre une image (comme avant)
            self.app._cmp_edit_click = self.sel is not None
            if self.sel is not None:
                self.sel = None
                self.view._redraw()
            return
        self.app._cmp_edit_click = True          # pas d'ouverture d'image sur ce clic
        kind, i, part = h
        self.sel = (kind, i)
        x, y, dw, dh = self._local(e)
        if kind == "b":
            b = self.app.bubbles[i]
            ref = (b["tx"], b["ty"]) if part == "pointe" else (b.get("cx", 0.5), b.get("cy", 0.3))
            self.drag = (kind, i, part, x / dw - ref[0], y / dh - ref[1])
        else:
            r = self._pip_rect(i, dw, dh)
            self.drag = (kind, i, part, x - r[0], y - r[1]) if r else None
        self.view._redraw()

    def motion(self, e):
        if self.drag is None or not self.active():
            return
        kind, i, part, gx, gy = self.drag
        x, y, dw, dh = self._local(e)
        a = self.app
        if kind == "b":
            if i >= len(a.bubbles):
                return
            b = a.bubbles[i]
            fx, fy = x / dw - gx, y / dh - gy
            if part == "pointe":
                b["tx"], b["ty"] = min(1.0, max(0.0, fx)), min(1.0, max(0.0, fy))
            else:
                nx, ny = min(1.0, max(0.0, fx)), min(1.0, max(0.0, fy))
                b["tx"] = min(1.0, max(0.0, b.get("tx", 0.6) + nx - b.get("cx", 0.5)))   # la pointe suit
                b["ty"] = min(1.0, max(0.0, b.get("ty", 0.6) + ny - b.get("cy", 0.3)))
                b["cx"], b["cy"] = nx, ny
        else:
            if i >= len(a.pips):
                return
            r = self._pip_rect(i, dw, dh)
            if not r:
                return
            W, H = r[2], r[3]
            nx, ny = x - gx, y - gy
            a.pips[i]["pos"] = [round(min(1.0, max(0.0, nx / (dw - W) if dw > W else 0.0)), 4),
                                round(min(1.0, max(0.0, ny / (dh - H) if dh > H else 0.0)), 4)]
        self.live()

    def release(self, e):
        if self.drag is not None:
            self.drag = None
            self.changed()

    def double(self, e):
        if not self.active():
            return
        h = self.hit(e)
        if h and h[0] == "b":
            self.sel = ("b", h[1])
            self.edit_text()
        elif h and h[0] == "p":
            self.app.pip_dialog()

    def wheel(self, e, step, rotate=False):
        """Molette sur un texte ou un logo : taille ; Maj + molette sur un logo / une image : rotation.
        -> True si la molette a servi (sinon : zoom de l'image)."""
        if not self.active():
            return False
        h = self.hit(e)
        if h is None:
            return rotate                         # Maj + molette hors élément : rien
        kind, i, _ = h
        self.sel = (kind, i)
        a = self.app
        if kind == "b":
            if rotate:
                return True
            b = a.bubbles[i]
            k = float(b.get("k") or 1.0) * (1.1 if step > 0 else 1 / 1.1)
            b["k"] = round(min(bubbles.K_MAX, max(bubbles.K_MIN, k)), 3)
        else:
            p = a.pips[i]
            if rotate:
                p["rot"] = max(-trafic.PIP_ROT_MAX, min(trafic.PIP_ROT_MAX, round(float(p.get("rot") or 0)) + 3 * step))
            else:
                loc = self._local(e)
                r = self._pip_rect(i, loc[2], loc[3])
                cur = p.get("scale") or trafic.PIP_SCALE.get(p.get("size", "moyenne"), 0.34)
                new = min(trafic.PIP_MAX, max(trafic.PIP_MIN, cur * (1.1 if step > 0 else 1 / 1.1)))
                if r:                                      # le centre ne bouge pas
                    dw, dh = loc[2], loc[3]
                    cx, cy = r[0] + r[2] / 2, r[1] + r[3] / 2
                    nW, nH = r[2] * new / cur, r[3] * new / cur
                    p["pos"] = [round(min(1.0, max(0.0, (cx - nW / 2) / (dw - nW) if dw > nW else 0.0)), 4),
                                round(min(1.0, max(0.0, (cy - nH / 2) / (dh - nH) if dh > nH else 0.0)), 4)]
                p["scale"] = round(new, 4)
        self.live()
        self._later_changed()
        return True

    # ------------------------------------------------------------------ aperçu
    def live(self):
        """Aperçu rapide sur une image réduite pendant qu'on déplace / redimensionne."""
        if self._job is None:
            self._job = self.view.after(25, self._live_now)

    def _live_now(self):
        self._job = None
        a = self.app
        box = self.view.image_box()
        if a.src_img is None or box is None:
            return
        dw, dh = box[2], box[3]
        try:
            self.preview_img = a._edit_preview((dw, dh))
        except Exception as ex:                      # l'aperçu ne doit jamais bloquer l'édition
            a.log(f"Aperçu de l'édition : {ex}")
            return
        self.view.set_image(self.preview_img)

    def _later_changed(self):
        if getattr(self, "_chg_job", None):
            self.view.after_cancel(self._chg_job)
        self._chg_job = self.view.after(500, self.changed)

    def changed(self):
        """Fin d'un déplacement / d'un réglage : réglages gardés, image à émettre recalculée."""
        self._chg_job = None
        a = self.app
        a._pip_cache = None
        a._pip_save_layouts()
        a._save_conf_file()
        a.prepare()

    def draw_selection(self, view):
        """Cadre jaune autour de l'élément choisi (et rond rouge de la pointe d'une bulle)."""
        if self.sel is None or self.app.src_img is None:
            return
        box = view.image_box()
        if box is None:
            return
        ox, oy, dw, dh = box
        kind, i = self.sel
        a = self.app
        if kind == "b":
            if i >= len(a.bubbles):
                self.sel = None
                return
            b = a.bubbles[i]
            g = bubbles.layout(dw, dh, b)
            x0, y0, x1, y1 = g["box"]
            view.create_rectangle(ox + x0 - 3, oy + y0 - 3, ox + x1 + 3, oy + y1 + 3, outline="#ffd400",
                                  dash=(4, 3), width=2)
            if b.get("style") not in bubbles.NO_TAIL:
                tx, ty = ox + b["tx"] * dw, oy + b["ty"] * dh
                view.create_oval(tx - 6, ty - 6, tx + 6, ty + 6, fill="#e02020", outline="white")
        else:
            if i >= len(a.pips):
                self.sel = None
                return
            r = self._pip_rect(i, dw, dh)
            if r:
                x, y, W, H = r
                view.create_rectangle(ox + x - 3, oy + y - 3, ox + x + W + 3, oy + y + H + 3, outline="#ffd400",
                                      dash=(4, 3), width=2)

    def cancel(self):
        """Annule les aperçus / recalculs en attente (fermeture)."""
        for name in ("_job", "_chg_job"):
            job = getattr(self, name, None)
            if job:
                try:
                    self.view.after_cancel(job)
                except Exception:
                    pass
                setattr(self, name, None)

    # ------------------------------------------------------------------ actions
    def selected(self):
        if self.sel is None:
            return None, None
        kind, i = self.sel
        lst = self.app.bubbles if kind == "b" else self.app.pips
        if i >= len(lst):
            self.sel = None
            return None, None
        return kind, lst[i]

    def delete(self):
        kind, item = self.selected()
        if item is None:
            return
        if kind == "b":
            self.app.bubbles.remove(item)
        else:
            self.app.pips.remove(item)
        self.sel = None
        self.changed()

    def add_text(self, text=None):
        a = self.app
        text = text if text is not None else a._edit_ask_text("")
        if not text:
            return
        b = bubbles.new(text, cx=0.5, cy=0.5)
        last = a.conf.get("bub_last") or {}
        b.update({k: last[k] for k in ("style", "size", "bg", "fg", "anim") if k in last})
        b["tx"], b["ty"] = 0.62, 0.72
        a.bubbles.append(b)
        self.sel = ("b", len(a.bubbles) - 1)
        self.changed()

    def edit_text(self):
        kind, b = self.selected()
        if kind != "b":
            return
        t = self.app._edit_ask_text(b.get("text", ""))
        if t is None:
            return
        if t.strip():
            b["text"] = t
        else:
            self.app.bubbles.remove(b)
            self.sel = None
        self.changed()

    def set_bubble(self, **kw):
        kind, b = self.selected()
        if kind == "b":
            b.update(kw)
            self.app.conf["bub_last"] = {k: b[k] for k in ("style", "size", "bg", "fg", "anim") if k in b}
            self.changed()

    def set_pip(self, **kw):
        kind, p = self.selected()
        if kind == "p":
            p.update(kw)
            self.changed()

    def add_pip(self, cand, logo=None):
        a = self.app
        if len(a.pips) >= a.PIP_MAX_N:
            a._edit_info(a._tr("4 images au maximum dans l'image TX. Retirez-en une dans "
                               "« Image du correspondant… »."))
            return
        p = a._pip_new(cand)
        p["pos"] = [0.5, 0.5]
        if logo is None:
            try:
                logo = a._pip_thumb(cand["path"]).mode == "RGBA"
            except Exception:
                logo = False
        p.update(cap=None, logo=bool(logo), opa=1.0)
        a.pips.append(p)
        a.conf["pip_on"] = True
        if hasattr(a, "v_pipon"):
            a.v_pipon.set(True)
        self.sel = ("p", len(a.pips) - 1)
        self.changed()

    def add_pc_image(self, path=None):
        a = self.app
        path = path or a._edit_ask_file()
        if not path:
            return
        try:
            a._pip_thumb(path)
        except Exception as ex:
            a._edit_error(a._tr("Image illisible :") + f" {ex}")
            return
        a._pip_remember_local(path)
        self.add_pip({"path": path, "call": "", "snr": None, "local": True})

    # ------------------------------------------------------------------ menu (clic droit)
    def menu(self, e):
        import tkinter as tk
        a, tr = self.app, self.app._tr
        m = tk.Menu(self.view, tearoff=0)
        keep = m._keep = []                       # variables des cases du menu (gardées en vie)
        if a.src_img is None:
            m.add_command(label=tr("Ouvrir une image…"), command=a.open_image)
        else:
            if self.active():
                h = self.hit(e)
                if h is not None:
                    self.sel = (h[0], h[1])
                    self.view._redraw()
            kind, item = self.selected()
            busy = "disabled" if a.tx_busy else "normal"
            m.add_command(label=tr("Ajouter un texte…"), command=self.add_text, state=busy)
            m.add_command(label=tr("Ajouter un logo / une image du PC…"), command=self.add_pc_image, state=busy)
            sub = tk.Menu(m, tearoff=0)
            recues = [(lab, c) for lab, c in a._pip_candidates() if not c.get("local")][:10]
            for lab, c in recues:
                sub.add_command(label=lab, command=lambda c=c: self.add_pip(dict(c), logo=False))
            m.add_cascade(label=tr("Ajouter l'image d'un correspondant"), menu=sub,
                          state="normal" if recues and not a.tx_busy else "disabled")
            if kind == "b":
                m.add_separator()
                m.add_command(label=tr("Modifier le texte…"), command=self.edit_text)
                st = tk.Menu(m, tearoff=0)
                v_st = tk.StringVar(m, value=item.get("style", "parole"))
                keep.append(v_st)
                for k in STYLES:
                    st.add_radiobutton(label=tr(STYLE_NAMES[k]), value=k, variable=v_st,
                                       command=lambda k=k: self.set_bubble(style=k))
                m.add_cascade(label=tr("Style"), menu=st)
                m.add_command(label=tr("Couleur du fond…"), command=lambda: self._color("bg"))
                m.add_command(label=tr("Couleur du texte…"), command=lambda: self._color("fg"))
                v_an = tk.BooleanVar(m, value=bool(item.get("anim")))
                keep.append(v_an)
                m.add_checkbutton(label=tr("Émoticônes animées (mode hybride : GIF animé)"), variable=v_an,
                                  command=lambda: self.set_bubble(anim=not item.get("anim")))
                m.add_command(label=tr("Supprimer"), command=self.delete)
            elif kind == "p":
                m.add_separator()
                v_lg = tk.BooleanVar(m, value=bool(item.get("logo")))
                v_sh = tk.StringVar(m, value=item.get("shape") or "rect")
                keep += [v_lg, v_sh]
                m.add_checkbutton(label=tr("Logo (sans cadre, transparence gardée)"), variable=v_lg,
                                  command=lambda: self.set_pip(logo=not item.get("logo")))
                sh = tk.Menu(m, tearoff=0)
                for k in trafic.PIP_SHAPES:
                    sh.add_radiobutton(label=tr(SHAPE_NAMES[k]), value=k, variable=v_sh,
                                       command=lambda k=k: self.set_pip(shape=k))
                m.add_cascade(label=tr("Forme"), menu=sh)
                m.add_command(label=tr("Légende…"), command=self._caption)
                m.add_command(label=tr("Remettre droit"), command=lambda: self.set_pip(rot=0, tilt=0))
                m.add_command(label=tr("Supprimer"), command=self.delete)
            m.add_separator()
            m.add_command(label=tr("Bulles de texte…"), command=a.bubble_dialog)
            m.add_command(label=tr("Image du correspondant…"), command=a.pip_dialog)
            m.add_command(label=tr("Ouvrir une autre image…"), command=a.open_image, state=busy)
        if self.view.zoom > 1.0:
            m.add_separator()
            m.add_command(label=tr("Revenir à l'image entière"), command=self.view.reset_zoom)
        try:
            m.tk_popup(e.x_root, e.y_root)
        finally:
            m.grab_release()

    def _color(self, which):
        from tkinter import colorchooser
        kind, b = self.selected()
        if kind != "b":
            return
        c = colorchooser.askcolor(color=b.get(which), parent=self.view)[1]
        if c:
            self.set_bubble(**{which: c})

    def _caption(self):
        kind, p = self.selected()
        if kind != "p":
            return
        t = self.app._edit_ask_text(p.get("cap") or "", title=self.app._tr("Légende"), single=True)
        if t is not None:
            self.set_pip(cap=t.strip() or None)


def describe_path(p):
    return os.path.basename(p or "")
