"""
FilePicker — Componente UI para seleccionar archivos de extractos bancarios.

Patrón Observer: expone un callback `on_files_selected` para que
la ventana principal pueda reaccionar sin acoplarse a este widget.
"""

from __future__ import annotations

from pathlib import Path
from tkinter import filedialog
from typing import Callable, List, Optional

import customtkinter as ctk  # type: ignore


class FilePicker(ctk.CTkFrame):
    """Widget para seleccionar uno o varios archivos de extractos bancarios.

    Muestra una lista de archivos seleccionados y un botón para añadir más.
    Notifica al observador mediante `on_files_selected` cada vez que la
    selección cambia (Patrón Observer desacoplado).

    Args:
        master:             Widget padre.
        on_files_selected:  Callback que recibe la lista actualizada de rutas.
        label_text:         Etiqueta descriptiva del picker.
        file_types:         Filtros de extensión para el diálogo de selección.
    """

    def __init__(
        self,
        master,
        on_files_selected: Optional[Callable[[List[Path]], None]] = None,
        label_text: str = "Archivos de extracto",
        file_types: Optional[List[tuple]] = None,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)

        self._callback = on_files_selected
        self._selected_paths: List[Path] = []
        self._file_types = file_types or [
            ("Extractos bancarios", "*.pdf *.csv"),
            ("PDF", "*.pdf"),
            ("CSV", "*.csv"),
            ("Todos los archivos", "*.*"),
        ]

        self._build_ui(label_text)

    # ------------------------------------------------------------------
    # Propiedades
    # ------------------------------------------------------------------

    @property
    def selected_paths(self) -> List[Path]:
        """Lista de rutas seleccionadas (copia defensiva)."""
        return list(self._selected_paths)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self, label_text: str) -> None:
        self.grid_columnconfigure(0, weight=1)

        # Etiqueta
        ctk.CTkLabel(
            self,
            text=label_text,
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 4), sticky="w")

        # Lista de archivos seleccionados
        self._listbox = ctk.CTkTextbox(self, height=80, state="disabled")
        self._listbox.grid(row=1, column=0, padx=(10, 4), pady=4, sticky="ew")

        # Botones
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=1, column=1, padx=(0, 10), pady=4, sticky="ns")

        ctk.CTkButton(
            btn_frame,
            text="Añadir",
            width=80,
            command=self._on_add,
        ).pack(pady=(0, 4))

        ctk.CTkButton(
            btn_frame,
            text="Limpiar",
            width=80,
            fg_color="gray40",
            hover_color="gray30",
            command=self._on_clear,
        ).pack()

    def _refresh_listbox(self) -> None:
        self._listbox.configure(state="normal")
        self._listbox.delete("1.0", "end")
        for path in self._selected_paths:
            self._listbox.insert("end", f"• {path.name}\n")
        self._listbox.configure(state="disabled")

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _on_add(self) -> None:
        paths = filedialog.askopenfilenames(filetypes=self._file_types)
        if not paths:
            return
        for p in paths:
            path = Path(p)
            if path not in self._selected_paths:
                self._selected_paths.append(path)
        self._refresh_listbox()
        self._notify()

    def _on_clear(self) -> None:
        self._selected_paths.clear()
        self._refresh_listbox()
        self._notify()

    def _notify(self) -> None:
        if self._callback:
            self._callback(list(self._selected_paths))
