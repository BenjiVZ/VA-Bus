"""
html_a_pdf.py — Convierte un HTML a un PDF de UNA sola página grande.

Usa Playwright (Chromium headless) para renderizar el HTML tal como lo
haría un navegador real, y luego genera un PDF con un tamaño de página
exacto al contenido, sin cortes ni paginación.

Uso:
    python html_a_pdf.py                          # usa el HTML por defecto
    python html_a_pdf.py archivo.html             # convierte un HTML específico
    python html_a_pdf.py archivo.html salida.pdf  # especifica nombre del PDF
"""

import sys
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def html_a_pdf(html_path: str, pdf_path: str | None = None):
    html_file = Path(html_path).resolve()

    if not html_file.exists():
        print(f"❌ No se encontró el archivo: {html_file}")
        sys.exit(1)

    if pdf_path is None:
        pdf_path = html_file.with_suffix('.pdf')
    else:
        pdf_path = Path(pdf_path).resolve()

    print(f"📄 HTML:  {html_file}")
    print(f"📦 PDF:   {pdf_path}")
    print(f"⏳ Renderizando con Chromium headless...")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        # Cargar el HTML como URL de archivo local
        page.goto(html_file.as_uri(), wait_until='networkidle')

        # Esperar a que las fuentes de Google se carguen
        page.wait_for_timeout(2000)

        # ── Medir el tamaño real del contenido ──
        dimensions = page.evaluate("""() => {
            // Quitar page-breaks y márgenes de impresión para una sola página
            const style = document.createElement('style');
            style.textContent = `
                @page { margin: 0 !important; size: auto !important; }
                * {
                    page-break-before: auto !important;
                    page-break-after: auto !important;
                    break-before: auto !important;
                    break-after: auto !important;
                }
                .page-break {
                    page-break-before: auto !important;
                    break-before: auto !important;
                    display: none !important;
                }
                body {
                    max-width: none !important;
                    margin: 0 !important;
                    padding: 40px !important;
                    background: white !important;
                }
                .page-container {
                    box-shadow: none !important;
                    border-radius: 0 !important;
                    margin: 0 !important;
                    padding: 40px !important;
                }
                @media print {
                    body {
                        padding: 0 !important;
                    }
                    .page-container {
                        padding: 30px !important;
                    }
                }
            `;
            document.head.appendChild(style);

            const body = document.body;
            const container = document.querySelector('.page-container') || body;

            return {
                width: Math.max(body.scrollWidth, container.scrollWidth, 850),
                height: Math.max(body.scrollHeight, container.scrollHeight) + 80
            };
        }""")

        page_width = dimensions['width']
        page_height = dimensions['height']

        print(f"📐 Tamaño del contenido: {page_width}px × {page_height}px")

        # ── Generar PDF de una sola página ──
        # Convertir px a pulgadas (96 DPI) y añadir márgenes
        width_inches = (page_width / 96) + 0.8   # +0.8" para márgenes laterales
        height_inches = (page_height / 96) + 0.5  # +0.5" para margen inferior

        page.pdf(
            path=str(pdf_path),
            width=f"{width_inches}in",
            height=f"{height_inches}in",
            margin={
                'top': '0.3in',
                'right': '0.4in',
                'bottom': '0.3in',
                'left': '0.4in',
            },
            print_background=True,
            scale=1,
        )

        browser.close()

    file_size = os.path.getsize(pdf_path)
    size_kb = file_size / 1024

    print(f"")
    print(f"✅ PDF generado exitosamente!")
    print(f"   📄 {pdf_path}")
    print(f"   📦 Tamaño: {size_kb:.0f} KB")
    print(f"   📐 Una sola página: {width_inches:.1f}\" × {height_inches:.1f}\"")
    print(f"")
    print(f"💡 Abriendo PDF...")

    # Abrir el PDF automáticamente
    os.startfile(str(pdf_path))


if __name__ == '__main__':
    # Archivo HTML por defecto
    default_html = os.path.join(os.path.dirname(__file__), 'presupuesto_aerorutas.html')

    html_input = sys.argv[1] if len(sys.argv) > 1 else default_html
    pdf_output = sys.argv[2] if len(sys.argv) > 2 else None

    html_a_pdf(html_input, pdf_output)
