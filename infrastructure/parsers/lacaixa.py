from domain.interfaces.parser import StatementParser
from domain.models.statement import Statement


class LaCaixaPDFParser(StatementParser):
    """Stub para el parser PDF de LaCaixa. Pendiente de implementación (Fase 2)."""

    def parse(self, file_path: str) -> Statement:
        raise NotImplementedError("El parser de LaCaixa aún no está implementado.")
