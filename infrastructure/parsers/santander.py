import re
from datetime import datetime

import pdfplumber

from domain.interfaces.parser import StatementParser
from domain.models.movement import Movement
from domain.models.statement import Statement


class SantanderPDFParser(StatementParser):
    """Parser para extractos PDF del Banco Santander.

    pdfplumber devuelve cada fila de la tabla como una lista de columnas:
      row[0] = fecha (ej: "28 feb 2026\\nF. valor: 02 mar 2026")
      row[1] = descripción
      row[2] = importe (ej: "-177,19€")
      row[3] = saldo (ignorar)
    """

    _DATE_RE = re.compile(r"(\d{1,2}\s+\w{3}\s+\d{4})", re.IGNORECASE)
    _AMOUNT_RE = re.compile(r"([+-]?\d[\d.]*,\d{2})\s*€?")

    def parse(self, file_path: str) -> Statement:
        statement = Statement(source="santander")

        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        movement = self._parse_row(row)
                        if movement:
                            statement.add(movement)

        return statement

    def _parse_row(self, row: list) -> Movement | None:
        if not row or len(row) < 3:
            return None

        date_cell = row[0] or ""
        description = (row[1] or "").strip()
        amount_cell = row[2] or ""

        date_match = self._DATE_RE.search(date_cell)
        if not date_match:
            return None

        try:
            date = datetime.strptime(date_match.group(1), "%d %b %Y").date()
        except ValueError:
            return None

        amount_match = self._AMOUNT_RE.search(amount_cell)
        if not amount_match:
            return None

        try:
            amount = float(amount_match.group(1).replace(".", "").replace(",", "."))
        except ValueError:
            return None

        if not description:
            return None

        return Movement(
            date=date,
            description=description,
            amount=amount,
            source="santander",
        )
