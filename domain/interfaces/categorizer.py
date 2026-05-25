"""ABC: Categorizer — Interfaz para categorizadores de movimientos."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from domain.models.movement import Movement


class Categorizer(ABC):
    """Interfaz común para estrategias de categorización de movimientos.

    Desacopla la lógica de categorización del dominio y de los casos de uso.
    Permite intercambiar reglas manuales, ML, etc. sin tocar el resto del código.
    """

    @abstractmethod
    def categorize(self, movement: Movement) -> str:
        """Determina y devuelve la categoría para un movimiento.

        Args:
            movement: Movimiento a categorizar.

        Returns:
            Cadena con el nombre de la categoría asignada.
            Debe devolver "Otros" si ninguna regla aplica.
        """
        ...

    @abstractmethod
    def categorize_all(self, movements: List[Movement]) -> List[Movement]:
        """Categoriza una lista entera de movimientos in-place.

        Modifica el campo `category` de cada Movement y devuelve la misma lista.

        Args:
            movements: Lista de movimientos a categorizar.

        Returns:
            La misma lista con el campo `category` relleno en cada elemento.
        """
        ...
