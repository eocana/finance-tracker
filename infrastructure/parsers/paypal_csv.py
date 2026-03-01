import re
from datetime import datetime

import pandas as pd

from domain.interfaces.parser import StatementParser
from domain.models.movement import Movement
from domain.models.statement import Statement


class PayPalCSVParser(StatementParser):
    """Parser para extractos CSV exportados desde PayPal.

    Columnas relevantes: Fecha, Nombre, Tipo, Bruto, Estado
    Solo se procesan las filas con Estado == "Completado".
    El importe usa coma decimal y puede tener puntos de miles (ej: "1.234,56").
    """

    _AMOUNT_RE = re.compile(r"([+-]?\d[\d.]*,\d{2})")

    def parse(self, file_path: str) -> Statement:
        df = pd.read_csv(file_path, encoding="utf-8-sig")
        statement = Statement(source="paypal")

        for _, row in df.iterrows():
            if str(row.get("Estado", "")).strip() != "Completado":
                continue

            try:
                date = datetime.strptime(str(row["Fecha"]).strip(), "%d/%m/%Y").date()
            except ValueError:
                continue

            description = str(row.get("Nombre", "")).strip()
            raw_amount = str(row.get("Bruto", "")).strip()
            amount_match = self._AMOUNT_RE.search(raw_amount)
            if not amount_match:
                continue

            try:
                amount = float(
                    amount_match.group(1).replace(".", "").replace(",", ".")
                )
            except ValueError:
                continue

            statement.add(
                Movement(
                    date=date,
                    description=description,
                    amount=amount,
                    source="paypal",
                )
            )

        return statement
