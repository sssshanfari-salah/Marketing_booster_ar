import importlib.util
import pathlib
import tkinter as tk
from tkinter import ttk

import python_code.translations as translations

root = pathlib.Path(__file__).resolve().parent


def resolve_ui_path():
    for candidate in (root / 'python_code' / 'clients_progress_ui.py', root / 'python code' / 'clients_progress_ui.py'):
        if candidate.exists():
            return candidate
    return root / 'python_code' / 'clients_progress_ui.py'


p = resolve_ui_path()
spec = importlib.util.spec_from_file_location('ui', p)
ui = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ui)

translations.set_language('ar')
root_window = tk.Tk()
root_window.withdraw()
label = ttk.Label(root_window, text='Client Name')
label.pack()
print('initial>', repr(label.cget('text')))
print('before refresh>', repr(label.cget('text')))
res = ui.refresh_translatable_widget(label, 'Client Name')
print('res>', res)
print('after refresh>', repr(label.cget('text')))
print('anchor>', label.cget('anchor'))
print('justify>', label.cget('justify'))
root_window.destroy()
