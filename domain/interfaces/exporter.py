"""ABC: Exporter — Interfaz para exportadores de movimientos."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

from domain.models.movement import Movement


class Exporter(ABC):
    """Interfaz común para exportadores de movimientos a distintos formatos.

    Permite desacoplar la lógica de exportación del dominio y de los
    casos de uso. Cada formato (Excel, CSV, JSON…) será una implementación.
    """

    @abstractmethod
    def export(self, movements: List[Movement], output_path: Path) -> None:
        """Exporta la lista de movimientos al destino indicado.

        Args:
            movements:   Lista de movimientos ya categorizados.
            output_path: Ruta donde se escribirá el archivo de salida.

        Raises:
            IOError: Si no es posible escribir en la ruta indicada.
        """
        ...
