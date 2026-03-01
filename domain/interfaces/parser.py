from abc import ABC, abstractmethod

from domain.models.statement import Statement


class StatementParser(ABC):
    """Interfaz para parsers de extractos bancarios."""

    @abstractmethod
    def parse(self, file_path: str) -> Statement:
        """Lee el archivo en file_path y devuelve un Statement normalizado."""
        ...
