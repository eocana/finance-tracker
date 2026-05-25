"""
Caso de uso: ExportMovements

Exporta la lista de movimientos al formato destino delegando
en la abstracción Exporter.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from domain.interfaces.exporter import Exporter
from domain.models.movement import Movement


class ExportMovements:
    """Caso de uso: exportar movimientos a un archivo.

    Recibe un Exporter inyectado; no conoce el formato de salida concreto.

    Args:
        exporter: Implementación de Exporter (Excel, CSV, JSON…)
    """

    def __init__(self, exporter: Exporter) -> None:
        self._exporter = exporter

    def execute(self, movements: List[Movement], output_path: Path) -> Path:
        """Ejecuta la exportación.

        Args:
            movements:   Lista de movimientos ya categorizados.
            output_path: Ruta donde se generará el archivo de salida.

        Returns:
            La ruta final donde se escribió el archivo.

        Raises:
            IOError: Si no es posible escribir en la ruta indicada.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._exporter.export(movements, output_path)
        return output_path
