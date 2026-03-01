# Finance Tracker

Herramienta de escritorio en **Python** para gestionar extractos bancarios personales. Lee extractos de **Santander** (PDF) y **PayPal** (CSV), cruza automáticamente los cobros PayPal con su detalle real, categoriza los movimientos y los exporta a Excel.

---

## Arquitectura

El proyecto aplica **Clean Architecture**: el dominio es independiente de cualquier librería externa; las capas externas dependen hacia adentro.

```
finance-tracker/
├── domain/            # Núcleo: sin imports externos
│   ├── models/        # Entidades Movement y Statement
│   └── interfaces/    # ABCs: StatementParser, Exporter, Categorizer
├── application/       # Casos de uso (orquestación)
│   └── use_cases/
├── infrastructure/    # Implementaciones concretas (pdfplumber, openpyxl, pandas)
│   ├── parsers/
│   ├── exporters/
│   └── categorizers/
└── ui/                # Interfaz gráfica (tkinter)
    └── views/
```

---

## Patrones de diseño

| Patrón | Clase / Módulo | Descripción |
|---|---|---|
| **Strategy** | `SantanderPDFParser`, `PayPalCSVParser`, `LaCaixaPDFParser` | Cada banco implementa `StatementParser.parse()` de forma intercambiable |
| **Factory** | `ParserFactory.get_parser()` | Detecta el tipo de archivo por nombre/extensión y devuelve el parser correcto sin modificar código existente (Open/Closed) |
| **Repository** | `Statement` | Abstrae la colección de `Movement` con `add()`, `all()` e iteración |
| **Clean Architecture** | Todo el directorio `domain/` | Cero imports de librerías externas; las capas externas dependen del dominio, nunca al revés |
| **Observer** | `MainWindow` + widgets | La interfaz reacciona a los eventos de los botones sin conocer los detalles de parseo ni exportación |

---

## Modelo de dominio

```python
@dataclass
class Movement:
    date: date
    description: str
    amount: float          # negativo = gasto, positivo = ingreso
    source: str            # "santander" | "paypal" | "lacaixa"
    category: str = ""
    resolved_from: str = ""  # descripción original si fue cruzado con PayPal
```

`Statement` actúa como repositorio en memoria: agrupa `Movement` de una misma fuente y expone `add()`, `all()` e iteración directa.

---

## Pipeline de procesamiento

1. **Parseo** — `parse_statement(parser, file_path)` delega en el parser correspondiente.
2. **Cruce PayPal ↔ Santander** — `resolve_paypal(santander_stmt, paypal_stmt)` busca movimientos de Santander con "paypal" en la descripción y los empareja con el CSV de PayPal por importe (±0,01 €) y fecha (±3 días). Si hay match, la descripción se sustituye por el nombre real del comercio y la original queda en `resolved_from`.
3. **Categorización** — `categorize_movements(movements, categorizer)` asigna una categoría a cada movimiento usando `RuleBasedCategorizer` (palabras clave configurables).
4. **Exportación** — `export_movements(movements, exporter, path)` genera el `.xlsx` con `ExcelExporter`.

---

## Parsers

### Santander PDF (`infrastructure/parsers/santander.py`)
Usa `pdfplumber`. Cada fila de la tabla tiene columnas separadas:
- `row[0]` → fecha (`"28 feb 2026\nF. valor: …"`)
- `row[1]` → descripción
- `row[2]` → importe (`"-177,19€"`)
- `row[3]` → saldo (ignorado)

### PayPal CSV (`infrastructure/parsers/paypal_csv.py`)
Usa `pandas`. Filtra `Estado == "Completado"` y lee las columnas `Fecha`, `Nombre` y `Bruto`. El importe admite puntos de miles y coma decimal.

### LaCaixa (`infrastructure/parsers/lacaixa.py`)
Stub — lanza `NotImplementedError`. Pendiente de implementación en Fase 2.

---

## Categorías predefinidas

Configuradas en `infrastructure/categorizers/rule_based.py`:

| Categoría | Palabras clave |
|---|---|
| Supermercado | mercadona, carrefour, bonpreu, supermercat, roges |
| Restaurante | mcdonald, kebab, sushi, rostisseria |
| Subscripción | paypal, spotify, netflix, google play |
| Transporte | autopista, renfe, bus |
| Alquiler | alquiler |
| Suministros | energia, llum, gas, agua |
| Inversión | trade republic, inversión, invest |
| Nómina | nomina, nómina, sueldo |
| Transferencia | transferencia |
| Otros | *(ninguna coincidencia)* |

---

## Excel de salida

Generado con `openpyxl` por `ExcelExporter`:
- Hoja `Movimientos` con columnas: Fecha · Descripción · Categoría · Fuente · Importe (€) · Detalle PayPal
- Cabecera con fondo azul oscuro y texto blanco
- Filas de ingresos en verde claro, gastos en rojo claro
- Importe con formato `#,##0.00€` y fuente roja si negativo
- `Detalle PayPal` solo tiene valor en movimientos cruzados

---

## Instalación y uso

```bash
pip install -r requirements.txt
python main.py
```

1. Selecciona el PDF de Santander y/o el CSV de PayPal con los botones **Examinar…**
2. Pulsa **Cargar y procesar** para ver la tabla unificada con categorías
3. Pulsa **Exportar a Excel** para guardar el archivo `.xlsx`

---

## Dependencias

| Paquete | Uso |
|---|---|
| `pdfplumber` | Extracción de tablas del PDF de Santander |
| `openpyxl` | Generación del Excel de salida |
| `pandas` | Lectura del CSV de PayPal |
| `tkinter` | Interfaz gráfica (incluida en Python estándar) |
