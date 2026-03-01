from typing import List

from domain.interfaces.categorizer import Categorizer
from domain.models.movement import Movement


def categorize_movements(
    movements: List[Movement],
    categorizer: Categorizer,
) -> List[Movement]:
    """Caso de uso: asigna una categoría a cada movimiento de la lista."""
    for movement in movements:
        movement.category = categorizer.categorize(movement)
    return movements
