"""
ParserFactory — Patrón Factory + Open/Closed Principle.

Detecta automáticamente qué parser usar en función del archivo indicado.
Para añadir un nuevo banco solo hay que registrar el parser en _REGISTRY;
no se modifica ningún código existente.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Type

from domain.interfaces.parser import StatementParser
from infrastructure.parsers.santander import SantanderPDFParser
from infrastructure.parsers.paypal_csv import PayPalCSVParser
from infrastructure.parsers.lacaixa import LaCaixaCSVParser, LaCaixaPDFParser


class ParserFactory:
    """Factory extensible de parsers bancarios.

    Mantiene un registro de clases de parser. Al llamar a `get_parser(file)`
    instancia y devuelve el parser que declara poder manejar ese archivo.

    Para registrar un nuevo parser basta con añadirlo a `_REGISTRY` o
    llamar a `ParserFactory.register(MyNewParser)` en tiempo de arranque.
    Cumple el principio Open/Closed: abierto a extensión, cerrado a modificación.
    """

    _REGISTRY: List[Type[StatementParser]] = [
        SantanderPDFParser,
        LaCaixaCSVParser,   # antes que PayPalCSVParser (también acepta .csv)
        PayPalCSVParser,
        LaCaixaPDFParser,
    ]

    @classmethod
    def register(cls, parser_class: Type[StatementParser]) -> None:
        """Registra un nuevo tipo de parser en el factory.

        Args:
            parser_class: Clase que implementa StatementParser.
        """
        if parser_class not in cls._REGISTRY:
            cls._REGISTRY.append(parser_class)

    @classmethod
    def get_parser(cls, file_path: Path) -> StatementParser:
        """Devuelve el parser apropiado para el archivo dado.

        Itera el registro hasta encontrar un parser cuyo `can_parse`
        devuelva True. Si ninguno es compatible, lanza ValueError.

        Args:
            file_path: Ruta al archivo de extracto bancario.

        Returns:
            Instancia del parser compatible.

        Raises:
            ValueError: Si ningún parser registrado es compatible.
        """
        resolved = file_path.resolve()
        for parser_class in cls._REGISTRY:
            instance: StatementParser = parser_class()
            if instance.can_parse(resolved):
                return instance

        supported = ", ".join(c.__name__ for c in cls._REGISTRY)
        raise ValueError(
            f"No se encontró un parser para el archivo '{file_path.name}'. "
            f"Parsers registrados: {supported}"
        )

    @classmethod
    def list_parsers(cls) -> List[str]:
        """Devuelve los nombres de los parsers registrados."""
        return [c.__name__ for c in cls._REGISTRY]
