"""
Caso de uso: ParseStatement

Orquesta el proceso de lectura de un extracto bancario delegando
en la abstracción StatementParser (nunca en implementaciones concretas).
"""

from __future__ import annotations

from pathlib import Path

from domain.interfaces.parser import StatementParser
from domain.models.statement import Statement


class ParseStatement:
    """Caso de uso: parsear un único extracto bancario.

    Recibe una interfaz StatementParser (inyección de dependencias),
    por lo que el caso de uso no depende de ninguna librería externa.

    Args:
        parser: Implementación concreta del parser inyectada desde fuera.
    """

    def __init__(self, parser: StatementParser) -> None:
        self._parser = parser

    def execute(self, file_path: Path) -> Statement:
        """Ejecuta el caso de uso.

        Args:
            file_path: Ruta al archivo de extracto bancario.

        Returns:
            Statement con los movimientos normalizados.

        Raises:
            FileNotFoundError: Si el archivo no existe.
            ValueError: Si el formato no es compatible con el parser.
        """
        resolved = file_path.resolve()
        if not resolved.exists():
            raise FileNotFoundError(f"El archivo no existe: {resolved}")

        if not self._parser.can_parse(resolved):
            raise ValueError(
                f"El parser {self._parser.__class__.__name__!r} "
                f"no es compatible con el archivo: {resolved.name}"
            )

        return self._parser.parse(resolved)
