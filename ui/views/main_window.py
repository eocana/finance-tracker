"""
MainWindow — Ventana principal de Finance Tracker.

Orquesta todos los componentes de la UI y los casos de uso:
  1. FilePicker (Observable)  →  recoge archivos del usuario
  2. Botón "Procesar"         →  ejecuta el pipeline completo
  3. PreviewTable (Observador) →  muestra los movimientos ya procesados
  4. Botón "Exportar Excel"   →  genera el .xlsx final

Patrón Observer: la ventana actúa como coordinador (no acoplamiento directo
entre FilePicker y PreviewTable). Cada componente notifica o recibe datos
a través de callbacks registrados en esta ventana.
"""

from __future__ import annotations

import calendar
from datetime import date, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox
import tkinter as tk
from typing import Dict, List, Optional, Tuple

import customtkinter as ctk  # type: ignore

from application.use_cases.categorize import CategorizeMovements
from application.use_cases.export import ExportMovements
from application.use_cases.parse_statement import ParseStatement
from application.use_cases.resolve_paypal import ResolvePayPal
from domain.models.movement import Movement
from infrastructure.categorizers.rule_based import RuleBasedCategorizer
from infrastructure.exporters.excel_exporter import ExcelExporter
from infrastructure.parsers.parser_factory import ParserFactory
from ui.views.file_picker import FilePicker
from ui.views.preview_table import PreviewTable

_MONTHS_ES = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
              "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

_ALL_LABEL = "Todos los meses"

# Días hacia atrás en el mes previo en los que un ingreso se considera
# del mes siguiente (p.ej. nómina del 31 de enero = ingreso de febrero).
_SALARY_LOOKBACK_DAYS = 5


class MainWindow(ctk.CTk):
    """Ventana principal de la aplicación Finance Tracker.

    Gestiona el ciclo completo: selección de archivos → procesamiento
    → previsualización → exportación.
    """

    def __init__(self) -> None:
        super().__init__()

        self.title("Finance Tracker")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self._movements: List[Movement] = []        # vista actual (filtrada)
        self._all_movements: List[Movement] = []    # lista completa tras procesar
        self._selected_files: List[Path] = []
        self._saldo_disponible: Optional[float] = None
        self._month_var: tk.StringVar = tk.StringVar(value=_ALL_LABEL)

        # Escala tipográfica según resolución de pantalla
        sw = self.winfo_screenwidth()
        if sw >= 3200:
            self._sf = 1.42
        elif sw >= 2400:
            self._sf = 1.22
        elif sw >= 1800:
            self._sf = 1.10
        else:
            self._sf = 1.00

        # Tamaño inicial de ventana proporcional a la resolución
        win_w = round(1200 * self._sf)
        win_h = round(760 * self._sf)
        self.geometry(f"{win_w}x{win_h}")
        self.minsize(round(900 * self._sf), round(600 * self._sf))

        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _fs(self, base: int) -> int:
        """Aplica el factor de escala al tamaño de fuente base."""
        return max(1, round(base * self._sf))

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)  # row 4 = tabla

        # --- Barra de título ---
        title_bar = ctk.CTkFrame(self, corner_radius=0, fg_color=("gray85", "#1F3864"))
        title_bar.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(
            title_bar,
            text="💰 Finance Tracker",
            font=ctk.CTkFont(size=self._fs(20), weight="bold"),
            text_color="white",
        ).pack(side="left", padx=20, pady=12)

        # --- Panel de control (izquierda) ---
        control_panel = ctk.CTkFrame(self)
        control_panel.grid(row=1, column=0, sticky="ew", padx=16, pady=(12, 4))
        control_panel.grid_columnconfigure((0, 1, 2), weight=1)

        # FilePicker
        self._file_picker = FilePicker(
            control_panel,
            on_files_selected=self._on_files_selected,
            label_text="Archivos de extracto (PDF Santander / CSV PayPal)",
        )
        self._file_picker.grid(row=0, column=0, columnspan=2, padx=(0, 8), pady=8, sticky="ew")

        # Botones de acción
        action_frame = ctk.CTkFrame(control_panel, fg_color="transparent")
        action_frame.grid(row=0, column=2, padx=(8, 0), pady=8, sticky="nsew")
        action_frame.grid_rowconfigure((0, 1, 2), weight=1)

        self._btn_process = ctk.CTkButton(
            action_frame,
            text="▶  Procesar",
            font=ctk.CTkFont(size=self._fs(14), weight="bold"),
            command=self._on_process,
            state="disabled",
        )
        self._btn_process.grid(row=0, column=0, sticky="ew", pady=(0, 6))

        self._btn_export = ctk.CTkButton(
            action_frame,
            text="📊  Exportar Excel",
            font=ctk.CTkFont(size=self._fs(13)),
            command=self._on_export,
            state="disabled",
            fg_color="green",
            hover_color="darkgreen",
        )
        self._btn_export.grid(row=1, column=0, sticky="ew", pady=(0, 6))

        self._btn_clear = ctk.CTkButton(
            action_frame,
            text="🗑  Limpiar todo",
            font=ctk.CTkFont(size=self._fs(13)),
            fg_color="gray40",
            hover_color="gray30",
            command=self._on_clear,
        )
        self._btn_clear.grid(row=2, column=0, sticky="ew")

        # --- Panel de estadísticas ---
        self._build_stats_panel()  # row 2

        # --- Selector de mes ---
        self._build_month_selector()  # row 3

        # --- Tabla de previsualización ---
        self._preview = PreviewTable(self, on_changed=self._on_table_changed)
        self._preview.grid(row=4, column=0, sticky="nsew", padx=16, pady=(4, 8))

        # --- Barra de estado ---
        self._status_bar = ctk.CTkLabel(
            self,
            text="Listo. Selecciona uno o más extractos bancarios.",
            anchor="w",
            font=ctk.CTkFont(size=self._fs(11)),
            text_color="gray60",
        )
        self._status_bar.grid(row=5, column=0, sticky="ew", padx=16, pady=(0, 8))

    def _build_month_selector(self) -> None:
        """Fila compacta con el selector desplegable de mes/año (row 3)."""
        h = max(40, round(42 * self._sf))
        row = ctk.CTkFrame(self, fg_color=("gray88", "gray20"), height=h)
        row.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 2))
        row.grid_columnconfigure(2, weight=1)
        row.grid_propagate(False)

        ctk.CTkLabel(row, text="Período:",
                     font=ctk.CTkFont(size=self._fs(12), weight="bold")).grid(
            row=0, column=0, padx=(12, 6), pady=8)

        self._cb_month = ctk.CTkComboBox(
            row,
            variable=self._month_var,
            values=[_ALL_LABEL],
            width=round(200 * self._sf),
            state="disabled",
            font=ctk.CTkFont(size=self._fs(12)),
            command=lambda _: self._apply_month_filter(),
        )
        self._cb_month.grid(row=0, column=1, padx=(0, 12), pady=8)

        self._lbl_month_count = ctk.CTkLabel(
            row, text="",
            font=ctk.CTkFont(size=self._fs(11)),
            text_color="gray60",
        )
        self._lbl_month_count.grid(row=0, column=2, padx=(0, 12), pady=8, sticky="e")

    def _build_stats_panel(self) -> None:
        """Construye el panel de 3 cajas de estadísticas (row 2)."""
        stats = ctk.CTkFrame(self, fg_color=("gray90", "gray17"))
        stats.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 4))
        stats.grid_columnconfigure((0, 1, 2), weight=1)

        boxes = [
            ("Ingresos totales",    "_lbl_ingresos"),
            ("Gastos totales",      "_lbl_gastos"),
            ("Resultado del período", "_lbl_balance"),
        ]
        for col, (title, attr) in enumerate(boxes):
            pad_l = 8 if col == 0 else 4
            pad_r = 8 if col == 2 else 4
            box = ctk.CTkFrame(stats, fg_color=("gray85", "gray22"), corner_radius=8)
            box.grid(row=0, column=col, padx=(pad_l, pad_r), pady=8, sticky="ew")
            ctk.CTkLabel(
                box, text=title,
                font=ctk.CTkFont(size=self._fs(10)),
                text_color="gray60",
            ).pack(pady=(6, 0))
            lbl = ctk.CTkLabel(
                box, text="—",
                font=ctk.CTkFont(size=self._fs(16), weight="bold"),
                text_color="gray50",
            )
            lbl.pack(pady=(2, 6))
            setattr(self, attr, lbl)

    # ------------------------------------------------------------------
    # Callback de cambios en la tabla
    # ------------------------------------------------------------------

    def _on_table_changed(self, action: str, movement: Movement) -> None:
        """Invocado por PreviewTable cuando el usuario edita, añade o borra.

        - "edit":   el objeto Movement ya está mutado; solo actualizar stats.
        - "add":    añadir a _all_movements y actualizar stats.
        - "delete": quitar de _all_movements y actualizar stats.
        """
        if action == "add":
            self._all_movements.append(movement)
            self._all_movements.sort(key=lambda m: m.date, reverse=True)
            # Actualizar ComboBox de meses si aparece un período nuevo
            self._populate_months()
        elif action == "delete":
            if movement in self._all_movements:
                self._all_movements.remove(movement)

        # Para "edit" los objetos son compartidos por referencia: ya está mutado.
        # En los tres casos recalcular estadísticas del período visible.
        self._update_stats(self._movements)

    # ------------------------------------------------------------------
    # Handlers — Observadores
    # ------------------------------------------------------------------

    def _on_files_selected(self, paths: List[Path]) -> None:
        """Callback del FilePicker. Actualiza estado y botones."""
        self._selected_files = paths
        if paths:
            self._btn_process.configure(state="normal")
            self._set_status(f"{len(paths)} archivo(s) seleccionado(s). Pulsa 'Procesar' para continuar.")
        else:
            self._btn_process.configure(state="disabled")
            self._set_status("No hay archivos seleccionados.")

    def _on_process(self) -> None:
        """Ejecuta el pipeline completo de parseo, cruce y categorización."""
        if not self._selected_files:
            messagebox.showwarning("Sin archivos", "Selecciona al menos un archivo de extracto.")
            return

        self._set_status("Procesando archivos…")
        self.update_idletasks()

        try:
            all_movements: List[Movement] = []
            paypal_movements: List[Movement] = []

            factory = ParserFactory()

            for file_path in self._selected_files:
                try:
                    parser = ParserFactory.get_parser(file_path)
                    use_case = ParseStatement(parser)
                    statement = use_case.execute(file_path)
                    all_movements.extend(statement.movements)

                    if statement.source == "paypal":
                        paypal_movements.extend(statement.movements)
                    elif statement.source == "santander" and statement.saldo_disponible is not None:
                        self._saldo_disponible = statement.saldo_disponible

                except (ValueError, FileNotFoundError) as exc:
                    messagebox.showerror("Error al parsear", str(exc))
                    return
                except NotImplementedError as exc:
                    messagebox.showinfo("Parser no disponible", str(exc))
                    continue

            # Cruce PayPal ↔ Santander
            if paypal_movements:
                santander_movements = [m for m in all_movements if m.source == "santander"]
                ResolvePayPal().execute(santander_movements, paypal_movements)

            # Eliminar movimientos PayPal standalone (ya están cruzados o son duplicados)
            final_movements = [m for m in all_movements if m.source != "paypal"]

            # Categorización
            CategorizeMovements(RuleBasedCategorizer()).execute(final_movements)

            # Ordenar por fecha descendente
            final_movements.sort(key=lambda m: m.date, reverse=True)

            self._all_movements = final_movements

            self._populate_months()
            self._apply_month_filter()
            self._btn_export.configure(state="normal")
            self._set_status(f"✔ {len(final_movements)} movimientos procesados correctamente.")

        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Error inesperado", str(exc))
            self._set_status(f"Error: {exc}")

    def _on_export(self) -> None:
        """Abre el diálogo de guardado y exporta el Excel (vista filtrada actual)."""
        if not self._movements:
            messagebox.showwarning("Sin datos", "Primero procesa los extractos.")
            return

        selected = self._month_var.get()
        if selected == _ALL_LABEL:
            period_label = "todos los meses"
            default_filename = "movimientos.xlsx"
        else:
            # "Febrero 2026" → "movimientos_febrero_2026.xlsx"
            default_filename = "movimientos_" + selected.lower().replace(" ", "_") + ".xlsx"
            period_label = selected

        output_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx"), ("Todos los archivos", "*.*")],
            initialfile=default_filename,
        )
        if not output_path:
            return

        try:
            exporter = ExcelExporter()
            if selected == _ALL_LABEL:
                exporter.export_multi_month(self._movements, Path(output_path))
            else:
                ExportMovements(exporter).execute(self._movements, Path(output_path))
            path = Path(output_path)
            messagebox.showinfo(
                "Exportación completada",
                f"Exportados {len(self._movements)} movimientos ({period_label}):\n{path}",
            )
            self._set_status(f"✔ Exportado {period_label} ({len(self._movements)} movimientos) → {path}")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Error al exportar", str(exc))

    def _on_clear(self) -> None:
        """Limpia la selección y la tabla."""
        self._movements = []
        self._all_movements = []
        self._selected_files = []
        self._saldo_disponible = None
        self._preview.clear()
        self._btn_process.configure(state="disabled")
        self._btn_export.configure(state="disabled")
        self._month_var.set(_ALL_LABEL)
        self._cb_month.configure(values=[_ALL_LABEL], state="disabled")
        self._lbl_month_count.configure(text="")
        for attr in ("_lbl_ingresos", "_lbl_gastos", "_lbl_balance"):
            getattr(self, attr).configure(text="—", text_color="gray50")
        self._set_status("Listo. Selecciona uno o más extractos bancarios.")

    # ------------------------------------------------------------------
    # Filtrado por mes
    # ------------------------------------------------------------------

    def _populate_months(self) -> None:
        """Rellena el ComboBox con los meses presentes en _all_movements."""
        seen: Dict[Tuple[int, int], str] = {}
        for m in self._all_movements:
            key = (m.date.year, m.date.month)
            if key not in seen:
                seen[key] = f"{_MONTHS_ES[m.date.month]} {m.date.year}"
        # Ordenar descendente (más reciente primero)
        options = [_ALL_LABEL] + [
            seen[k] for k in sorted(seen.keys(), reverse=True)
        ]
        self._cb_month.configure(values=options, state="readonly")
        self._month_var.set(_ALL_LABEL)

    def _apply_month_filter(self) -> None:
        """Filtra _all_movements según el mes seleccionado y actualiza UI.

        Reglas de nómina (en orden de aplicación):
          1. Si el mes tiene 2+ nóminas, descartar todas excepto la MÁS TARDÍA.
             La(s) primera(s) son el salario del mes anterior cobrado pronto
             (ej: nómina dic llega el 1 ene junto con la de ene el 31 ene).
          2. Si tras eso el mes sigue sin nómina, mirar la ventana de
             _SALARY_LOOKBACK_DAYS al final del mes anterior y tomar la
             nómina más tardía que encuentre.
          Nunca se cuenta más de 1 nómina por mes.
        """
        selected = self._month_var.get()
        advance_count = 0
        excluded_nominas = 0

        if selected == _ALL_LABEL:
            filtered = list(self._all_movements)
        else:
            # Parsear "Febrero 2026" → (2026, 2)
            parts = selected.rsplit(" ", 1)
            try:
                year = int(parts[1])
                month = _MONTHS_ES.index(parts[0])
            except (IndexError, ValueError):
                filtered = list(self._all_movements)
            else:
                first_day = date(year, month, 1)
                last_day = date(year, month, calendar.monthrange(year, month)[1])

                regular = [
                    m for m in self._all_movements
                    if first_day <= m.date <= last_day
                ]

                # --- Regla 1: deduplicar nóminas dentro del mes ---
                # Solo se consideran ingresos (amount > 0).
                # Solo se deduplica cuando hay dos entradas con el MISMO importe
                # (= misma nómina cobrada antes de tiempo desde el mes anterior).
                # Nóminas con importes distintos son componentes salariales
                # diferentes y se conservan todas.
                nominas = sorted(
                    [m for m in regular if m.category == "Nómina" and m.amount > 0],
                    key=lambda m: m.date,
                )
                excluded_ids: set = set()
                if len(nominas) >= 2:
                    from collections import defaultdict
                    by_amount: dict = defaultdict(list)
                    for nm in nominas:
                        by_amount[round(nm.amount, 2)].append(nm)
                    for dupes in by_amount.values():
                        if len(dupes) >= 2:
                            # Conservar solo la más tardía del grupo duplicado
                            for older in sorted(dupes, key=lambda m: m.date)[:-1]:
                                excluded_ids.add(id(older))
                    excluded_nominas = len(excluded_ids)
                    if excluded_ids:
                        regular = [m for m in regular if id(m) not in excluded_ids]
                        nominas = [m for m in nominas if id(m) not in excluded_ids]

                # --- Regla 2: lookback si aún no hay nómina ---
                advance: List[Movement] = []
                if not nominas:
                    prev_last = first_day - timedelta(days=1)
                    prev_window_start = prev_last.replace(
                        day=max(1, prev_last.day - _SALARY_LOOKBACK_DAYS + 1)
                    )
                    candidates = [
                        m for m in self._all_movements
                        if prev_window_start <= m.date <= prev_last
                        and m.category == "Nómina"
                        and m.amount > 0
                    ]
                    # Tomar solo la más tardía del período anterior
                    if candidates:
                        advance = [max(candidates, key=lambda m: m.date)]

                advance_count = len(advance)
                filtered = regular + advance
                filtered.sort(key=lambda mv: mv.date, reverse=True)

        self._movements = filtered
        self._preview.update_movements(filtered)

        self._update_stats(filtered)

        n = len(filtered)
        total = len(self._all_movements)
        notes = []
        if advance_count:
            notes.append(f"+{advance_count} nómina del mes anterior")
        if excluded_nominas:
            notes.append(f"{excluded_nominas} nómina{'s' if excluded_nominas > 1 else ''} duplicada{'s' if excluded_nominas > 1 else ''} excluida{'s' if excluded_nominas > 1 else ''}")
        note = f" ({', '.join(notes)})" if notes else ""
        self._lbl_month_count.configure(
            text=f"{n} movimiento{'s' if n != 1 else ''}"
                 + (f" (de {total} totales)" if n < total else "")
                 + note
        )

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------

    def _update_stats(self, movements: List[Movement]) -> None:
        """Actualiza las cajas de estadísticas con los movimientos dados."""
        total_income  = sum(m.amount for m in movements if m.amount > 0)
        total_expense = sum(m.amount for m in movements if m.amount < 0)
        net = total_income + total_expense
        self._lbl_ingresos.configure(text=self._fmt(total_income), text_color="#4caf50")
        self._lbl_gastos.configure(text=self._fmt(total_expense),  text_color="#f44336")
        self._lbl_balance.configure(
            text=self._fmt(net),
            text_color="#4caf50" if net >= 0 else "#f44336",
        )

    @staticmethod
    def _fmt(v: float, sign: bool = True) -> str:
        s = f"{abs(v):,.2f}€".replace(",", "X").replace(".", ",").replace("X", ".")
        return (("+" if v >= 0 else "−") + s) if sign else s

    def _set_status(self, message: str) -> None:
        self._status_bar.configure(text=message)
