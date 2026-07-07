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
            
            # Seleccionar Hurto a personas usando JS para buscar la etiqueta y Playwright select_option
            option_label = page.evaluate("""() => {
                const sel = document.getElementById('tematicasCombo');
                if (!sel) return null;
                const scope = angular.element(sel).scope();
                if (!scope) return null;
                const kws = ["extorsi"];
                const optionObj = scope.tematicasCombo.find(item => {
                    const labelLower = item.label.toLowerCase();
                    return kws.every(kw => labelLower.includes(kw));
                });
                return optionObj ? optionObj.label : null;
            }""")
            print("Encontrado label del combo:", option_label)
            if not option_label:
                raise Exception("No se encontró la temática por keywords")
                
            page.select_option("select#tematicasCombo", label=option_label)
            page.select_option("select[id$='osCombo']", label="2026")
            page.wait_for_timeout(1500)
            
            # Click
            page.locator(".btn-enter").evaluate("el => el.removeAttribute('disabled')")
            page.locator(".btn-enter").first.click()
            
            # Wait for dashboard
            page.locator(".qv-object-filterpane", has_text="Departamento").first.wait_for(state="visible", timeout=60000)
            page.wait_for_timeout(3000)
            
            # Seleccionar Valle
            muni_filter = page.locator(".qv-object-filterpane", has_text="Departamento").locator(".folded-listbox").first
            muni_filter.click(force=True)
            page.wait_for_timeout(1500)
            dept_search = page.locator("input[placeholder='Buscar en cuadro de lista']:visible").first
            dept_search.fill("VALLE")
            page.wait_for_timeout(2000)
            page.locator("[data-testid='listbox.item']", has_text="VALLE").first.click(force=True)
            page.wait_for_timeout(1500)
            confirm_btn = page.locator(".qs-actions-confirm:visible, .qv-confirm-button:visible, button[title*='Confirmar']:visible, .actions-toolbar-confirm:visible").first
            confirm_btn.click(force=True)
            page.wait_for_timeout(4500)
            
            # Seleccionar Jamundí
            muni_filter = page.locator(".qv-object-filterpane", has_text="Municipio").locator(".folded-listbox").first
            muni_filter.click(force=True)
            page.wait_for_timeout(1500)
            muni_search = page.locator("input[placeholder='Buscar en cuadro de lista']:visible").first
            muni_search.fill("JAMUNDI")
            page.wait_for_timeout(2000)
            page.locator("[data-testid='listbox.item']", has_text="JAMUNDÍ").first.click(force=True)
            page.wait_for_timeout(1500)
            confirm_btn = page.locator(".qs-actions-confirm:visible, .qv-confirm-button:visible, button[title*='Confirmar']:visible, .actions-toolbar-confirm:visible").first
            confirm_btn.click(force=True)
            page.wait_for_timeout(10000)
            
            # Guardar captura de pantalla para inspeccionar visualmente
            page.screenshot(path="siedco_hurto_a_personas_debug.png", full_page=True)
            print("Captura guardada en: siedco_hurto_a_personas_debug.png")
            
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
