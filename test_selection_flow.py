import sys
import time
from playwright.sync_api import sync_playwright

def main():
    print("Testing selection flow in Qlik Sense...")
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
            
            # Click the folded-listbox of Departamento
            print("Abriendo popover de Departamento...")
            page.locator(".qv-object-filterpane", has_text="Departamento").locator(".folded-listbox").first.click(force=True)
            page.wait_for_timeout(2000)
            
            # Locate search input and fill it
            print("Buscando input de búsqueda...")
            search_input = page.locator("input[placeholder='Buscar en cuadro de lista']").first
            search_input.fill("VALLE")
            page.wait_for_timeout(2000)
            
            # Dump the list items
            elements = page.evaluate("""() => {
                // Find listbox items or rows
                const items = document.querySelectorAll('.qv-listbox-row, li, [role="option"], .q-list-item');
                return Array.from(items).map((el, i) => ({
                    index: i,
                    tag: el.tagName,
                    class: el.className,
                    text: el.innerText ? el.innerText.trim() : "",
                    title: el.getAttribute("title") || ""
                })).filter(el => el.text && el.text.length < 80).slice(0, 20);
            }""")
            
            print("\n--- Listbox Search Results DOM ---")
            for el in elements:
                print(f"[{el['tag']}] text='{el['text']}', class='{el['class']}', title='{el['title']}'")
            print("----------------------------------\n")
            
            # Dump confirmation buttons
            confirm_buttons = page.evaluate("""() => {
                const buttons = document.querySelectorAll('button, a, span, .confirm, .icon-tick, [title*="Confirm"]');
                return Array.from(buttons).map((el, i) => ({
                    index: i,
                    tag: el.tagName,
                    class: el.className,
                    text: el.innerText ? el.innerText.strip : el.innerText,
                    title: el.getAttribute("title") || ""
                })).filter(el => el.title || (el.text && el.text.length < 50)).slice(0, 30);
            }""")
            
            print("\n--- Confirmation Buttons ---")
            for el in confirm_buttons:
                print(f"[{el['tag']}] text='{el['text']}', class='{el['class']}', title='{el['title']}'")
            print("----------------------------\n")
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
