from typing import Iterator, List

from domain.models.movement import Movement


class Statement:
    """Colección de movimientos de una misma fuente bancaria."""

    def __init__(self, source: str, movements: List[Movement] | None = None) -> None:
        self.source = source
        self._movements: List[Movement] = movements or []

    def add(self, movement: Movement) -> None:
        self._movements.append(movement)

    def all(self) -> List[Movement]:
        return list(self._movements)

    def __iter__(self) -> Iterator[Movement]:
        return iter(self._movements)

    def __len__(self) -> int:
        return len(self._movements)
