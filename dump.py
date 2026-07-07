import sys
from playwright.sync_api import sync_playwright

def aplicar_filtro_qlik(page, panel_titulo, valor_busqueda, valor_confirmar=None):
    if not valor_confirmar:
        valor_confirmar = valor_busqueda
        
    print(f"  Esperando a que el panel de {panel_titulo} esté visible...")
    panel = page.locator(".qv-object-filterpane", has_text=panel_titulo).first
    panel.wait_for(state="visible", timeout=60000)
    page.wait_for_timeout(1500)
    
    print(f"  Abriendo listbox de {panel_titulo}...")
    listbox = panel.locator(".folded-listbox").first
    listbox.click(force=True)
    page.wait_for_timeout(1500)
    
    print(f"  Buscando input de búsqueda visible...")
    search_input = page.locator("input[placeholder='Buscar en cuadro de lista']:visible").first
    search_input.wait_for(state="visible", timeout=15000)
    search_input.click()
    search_input.fill("")
    search_input.press_sequentially(valor_busqueda, delay=100)
    page.wait_for_timeout(2500)
    
    print(f"  Seleccionando la opción '{valor_confirmar}'...")
    item_selector = page.locator("[data-testid='listbox.item']", has_text=valor_confirmar).first
    item_selector.wait_for(state="visible", timeout=15000)
    item_selector.click(force=True)
    page.wait_for_timeout(1500)
    
    print(f"  Confirmando selección...")
    confirm_btn = page.locator(".qs-actions-confirm:visible, .qv-confirm-button:visible, button[title*='Confirmar']:visible, .actions-toolbar-confirm:visible").first
    confirm_btn.click(force=True)
    page.wait_for_timeout(3000)

def main():
    print("Iniciando prueba de extracción para Homicidios...")
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
            
            # Buscar opción por Angular Scope para obtener el label exacto
            option_label = page.evaluate("""() => {
                const sel = document.getElementById('tematicasCombo');
                if (!sel) return null;
                const scope = angular.element(sel).scope();
                if (!scope) return null;
                const kws = ["homicidio"];
                const optionObj = scope.tematicasCombo.find(item => {
                    const labelLower = item.label.toLowerCase();
                    return kws.every(kw => labelLower.includes(kw));
                });
                return optionObj ? optionObj.label : null;
            }""")
            print("Label exacto encontrado:", option_label)
            
            # Selección nativa con label exacto
            page.select_option("select#tematicasCombo", label=option_label)
            page.select_option("select[id$='osCombo']", label="2026")
            
            # Force AngularJS model sync by dispatching events
            page.evaluate("""() => {
                const selectTematica = document.getElementById('tematicasCombo');
                const selectAnio = document.querySelector("select[id$='osCombo']");
                if (selectTematica) {
                    selectTematica.dispatchEvent(new Event('change', { bubbles: true }));
                    selectTematica.dispatchEvent(new Event('input', { bubbles: true }));
                }
                if (selectAnio) {
                    selectAnio.dispatchEvent(new Event('change', { bubbles: true }));
                    selectAnio.dispatchEvent(new Event('input', { bubbles: true }));
                }
            }""")
            page.wait_for_timeout(2000)
            
            # Entrar
            page.locator(".btn-enter").evaluate("el => el.removeAttribute('disabled')")
            page.locator(".btn-enter").first.click()
            
            # Esperar a que cargue
            page.locator(".qv-object-filterpane", has_text="Departamento").first.wait_for(state="visible", timeout=60000)
            page.wait_for_timeout(3000)
            
            # Aplicar filtros
            aplicar_filtro_qlik(page, "Departamento", "VALLE")
            aplicar_filtro_qlik(page, "Municipio", "JAMUNDI", "JAMUNDÍ")
            
            print("Esperando 10 segundos para actualizar...")
            page.wait_for_timeout(10000)
            
            body_text = page.locator("body").inner_text()
            print("--- BODY TEXT EXTRACTED ---")
            print(body_text[:1500])
            print("---------------------------")
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()

