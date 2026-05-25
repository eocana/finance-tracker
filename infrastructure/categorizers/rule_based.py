"""
RuleBasedCategorizer — Categorizador por reglas de palabras clave.

Patrón Strategy aplicado al categorizador: esta implementación usa
un diccionario de reglas configurable. Puede sustituirse por otro
Categorizer (ML, API…) sin tocar ningún caso de uso.

Lógica: iterar las reglas en orden, comprobar si alguna keyword está
contenida en description.lower(). Devolver la primera categoría que haga
match. Si ninguna coincide: "Otros".
"""

from __future__ import annotations

from typing import Dict, List

from domain.interfaces.categorizer import Categorizer
from domain.models.movement import Movement


# -----------------------------------------------------------------------
# Reglas predefinidas
# -----------------------------------------------------------------------
# IMPORTANTE: las reglas se evalúan en orden; la primera que haga match gana.
# Las reglas más específicas (crédito, movimientos internos, ocio…) deben ir
# antes que las genéricas (transferencia, subscripción…).
DEFAULT_RULES: Dict[str, List[str]] = {
    # Movimientos propios / internos — antes que "Transferencia" genérica
    "Movimiento entre cuentas": [
        "transferencia inmediata a favor de eric",
        "transferencia a favor de eric ocaña",
        "transferencia a favor de eric ocana",
        "transferencia a favor de eric",
        "resto nomina",   # traspaso parcial del sueldo a otra cuenta
        "resto nómina",
    ],
    # Liquidación / crédito bancario
    "Crédito": [
        "liquidacion de las tarjetas",
        "liquidación de las tarjetas",
        "liquidacion tarjeta",
        "liquidacion credito",
        "liquidación crédito",
    ],
    # Nómina / ingresos laborales
    "Nómina": ["nomina", "nómina", "sueldo", "auditing software"],
    # Bonificaciones bancarias
    "Bonificación": ["bonificacion", "bonificación", "campaña"],
    # Bizum — antes de Restaurante para evitar que "bizum" caiga en otra categoría
    "Bizum": ["bizum"],
    # Suministros — ANTES de Supermercado para que "energia" gane a "bonpreu"
    "Suministros": [
        "energia", "llum", "gas natural", "iberdrola", "endesa",
        "naturgy", "aguas", "recibo energia",
    ],
    # Supermercado
    "Supermercado": [
        "mercadona", "carrefour", "carref", "bonpreu", "supermercat",
        "roges", "lidl", "aldi", "dia ",
    ],
    # Restaurante
    "Restaurante": [
        "mcdonald", "kebab", "sushi", "rostisseria",
        "burger", "pizza", "restaurante",
    ],
    # Ocio — videojuegos, entretenimiento
    "Ocio": [
        "steam", "instant gaming", "playstation", "xbox", "nintendo",
        "twitch", "humble", "epic games", "gaming",
    ],
    # Subscripciones de streaming y servicios digitales
    "Subscripción": [
        "spotify", "netflix", "disney", "hbo", "amazon prime",
        "youtube premium", "apple", "google one", "100 gb", "github",
    ],
    # Transporte
    "Transporte": [
        "autopista", "renfe", "metro", "bus ", "taxi",
        "cabify", "uber", "parking", "peaje",
    ],
    # Alquiler
    "Alquiler": [
        "alquiler",
        # Conceptos en catalán / español comunes para pagos de alquiler
        "pagament", "pagament traspas", "pagament traspassos", "pagament traspasos",
        "traspassos", "traspasso", "traspasos", "pago alquiler", "alquiler gelida",
    ],
    # Inversiones  (transferencias recibidas con concepto de inversión)
    "Inversiones": [
        "trade republic", "degiro", "etoro", "interactive brokers",
        "inversión", "inversion", "inversiones", "inversio", "inversions",
        "invest", "bolsa", "acciones", "dividendo",
    ],
    # Transferencias genéricas (debe ir DESPUÉS de "Movimiento entre cuentas")
    "Transferencia": ["transferencia"],
    # Cobros PayPal que no pudieron resolverse con el CSV exportado
    "PayPal sin detalle": ["paypal — sin detalle"],
    # Compras online genéricas
    "Compras online": ["google*", "google play", "amazon", "aliexpress", "ebay"],
}

_FALLBACK_CATEGORY = "Otros"


class RuleBasedCategorizer(Categorizer):
    """Categorizador que usa un diccionario de palabras clave.

    Args:
        rules: Diccionario {categoría: [keywords]}.
               Si se omite, se usan DEFAULT_RULES.
    """

    def __init__(self, rules: Dict[str, List[str]] | None = None) -> None:
        self._rules: Dict[str, List[str]] = rules if rules is not None else DEFAULT_RULES

    # ------------------------------------------------------------------
    # Categorizer interface
    # ------------------------------------------------------------------

    def categorize(self, movement: Movement) -> str:
        """Devuelve la categoría para un movimiento según las reglas.

        Itera las reglas en orden de inserción del diccionario. La primera
        categoría cuya keyword aparezca en la descripción (case-insensitive)
        es la ganadora. Si ninguna coincide, devuelve "Otros".

        Args:
            movement: Movimiento a categorizar.

        Returns:
            Nombre de la categoría asignada.
        """
        description_lower = movement.description.lower()

        for category, keywords in self._rules.items():
            for keyword in keywords:
                if keyword.lower() in description_lower:
                    return category

        return _FALLBACK_CATEGORY

    def categorize_all(self, movements: List[Movement]) -> List[Movement]:
        """Categoriza in-place todos los movimientos de la lista.

        Args:
            movements: Lista de movimientos a categorizar.

        Returns:
            La misma lista con el campo `category` relleno.
        """
        for movement in movements:
            movement.category = self.categorize(movement)
        return movements

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------

    def add_rule(self, category: str, keywords: List[str]) -> None:
        """Añade o amplía una regla en tiempo de ejecución.

        Args:
            category: Nombre de la categoría.
            keywords: Lista de nuevas palabras clave para esa categoría.
        """
        if category in self._rules:
            self._rules[category].extend(keywords)
        else:
            self._rules[category] = keywords

    @property
    def rules(self) -> Dict[str, List[str]]:
        """Devuelve una copia del diccionario de reglas activo."""
        return {cat: list(kws) for cat, kws in self._rules.items()}
