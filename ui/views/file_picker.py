import tkinter as tk
from tkinter import filedialog


class FilePicker(tk.Frame):
    """Widget para seleccionar archivos de extractos bancarios."""

    def __init__(self, master, label: str, filetypes: list, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self._path = tk.StringVar()
        self._label = label
        self._filetypes = filetypes
        self._build()

    def _build(self) -> None:
        tk.Label(self, text=self._label, anchor="w").pack(side=tk.LEFT, padx=(0, 5))
        tk.Entry(self, textvariable=self._path, width=40).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(self, text="Examinar…", command=self._browse).pack(side=tk.LEFT)

    def _browse(self) -> None:
        path = filedialog.askopenfilename(filetypes=self._filetypes)
        if path:
            self._path.set(path)

    @property
    def path(self) -> str:
        return self._path.get()
