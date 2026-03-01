from abc import ABC, abstractmethod
from typing import List

from domain.models.movement import Movement


class Exporter(ABC):
    """Interfaz para exportadores de movimientos."""

    @abstractmethod
    def export(self, movements: List[Movement], output_path: str) -> None:
        """Exporta la lista de movimientos al archivo indicado."""
        ...
