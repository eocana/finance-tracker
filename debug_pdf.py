"""
Script de diagnóstico para el parser Santander.
Uso:  python debug_pdf.py <ruta_al_pdf>
"""
import sys, os, logging
logging.getLogger("pdfminer").setLevel(logging.ERROR)

sys.path.insert(0, os.path.dirname(__file__))

import pdfplumber
from infrastructure.parsers.santander import SantanderPDFParser, _TABLE_SETTINGS_LIST

if len(sys.argv) < 2:
    print("Uso: python debug_pdf.py <ruta.pdf>")
    sys.exit(1)

pdf_path = sys.argv[1]
print(f"\n=== Diagnóstico: {pdf_path} ===\n")

with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[0]

    print("── extract_text (primeras 600 chars) ──────────────────────────────")
    print(repr(page.extract_text()[:600]))
    print()

    print("── extract_words (primeros 10) ─────────────────────────────────────")
    for w in page.extract_words()[:10]:
        print(f"  x0={w['x0']:.0f}  top={w['top']:.0f}  text={w['text']!r}")
    print()

    for i, settings in enumerate(_TABLE_SETTINGS_LIST):
        try:
            t = page.extract_table(settings) if settings else page.extract_table()
        except Exception as e:
            t = None
            print(f"  settings[{i}] → ERROR: {e}")
        if t:
            print(f"── extract_table settings[{i}]={settings or 'default'} → {len(t)} filas ──")
            for row in t[:5]:
                print(" ", row)
        else:
            print(f"  settings[{i}] → None")
    print()

print("── Parser completo (primeros 10 movimientos) ─────────────────────")
parser = SantanderPDFParser()
stmt = parser.parse(__import__("pathlib").Path(pdf_path))
print(f"Total movimientos extraídos: {len(stmt)}")
for m in list(stmt)[:10]:
    print(f"  {m}")
