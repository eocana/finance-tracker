# Finance Tracker

Herramienta de escritorio en Python y CustomTkinter para gestionar extractos bancarios personales. Lee PDFs de Santander y CSVs de PayPal, cruza los cobros automáticamente y exporta a un Excel formateado.

> Proyecto de portfolio orientado a demostrar principios de arquitectura limpia y patrones de diseño en Python.

---

## Características principales

- Parseo automático de extractos PDF (Santander) y CSV (PayPal)
- Cruce inteligente PayPal ↔ Santander: sustituye "PAYPAL *XXXXX" por el nombre real del comercio
- Categorización por reglas configurables (supermercado, restaurante, suscripciones, nómina…)
- Exportación a Excel formateada con colores, autofiltro y formato de moneda
- Interfaz de escritorio con CustomTkinter (tema oscuro/claro)

---

## Arquitectura

El proyecto sigue los principios de Clean Architecture: las capas internas no conocen las externas.

```
finance-tracker/
├── domain/              ← Núcleo — cero imports externos
│   ├── models/
│   │   ├── movement.py     # Entidad Movement (dataclass)
│   │   └── statement.py    # Repositorio en memoria de movimientos
│   └── interfaces/
│       ├── parser.py       # ABC StatementParser
│       ├── exporter.py     # ABC Exporter
│       └── categorizer.py  # ABC Categorizer
├── application/         ← Casos de uso — dependen solo de interfaces
│   └── use_cases/
│       ├── parse_statement.py
│       ├── resolve_paypal.py
│       ├── categorize.py
│       └── export.py
├── infrastructure/      ← Implementaciones concretas
│   ├── parsers/
│   │   ├── parser_factory.py
│   │   ├── santander.py
│   │   ├── paypal_csv.py
│   │   └── lacaixa.py       # Implementa LaCaixaCSVParser; LaCaixaPDFParser es un stub
│   ├── exporters/
│   │   └── excel_exporter.py
│   └── categorizers/
│       └── rule_based.py
└── ui/                  ← Interfaz gráfica
    └── views/
        ├── main_window.py
        ├── file_picker.py
        └── preview_table.py
```

### Regla de dependencia

```
UI → Application → Domain ← Infrastructure
```

El módulo `domain/` no importa ninguna librería externa. `pdfplumber`, `openpyxl` y `pandas` existen solo en `infrastructure/`.

---

## Patrones de diseño aplicados

### 1. Strategy — `infrastructure/parsers/`

Cada parser bancario es una estrategia intercambiable que implementa `StatementParser`.

```python
# domain/interfaces/parser.py
class StatementParser(ABC):
    def parse(self, file_path: Path) -> Statement: ...
    def can_parse(self, file_path: Path) -> bool: ...
```

El caso de uso `ParseStatement` funciona con cualquiera de estas implementaciones:

```python
# application/use_cases/parse_statement.py
class ParseStatement:
    def __init__(self, parser: StatementParser) -> None:
        self._parser = parser

    def execute(self, file_path: Path) -> Statement:
        return self._parser.parse(file_path)
```

### 2. Factory — `infrastructure/parsers/parser_factory.py`

`ParserFactory` mantiene un registro de clases de parser y detecta automáticamente cuál usar según el archivo.

```python
parser = ParserFactory.get_parser(Path("extracto_santander_2026.pdf"))
# → devuelve SantanderPDFParser()
```

Se pueden registrar nuevos parsers sin modificar código existente:

```python
ParserFactory.register(MiBancoParser)
```

### 3. Repository — `domain/models/statement.py`

`Statement` actúa como repositorio en memoria y expone métodos de consulta para la colección de movimientos.

### 4. Clean Architecture

Los casos de uso en `application/use_cases/` consumen interfaces; la inyección de dependencias se realiza en `MainWindow`.

### 5. Observer — `ui/`

`FilePicker` notifica cambios mediante callbacks; `MainWindow` coordina y actualiza `PreviewTable` mediante `update_movements()`.

---

## Lógica de cruce PayPal ↔ Santander

Implementada en `application/use_cases/resolve_paypal.py` → `ResolvePayPal.execute`.

Reglas principales de cruce:

- `abs(paypal.amount) == abs(santander.amount)` — mismo importe
- `abs((paypal.date - santander.date).days) <= 3` — tolerancia temporal

Después del cruce, la descripción del movimiento de Santander se sustituye por el nombre real del comercio y `resolved_from` guarda la descripción original.

---

## Pipeline completo

```
Archivos seleccionados
        │
        ▼
ParserFactory.get_parser(file)
        │
        ▼
ParseStatement.execute(file)
        │
        ▼
ResolvePayPal.execute(...)
        │
        ▼
CategorizeMovements.execute(...)
        │
        ▼
ExportMovements.execute(...)
        │
        ▼
  movimientos.xlsx
```

---

## Instalación y uso

### Requisitos

- Python 3.10+

### Instalar dependencias

```bash
pip install -r requirements.txt
```

### Ejecutar

```bash
python main.py
```

### Preparar los archivos de entrada

| Archivo | Cómo obtenerlo |
|---|---|
| `santander_*.pdf` | Descargar el extracto mensual desde la banca online de Santander. El nombre del archivo debe contener "santander". |
| `paypal_*.csv` | Panel de PayPal → Actividad → Descargar → CSV. El nombre del archivo debe contener "paypal". |
| `CaixaBank_*.csv` | Exportación digital desde CaixaBankNow (si aplica). El parser acepta ficheros cuyo nombre comience por `CaixaBank_`. |

---

## Dependencias

| Librería | Uso | Capa |
|---|---|---|
| `pdfplumber` | Extracción de tablas de PDFs | `infrastructure/parsers/santander.py` |
| `pandas` | Lectura del CSV de PayPal y LaCaixa | `infrastructure/parsers/*` |
| `openpyxl` | Generación del Excel formateado | `infrastructure/exporters/excel_exporter.py` |
| `customtkinter` | Interfaz gráfica de escritorio | `ui/` |

El módulo `domain/` tiene cero dependencias externas.

---

## Categorías predefinidas

Configuradas en `infrastructure/categorizers/rule_based.py` → `DEFAULT_RULES`:

| Categoría | Keywords |
|---|---|
| Supermercado | mercadona, carrefour, bonpreu… |
| Restaurante | mcdonald, kebab, sushi… |
| Subscripción | paypal, spotify, netflix… |
| Transporte | autopista, renfe, bus |
| Alquiler | alquiler, pagament, traspassos |
| Suministros | energia, llum, gas, agua |
| Inversión | trade republic, invest… |
| Nómina | nomina, nómina, sueldo |
| Transferencia | transferencia |

Para añadir reglas en tiempo de ejecución: `RuleBasedCategorizer().add_rule("Farmacia", ["farmacia", "parafarmacia"])`.

---

## Modelo de dominio

```python
@dataclass
class Movement:
    date: date
    description: str
    amount: float        # negativo = gasto, positivo = ingreso
    source: str          # "santander" | "paypal" | "lacaixa"
    category: str = ""
    resolved_from: str = ""  # descripción original antes del cruce PayPal
```

---

## Roadmap

- [x] Fase 1 — Pipeline completo: parseo, cruce PayPal, categorización, exportación Excel
- [ ] Fase 2 — Parser LaCaixa: CSV implementado; parser PDF pendiente
- [ ] Fase 3 — Persistencia local (SQLite), historial de extractos, búsqueda avanzada

---

## Licencia

MIT

