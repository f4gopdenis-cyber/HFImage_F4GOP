"""Glisser-déposer de fichiers depuis l'Explorateur sur la fenêtre HFImage.

Utilise l'extension tkdnd (paquet tkinterdnd2, licence MIT ; tkdnd : licence BSD), chargée dans
l'interpréteur Tk existant. (La 1.08 interceptait WM_DROPFILES par ctypes : le programme se
fermait au premier dépôt ; abandonné.)

hook(root, widgets, callback) : callback(liste de chemins), appelé par Tk dans le fil de
l'interface. -> True si le glisser-déposer est actif.
"""


def hook(root, widgets, callback):
    try:
        from tkinterdnd2 import DND_FILES, TkinterDnD
    except ImportError:
        return False
    TkinterDnD._require(root)                  # charge tkdnd (lève une erreur si impossible)

    def on_drop(event):
        try:
            paths = list(root.tk.splitlist(event.data))
        except Exception:
            paths = [event.data]
        if paths:
            root.after(0, lambda: callback(paths))
        return event.action

    ok = False
    for w in widgets:
        try:
            w.drop_target_register(DND_FILES)      # méthodes ajoutées aux widgets Tk par tkinterdnd2
            w.dnd_bind("<<Drop>>", on_drop)
            ok = True
        except Exception:
            continue
    return ok


def all_widgets(root):
    """Tous les widgets de la fenêtre principale (sous Windows, chacun reçoit ses propres dépôts)."""
    import tkinter as tk
    out, todo = [], list(root.winfo_children())
    while todo:
        w = todo.pop()
        if isinstance(w, (tk.Toplevel, tk.Menu)):
            continue
        out.append(w)
        todo.extend(w.winfo_children())
    return out
