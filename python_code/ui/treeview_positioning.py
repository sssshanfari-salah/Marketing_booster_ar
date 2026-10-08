import tkinter as tk
from tkinter import ttk
from typing import Dict


def position_widget_in_column(
    tree: ttk.Treeview,
    widgets: Dict[str, tk.Widget],
    column_id: str,
    x_offset: int = 2,
    min_width: int = 90,
    width_adjustment: int = 6,
    min_height: int = 22,
    y_offset: int = 2,
):
    for row_id, widget in list(widgets.items()):
        if not tree.exists(row_id):
            widget.destroy()
            widgets.pop(row_id, None)
            continue

        try:
            x, y, width, height = tree.bbox(row_id, column_id)
        except Exception:
            continue

        if width <= 0:
            continue

        widget.place(
            x=x + x_offset,
            y=y + y_offset,
            width=max(min_width, width - width_adjustment),
            height=max(min_height, height - 4),
        )
