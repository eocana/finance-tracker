from typing import Dict, List

from domain.interfaces.categorizer import Categorizer
from domain.models.movement import Movement

RULES: Dict[str, List[str]] = {
    "Supermercado": ["mercadona", "carrefour", "bonpreu", "supermercat", "roges"],
    "Restaurante": ["mcdonald", "kebab", "sushi", "rostisseria"],
    "Subscripción": ["paypal", "spotify", "netflix", "google play"],
    "Transporte": ["autopista", "renfe", "bus"],
    "Alquiler": ["alquiler"],
    "Suministros": ["energia", "llum", "gas", "agua"],
    "Inversión": ["trade republic", "inversión", "invest"],
    "Nómina": ["nomina", "nómina", "sueldo"],
    "Transferencia": ["transferencia"],
}


class RuleBasedCategorizer(Categorizer):
    """Categorizador basado en reglas de palabras clave configurables."""

    def __init__(self, rules: Dict[str, List[str]] | None = None) -> None:
        self._rules = rules if rules is not None else RULES

    def categorize(self, movement: Movement) -> str:
        description_lower = movement.description.lower()
        for category, keywords in self._rules.items():
            for keyword in keywords:
                if keyword in description_lower:
                    return category
        return "Otros"
