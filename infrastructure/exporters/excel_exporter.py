"""
ExcelExporter — Genera un archivo .xlsx con openpyxl.

Especificaciones de la hoja "Movimientos":
  Columnas: Fecha | Descripción | Categoría | Fuente | Importe (€)
  - Cabecera: fondo azul oscuro, texto blanco, negrita
  - Ingresos: fondo verde claro
  - Gastos:   fondo rojo claro (alternado para legibilidad)
  - Importe:  formato #,##0.00€; color rojo si negativo
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Dict, List, Tuple

import openpyxl  # type: ignore
from openpyxl.styles import Alignment, Font, PatternFill  # type: ignore
from openpyxl.utils import get_column_letter  # type: ignore

from domain.interfaces.exporter import Exporter
from domain.models.movement import Movement


# -----------------------------------------------------------------------
# Paleta de colores
# -----------------------------------------------------------------------
_COLOR_HEADER_BG = "1F3864"   # Azul oscuro (fondo cabecera)
_COLOR_HEADER_FG = "FFFFFF"   # Blanco (texto cabecera)
_COLOR_INCOME = "C6EFCE"      # Verde claro (ingresos)
_COLOR_EXPENSE_A = "FFCCCC"   # Rojo claro fila par
_COLOR_EXPENSE_B = "FFE5E5"   # Rojo muy claro fila impar
# Colores resumen
_COLOR_SUMMARY_BG  = "2E4057"   # Azul-gris oscuro (fila resumen)
_COLOR_SUMMARY_FG  = "FFFFFF"
_COLOR_INCOME_DARK = "1E7E34"   # Verde oscuro (importe ingreso en resumen)
_COLOR_EXPENSE_DARK= "C0392B"   # Rojo oscuro (importe gasto en resumen)
_COLOR_BALANCE_POS = "27AE60"   # Verde balance positivo
_COLOR_BALANCE_NEG = "E74C3C"   # Rojo balance negativo

_MONTHS_ES = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
              "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

_COLUMNS = [
    ("Fecha", 14),
    ("Descripción", 55),
    ("Categoría", 20),
    ("Fuente", 14),
    ("Importe (€)", 16),
]


class ExcelExporter(Exporter):
    """Implementación de Exporter que genera archivos .xlsx con openpyxl."""

    def export(self, movements: List[Movement], output_path: Path) -> None:
        """Genera el archivo Excel con una sola hoja 'Movimientos'."""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Movimientos"

        self._write_header(ws)
        self._write_rows(ws, movements)
        self._write_summary_row(ws, movements)
        self._auto_filter(ws)
        self._freeze_header(ws)

        wb.save(output_path)

    def export_multi_month(self, movements: List[Movement], output_path: Path) -> None:
        """Genera un .xlsx con una hoja por mes + hoja resumen global.

        Cada hoja de mes contiene los movimientos del período y una fila
        de totales al final con ingresos, gastos y balance.
        La primera hoja 'Resumen' lista todos los meses con sus totales.
        """
        # Agrupar por (año, mes) manteniendo orden cronológico descendente
        groups: Dict[Tuple[int, int], List[Movement]] = {}
        for m in movements:
            key = (m.date.year, m.date.month)
            groups.setdefault(key, []).append(m)

        wb = openpyxl.Workbook()
        wb.remove(wb.active)  # quitar hoja vacía por defecto

        # --- Hoja Resumen ---
        ws_res = wb.create_sheet("Resumen")
        self._write_global_summary(ws_res, groups)

        # --- Una hoja por mes ---
        for key in sorted(groups.keys(), reverse=True):
            year, month = key
            sheet_name = f"{_MONTHS_ES[month]} {year}"
            ws = wb.create_sheet(sheet_name)
            self._write_header(ws)
            self._write_rows(ws, groups[key])
            self._write_summary_row(ws, groups[key])
            self._auto_filter(ws)
            self._freeze_header(ws)

        wb.save(output_path)

    # ------------------------------------------------------------------
    # Privado — construcción de la hoja
    # ------------------------------------------------------------------

    def _write_global_summary(self, ws, groups: Dict[Tuple[int, int], List[Movement]]) -> None:
        """Escribe la hoja Resumen con una fila por mes."""
        header_fill = PatternFill("solid", fgColor=_COLOR_HEADER_BG)
        header_font = Font(bold=True, color=_COLOR_HEADER_FG)
        summary_cols = [("Período", 20), ("Ingresos (€)", 16), ("Gastos (€)", 16), ("Balance (€)", 16)]

        for col_idx, (name, width) in enumerate(summary_cols, start=1):
            cell = ws.cell(row=1, column=col_idx, value=name)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
            ws.column_dimensions[get_column_letter(col_idx)].width = width
        ws.row_dimensions[1].height = 20

        total_income_all = 0.0
        total_expense_all = 0.0

        for row_idx, key in enumerate(sorted(groups.keys(), reverse=True), start=2):
            year, month = key
            mvs = groups[key]
            income  = sum(m.amount for m in mvs if m.amount > 0)
            expense = sum(m.amount for m in mvs if m.amount < 0)
            balance = income + expense
            total_income_all  += income
            total_expense_all += expense

            ws.cell(row=row_idx, column=1, value=f"{_MONTHS_ES[month]} {year}")
            for col_idx, (val, color) in enumerate([
                (income,  _COLOR_INCOME_DARK),
                (expense, _COLOR_EXPENSE_DARK),
                (balance, _COLOR_BALANCE_POS if balance >= 0 else _COLOR_BALANCE_NEG),
            ], start=2):
                cell = ws.cell(row=row_idx, column=col_idx, value=val)
                cell.number_format = '#,##0.00"€"'
                cell.font = Font(bold=False, color=color)
                cell.alignment = Alignment(vertical="center")

        # Fila total global
        total_row = len(groups) + 2
        total_fill = PatternFill("solid", fgColor=_COLOR_SUMMARY_BG)
        total_font_base = Font(bold=True, color=_COLOR_SUMMARY_FG)
        ws.cell(row=total_row, column=1, value="TOTAL").fill = total_fill
        ws.cell(row=total_row, column=1).font = total_font_base
        ws.cell(row=total_row, column=1).alignment = Alignment(horizontal="center")
        balance_all = total_income_all + total_expense_all
        for col_idx, (val, color) in enumerate([
            (total_income_all,  _COLOR_INCOME_DARK),
            (total_expense_all, _COLOR_EXPENSE_DARK),
            (balance_all, _COLOR_BALANCE_POS if balance_all >= 0 else _COLOR_BALANCE_NEG),
        ], start=2):
            cell = ws.cell(row=total_row, column=col_idx, value=val)
            cell.number_format = '#,##0.00"€"'
            cell.fill = total_fill
            cell.font = Font(bold=True, color=color)
            cell.alignment = Alignment(vertical="center")
        ws.row_dimensions[total_row].height = 18

    @staticmethod
    def _write_summary_row(ws, movements: List[Movement]) -> None:
        """Añade una fila de totales al final de la hoja de movimientos."""
        income  = sum(m.amount for m in movements if m.amount > 0)
        expense = sum(m.amount for m in movements if m.amount < 0)
        balance = income + expense

        next_row = ws.max_row + 1
        summary_fill = PatternFill("solid", fgColor=_COLOR_SUMMARY_BG)
        base_font    = Font(bold=True, color=_COLOR_SUMMARY_FG)

        # Columnas 1-4: etiqueta extendida
        for col in range(1, 5):
            cell = ws.cell(row=next_row, column=col)
            cell.fill = summary_fill
            cell.font = base_font
        ws.cell(row=next_row, column=1, value="RESUMEN DEL PERÍODO")
        ws.cell(row=next_row, column=1).alignment = Alignment(horizontal="left")

        # Columna 5: balance
        bal_color = _COLOR_BALANCE_POS if balance >= 0 else _COLOR_BALANCE_NEG
        bal_cell  = ws.cell(row=next_row, column=5, value=balance)
        bal_cell.number_format = '#,##0.00"€"'
        bal_cell.fill  = summary_fill
        bal_cell.font  = Font(bold=True, color=bal_color)
        bal_cell.alignment = Alignment(vertical="center")

        # Fila extra con detalle ingreso/gasto
        detail_row = next_row + 1
        detail_fill = PatternFill("solid", fgColor="162030")
        for col in range(1, 6):
            ws.cell(row=detail_row, column=col).fill = detail_fill
        ws.cell(row=detail_row, column=1, value=f"  Ingresos: {income:,.2f}€   Gastos: {expense:,.2f}€")
        ws.cell(row=detail_row, column=1).font = Font(italic=True, color="AAAAAA")
        ws.row_dimensions[detail_row].height = 14

    @staticmethod
    def _write_header(ws) -> None:
        """Escribe la fila de cabecera con estilos."""
        header_fill = PatternFill("solid", fgColor=_COLOR_HEADER_BG)
        header_font = Font(bold=True, color=_COLOR_HEADER_FG)

        for col_idx, (col_name, col_width) in enumerate(_COLUMNS, start=1):
            cell = ws.cell(row=1, column=col_idx, value=col_name)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
            ws.column_dimensions[get_column_letter(col_idx)].width = col_width

        ws.row_dimensions[1].height = 20

    @staticmethod
    def _write_rows(ws, movements: List[Movement]) -> None:
        """Escribe las filas de datos con estilos condicionales."""
        expense_even_fill = PatternFill("solid", fgColor=_COLOR_EXPENSE_A)
        expense_odd_fill = PatternFill("solid", fgColor=_COLOR_EXPENSE_B)
        income_fill = PatternFill("solid", fgColor=_COLOR_INCOME)

        expense_count = 0  # contador independiente para alternado de gastos

        for row_offset, movement in enumerate(movements):
            excel_row = row_offset + 2  # fila 1 = cabecera

            # Determinar color de fila
            if movement.is_income():
                row_fill = income_fill
            else:
                expense_count += 1
                row_fill = expense_even_fill if expense_count % 2 == 0 else expense_odd_fill

            # Escribir celdas
            values = [
                movement.date.strftime("%d/%m/%Y") if isinstance(movement.date, date) else str(movement.date),
                movement.description,
                movement.category or "Sin categoría",
                movement.source,
                movement.amount,
            ]

            for col_idx, value in enumerate(values, start=1):
                cell = ws.cell(row=excel_row, column=col_idx, value=value)
                cell.fill = row_fill
                cell.alignment = Alignment(vertical="center")

                # Formato especial para la columna Importe
                if col_idx == 5:
                    cell.number_format = '#,##0.00"€"'
                    if isinstance(value, (int, float)) and value < 0:
                        cell.font = Font(color="FF0000")

    @staticmethod
    def _auto_filter(ws) -> None:
        """Activa el autofiltro en la cabecera."""
        last_col = get_column_letter(len(_COLUMNS))
        ws.auto_filter.ref = f"A1:{last_col}1"

    @staticmethod
    def _freeze_header(ws) -> None:
        """Congela la primera fila para que quede visible al desplazarse."""
        ws.freeze_panes = "A2"
