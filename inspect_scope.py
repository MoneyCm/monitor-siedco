import sys
from playwright.sync_api import sync_playwright

def main():
    print("Inspecting SIEDCO AngularJS scope...")
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
            
            # Inspect the scope keys
            scope_data = page.evaluate("""() => {
                const sel = document.getElementById('tematicasCombo');
                if (!sel) return { error: "No select element found" };
                const scope = angular.element(sel).scope();
                if (!scope) return { error: "No scope found" };
                
                // Extract keys and values (ignoring functions and internal Angular variables starting with $)
                const keys = {};
                for (let k in scope) {
                    if (k.startsWith('$') || typeof scope[k] === 'function') continue;
                    try {
                        keys[k] = JSON.parse(JSON.stringify(scope[k]));
                    } catch (e) {
                        keys[k] = "Circular or Unserializable: " + typeof scope[k];
                    }
                }
                
                // Get the text of getSeleccionesCombos function
                const fnText = scope.getSeleccionesCombos ? scope.getSeleccionesCombos.toString() : "Not found";
                const enterFnText = scope.enterDashboard ? scope.enterDashboard.toString() : "Not found";
                
                return {
                    scopeData: keys,
                    getSeleccionesCombosText: fnText,
                    enterDashboardText: enterFnText
                };
            }""")
            
            import pprint
            print("\nScope Variables:")
            pprint.pprint(scope_data["scopeData"])
            print("\ngetSeleccionesCombos Function Text:")
            print(scope_data["getSeleccionesCombosText"])
            print("\nenterDashboard Function Text:")
            print(scope_data["enterDashboardText"])
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
