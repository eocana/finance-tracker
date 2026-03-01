import tkinter as tk
from tkinter import filedialog, messagebox
from typing import List

from application.use_cases.categorize import categorize_movements
from application.use_cases.export import export_movements
from application.use_cases.parse_statement import parse_statement
from application.use_cases.resolve_paypal import resolve_paypal
from domain.models.movement import Movement
from domain.models.statement import Statement
from infrastructure.categorizers.rule_based import RuleBasedCategorizer
from infrastructure.exporters.excel_exporter import ExcelExporter
from infrastructure.parsers.parser_factory import ParserFactory
from ui.views.file_picker import FilePicker
from ui.views.preview_table import PreviewTable


class MainWindow(tk.Tk):
    """Ventana principal de Finance Tracker."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Finance Tracker")
        self.geometry("1100x640")
        self._movements: List[Movement] = []
        self._statements: List[Statement] = []
        self._build()

    def _build(self) -> None:
        top = tk.Frame(self, pady=10, padx=10)
        top.pack(fill=tk.X)

        self._santander_picker = FilePicker(
            top,
            label="Santander PDF:",
            filetypes=[("PDF files", "*.pdf")],
        )
        self._santander_picker.pack(fill=tk.X, pady=4)

        self._paypal_picker = FilePicker(
            top,
            label="PayPal CSV:    ",
            filetypes=[("CSV files", "*.csv")],
        )
        self._paypal_picker.pack(fill=tk.X, pady=4)

        btn_frame = tk.Frame(self, padx=10)
        btn_frame.pack(fill=tk.X)

        tk.Button(btn_frame, text="Cargar y procesar", command=self._process).pack(
            side=tk.LEFT, padx=(0, 10)
        )
        tk.Button(btn_frame, text="Exportar a Excel", command=self._export).pack(
            side=tk.LEFT
        )

        self._table = PreviewTable(self)
        self._table.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def _process(self) -> None:
        self._movements = []
        self._statements = []

        santander_path = self._santander_picker.path
        paypal_path = self._paypal_picker.path

        try:
            if santander_path:
                parser = ParserFactory.get_parser(santander_path)
                santander_stmt = parse_statement(parser, santander_path)
                self._statements.append(santander_stmt)
            else:
                santander_stmt = Statement("santander")

            if paypal_path:
                parser = ParserFactory.get_parser(paypal_path)
                paypal_stmt = parse_statement(parser, paypal_path)
                self._statements.append(paypal_stmt)
            else:
                paypal_stmt = Statement("paypal")

            # Cruce PayPal ↔ Santander
            resolved, unmatched_paypal = resolve_paypal(santander_stmt, paypal_stmt)
            self._movements.extend(resolved)

            # Añadir movimientos de PayPal que no fueron cruzados con Santander
            self._movements.extend(unmatched_paypal)

            categorizer = RuleBasedCategorizer()
            categorize_movements(self._movements, categorizer)

            self._table.load(self._movements)

        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Error", str(exc))

    def _export(self) -> None:
        if not self._movements:
            messagebox.showwarning("Sin datos", "Carga los extractos primero.")
            return

        output_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
        )
        if not output_path:
            return

        try:
            export_movements(self._movements, ExcelExporter(), output_path)
            messagebox.showinfo("Exportado", f"Archivo guardado en:\n{output_path}")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Error al exportar", str(exc))
