import sys
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

def render(in_path, out_path):
    """Isolated rendering function to be run in a separate process."""
    with sync_playwright() as p:
        # Launch browser in a fresh process
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Load the HTML file
        # We use an absolute file path to ensure Chromium finds it
        abs_in_path = Path(in_path).absolute().as_uri()
        page.goto(abs_in_path, wait_until="networkidle")
        
        # Generate the professional PDF
        page.pdf(
            path=out_path,
            format="A4",
            print_background=True,
            margin={"top": "1.25cm", "bottom": "1.25cm", "left": "1.25cm", "right": "1.25cm"}
        )
        
        browser.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python render_helper.py <input_html> <output_pdf>")
        sys.exit(1)
    
    render(sys.argv[1], sys.argv[2])
