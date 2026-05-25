"""
PreviewTable — Tabla para previsualizar movimientos dentro de la aplicación.

Implementa el lado "observador" del patrón Observer: expone el método
`update_movements` para que la ventana principal lo invoque cuando los
datos cambien, sin que este widget conozca de dónde vienen los datos.

Funcionalidades:
  - Búsqueda dinámica en tiempo real (descripción, categoría, importe)
  - Ordenación por columna (clic en cabecera)
  - Edición inline de descripción, categoría e importe (doble clic / botón)
  - Añadir y borrar entradas manualmente
  - Menú contextual con clic derecho
  - Atajos de teclado: F2 = editar, Supr = borrar
  - Tipografía escalada según resolución de pantalla (1080p → 4K UHD)
  - Columna Fuente oculta (comentada)
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Callable, List, Optional

import customtkinter as ctk  # type: ignore
import tkinter as tk
from tkinter import messagebox, ttk

from domain.models.movement import Movement


# -----------------------------------------------------------------------
# Categorías disponibles para el desplegable de edición
# -----------------------------------------------------------------------
ALL_CATEGORIES: List[str] = [
    "Movimiento entre cuentas",
    "Crédito",
    "Nómina",
    "Bonificación",
    "Bizum",
    "Suministros",
    "Supermercado",
    "Restaurante",
    "Ocio",
    "Subscripción",
    "Transporte",
    "Alquiler",
    "Inversiones",
    "Transferencia",
    "PayPal sin detalle",
    "Compras online",
    "Otros",
]

# -----------------------------------------------------------------------
# Columnas  (Fuente comentada — eliminada de la tabla)
# -----------------------------------------------------------------------
_COLUMNS = ("Fecha", "Descripción", "Categoría", "Importe (€)")
# "Fuente" se omite de la UI pero sigue presente en el modelo de datos.

_COL_WIDTHS = {
    "Fecha": 95,
    "Descripción": 460,
    "Categoría": 150,
    # "Fuente": 95,          # columna oculta
    "Importe (€)": 130,
}

# Paleta de colores modo oscuro
_C_ROW_INCOME    = "#193325"
_C_ROW_INCOME_FG = "#7ee89a"
_C_ROW_EXP_A     = "#4a1c1c"    # rojo visible, no vino
_C_ROW_EXP_A_FG  = "#ffaaaa"
_C_ROW_EXP_B     = "#3a1414"    # rojo alternado ligeramente más oscuro
_C_ROW_EXP_B_FG  = "#f09090"
_C_ROW_MANUAL    = "#1a2a3a"
_C_ROW_MANUAL_FG = "#aad4f5"
_C_HEADER_BG     = "#1c3360"
_C_TREE_BG       = "#111827"
_C_SEL_BG        = "#2e5fa3"


def _scale(base: int, screen_w: int) -> int:
    """Escala un valor de píxeles/fuente al ancho de pantalla detectado.

    Referencia:
        1920 px  →  factor 1.00
        2560 px  →  factor 1.22
        3440 px  →  factor 1.42
    """
    if screen_w >= 3200:
        factor = 1.42
    elif screen_w >= 2400:
        factor = 1.22
    elif screen_w >= 1800:
        factor = 1.10
    else:
        factor = 1.00
    return max(1, round(base * factor))


def _fmt_amount(v: float) -> str:
    """Formatea un importe en euros con separadores locales y margen derecho."""
    # El espacio final actúa de padding visual en la columna right-aligned
    return f"{v:,.2f}€".replace(",", "X").replace(".", ",").replace("X", ".") + "  "


class PreviewTable(ctk.CTkFrame):
    """Widget de tabla para previsualizar una lista de movimientos.

    Usa `ttk.Treeview` internamente con estilos personalizados.
    No depende de ningún caso de uso ni de infraestructura.

    Args:
        master:     Widget padre.
        on_changed: Callback opcional invocado cuando los datos cambian.
                    Firma: on_changed(action: str, movement: Movement)
                    Acciones: "edit" | "add" | "delete"
    """

    def __init__(
        self,
        master,
        on_changed: Optional[Callable[[str, Movement], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self._movements: List[Movement] = []
        self._sort_col: Optional[str] = None
        self._sort_asc: bool = True
        self._search_var: Optional[tk.StringVar] = None
        self._on_changed = on_changed

        # Resolución → escala tipográfica
        self._screen_w: int = self.winfo_screenwidth()
        self._fs_base: int  = _scale(11, self._screen_w)
        self._fs_ui: int    = _scale(12, self._screen_w)

        self._build_ui()
        self._apply_treeview_style()

    # ------------------------------------------------------------------
    # API pública  (interfaz observador)
    # ------------------------------------------------------------------

    def update_movements(self, movements: List[Movement]) -> None:
        """Actualiza la tabla con una nueva lista de movimientos."""
        self._movements = movements
        self._refresh_table()

    def clear(self) -> None:
        """Vacía la tabla completamente."""
        self._tree.delete(*self._tree.get_children())
        self._movements = []
        self._lbl_count.configure(text="0 movimientos")
        self._lbl_hint.configure(text="")

    # ------------------------------------------------------------------
    # Construcción de la UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        sw = self._screen_w
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # ── Cabecera con contador ────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 0))

        ctk.CTkLabel(
            header,
            text="Vista previa de movimientos",
            font=ctk.CTkFont(size=_scale(13, sw), weight="bold"),
        ).pack(side="left")

        self._lbl_count = ctk.CTkLabel(
            header,
            text="0 movimientos",
            text_color="gray60",
            font=ctk.CTkFont(size=_scale(11, sw)),
        )
        self._lbl_count.pack(side="right")

        # ── Barra de herramientas ────────────────────────────────────
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.grid(row=1, column=0, sticky="ew", padx=12, pady=(6, 2))
        toolbar.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            toolbar, text="🔍", width=_scale(26, sw),
            font=ctk.CTkFont(size=_scale(13, sw)),
        ).grid(row=0, column=0, padx=(0, 4))

        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._refresh_table())

        ctk.CTkEntry(
            toolbar,
            textvariable=self._search_var,
            placeholder_text="Filtrar por descripción, categoría o importe  (ej: -35,50)…",
            font=ctk.CTkFont(size=_scale(12, sw)),
            height=_scale(32, sw),
        ).grid(row=0, column=1, sticky="ew", padx=(0, 6))

        ctk.CTkButton(
            toolbar, text="✕",
            width=_scale(30, sw), height=_scale(30, sw),
            command=lambda: self._search_var.set(""),
            fg_color="gray40", hover_color="gray30",
            font=ctk.CTkFont(size=_scale(11, sw)),
        ).grid(row=0, column=2, padx=(0, 10))

        # Separador visual
        ctk.CTkFrame(
            toolbar, width=1, height=_scale(28, sw), fg_color="gray35",
        ).grid(row=0, column=3, padx=(0, 10))

        btn_h   = _scale(30, sw)
        btn_fnt = ctk.CTkFont(size=_scale(12, sw), weight="bold")

        self._btn_add = ctk.CTkButton(
            toolbar, text="➕  Añadir",
            width=_scale(95, sw), height=btn_h,
            fg_color="#265f38", hover_color="#1a4527",
            font=btn_fnt, command=self._open_add_dialog,
        )
        self._btn_add.grid(row=0, column=4, padx=(0, 6))

        self._btn_edit = ctk.CTkButton(
            toolbar, text="✏  Editar",
            width=_scale(85, sw), height=btn_h,
            fg_color="#1a5280", hover_color="#143e60",
            font=btn_fnt, command=self._edit_selected,
            state="disabled",
        )
        self._btn_edit.grid(row=0, column=5, padx=(0, 6))

        self._btn_del = ctk.CTkButton(
            toolbar, text="🗑  Borrar",
            width=_scale(85, sw), height=btn_h,
            fg_color="#6e1a1a", hover_color="#521212",
            font=btn_fnt, command=self._delete_selected,
            state="disabled",
        )
        self._btn_del.grid(row=0, column=6)

        # ── Treeview ─────────────────────────────────────────────────
        tree_frame = tk.Frame(self, bg=_C_TREE_BG)
        tree_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=(4, 0))
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        self._tree = ttk.Treeview(
            tree_frame,
            columns=_COLUMNS,
            show="headings",
            selectmode="browse",
            style="Finance.Treeview",
        )

        vsb = ttk.Scrollbar(tree_frame, orient="vertical",   command=self._tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        # Configurar columnas
        for col in _COLUMNS:
            w = _scale(_COL_WIDTHS.get(col, 100), sw)
            self._tree.heading(
                col, text=col, anchor="w",
                command=lambda c=col: self._on_sort(c),
            )
            self._tree.column(col, width=w, anchor="w", minwidth=60)

        # Importe alineado a la derecha
        self._tree.column("Importe (€)", anchor="e")

        # Tags de color por tipo de movimiento
        self._tree.tag_configure("income",    background=_C_ROW_INCOME,  foreground=_C_ROW_INCOME_FG)
        self._tree.tag_configure("expense_a", background=_C_ROW_EXP_A,   foreground=_C_ROW_EXP_A_FG)
        self._tree.tag_configure("expense_b", background=_C_ROW_EXP_B,   foreground=_C_ROW_EXP_B_FG)
        self._tree.tag_configure("manual",    background=_C_ROW_MANUAL,  foreground=_C_ROW_MANUAL_FG)

        # Bindings
        self._tree.bind("<ButtonRelease-1>", self._on_selection_change)
        self._tree.bind("<Double-1>",        self._on_double_click)
        self._tree.bind("<Delete>",          lambda _e: self._delete_selected())
        self._tree.bind("<F2>",              lambda _e: self._edit_selected())
        self._tree.bind("<Button-3>",        self._show_context_menu)

        # Menú contextual (clic derecho)
        self._context_menu = tk.Menu(self._tree, tearoff=0)
        self._context_menu.add_command(label="✏  Editar",              command=self._edit_selected)
        self._context_menu.add_command(label="🗑  Borrar",              command=self._delete_selected)
        self._context_menu.add_separator()
        self._context_menu.add_command(label="📋  Copiar descripción",  command=self._copy_description)

        # ── Hint: descripción completa al seleccionar ──────────────────
        self._lbl_hint = ctk.CTkLabel(
            self, text="",
            font=ctk.CTkFont(size=_scale(10, sw)),
            text_color="gray55",
            anchor="w",
            justify="left",
        )
        self._lbl_hint.grid(row=3, column=0, sticky="ew", padx=14, pady=(2, 5))
        # Actualizar wraplength cuando cambia el tamaño del contenedor
        self._lbl_hint.bind(
            "<Configure>",
            lambda e: self._lbl_hint.configure(wraplength=max(200, e.width - 20)),
        )

        # ── Tooltip flotante al pasar el ratón sobre una fila ────────
        self._tooltip_win: Optional[tk.Toplevel] = None
        self._tree.bind("<Motion>", self._on_tree_hover)
        self._tree.bind("<Leave>",  self._hide_tooltip)

    def _apply_treeview_style(self) -> None:
        """Aplica estilos personalizados al Treeview via ttk.Style."""
        sw = self._screen_w
        rh = _scale(28, sw)   # fila ligeramente más alta para más aire
        fs = self._fs_base

        style = ttk.Style()
        # clam es el único tema integrado que permite personalizar headings en Windows
        try:
            style.theme_use("clam")
        except Exception:  # noqa: BLE001
            pass

        style.configure(
            "Finance.Treeview",
            background=_C_TREE_BG,
            foreground="#d8d8d8",
            rowheight=rh,
            fieldbackground=_C_TREE_BG,
            borderwidth=0,
            relief="flat",
            font=("Segoe UI", fs),
        )
        style.configure(
            "Finance.Treeview.Heading",
            background=_C_HEADER_BG,
            foreground="#e8eaf0",
            font=("Segoe UI", fs + 1, "bold"),
            relief="flat",
            borderwidth=0,
            padding=(10, 6),
        )
        style.map(
            "Finance.Treeview",
            background=[("selected", _C_SEL_BG)],
            foreground=[("selected", "#ffffff")],
        )
        style.map(
            "Finance.Treeview.Heading",
            background=[("active", "#274d87"), ("", _C_HEADER_BG)],
            foreground=[("active", "#ffffff")],
            relief=[("active", "flat")],
        )
        # Scrollbars con estilo discreto
        style.configure(
            "Vertical.TScrollbar",
            background="#1e2938", troughcolor=_C_TREE_BG,
            arrowcolor="#6a7a8a", borderwidth=0,
        )
        style.configure(
            "Horizontal.TScrollbar",
            background="#1e2938", troughcolor=_C_TREE_BG,
            arrowcolor="#6a7a8a", borderwidth=0,
        )

    # ------------------------------------------------------------------
    # Eventos del Treeview
    # ------------------------------------------------------------------

    def _on_selection_change(self, _event=None) -> None:
        sel = self._tree.selection()
        enabled = "normal" if sel else "disabled"
        self._btn_edit.configure(state=enabled)
        self._btn_del.configure(state=enabled)
        if sel:
            vals = self._tree.item(sel[0], "values")
            if vals:
                full_desc = vals[1]  # descripción completa (Treeview guarda el string entero)
                self._lbl_hint.configure(text=f"  📌  {full_desc}")
        else:
            self._lbl_hint.configure(text="")

    def _on_double_click(self, _event=None) -> None:
        if self._tree.selection():
            self._edit_selected()

    def _show_context_menu(self, event) -> None:
        item = self._tree.identify_row(event.y)
        if item:
            self._tree.selection_set(item)
            self._on_selection_change()
            self._context_menu.post(event.x_root, event.y_root)

    # ------------------------------------------------------------------
    # Tooltip flotante (hover sobre la fila)
    # ------------------------------------------------------------------

    def _on_tree_hover(self, event) -> None:
        item = self._tree.identify_row(event.y)
        if not item:
            self._hide_tooltip()
            return
        vals = self._tree.item(item, "values")
        if not vals:
            self._hide_tooltip()
            return
        full_desc = vals[1]
        # Solo mostrar tooltip si hay texto que no cabe en la columna visible
        self._show_tooltip(event.x_root + 16, event.y_root + 10, full_desc)

    def _show_tooltip(self, x: int, y: int, text: str) -> None:
        self._hide_tooltip()
        tw = tk.Toplevel(self)
        tw.overrideredirect(True)
        tw.attributes("-topmost", True)
        tw.configure(bg="#1e2a3a")
        lbl = tk.Label(
            tw, text=text,
            bg="#1e2a3a", fg="#dce8f5",
            font=("Segoe UI", self._fs_base),
            wraplength=500, justify="left",
            padx=10, pady=6,
            relief="flat", bd=0,
        )
        lbl.pack()
        # Borde fino con un Frame exterior
        tw.geometry(f"+{x}+{y}")
        self._tooltip_win = tw

    def _hide_tooltip(self, _event=None) -> None:
        if self._tooltip_win:
            try:
                self._tooltip_win.destroy()
            except Exception:  # noqa: BLE001
                pass
            self._tooltip_win = None

    # ------------------------------------------------------------------
    # Obtener movimiento seleccionado (por tag idx_NNN)
    # ------------------------------------------------------------------

    def _get_selected_movement(self) -> Optional[Movement]:
        sel = self._tree.selection()
        if not sel:
            return None
        for tag in self._tree.item(sel[0], "tags"):
            if tag.startswith("idx_"):
                try:
                    return self._movements[int(tag[4:])]
                except (IndexError, ValueError):
                    pass
        return None

    # ------------------------------------------------------------------
    # Ordenación
    # ------------------------------------------------------------------

    def _on_sort(self, col: str) -> None:
        if self._sort_col == col:
            self._sort_asc = not self._sort_asc
        else:
            self._sort_col = col
            self._sort_asc = True
        self._refresh_table()

    # ------------------------------------------------------------------
    # Refresco de tabla
    # ------------------------------------------------------------------

    def _refresh_table(self) -> None:
        self._tree.delete(*self._tree.get_children())
        self._btn_edit.configure(state="disabled")
        self._btn_del.configure(state="disabled")
        self._lbl_hint.configure(text="")

        raw = (self._search_var.get() if self._search_var else "").strip()
        search_lower = raw.lower()

        # ── Filtrado ─────────────────────────────────────────────────
        if search_lower:
            displayed: List[tuple] = []
            for i, m in enumerate(self._movements):
                amt_dot    = f"{m.amount:.2f}"
                amt_comma  = f"{m.amount:.2f}".replace(".", ",")
                amt_pretty = _fmt_amount(m.amount)
                if (
                    search_lower in (m.description or "").lower()
                    or search_lower in (m.category or "").lower()
                    or search_lower in (m.source or "").lower()
                    or search_lower in amt_dot
                    or search_lower in amt_comma
                    or search_lower in amt_pretty
                ):
                    displayed.append((i, m))
        else:
            displayed = list(enumerate(self._movements))

        # ── Ordenación ───────────────────────────────────────────────
        _sort_keys = {
            "Fecha":       lambda x: x[1].date,
            "Descripción": lambda x: (x[1].description or "").lower(),
            "Categoría":   lambda x: (x[1].category or "").lower(),
            "Importe (€)": lambda x: x[1].amount,
        }
        if self._sort_col and self._sort_col in _sort_keys:
            displayed.sort(
                key=_sort_keys[self._sort_col],
                reverse=not self._sort_asc,
            )

        # Flechas en cabeceras
        for col in _COLUMNS:
            arrow = (" ↑" if self._sort_asc else " ↓") if col == self._sort_col else ""
            self._tree.heading(col, text=col + arrow)

        # ── Renderizado ───────────────────────────────────────────────
        income_count  = 0
        expense_count = 0

        for orig_idx, movement in displayed:
            date_str = (
                movement.date.strftime("%d/%m/%Y")
                if isinstance(movement.date, date)
                else str(movement.date)
            )
            row_values = (
                date_str,
                movement.description or "—",
                movement.category or "—",
                _fmt_amount(movement.amount),
            )

            if getattr(movement, "source", "") == "manual":
                tag = "manual"
            elif movement.is_income():
                income_count += 1
                tag = "income"
            else:
                expense_count += 1
                tag = "expense_a" if expense_count % 2 == 0 else "expense_b"

            self._tree.insert(
                "", "end",
                values=row_values,
                tags=(tag, f"idx_{orig_idx}"),
            )

        # ── Contador con desglose ─────────────────────────────────────
        total = len(self._movements)
        shown = len(displayed)
        parts = []
        if income_count:
            parts.append(f"{income_count} ingreso{'s' if income_count > 1 else ''}")
        if expense_count:
            parts.append(f"{expense_count} gasto{'s' if expense_count > 1 else ''}")
        detail = f"  ({', '.join(parts)})" if parts and shown == total else ""

        if shown < total:
            self._lbl_count.configure(
                text=f"{shown} de {total} movimientos{detail}"
            )
        else:
            self._lbl_count.configure(
                text=f"{total} movimiento{'s' if total != 1 else ''}{detail}"
            )

    # ------------------------------------------------------------------
    # Acciones: editar, borrar, copiar
    # ------------------------------------------------------------------

    def _edit_selected(self) -> None:
        m = self._get_selected_movement()
        if m:
            self._open_edit_dialog(m)

    def _delete_selected(self) -> None:
        m = self._get_selected_movement()
        if not m:
            return
        if messagebox.askyesno(
            "Borrar movimiento",
            f"¿Eliminar este movimiento?\n\n"
            f"{m.date.strftime('%d/%m/%Y')}  |  {m.description}  |  {_fmt_amount(m.amount)}",
            parent=self,
        ):
            if m in self._movements:
                self._movements.remove(m)
            self._refresh_table()
            if self._on_changed:
                self._on_changed("delete", m)

    def _copy_description(self) -> None:
        m = self._get_selected_movement()
        if not m:
            return
        self.clipboard_clear()
        self.clipboard_append(m.description or "")

    # ------------------------------------------------------------------
    # Diálogos
    # ------------------------------------------------------------------

    def _open_edit_dialog(self, movement: Movement) -> None:
        sw  = self._screen_w
        fs  = self._fs_ui
        pad = {"padx": 16, "pady": 5}

        dlg = ctk.CTkToplevel(self)
        dlg.title("Editar movimiento")
        dlg.geometry(f"{_scale(500, sw)}x{_scale(310, sw)}")
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.transient(self.winfo_toplevel())
        dlg.lift()
        dlg.focus_force()
        dlg.grid_columnconfigure(1, weight=1)

        # Fecha (solo lectura para no romper filtros de mes)
        ctk.CTkLabel(dlg, text="Fecha:", font=ctk.CTkFont(size=fs)).grid(
            row=0, column=0, sticky="w", **pad)
        ctk.CTkLabel(
            dlg,
            text=movement.date.strftime("%d/%m/%Y"),
            font=ctk.CTkFont(size=fs), text_color="gray60",
        ).grid(row=0, column=1, sticky="w", **pad)

        # Descripción
        ctk.CTkLabel(dlg, text="Descripción:", font=ctk.CTkFont(size=fs)).grid(
            row=1, column=0, sticky="w", **pad)
        desc_var = tk.StringVar(value=movement.description)
        ctk.CTkEntry(
            dlg, textvariable=desc_var,
            font=ctk.CTkFont(size=fs),
            width=_scale(310, sw), height=_scale(32, sw),
        ).grid(row=1, column=1, sticky="ew", **pad)

        # Categoría
        ctk.CTkLabel(dlg, text="Categoría:", font=ctk.CTkFont(size=fs)).grid(
            row=2, column=0, sticky="w", **pad)
        cat_var = tk.StringVar(value=movement.category or "Otros")
        ctk.CTkComboBox(
            dlg, variable=cat_var, values=ALL_CATEGORIES,
            font=ctk.CTkFont(size=fs),
            width=_scale(310, sw), height=_scale(32, sw),
        ).grid(row=2, column=1, sticky="ew", **pad)

        # Importe
        ctk.CTkLabel(dlg, text="Importe (€):", font=ctk.CTkFont(size=fs)).grid(
            row=3, column=0, sticky="w", **pad)
        amount_var = tk.StringVar(value=str(movement.amount))
        ctk.CTkEntry(
            dlg, textvariable=amount_var,
            font=ctk.CTkFont(size=fs),
            width=_scale(310, sw), height=_scale(32, sw),
        ).grid(row=3, column=1, sticky="ew", **pad)

        ctk.CTkLabel(
            dlg,
            text="  Los gastos son negativos (ej: -45.20),  los ingresos positivos.",
            font=ctk.CTkFont(size=_scale(10, sw)), text_color="gray55",
        ).grid(row=4, column=0, columnspan=2, sticky="w", padx=16, pady=(0, 2))

        def _confirm() -> None:
            try:
                new_amount = float(
                    amount_var.get().replace(",", ".").replace("€", "").strip()
                )
            except ValueError:
                messagebox.showerror("Error", "El importe debe ser un número.", parent=dlg)
                return
            new_desc = desc_var.get().strip()
            if not new_desc:
                messagebox.showerror("Error", "La descripción no puede estar vacía.", parent=dlg)
                return
            movement.description = new_desc
            movement.category    = cat_var.get()
            movement.amount      = new_amount
            dlg.destroy()
            self._refresh_table()
            if self._on_changed:
                self._on_changed("edit", movement)

        btn_frame = ctk.CTkFrame(dlg, fg_color="transparent")
        btn_frame.grid(row=5, column=0, columnspan=2, pady=14)
        ctk.CTkButton(
            btn_frame, text="✔  Guardar",
            fg_color="#265f38", hover_color="#1a4527",
            font=ctk.CTkFont(size=fs), command=_confirm,
        ).pack(side="left", padx=8)
        ctk.CTkButton(
            btn_frame, text="Cancelar",
            fg_color="gray40", hover_color="gray30",
            font=ctk.CTkFont(size=fs), command=dlg.destroy,
        ).pack(side="left", padx=8)
        dlg.bind("<Return>", lambda _e: _confirm())

    def _open_add_dialog(self) -> None:
        sw  = self._screen_w
        fs  = self._fs_ui
        pad = {"padx": 16, "pady": 5}

        dlg = ctk.CTkToplevel(self)
        dlg.title("Añadir movimiento manual")
        dlg.geometry(f"{_scale(500, sw)}x{_scale(360, sw)}")
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.transient(self.winfo_toplevel())
        dlg.lift()
        dlg.focus_force()
        dlg.grid_columnconfigure(1, weight=1)

        # Fecha
        ctk.CTkLabel(dlg, text="Fecha (dd/mm/aaaa):", font=ctk.CTkFont(size=fs)).grid(
            row=0, column=0, sticky="w", **pad)
        date_var = tk.StringVar(value=datetime.today().strftime("%d/%m/%Y"))
        ctk.CTkEntry(
            dlg, textvariable=date_var,
            font=ctk.CTkFont(size=fs),
            width=_scale(310, sw), height=_scale(32, sw),
        ).grid(row=0, column=1, sticky="ew", **pad)

        # Descripción
        ctk.CTkLabel(dlg, text="Descripción:", font=ctk.CTkFont(size=fs)).grid(
            row=1, column=0, sticky="w", **pad)
        desc_var = tk.StringVar()
        ctk.CTkEntry(
            dlg, textvariable=desc_var,
            font=ctk.CTkFont(size=fs),
            width=_scale(310, sw), height=_scale(32, sw),
        ).grid(row=1, column=1, sticky="ew", **pad)

        # Categoría
        ctk.CTkLabel(dlg, text="Categoría:", font=ctk.CTkFont(size=fs)).grid(
            row=2, column=0, sticky="w", **pad)
        cat_var = tk.StringVar(value="Otros")
        ctk.CTkComboBox(
            dlg, variable=cat_var, values=ALL_CATEGORIES,
            font=ctk.CTkFont(size=fs),
            width=_scale(310, sw), height=_scale(32, sw),
        ).grid(row=2, column=1, sticky="ew", **pad)

        # Importe
        ctk.CTkLabel(dlg, text="Importe (€):", font=ctk.CTkFont(size=fs)).grid(
            row=3, column=0, sticky="w", **pad)
        amount_var = tk.StringVar(value="0.00")
        ctk.CTkEntry(
            dlg, textvariable=amount_var,
            font=ctk.CTkFont(size=fs),
            width=_scale(310, sw), height=_scale(32, sw),
        ).grid(row=3, column=1, sticky="ew", **pad)

        ctk.CTkLabel(
            dlg,
            text="  Gastos → negativos (ej: -45.20)   Ingresos → positivos (ej: 1500)",
            font=ctk.CTkFont(size=_scale(10, sw)), text_color="gray55",
        ).grid(row=4, column=0, columnspan=2, sticky="w", padx=16, pady=(0, 2))

        def _confirm() -> None:
            try:
                new_date = datetime.strptime(date_var.get().strip(), "%d/%m/%Y").date()
            except ValueError:
                messagebox.showerror("Error", "Formato de fecha inválido. Usa dd/mm/aaaa.", parent=dlg)
                return
            new_desc = desc_var.get().strip()
            if not new_desc:
                messagebox.showerror("Error", "La descripción no puede estar vacía.", parent=dlg)
                return
            try:
                new_amount = float(
                    amount_var.get().replace(",", ".").replace("€", "").strip()
                )
            except ValueError:
                messagebox.showerror("Error", "El importe debe ser un número.", parent=dlg)
                return

            new_m = Movement(
                date=new_date,
                description=new_desc,
                amount=new_amount,
                source="manual",
                category=cat_var.get(),
            )
            self._movements.append(new_m)
            self._movements.sort(key=lambda mv: mv.date, reverse=True)
            dlg.destroy()
            self._refresh_table()
            if self._on_changed:
                self._on_changed("add", new_m)

        btn_frame = ctk.CTkFrame(dlg, fg_color="transparent")
        btn_frame.grid(row=5, column=0, columnspan=2, pady=14)
        ctk.CTkButton(
            btn_frame, text="➕  Añadir",
            fg_color="#265f38", hover_color="#1a4527",
            font=ctk.CTkFont(size=fs), command=_confirm,
        ).pack(side="left", padx=8)
        ctk.CTkButton(
            btn_frame, text="Cancelar",
            fg_color="gray40", hover_color="gray30",
            font=ctk.CTkFont(size=fs), command=dlg.destroy,
        ).pack(side="left", padx=8)
        dlg.bind("<Return>", lambda _e: _confirm())

