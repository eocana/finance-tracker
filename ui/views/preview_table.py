import tkinter as tk
from tkinter import ttk
from typing import List

from domain.models.movement import Movement


class PreviewTable(tk.Frame):
    """Tabla de previsualización de movimientos."""

    _COLUMNS = ("Fecha", "Descripción", "Categoría", "Fuente", "Importe (€)", "Detalle PayPal")

    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self._build()

    def _build(self) -> None:
        self._tree = ttk.Treeview(self, columns=self._COLUMNS, show="headings")
        for col in self._COLUMNS:
            self._tree.heading(col, text=col)
            self._tree.column(col, width=130)

        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)

        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def load(self, movements: List[Movement]) -> None:
        self._tree.delete(*self._tree.get_children())
        for mv in movements:
            self._tree.insert(
                "",
                tk.END,
                values=(
                    mv.date.strftime("%d/%m/%Y"),
                    mv.description,
                    mv.category,
                    mv.source,
                    f"{mv.amount:.2f}€",
                    mv.resolved_from,
                ),
            )
