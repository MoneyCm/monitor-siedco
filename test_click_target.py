import sys
import time
from playwright.sync_api import sync_playwright

def main():
    print("Testing click targets for Qlik Sense filter pane...")
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
            
            # Select Homicidios and Year
            page.evaluate("""() => {
                const sel = document.getElementById('tematicasCombo');
                const scope = angular.element(sel).scope();
                scope.$apply(() => {
                    scope.tematicaSeleccionada = scope.tematicasCombo.find(item => item.label.includes('Homicidios'));
                    scope.anioSeleccionado = scope.aniosCombo.find(y => y === 2025) || 2025;
                    scope.getSeleccionesCombos();
                });
            }""")
            page.wait_for_timeout(1000)
            page.locator(".btn-enter").click()
            
            print("Esperando 12 segundos...")
            page.wait_for_timeout(12000)
            
            # Let's find the specific "Departamento" pane and print its HTML structure
            structure = page.evaluate("""() => {
                const pane = Array.from(document.querySelectorAll('.qv-object-filterpane')).find(el => el.innerText.includes('Departamento'));
                if (!pane) return "Pane not found";
                
                // Return tags and classes inside the pane
                const elements = Array.from(pane.querySelectorAll('*')).map(el => ({
                    tag: el.tagName,
                    class: el.className,
                    text: el.innerText ? el.innerText.trim() : "",
                    id: el.id
                }));
                return elements;
            }""")
            
            print("\n--- Departamento Filter Pane DOM Structure ---")
            for el in structure[:30]:
                print(f"[{el['tag']}] id='{el['id']}', class='{el['class']}', text='{el['text']}'")
            print("----------------------------------------------\n")
            
            # Intentar click en el elemento folded-listbox del panel de Departamento
            print("Intentando click en el elemento folded-listbox de 'Departamento'...")
            target_element = page.locator(".qv-object-filterpane", has_text="Departamento").locator(".folded-listbox").first
            target_element.click(force=True)
            page.wait_for_timeout(2000)
            
            page.screenshot(path="click_test_result.png")
            print("Resultado del click guardado en: click_test_result.png")
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
