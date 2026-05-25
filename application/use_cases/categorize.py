"""
Caso de uso: CategorizeMovements

Asigna una categoría a cada movimiento de la lista delegando
en la abstracción Categorizer.
"""

from __future__ import annotations

from typing import List

from domain.interfaces.categorizer import Categorizer
from domain.models.movement import Movement


class CategorizeMovements:
    """Caso de uso: categorizar una lista de movimientos.

    Recibe un Categorizer inyectado; no conoce la implementación concreta.

    Args:
        categorizer: Implementación de Categorizer (reglas, ML, etc.)
    """

    def __init__(self, categorizer: Categorizer) -> None:
        self._categorizer = categorizer

    def execute(self, movements: List[Movement]) -> List[Movement]:
        """Ejecuta la categorización sobre todos los movimientos.

        Modifica el campo `category` de cada Movement in-place
        y devuelve la misma lista para encadenamiento fluido.

        Args:
            movements: Lista de movimientos a categorizar.

        Returns:
            La misma lista con el campo `category` relleno.
        """
        return self._categorizer.categorize_all(movements)
