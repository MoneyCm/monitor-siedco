import sys
import time
from playwright.sync_api import sync_playwright

def main():
    print("Iniciando prueba de navegación en SIEDCO...")
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
            
            # Seleccionar Homicidios y Año manipulando directamente el scope de AngularJS
            print("Seleccionando 'Homicidios' y Año 2025 mediante el Scope de AngularJS...")
            js_result = page.evaluate("""() => {
                const sel = document.getElementById('tematicasCombo');
                if (!sel) return "No select element found";
                const scope = angular.element(sel).scope();
                if (!scope) return "No scope found";
                
                // Buscar el objeto Homicidios
                const optionObj = scope.tematicasCombo.find(item => item.label.includes('Homicidios'));
                if (!optionObj) return "Homicidios option not found in scope";
                
                // Seleccionar año 2025
                const selectedYear = scope.aniosCombo.find(y => y === 2025) || scope.aniosCombo[1] || 2025;
                
                // Actualizar el modelo e invocar ng-change
                scope.$apply(() => {
                    scope.tematicaSeleccionada = optionObj;
                    scope.anioSeleccionado = selectedYear;
                    scope.getSeleccionesCombos();
                });
                return "SUCCESS";
            }""")
            print(f"Resultado de inyección Angular: {js_result}")
            page.wait_for_timeout(2000)
            
            # Click en "Ver indicadores"
            print("Dando click en 'Ver indicadores'...")
            btn_enter = page.locator(".btn-enter").first
            btn_enter.click()
            
            print("Esperando a que cargue el dashboard (10 segundos)...")
            page.wait_for_timeout(10000)
            
            print(f"URL actual: {page.url}")
            
            # Ver si hay iframes cargados
            iframes = page.frames
            print(f"Número de frames en la página: {len(iframes)}")
            for i, f in enumerate(iframes):
                print(f"Frame {i}: Name='{f.name}', URL='{f.url[:80]}'")
                
            # Tomar captura de pantalla del dashboard
            screenshot_path = "siedco_dashboard_capture.png"
            page.screenshot(path=screenshot_path, full_page=True)
            print(f"Captura de pantalla guardada en: {screenshot_path}")
            
            # Intentar extraer texto del dashboard para ver si cargó contenido
            body_text = page.locator("body").inner_text()
            print("\n--- Texto del Dashboard (Primeros 500 caracteres) ---")
            print(body_text[:500])
            print("----------------------------------------------------\n")
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
