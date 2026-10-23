import os
from playwright.sync_api import sync_playwright

def run():
    screenshots_dir = 'docs/screenshots'
    os.makedirs(screenshots_dir, exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        
        # 1. Main Dashboard
        print("Navigating to Dashboard...")
        page.goto('http://localhost:5173/')
        page.wait_for_timeout(3000)  # wait for potential API calls
        page.screenshot(path=os.path.join(screenshots_dir, '01_dashboard.png'))
        print("Captured 01_dashboard.png")
        
        # We can try to navigate through the app if there are links/buttons
        # For a basic capture, we will try to fill the recommendation form
        
        print("Taking recommendation form screenshot...")
        # Since I don't know the exact UI, I will just capture the initial state.
        
        browser.close()

if __name__ == '__main__':
    run()
