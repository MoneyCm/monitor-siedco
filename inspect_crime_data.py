import sys
from playwright.sync_api import sync_playwright

def main():
    print("Iniciando inspección de Hurto a personas...")
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
            page.wait_for_timeout(5000)
            
            # Seleccionar Hurto a personas
            js_result = page.evaluate("""() => {
                const sel = document.getElementById('tematicasCombo');
                if (!sel) return "No select element found";
                const scope = angular.element(sel).scope();
                if (!scope) return "No scope found";
                
                const optionObj = scope.tematicasCombo.find(item => item.label.includes('Hurto a personas'));
                if (!optionObj) return "Option not found";
                
                const selectedYear = 2026;
                
                sel.value = optionObj.value;
                sel.dispatchEvent(new Event('change'));
                const selAnio = document.querySelector("select[id$='osCombo']");
                if (selAnio) {
                    selAnio.value = selectedYear.toString();
                    selAnio.dispatchEvent(new Event('change'));
                }
                
                scope.$apply(() => {
                    scope.tematicaSeleccionada = optionObj;
                    scope.anioSeleccionado = selectedYear;
                    scope.getSeleccionesCombos();
                });
                return "SUCCESS";
            }""")
            print("Angular result:", js_result)
            page.wait_for_timeout(1500)
            
            # Click
            page.locator(".btn-enter:not([disabled])").first.click()
            
            # Wait for dashboard
            page.locator(".qv-object-filterpane", has_text="Departamento").first.wait_for(state="visible", timeout=60000)
            page.wait_for_timeout(3000)
            
            # Seleccionar Valle
            muni_filter = page.locator(".qv-object-filterpane", has_text="Departamento").locator(".folded-listbox").first
            muni_filter.click(force=True)
            page.wait_for_timeout(1500)
            dept_search = page.locator("input[placeholder='Buscar en cuadro de lista']:visible").first
            dept_search.fill("VALLE")
            page.wait_for_timeout(1000)
            page.locator("[data-testid='listbox.item']", has_text="VALLE").first.click(force=True)
            page.wait_for_timeout(1000)
            page.locator(".actions-toolbar-confirm:visible").first.click(force=True)
            page.wait_for_timeout(4500)
            
            # Seleccionar Jamundí
            muni_filter = page.locator(".qv-object-filterpane", has_text="Municipio").locator(".folded-listbox").first
            muni_filter.click(force=True)
            page.wait_for_timeout(1500)
            muni_search = page.locator("input[placeholder='Buscar en cuadro de lista']:visible").first
            muni_search.fill("JAMUNDI")
            page.wait_for_timeout(1000)
            page.locator("[data-testid='listbox.item']", has_text="JAMUNDÍ").first.click(force=True)
            page.wait_for_timeout(1000)
            page.locator(".actions-toolbar-confirm:visible").first.click(force=True)
            page.wait_for_timeout(8000)
            
            body_text = page.locator("body").inner_text()
            print("=== BODY TEXT ===")
            print(body_text)
            print("=================")
            
        except Exception as e:
            print("Error:", e)
        finally:
            browser.close()

if __name__ == "__main__":
    main()
