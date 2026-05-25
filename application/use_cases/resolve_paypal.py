"""
Caso de uso: ResolvePayPal

Cruza los movimientos de Santander cuya descripción contiene "paypal"
con el detalle real de cada cobro proveniente del CSV de PayPal.

Criterio de match:
  - |paypal.amount| == |santander.amount|  (mismo importe absoluto)
  - |paypal.date - santander.date| <= 3 días  (tolerancia de liquidación)

Cuando hay match:
  - santander.description  ← nombre del comercio real (de PayPal)
  - santander.resolved_from ← descripción original de Santander
"""

from __future__ import annotations

import re
from typing import List

from domain.models.movement import Movement

_RECIBO_PAYPAL_RE = re.compile(r"recibo paypal", re.IGNORECASE)


_TOLERANCE_DAYS: int = 5  # Incluye retrasos por conversión de divisa (3-4 días)


class ResolvePayPal:
    """Caso de uso: enriquecer movimientos Santander↔PayPal.

    No depende de ninguna librería externa; opera solo sobre Movement.
    """

    def execute(
        self,
        santander_movements: List[Movement],
        paypal_movements: List[Movement],
    ) -> List[Movement]:
        """Cruza y enriquece los movimientos de Santander con los de PayPal.

        Modifica in-place los movimientos de Santander que tengan match
        y devuelve la lista completa de movimientos de Santander (modificados
        o no).

        Args:
            santander_movements: Lista de movimientos de Santander.
            paypal_movements:    Lista de movimientos del CSV de PayPal.

        Returns:
            Lista de movimientos de Santander con los campos `description`
            y `resolved_from` actualizados cuando corresponde.
        """
        unmatched_paypal = list(paypal_movements)

        for movement in santander_movements:
            if "paypal" not in movement.description.lower():
                continue

            match = self._find_match(movement, unmatched_paypal)
            if match is None:
                continue

            # Enriquecer movimiento con datos reales de PayPal
            movement.resolved_from = movement.description
            movement.description = match.description
            # Marcar el movimiento PayPal como ya usado para evitar
            # dobles asignaciones en el mismo extracto
            unmatched_paypal.remove(match)

        # ----------------------------------------------------------------
        # Limpiar cobros PayPal que no pudieron resolverse con el CSV
        # (p.ej. el CSV exportado no cubre todas las fechas).
        # En lugar de mostrar el código bancario crudo, usamos un nombre
        # legible para que el usuario sepa de qué se trata.
        # ----------------------------------------------------------------
        for movement in santander_movements:
            if _RECIBO_PAYPAL_RE.search(movement.description) and not movement.is_resolved():
                movement.resolved_from = movement.description
                movement.description = "PayPal — sin detalle en CSV"

        return santander_movements

    # ------------------------------------------------------------------
    # Privado
    # ------------------------------------------------------------------

    @staticmethod
    def _find_match(
        santander: Movement,
        candidates: List[Movement],
    ) -> Movement | None:
        """Busca el movimiento PayPal que mejor encaja con el de Santander.

        Args:
            santander:  Movimiento de Santander a resolver.
            candidates: Movimientos de PayPal todavía sin asignar.

        Returns:
            El primer movimiento PayPal que cumple los criterios, o None.
        """
        for candidate in candidates:
            same_amount = abs(candidate.amount) == abs(santander.amount)
            date_diff = abs((candidate.date - santander.date).days)
            within_tolerance = date_diff <= _TOLERANCE_DAYS

            if same_amount and within_tolerance:
                return candidate

        return None
