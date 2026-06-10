import sys
from playwright.sync_api import sync_playwright

def main():
    print("Debugging SIEDCO select element...")
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
            
            # Inspect select element attributes
            data = page.evaluate("""() => {
                const sel = document.querySelector('select');
                if (!sel) return { error: "No select element found" };
                
                const attrs = {};
                for (let i = 0; i < sel.attributes.length; i++) {
                    const attr = sel.attributes[i];
                    attrs[attr.name] = attr.value;
                }
                
                // Check if angular is defined
                const hasAngular = typeof angular !== 'undefined';
                
                // Get options labels and values
                const opts = Array.from(sel.options).map(o => ({
                    index: o.index,
                    value: o.value,
                    label: o.label,
                    text: o.text
                }));
                
                return {
                    attrs: attrs,
                    hasAngular: hasAngular,
                    options: opts
                };
            }""")
            
            print("Select element details:")
            import pprint
            pprint.pprint(data)
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
