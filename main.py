"""
Finance Tracker — Punto de entrada principal.

Arranca la aplicación de escritorio CustomTkinter.
Todos los imports de infraestructura y UI ocurren aquí; el dominio
permanece completamente aislado de este módulo.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Asegurar que el directorio raíz del proyecto esté en sys.path
# para que los imports absolutos funcionen correctamente al ejecutar
# directamente con `python main.py`.
_ROOT = Path(__file__).parent.resolve()
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import customtkinter as ctk  # type: ignore  # noqa: E402

from ui.views.main_window import MainWindow  # noqa: E402


def main() -> None:
    """Punto de entrada de la aplicación."""
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
