import os

from domain.interfaces.parser import StatementParser
from infrastructure.parsers.lacaixa import LaCaixaPDFParser
from infrastructure.parsers.paypal_csv import PayPalCSVParser
from infrastructure.parsers.santander import SantanderPDFParser


class ParserFactory:
    """Factory que detecta el tipo de archivo y devuelve el parser adecuado.

    La detección se basa en la extensión y el nombre del archivo, lo que permite
    añadir nuevos parsers sin modificar los existentes (principio Open/Closed).
    """

    @staticmethod
    def get_parser(file_path: str) -> StatementParser:
        name = os.path.basename(file_path).lower()
        _, ext = os.path.splitext(name)

        if ext == ".csv" and "paypal" in name:
            return PayPalCSVParser()
        if ext == ".pdf" and "santander" in name:
            return SantanderPDFParser()
        if ext == ".pdf" and "lacaixa" in name:
            return LaCaixaPDFParser()

        raise ValueError(
            f"No se encontró un parser para el archivo: {file_path}. "
            "Asegúrate de que el nombre del archivo incluye 'paypal', 'santander' o 'lacaixa'."
        )
