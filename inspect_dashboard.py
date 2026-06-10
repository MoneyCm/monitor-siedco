import sys
import time
from playwright.sync_api import sync_playwright

def main():
    print("Inspecting SIEDCO dashboard elements...")
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
            
            # Click elements via Angular
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
            
            print("Esperando 12 segundos a que el dashboard cargue...")
            page.wait_for_timeout(12000)
            
            # Dump all divs, buttons, list items that look like filters
            print("--- HTML CONTENT ANALYSIS ---")
            
            # Qlik Sense usually uses tags like <div class="qv-object-... or filter panels
            # Let's find elements with class containing 'qv-' or 'filter' or 'search'
            elements = page.evaluate("""() => {
                const results = [];
                // Find Qlik objects
                const qvObjects = document.querySelectorAll('.qv-object, .qv-panel-sheet, button, li, a');
                qvObjects.forEach((el, index) => {
                    const text = el.innerText ? el.innerText.trim() : "";
                    const id = el.id || "";
                    const cls = el.className || "";
                    const role = el.getAttribute("role") || "";
                    if (text && text.length < 80 && (cls.includes("qv") || cls.includes("filter") || role.includes("button") || el.tagName === "BUTTON")) {
                        results.push({
                            index: index,
                            tag: el.tagName,
                            text: text,
                            id: id,
                            class: cls,
                            role: role
                        });
                    }
                });
                return results.slice(0, 50); // Get first 50 relevant elements
            }""")
            
            for el in elements:
                print(f"[{el['tag']}] text='{el['text']}', id='{el['id']}', class='{el['class']}', role='{el['role']}'")
            print("-----------------------------\n")
            
            # Take a second screenshot
            page.screenshot(path="siedco_dashboard_details.png")
            print("Screenshot saved to: siedco_dashboard_details.png")
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
