"""ABC: StatementParser — Patrón Strategy para parsers bancarios."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from domain.models.statement import Statement


class StatementParser(ABC):
    """Interfaz común para todos los parsers de extractos bancarios.

    Cada banco implementa su propia estrategia de parsing (Patrón Strategy).
    El dominio depende solo de esta abstracción, nunca de implementaciones
    concretas como pdfplumber u openpyxl.
    """

    @abstractmethod
    def parse(self, file_path: Path) -> Statement:
        """Lee el archivo indicado y devuelve un Statement normalizado.

        Args:
            file_path: Ruta absoluta al archivo de extracto bancario.

        Returns:
            Statement con todos los movimientos normalizados.

        Raises:
            FileNotFoundError: Si el archivo no existe.
            ValueError: Si el formato del archivo no es compatible.
        """
        ...

    @abstractmethod
    def can_parse(self, file_path: Path) -> bool:
        """Indica si este parser puede procesar el archivo dado.

        Usado por el ParserFactory para seleccionar el parser correcto.

        Args:
            file_path: Ruta al archivo a inspeccionar.

        Returns:
            True si el parser es compatible con el archivo.
        """
        ...
