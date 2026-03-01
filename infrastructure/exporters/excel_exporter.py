from typing import List

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from domain.interfaces.exporter import Exporter
from domain.models.movement import Movement


class ExcelExporter(Exporter):
    """Exporta movimientos a un archivo .xlsx con formato visual."""

    _HEADER_FILL = PatternFill("solid", fgColor="1F3864")
    _INCOME_FILL = PatternFill("solid", fgColor="C6EFCE")
    _EXPENSE_FILL = PatternFill("solid", fgColor="FFC7CE")
    _RED_FONT = Font(color="9C0006")
    _HEADER_FONT = Font(bold=True, color="FFFFFF")

    _COLUMNS = [
        ("Fecha", 14),
        ("Descripción", 45),
        ("Categoría", 18),
        ("Fuente", 14),
        ("Importe (€)", 14),
        ("Detalle PayPal", 40),
    ]

    def export(self, movements: List[Movement], output_path: str) -> None:
        wb = Workbook()
        ws = wb.active
        ws.title = "Movimientos"

        self._write_header(ws)
        self._write_rows(ws, movements)
        self._apply_column_widths(ws)

        wb.save(output_path)

    def _write_header(self, ws) -> None:
        for col_idx, (title, _) in enumerate(self._COLUMNS, start=1):
            cell = ws.cell(row=1, column=col_idx, value=title)
            cell.font = self._HEADER_FONT
            cell.fill = self._HEADER_FILL
            cell.alignment = Alignment(horizontal="center")

    def _write_rows(self, ws, movements: List[Movement]) -> None:
        for row_idx, mv in enumerate(movements, start=2):
            ws.cell(row=row_idx, column=1, value=mv.date)
            ws.cell(row=row_idx, column=2, value=mv.description)
            ws.cell(row=row_idx, column=3, value=mv.category)
            ws.cell(row=row_idx, column=4, value=mv.source)

            amount_cell = ws.cell(row=row_idx, column=5, value=mv.amount)
            amount_cell.number_format = '#,##0.00"€"'
            if mv.amount < 0:
                amount_cell.font = self._RED_FONT

            ws.cell(row=row_idx, column=6, value=mv.resolved_from or "")

            row_fill = self._INCOME_FILL if mv.amount >= 0 else self._EXPENSE_FILL
            for col_idx in range(1, 7):
                ws.cell(row=row_idx, column=col_idx).fill = row_fill

    def _apply_column_widths(self, ws) -> None:
        for col_idx, (_, width) in enumerate(self._COLUMNS, start=1):
            ws.column_dimensions[get_column_letter(col_idx)].width = width
