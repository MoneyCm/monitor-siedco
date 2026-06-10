import sys
import time
from playwright.sync_api import sync_playwright

def main():
    print("Iniciando prueba de filtrado por departamento y municipio...")
    url = "https://portalsiedco.policia.gov.co:4443/extensions/PortalPublico/index.html#/home"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--ignore-certificate-errors"]
        )
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        
        try:
            page.goto(url, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(3000)
            
            # 1. Seleccionar temática y año de forma nativa
            print("Seleccionando Temática y Año en el formulario inicial...")
            page.select_option("select#tematicasCombo", label="Homicidios")
            page.select_option("select[id$='osCombo']", label="2025")
            page.wait_for_timeout(1000)
            
            # Forzar habilitación del botón por si acaso
            page.locator(".btn-enter").evaluate("el => el.removeAttribute('disabled')")
            page.locator(".btn-enter").click()
            
            print("Esperando 15 segundos a que el dashboard de Qlik cargue completamente...")
            page.wait_for_timeout(15000)
            
            # 2. Filtrar por Departamento (Valle del Cauca)
            print("Abriendo filtro de Departamento...")
            dept_filter = page.locator(".qv-object-filterpane", has_text="Departamento").locator(".folded-listbox").first
            dept_filter.click(force=True)
            page.wait_for_timeout(1500)
            
            # Escribir "VALLE" en la caja de búsqueda activa
            print("Escribiendo 'VALLE' en la búsqueda de departamento...")
            dept_search = page.locator("input[placeholder='Buscar en cuadro de lista']").last
            dept_search.click()
            dept_search.fill("")
            dept_search.press_sequentially("VALLE", delay=100)
            page.wait_for_timeout(2000)
            
            # Captura de pantalla intermedia
            page.screenshot(path="siedco_valle_busqueda.png")
            print("Captura de búsqueda guardada en: siedco_valle_busqueda.png")
            
            # Hacer click en la opción filtrada y confirmar
            print("Seleccionando la opción VALLE...")
            page.locator("[data-testid='listbox.item']", has_text="VALLE").first.click(force=True)
            page.wait_for_timeout(1000)
            
            print("Confirmando selección de Departamento...")
            page.locator(".actions-toolbar-confirm:visible").first.click(force=True)
            print("Esperando 5 segundos a que se aplique el filtro de Departamento...")
            page.wait_for_timeout(5000)
            
            # Captura de pantalla de departamento confirmado
            page.screenshot(path="siedco_valle_confirmado.png")
            print("Captura de departamento confirmado guardada en: siedco_valle_confirmado.png")
            
            # 3. Filtrar por Municipio (Jamundí)
            print("Abriendo filtro de Municipio...")
            muni_filter = page.locator(".qv-object-filterpane", has_text="Municipio").locator(".folded-listbox").first
            muni_filter.click(force=True)
            page.wait_for_timeout(1500)
            
            print("Escribiendo 'JAMUNDI' en la búsqueda de municipio...")
            muni_search = page.locator("input[placeholder='Buscar en cuadro de lista']").last
            muni_search.click()
            muni_search.fill("")
            muni_search.press_sequentially("JAMUNDI", delay=100)
            page.wait_for_timeout(2000)
            
            # Captura de pantalla intermedia
            page.screenshot(path="siedco_jamundi_busqueda.png")
            print("Captura de búsqueda guardada en: siedco_jamundi_busqueda.png")
            
            print("Seleccionando la opción JAMUNDÍ...")
            page.locator("[data-testid='listbox.item']", has_text="JAMUNDÍ").first.click(force=True)
            page.wait_for_timeout(1000)
            
            print("Confirmando selección de Municipio...")
            page.locator(".actions-toolbar-confirm:visible").first.click(force=True)
            print("Esperando 8 segundos a que se aplique el filtro de Municipio y se actualicen los gráficos...")
            page.wait_for_timeout(8000)
            
            # 4. Captura del dashboard final filtrado
            screenshot_path = "siedco_jamundi_final.png"
            page.screenshot(path=screenshot_path, full_page=True)
            print(f"[OK] Dashboard filtrado completado. Captura guardada en: {screenshot_path}")
            
            # Extraer y mostrar el texto del dashboard final para confirmar datos
            body_text = page.locator("body").inner_text()
            print("\n--- Texto del Dashboard Filtrado (Primeros 1000 caracteres) ---")
            print(body_text[:1000])
            print("-------------------------------------------------------------\n")
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
