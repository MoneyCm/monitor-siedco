import sys
from playwright.sync_api import sync_playwright

def main():
    print("Finding AMAZONAS element in SIEDCO listbox...")
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
            
            # Locate element containing "AMAZONAS"
            amazonas_data = page.evaluate("""() => {
                const results = [];
                // Search for any element containing the text "AMAZONAS"
                const allElements = document.querySelectorAll('*');
                allElements.forEach(el => {
                    if (el.innerText && el.innerText.trim() === 'AMAZONAS') {
                        // Get its path or details
                        const classes = el.className || "";
                        const tag = el.tagName;
                        const parentTag = el.parentElement ? el.parentElement.tagName : "";
                        const parentClass = el.parentElement ? el.parentElement.className : "";
                        results.push({
                            tag: tag,
                            class: classes,
                            parentTag: parentTag,
                            parentClass: parentClass,
                            html: el.outerHTML.slice(0, 150)
                        });
                    }
                });
                return results;
            }""")
            
            import pprint
            pprint.pprint(amazonas_data)
            
            # Let's also see if we can find elements with the checkmark character "✓"
            checkmark_data = page.evaluate("""() => {
                const results = [];
                const allElements = document.querySelectorAll('*');
                allElements.forEach(el => {
                    // Check if it contains checkmark and is small or a button/icon
                    if (el.innerText && (el.innerText.trim() === '✓' || el.innerText.trim() === 'confirm' || el.innerText.trim() === 'check')) {
                        results.push({
                            tag: el.tagName,
                            class: el.className,
                            parentTag: el.parentElement ? el.parentElement.tagName : "",
                            parentClass: el.parentElement ? el.parentElement.className : "",
                            html: el.outerHTML.slice(0, 150)
                        });
                    }
                });
                return results;
            }""")
            print("\nCheckmark elements:")
            pprint.pprint(checkmark_data)
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
