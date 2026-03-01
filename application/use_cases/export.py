from typing import List

from domain.interfaces.exporter import Exporter
from domain.models.movement import Movement


def export_movements(
    movements: List[Movement],
    exporter: Exporter,
    output_path: str,
) -> None:
    """Caso de uso: exporta la lista de movimientos al archivo indicado."""
    exporter.export(movements, output_path)
