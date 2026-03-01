from typing import List, Tuple

from domain.models.movement import Movement
from domain.models.statement import Statement


def resolve_paypal(
    santander_statement: Statement,
    paypal_statement: Statement,
) -> Tuple[List[Movement], List[Movement]]:
    """Cruza los cobros de PayPal del extracto de Santander con el detalle del CSV de PayPal.

    Para cada movimiento de Santander que contenga 'paypal' en la descripción,
    busca en PayPal un movimiento con mismo importe (abs) y fecha próxima (±3 días).
    Si hay match, sustituye la descripción por el nombre real del comercio y guarda
    la descripción original en resolved_from. Cada movimiento de PayPal solo puede
    ser usado una vez.

    Devuelve una tupla (movimientos_santander_resueltos, movimientos_paypal_no_cruzados).
    """
    available_paypal: List[Movement] = list(paypal_statement.all())
    resolved_santander: List[Movement] = []

    for movement in santander_statement.all():
        if "paypal" in movement.description.lower():
            matched = _find_paypal_match(movement, available_paypal)
            if matched:
                movement.resolved_from = movement.description
                movement.description = matched.description
                available_paypal.remove(matched)
        resolved_santander.append(movement)

    return resolved_santander, available_paypal


def _find_paypal_match(
    santander: Movement,
    paypal_movements: List[Movement],
) -> Movement | None:
    for pp in paypal_movements:
        same_amount = abs(abs(pp.amount) - abs(santander.amount)) < 0.01
        close_date = abs((pp.date - santander.date).days) <= 3
        if same_amount and close_date:
            return pp
    return None
