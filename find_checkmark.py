import sys
from playwright.sync_api import sync_playwright

def main():
    print("Finding checkmark/confirm elements in SIEDCO listbox popover...")
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
            
            # Open the popover
            page.locator(".qv-object-filterpane", has_text="Departamento").locator(".folded-listbox").first.click(force=True)
            page.wait_for_timeout(2000)
            
            # Dump all clickable elements in the popover
            popover_elements = page.evaluate("""() => {
                // Find the popover container
                const container = document.querySelector('.listbox-popover-container') || document.querySelector('.folded-listbox');
                if (!container) return "Container not found";
                
                // Find all buttons, spans, svgs, a
                const clickables = container.querySelectorAll('button, span, svg, a, [role="button"]');
                return Array.from(clickables).map((el, i) => ({
                    index: i,
                    tag: el.tagName,
                    class: el.className,
                    text: el.innerText ? el.innerText.trim() : "",
                    title: el.getAttribute("title") || "",
                    html: el.outerHTML.slice(0, 150)
                }));
            }""")
            
            import pprint
            pprint.pprint(popover_elements)
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
