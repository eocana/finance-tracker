"""
Entidad principal del dominio: Movement.

No tiene dependencias externas; cumple con la regla de Clean Architecture
de mantener el dominio libre de infraestructura.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class Movement:
    """Representa un movimiento bancario normalizado.

    Atributos:
        date:          Fecha de la operación.
        description:   Descripción del movimiento (puede ser enriquecida tras cruce).
        amount:        Importe en euros. Negativo = gasto, positivo = ingreso.
        source:        Fuente del movimiento: "santander" | "paypal" | "lacaixa".
        category:      Categoría asignada por el categorizador. Vacío hasta categorizar.
        resolved_from: Descripción original antes del cruce con PayPal.
                       Solo tiene valor cuando se ha resuelto el movimiento.
    """

    date: date
    description: str
    amount: float
    source: str
    category: str = ""
    resolved_from: str = ""

    def is_expense(self) -> bool:
        """Devuelve True si el movimiento es un gasto (importe negativo)."""
        return self.amount < 0

    def is_income(self) -> bool:
        """Devuelve True si el movimiento es un ingreso (importe positivo)."""
        return self.amount > 0

    def is_resolved(self) -> bool:
        """Devuelve True si el movimiento fue cruzado con PayPal."""
        return bool(self.resolved_from)

    def __repr__(self) -> str:
        sign = "-" if self.is_expense() else "+"
        return (
            f"Movement({self.date} | {self.source} | "
            f"{sign}{abs(self.amount):.2f}€ | {self.description[:40]!r})"
        )
