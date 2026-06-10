import sys
import time
from playwright.sync_api import sync_playwright

def main():
    print("Iniciando prueba de navegación con inyección Scope Angular para 2026...")
    url = "https://portalsiedco.policia.gov.co:4443/extensions/PortalPublico/index.html#/home"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--ignore-certificate-errors"]
        )
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        
        try:
            print("Navegando a la página...")
            page.goto(url, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(3000)
            
            # Inyección de AngularJS Scope para Temática: Homicidios y Año: 2026
            print("Inyectando variables de Scope en AngularJS...")
            js_result = page.evaluate("""() => {
                const sel = document.getElementById('tematicasCombo');
                if (!sel) return "No select element found";
                const scope = angular.element(sel).scope();
                if (!scope) return "No scope found";
                
                // Buscar Homicidios
                const optionObj = scope.tematicasCombo.find(item => item.label.includes('Homicidios'));
                if (!optionObj) return "Homicidios option not found in scope";
                
                // Buscar año 2026
                const selectedYear = scope.aniosCombo.find(y => y === 2026) || scope.aniosCombo[0] || 2026;
                
                scope.$apply(() => {
                    scope.tematicaSeleccionada = optionObj;
                    scope.anioSeleccionado = selectedYear;
                    scope.getSeleccionesCombos();
                });
                return "SUCCESS - Selected Year: " + selectedYear + " (" + typeof selectedYear + ")";
            }""")
            print(f"Resultado de inyección Angular: {js_result}")
            page.wait_for_timeout(2000)
            
            # Hacer clic en el botón Entrar forzando habilitación
            print("Haciendo clic en 'Ver indicadores'...")
            page.locator(".btn-enter").evaluate("el => el.removeAttribute('disabled')")
            page.locator(".btn-enter").click()
            
            print("Esperando a que el panel de Departamento esté visible en Qlik...")
            page.locator(".qv-object-filterpane", has_text="Departamento").first.wait_for(state="visible", timeout=60000)
            print("¡Dashboard de Qlik cargado con éxito!")
            
            # Extraer y mostrar el texto del dashboard
            body_text = page.locator("body").inner_text()
            print("\n--- Vista preliminar del texto del Dashboard ---")
            # Buscar fragmento del KPI de Año 2025/2026
            lines = body_text.split("\n")
            kpi_lines = [l.strip() for l in lines if l.strip()]
            for idx, l in enumerate(kpi_lines):
                if "Año 2025" in l or "Año 2026" in l:
                    start = max(0, idx - 2)
                    end = min(len(kpi_lines), idx + 3)
                    print(f"Contexto KPI found:")
                    for i in range(start, end):
                        print(f"  {kpi_lines[i]}")
                    print("-" * 30)
            
        except Exception as e:
            print(f"Error durante la prueba: {e}")
            try:
                page.screenshot(path="test_siedco_2026_scope_error.png")
                print("Captura de pantalla de error guardada en test_siedco_2026_scope_error.png")
            except Exception:
                pass
        finally:
            browser.close()

if __name__ == "__main__":
    main()
