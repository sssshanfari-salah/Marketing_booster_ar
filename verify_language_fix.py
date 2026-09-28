import importlib.util
import pathlib
import tkinter as tk
from tkinter import ttk

base = pathlib.Path(__file__).resolve().parent


def resolve_ui_module_path():
    candidates = [
        base / 'python_code' / 'clients_progress_ui.py',
        base / 'python code' / 'clients_progress_ui.py',
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return base / 'python_code' / 'clients_progress_ui.py'


module_path = resolve_ui_module_path()
spec = importlib.util.spec_from_file_location('ui_module', module_path)
ui = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ui)

root = tk.Tk()
root.withdraw()
label = ttk.Label(root, text='Client Name')
label.pack()
orig_font = label.cget('font')
ui.set_language('ar')
ui.refresh_translatable_widget(label, 'Client Name')
text = label.cget('text')
font = label.cget('font')
print('FONT_UNCHANGED=', font == orig_font)
print('TEXT=', repr(text))
print('HAS_ARABIC=', any('\u0600' <= ch <= '\u06FF' for ch in text))
root.destroy()
