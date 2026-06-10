import sys
from playwright.sync_api import sync_playwright

def main():
    print("Searching entire DOM for confirm/tick buttons...")
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
            
            # Open the popover of Departamento
            page.locator(".qv-object-filterpane", has_text="Departamento").locator(".folded-listbox").first.click(force=True)
            page.wait_for_timeout(2000)
            
            # Search entire DOM for buttons/spans that contain the checkmark or have title 'Confirm'
            tick_elements = page.evaluate("""() => {
                const results = [];
                const clickables = document.querySelectorAll('button, span, svg, a, [role="button"], div');
                clickables.forEach(el => {
                    const title = el.getAttribute("title") || "";
                    const text = el.innerText ? el.innerText.trim() : "";
                    const cls = typeof el.className === 'string' ? el.className : (el.className && el.className.baseVal ? el.className.baseVal : "");
                    
                    // Look for checkmark symbol, icon class, or confirm titles
                    if (
                        title.toLowerCase().includes("confirm") || 
                        title.toLowerCase().includes("selec") ||
                        text === '✓' || 
                        cls.includes("confirm") || 
                        cls.includes("tick") || 
                        cls.includes("accept")
                    ) {
                        results.push({
                            tag: el.tagName,
                            class: cls,
                            text: text,
                            title: title,
                            html: el.outerHTML.slice(0, 150)
                        });
                    }
                });
                return results;
            }""")
            
            import pprint
            pprint.pprint(tick_elements)
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
