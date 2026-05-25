"""
Parsers para extractos de CaixaBank (La Caixa).

  LaCaixaCSVParser  — CSV exportado desde CaixaBankNow (portal digital).
    Formato: separador ";", cabecera de metadatos de 3 filas, columnas
    Concepte/Data/Import/Saldo. Detectado por prefijo de nombre 'CaixaBank_'.

  LaCaixaPDFParser  — STUB pendiente de implementación (Fase 2).
"""

from __future__ import annotations

from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import List, Optional

import pandas as pd  # type: ignore

from domain.interfaces.parser import StatementParser
from domain.models.movement import Movement
from domain.models.statement import Statement

_SOURCE = "lacaixa"
_CSV_PREFIX = "CaixaBank_"


class LaCaixaCSVParser(StatementParser):
    """Parser para CSV exportados desde CaixaBankNow (La Caixa).

    El CSV tiene una cabecera de metadatos (titular, IBAN, período) antes
    de la fila de columnas 'Concepte;Data;Import;Saldo'. Se detecta por el
    prefijo de nombre de archivo 'CaixaBank_'.
    """

    _SOURCE = _SOURCE

    # ------------------------------------------------------------------
    # StatementParser interface
    # ------------------------------------------------------------------

    def can_parse(self, file_path: Path) -> bool:
        """Acepta archivos .csv cuyo nombre empieza por 'CaixaBank_'."""
        return (
            file_path.suffix.lower() == ".csv"
            and file_path.name.startswith(_CSV_PREFIX)
        )

    def parse(self, file_path: Path) -> Statement:
        """Lee el CSV de CaixaBank y devuelve un Statement con los movimientos."""
        df = self._read_csv(file_path)
        movements = self._parse_movements(df)
        saldo = self._extract_saldo(df)
        return Statement(source=self._SOURCE, movements=movements, saldo_disponible=saldo)

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------

    def _read_csv(self, file_path: Path) -> pd.DataFrame:
        """Lee el CSV, localiza la fila de cabecera de datos y devuelve el DataFrame."""
        raw: Optional[str] = None
        for encoding in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                raw = file_path.read_text(encoding=encoding)
                break
            except UnicodeDecodeError:
                continue

        if raw is None:
            raise ValueError(
                f"No se pudo leer '{file_path.name}' con ninguna codificación conocida."
            )

        lines = raw.splitlines()

        # Localizar la fila que contiene las columnas de datos
        header_idx: Optional[int] = None
        for i, line in enumerate(lines):
            if line.startswith("Concepte;"):
                header_idx = i
                break

        if header_idx is None:
            raise ValueError(
                f"No se encontró la cabecera 'Concepte;Data;Import;Saldo' "
                f"en '{file_path.name}'."
            )

        df = pd.read_csv(StringIO("\n".join(lines[header_idx:])), sep=";", dtype=str)

        # Eliminar filas vacías o sin concepto
        df = df[df["Concepte"].notna() & (df["Concepte"].str.strip() != "")]
        return df.reset_index(drop=True)

    def _parse_movements(self, df: pd.DataFrame) -> List[Movement]:
        movements: List[Movement] = []
        for _, row in df.iterrows():
            try:
                movement_date = datetime.strptime(row["Data"].strip(), "%d/%m/%Y").date()
                amount = float(row["Import"].strip())
                description = row["Concepte"].strip()
                movements.append(
                    Movement(
                        date=movement_date,
                        description=description,
                        amount=amount,
                        source=self._SOURCE,
                    )
                )
            except (ValueError, AttributeError, KeyError):
                continue
        return movements

    def _extract_saldo(self, df: pd.DataFrame) -> Optional[float]:
        """Extrae el saldo disponible de la primera fila válida (movimiento más reciente)."""
        if "Saldo" not in df.columns:
            return None
        for val in df["Saldo"]:
            if isinstance(val, str) and val.strip():
                try:
                    # Formato: "483,86EUR"  →  483.86
                    cleaned = val.strip().replace("EUR", "").replace(".", "").replace(",", ".")
                    return float(cleaned)
                except ValueError:
                    continue
        return None


class LaCaixaPDFParser(StatementParser):
    """STUB: Parser para extractos PDF de LaCaixa (pendiente, Fase 2)."""

    _SOURCE = _SOURCE

    def can_parse(self, file_path: Path) -> bool:
        return False

    def parse(self, file_path: Path) -> Statement:
        raise NotImplementedError(
            "El parser PDF de LaCaixa está pendiente de implementación (Fase 2). "
            f"Archivo recibido: {file_path}"
        )
