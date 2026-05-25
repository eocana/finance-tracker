"""
Colección de movimientos de una fuente bancaria concreta.
Actúa como Repository en memoria para los movimientos de un extracto.
"""

from __future__ import annotations

from datetime import date
from typing import Iterator, List, Optional

from domain.models.movement import Movement


class Statement:
    """Repositorio en memoria que agrupa movimientos de una misma fuente.

    Patrón Repository: expone una interfaz limpia para filtrar y acceder
    a la colección sin exponer detalles de almacenamiento.

    Args:
        source:    Nombre de la fuente ("santander", "paypal", "lacaixa").
        movements: Lista inicial de movimientos (opcional).
    """

    def __init__(self, source: str, movements: Optional[List[Movement]] = None, saldo_disponible: Optional[float] = None) -> None:
        self._source: str = source
        self._movements: List[Movement] = movements or []
        self._saldo_disponible: Optional[float] = saldo_disponible

    # ------------------------------------------------------------------
    # Propiedades de acceso
    # ------------------------------------------------------------------

    @property
    def source(self) -> str:
        return self._source

    @property
    def movements(self) -> List[Movement]:
        """Lista de movimientos (copia defensiva)."""
        return list(self._movements)

    @property
    def saldo_disponible(self) -> Optional[float]:
        """Saldo disponible informado por el banco en la cabecera del extracto."""
        return self._saldo_disponible

    # ------------------------------------------------------------------
    # Mutaciones
    # ------------------------------------------------------------------

    def add(self, movement: Movement) -> None:
        """Añade un movimiento al extracto."""
        self._movements.append(movement)

    def add_many(self, movements: List[Movement]) -> None:
        """Añade varios movimientos de una vez."""
        self._movements.extend(movements)

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    def filter_by_source(self, source: str) -> List[Movement]:
        return [m for m in self._movements if m.source == source]

    def filter_by_date_range(self, start: date, end: date) -> List[Movement]:
        return [m for m in self._movements if start <= m.date <= end]

    def filter_expenses(self) -> List[Movement]:
        return [m for m in self._movements if m.is_expense()]

    def filter_incomes(self) -> List[Movement]:
        return [m for m in self._movements if m.is_income()]

    def filter_by_description(self, keyword: str) -> List[Movement]:
        kw = keyword.lower()
        return [m for m in self._movements if kw in m.description.lower()]

    def total_expenses(self) -> float:
        return sum(m.amount for m in self._movements if m.is_expense())

    def total_incomes(self) -> float:
        return sum(m.amount for m in self._movements if m.is_income())

    # ------------------------------------------------------------------
    # Protocolo Python
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return len(self._movements)

    def __iter__(self) -> Iterator[Movement]:
        return iter(self._movements)

    def __repr__(self) -> str:
        return f"Statement(source={self._source!r}, movements={len(self._movements)})"
