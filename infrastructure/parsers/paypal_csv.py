"""
Parser para CSV exportados desde el panel de PayPal.

Columnas relevantes del CSV de PayPal:
  - Fecha       → formato "DD/MM/YYYY"
  - Nombre      → nombre del comercio o remitente
  - Tipo        → tipo de transacción (se conserva como info extra)
  - Bruto       → importe con coma decimal y posibles puntos de miles
  - Estado      → solo se importan filas con Estado == "Completado"

El archivo puede estar en UTF-8 con BOM o en latin-1 dependiendo
del idioma del panel de PayPal.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import List, Optional

import pandas as pd  # type: ignore

from domain.interfaces.parser import StatementParser
from domain.models.movement import Movement
from domain.models.statement import Statement

_SOURCE = "paypal"

# Importe con puntos de miles y coma decimal, signo opcional al inicio o al final
_AMOUNT_RE = re.compile(r"([+-]?\d[\d.]*,\d{2})")


class PayPalCSVParser(StatementParser):
    """Estrategia de parsing para CSVs exportados desde PayPal.

    Patrón Strategy: implementa StatementParser para este proveedor.
    Solo importa movimientos con Estado == "Completado".
    """

    # ------------------------------------------------------------------
    # StatementParser interface
    # ------------------------------------------------------------------

    def can_parse(self, file_path: Path) -> bool:
        """Acepta cualquier archivo CSV."""
        return file_path.suffix.lower() == ".csv"

    def parse(self, file_path: Path) -> Statement:
        """Lee el CSV de PayPal y devuelve un Statement con los movimientos.

        Lee el archivo probando UTF-8-BOM primero y latin-1 como fallback.
        Solo incluye filas con Estado == "Completado".
        """
        df = self._read_csv(file_path)

        # Normalizar nombres de columna (quitar espacios, BOM residual)
        df.columns = [c.strip().lstrip("\ufeff") for c in df.columns]

        # Filtrar solo transacciones completadas
        status_col = self._find_column(df, ["Estado", "Status"])
        if status_col:
            df = df[df[status_col].str.strip() == "Completado"].copy()

        movements: List[Movement] = []

        date_col = self._find_column(df, ["Fecha", "Date"])
        name_col = self._find_column(df, ["Nombre", "Name"])
        amount_col = self._find_column(df, ["Bruto", "Gross"])
        article_col = self._find_column(df, ["Nombre de artículo", "Item Title", "Nombre de articulo"])

        if not all([date_col, name_col, amount_col]):
            raise ValueError(
                f"El CSV de PayPal no tiene las columnas esperadas. "
                f"Columnas encontradas: {list(df.columns)}"
            )

        tipo_col = self._find_column(df, ["Tipo", "Type"])

        # 1) Filas con nombre de comercio conocido (el grueso de los pagos)
        df_named = df[df[name_col].notna() & (df[name_col].str.strip() != "")].copy()
        for _, row in df_named.iterrows():
            movement = self._parse_row(row, date_col, name_col, amount_col, article_col)
            if movement is not None:
                movements.append(movement)

        # 2) Filas de conversión de divisas: el importe real en EUR cargado al
        #    banco aparece en una fila sin nombre ("Conversión de divisas").
        #    Las vinculamos al comercio del mismo día para poder hacer match
        #    con el cargo en Santander.
        conversion_movements = self._parse_conversion_rows(
            df, date_col, name_col, amount_col, tipo_col, article_col
        )
        movements.extend(conversion_movements)

        return Statement(source=_SOURCE, movements=movements)

    # ------------------------------------------------------------------
    # Privado
    # ------------------------------------------------------------------

    @staticmethod
    def _read_csv(file_path: Path) -> pd.DataFrame:
        """Lee el CSV intentando UTF-8-BOM primero, latin-1 como fallback."""
        for encoding in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                return pd.read_csv(file_path, encoding=encoding)
            except UnicodeDecodeError:
                continue
        raise ValueError(f"No se pudo leer el CSV con ninguna codificación conocida: {file_path}")

    @staticmethod
    def _find_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
        """Devuelve el primer nombre de columna encontrado de la lista."""
        for candidate in candidates:
            if candidate in df.columns:
                return candidate
        return None

    def _parse_conversion_rows(
        self,
        df: pd.DataFrame,
        date_col: str,
        name_col: str,
        amount_col: str,
        tipo_col: Optional[str],
        article_col: Optional[str],
    ) -> List[Movement]:
        """Genera movimientos para filas de 'Conversión de divisas'.

        Cuando PayPal convierte de otra moneda a EUR, el importe real cobrado
        al banco aparece en una fila sin comercio de tipo 'Conversión de divisas
        general'. Esta función la vincula al comercio de la fila 'Completado'
        del mismo día para que el matching con Santander pueda funcionar.
        """
        movements: List[Movement] = []

        if not tipo_col:
            return movements

        # Filas de conversión sin nombre de comercio y con importe negativo
        mask_conversion = (
            df[tipo_col].str.contains("Conversión", na=False, case=False)
            & (df[name_col].isna() | (df[name_col].str.strip() == ""))
        )
        df_conv = df[mask_conversion].copy()

        # Índice fecha → texto de fecha para buscar el comercio del mismo día
        for _, conv_row in df_conv.iterrows():
            raw_date = str(conv_row.get(date_col, "")).strip()
            try:
                parts = raw_date.split("/")
                conv_date = date(int(parts[2]), int(parts[1]), int(parts[0]))
            except (ValueError, IndexError):
                continue

            raw_amount = re.sub(r"[€$£\s]", "", str(conv_row.get(amount_col, "")).strip())
            m = _AMOUNT_RE.search(raw_amount)
            if not m:
                continue
            try:
                amount = float(m.group(1).replace(".", "").replace(",", "."))
            except ValueError:
                continue

            if amount >= 0:  # Solo gastos (negativo)
                continue

            # Buscar comercio en una fila Completado del mismo día
            same_day = df[
                (df[date_col] == conv_row[date_col])
                & df[name_col].notna()
                & (df[name_col].str.strip() != "")
            ]
            if same_day.empty:
                continue

            merchant_row = same_day.iloc[0]
            name = str(merchant_row.get(name_col, "")).strip()

            article = ""
            if article_col:
                raw_article = str(merchant_row.get(article_col, "")).strip()
                if raw_article and raw_article.lower() not in ("nan", ""):
                    article = raw_article.split(", Condiciones")[0].strip()

            description = f"{name} — {article}" if article else name

            movements.append(
                Movement(
                    date=conv_date,
                    description=description,
                    amount=amount,
                    source=_SOURCE,
                )
            )

        return movements

    @staticmethod
    def _parse_row(
        row: pd.Series,
        date_col: str,
        name_col: str,
        amount_col: str,
        article_col: Optional[str] = None,
    ) -> Optional[Movement]:
        """Intenta construir un Movement a partir de una fila del DataFrame."""
        # Fecha
        raw_date = str(row.get(date_col, "")).strip()
        try:
            parts = raw_date.split("/")
            parsed_date = date(int(parts[2]), int(parts[1]), int(parts[0]))
        except (ValueError, IndexError):
            return None

        # Descripción: Nombre + Nombre de artículo (si existe y no está vacío)
        name = str(row.get(name_col, "")).strip()
        if not name:
            return None

        article = ""
        if article_col:
            raw_article = str(row.get(article_col, "")).strip()
            # Limpiar texto extra tras coma (ej: "S.T.A.L.K.E.R. 2..., Condiciones de pago:")
            if raw_article and raw_article.lower() not in ("nan", ""):
                article = raw_article.split(", Condiciones")[0].strip()

        description = f"{name} — {article}" if article else name

        # Importe
        raw_amount = str(row.get(amount_col, "")).strip()
        # Quitar el símbolo de moneda y posibles espacios
        raw_amount = re.sub(r"[€$£\s]", "", raw_amount)
        match = _AMOUNT_RE.search(raw_amount)
        if not match:
            return None
        normalized = match.group(1).replace(".", "").replace(",", ".")
        try:
            amount = float(normalized)
        except ValueError:
            return None

        return Movement(
            date=parsed_date,
            description=description,
            amount=amount,
            source=_SOURCE,
        )
