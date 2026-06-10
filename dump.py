import sys
from playwright.sync_api import sync_playwright

def main():
    print("Dumping SIEDCO landing page elements...")
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
            
            # Print page text
            print("--- TEXT CONTENT ---")
            print(page.locator("body").inner_text()[:600])
            print("--------------------\n")
            
            # Find all buttons and links
            print("--- BUTTONS & LINKS ---")
            buttons = page.query_selector_all("button")
            for i, btn in enumerate(buttons):
                print(f"Button {i}: Text='{btn.inner_text().strip()}', Class='{btn.get_attribute('class')}'")
                
            links = page.query_selector_all("a")
            for i, l in enumerate(links):
                print(f"Link {i}: Text='{l.inner_text().strip()}', Href='{l.get_attribute('href')}'")
                
            divs = page.query_selector_all("div[role='button']")
            for i, d in enumerate(divs):
                print(f"DivButton {i}: Text='{d.inner_text().strip()}'")
            print("-----------------------\n")
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
