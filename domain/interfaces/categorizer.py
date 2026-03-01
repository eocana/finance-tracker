from abc import ABC, abstractmethod

from domain.models.movement import Movement


class Categorizer(ABC):
    """Interfaz para categorizadores de movimientos."""

    @abstractmethod
    def categorize(self, movement: Movement) -> str:
        """Devuelve la categoría correspondiente al movimiento dado."""
        ...
