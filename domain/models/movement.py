from dataclasses import dataclass, field
from datetime import date


@dataclass
class Movement:
    date: date
    description: str
    amount: float          # negativo = gasto, positivo = ingreso
    source: str            # "santander" | "paypal" | "lacaixa"
    category: str = ""
    resolved_from: str = ""  # Si fue cruzado con PayPal, descripción original
