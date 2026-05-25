"""
Parser para extractos bancarios de Santander en formato PDF.

Usa pdfplumber con tres estrategias en cascada, de más a menos estructurada:

  Estrategia 1 — extract_table() con varios conjuntos de settings.
    Funciona cuando el PDF tiene líneas reales que delimitan la tabla.

  Estrategia 2 — extract_words() agrupando por coordenada Y.
    Funciona cuando el PDF es visual (sin líneas de tabla) pero con texto
    posicionado en columnas. Las palabras de la misma fila comparten
    la misma coordenada 'top' (tolerancia ±4 px).

  Estrategia 3 — extract_text() línea a línea con regex.
    Último recurso: detecta líneas que empiezan por fecha y terminan
    por al menos un importe.

Formato esperado por fila (columnas separadas o texto juntado):
  fecha  |  descripción  |  importe  |  saldo (ignorado)
"""

from __future__ import annotations

import logging
import re
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pdfplumber  # type: ignore

from domain.interfaces.parser import StatementParser
from domain.models.movement import Movement
from domain.models.statement import Statement

# Silenciar los warnings de pdfminer sobre FontBBox y similares
logging.getLogger("pdfminer").setLevel(logging.ERROR)

# ---------------------------------------------------------------------------
# Constantes de parsing
# ---------------------------------------------------------------------------

_MONTH_ES: Dict[str, int] = {
    "ene": 1, "feb": 2, "mar": 3, "abr": 4,
    "may": 5, "jun": 6, "jul": 7, "ago": 8,
    "sep": 9, "oct": 10, "nov": 11, "dic": 12,
}

# Fecha con mes en letras:  "28 feb 2026"
_DATE_WORDS = re.compile(
    r"\b(\d{1,2})\s+([a-záéíóúüñ]{3,})\s+(\d{4})\b", re.IGNORECASE
)
# Fecha numérica:  "28/02/2026"  o  "28-02-2026"
_DATE_SLASH = re.compile(r"\b(\d{2})[/\-](\d{2})[/\-](\d{4})\b")

# Importe: signo opcional + dígitos + posibles puntos de miles + coma + 2 dec
_AMOUNT_RE = re.compile(r"([+\-]?\d{1,3}(?:\.\d{3})*,\d{2})")

# Saldo disponible en la cabecera:  "Saldo disponible: 147,88€(a fecha ...)"
_SALDO_DISPONIBLE_RE = re.compile(r"Saldo disponible:\s*([+\-]?\d[\d.]*,\d{2})", re.IGNORECASE)

# Configuraciones alternativas para extract_table()
_TABLE_SETTINGS_LIST = [
    {},  # sin ajustes → deja que pdfplumber infiera todo
    {"vertical_strategy": "lines", "horizontal_strategy": "lines"},
    {"vertical_strategy": "text",  "horizontal_strategy": "text"},
    {"vertical_strategy": "lines_strict", "horizontal_strategy": "lines_strict"},
    {"vertical_strategy": "explicit", "horizontal_strategy": "text",
     "explicit_vertical_lines": []},
]

# Tolerancia en píxeles para agrupar palabras en la misma fila (estrategia 2)
_Y_TOLERANCE = 4


class SantanderPDFParser(StatementParser):
    """Estrategia de parsing para extractos PDF de Santander.

    Aplica hasta tres estrategias en cascada por página hasta obtener
    movimientos, evitando así fallos silenciosos cuando el PDF no tiene
    estructura de tabla.
    """

    _SOURCE = "santander"

    # ------------------------------------------------------------------
    # StatementParser interface
    # ------------------------------------------------------------------

    def can_parse(self, file_path: Path) -> bool:
        """Acepta cualquier archivo PDF."""
        return file_path.suffix.lower() == ".pdf"

    def parse(self, file_path: Path) -> Statement:
        movements: List[Movement] = []
        saldo_disponible: Optional[float] = None

        with pdfplumber.open(file_path) as pdf:
            # Extraer saldo disponible de la primera página
            if pdf.pages:
                first_text = pdf.pages[0].extract_text() or ""
                sd_m = _SALDO_DISPONIBLE_RE.search(first_text)
                if sd_m:
                    saldo_disponible = self._parse_amount_str(sd_m.group(1))

            for page in pdf.pages:
                page_movements = (
                    self._strategy_table(page)
                    or self._strategy_words(page)
                    or self._strategy_text(page)
                )
                movements.extend(page_movements)

        return Statement(source=self._SOURCE, movements=movements, saldo_disponible=saldo_disponible)

    # ------------------------------------------------------------------
    # Estrategia 1: extract_table con settings alternativos
    # ------------------------------------------------------------------

    def _strategy_table(self, page) -> List[Movement]:
        for settings in _TABLE_SETTINGS_LIST:
            try:
                table = page.extract_table(settings) if settings else page.extract_table()
            except Exception:
                continue
            if not table:
                continue
            results = []
            for row in table:
                m = self._parse_table_row(row)
                if m:
                    results.append(m)
            if results:
                return results
        return []

    def _parse_table_row(self, row: list) -> Optional[Movement]:
        if not row:
            return None

        # Caso A: columnas separadas correctamente [fecha, desc, importe, saldo]
        if len(row) >= 3 and row[1] is not None and str(row[1]).strip():
            raw_date = str(row[0] or "")
            parsed_date = self._parse_date(raw_date)
            if parsed_date is None:
                return None
            description = str(row[1] or "").strip().replace("\n", " ")
            raw_amount = str(row[2] or "").strip()
            amount = self._extract_last_amount(raw_amount)
            if amount is None:
                return None
            return Movement(date=parsed_date, description=description,
                            amount=amount, source=self._SOURCE)

        # Caso B: pdfplumber fusiona todo en row[0] (columnas restantes = None)
        # Delegar a _parse_text_line que ya maneja este formato
        merged = str(row[0] or "").replace("\n", " ").strip()
        return self._parse_text_line(merged)

    # ------------------------------------------------------------------
    # Estrategia 2: extract_words agrupando por coordenada Y
    # ------------------------------------------------------------------

    def _strategy_words(self, page) -> List[Movement]:
        words = page.extract_words(x_tolerance=3, y_tolerance=_Y_TOLERANCE)
        if not words:
            return []

        # Agrupar palabras por banda vertical (round al múltiplo de _Y_TOLERANCE)
        rows: Dict[int, List[dict]] = {}
        for w in words:
            key = round(w["top"] / _Y_TOLERANCE) * _Y_TOLERANCE
            rows.setdefault(key, []).append(w)

        results = []
        for key in sorted(rows):
            line = " ".join(w["text"] for w in sorted(rows[key], key=lambda w: w["x0"]))
            m = self._parse_text_line(line)
            if m:
                results.append(m)
        return results

    # ------------------------------------------------------------------
    # Estrategia 3: extract_text línea a línea
    # ------------------------------------------------------------------

    def _strategy_text(self, page) -> List[Movement]:
        text = page.extract_text() or ""
        results = []
        for line in text.splitlines():
            m = self._parse_text_line(line.strip())
            if m:
                results.append(m)
        return results

    # ------------------------------------------------------------------
    # Parser de línea de texto (usado por estrategias 2 y 3)
    # ------------------------------------------------------------------

    def _parse_text_line(self, line: str) -> Optional[Movement]:
        """Interpreta una línea de texto buscando fecha + descripción + importe.

        Asume que:
          - La fecha aparece al principio de la línea.
          - Los importes están al final (el último puede ser el saldo).
          - Si hay ≥2 importes, el penúltimo es la operación; si hay solo
            uno, ese es el importe de la operación.
        """
        if not line:
            return None

        # Detectar fecha al inicio de la línea
        date_match = _DATE_SLASH.match(line) or _DATE_WORDS.match(line)
        if date_match is None:
            return None

        parsed_date = self._match_to_date(date_match)
        if parsed_date is None:
            return None

        # Todos los importes de la línea
        amounts_found = _AMOUNT_RE.findall(line)
        if not amounts_found:
            return None

        # El importe de la operación es SIEMPRE el PRIMERO que aparece en
        # la línea; los siguientes son saldo, comisiones u otros datos.
        # (La lógica anterior "penúltimo" fallaba cuando había ≥3 importes:
        #  importe | saldo | comisión → penúltimo = saldo, incorrecto.)
        raw_amount = amounts_found[0]
        amount = self._parse_amount_str(raw_amount)
        if amount is None:
            return None

        # Descripción: texto entre el fin de la fecha y el primer importe
        desc_start = date_match.end()
        first_amount_pos = line.find(amounts_found[0])
        description = line[desc_start:first_amount_pos].strip(" \t|,")
        description = re.sub(r"\s+", " ", description)
        if not description:
            return None

        return Movement(date=parsed_date, description=description,
                        amount=amount, source=self._SOURCE)

    # ------------------------------------------------------------------
    # Helpers de fecha
    # ------------------------------------------------------------------

    def _parse_date(self, raw: str) -> Optional[date]:
        """Detecta cualquier formato de fecha en raw (multilinea tolerado)."""
        first_line = raw.split("\n")[0].strip()
        for pattern in (_DATE_SLASH, _DATE_WORDS):
            m = pattern.search(first_line)
            if m:
                return self._match_to_date(m)
        return None

    @staticmethod
    def _match_to_date(m: re.Match) -> Optional[date]:
        try:
            if "/" in m.group(0) or "-" in m.group(0):
                # DD/MM/YYYY
                day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
            else:
                # DD mes YYYY
                day = int(m.group(1))
                month_name = m.group(2).lower()[:3]
                month = _MONTH_ES.get(month_name)
                year = int(m.group(3))
                if month is None:
                    return None
            return date(year, month, day)
        except (ValueError, IndexError):
            return None

    # ------------------------------------------------------------------
    # Helpers de importe
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_amount_str(raw: str) -> Optional[float]:
        """Convierte '−1.234,56' o '1.234,56' a float."""
        raw = raw.strip().replace("\u2212", "-")  # guión largo → menos
        normalized = raw.replace(".", "").replace(",", ".")
        try:
            return float(normalized)
        except ValueError:
            return None

    def _extract_last_amount(self, raw: str) -> Optional[float]:
        """Devuelve el primer importe encontrado en raw."""
        matches = _AMOUNT_RE.findall(raw)
        if not matches:
            return None
        return self._parse_amount_str(matches[0])
