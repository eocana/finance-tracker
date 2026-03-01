from domain.interfaces.parser import StatementParser
from domain.models.statement import Statement


def parse_statement(parser: StatementParser, file_path: str) -> Statement:
    """Caso de uso: parsea un extracto bancario usando el parser proporcionado."""
    return parser.parse(file_path)
