import os
import json
import logging
from datetime import datetime
import time
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/lego_monitor_test.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create log directory if it doesn't exist
os.makedirs("logs", exist_ok=True)
os.makedirs("data", exist_ok=True)

# Load configuration
def load_config():
    try:
        with open('test_config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning("Test config file not found, using defaults")
        return {
            "lego_categories": [
                {
                    "name": "Architecture",
                    "url": "https://www.lego.com/en-us/themes/architecture"
                }
            ],
            "use_javascript": True,
            "max_pages": 1
        }

def test_playwright_scraping():
    """Test Playwright scraping functionality."""
    config = load_config()
    category = config["lego_categories"][0]
    
    logger.info(f"Testing scraper on {category['name']}: {category['url']}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            logger.info(f"Navigating to {category['url']}")
            page.goto(category['url'], wait_until="networkidle")
            
            # Wait a bit for any dynamic content to load
            page.wait_for_timeout(5000)
            
            # Get the page title
            title = page.title()
            logger.info(f"Page title: {title}")
            
            # Take a screenshot for verification
            page.screenshot(path="data/screenshot.png")
            logger.info("Screenshot saved to data/screenshot.png")
            
            # Examine the DOM structure to help find proper selectors
            # Find product containers using JavaScript (more reliable for dynamic sites)
            products_count = page.evaluate("""
                () => {
                    // Try different common selectors for product grids
                    const selectors = [
                        '.product-item', '.product-card', 
                        '[data-test="product-item"]', '.product',
                        '.product-grid-item', '.set-item', 
                        'article', '.ProductGridItem__Container', 
                        '[data-test="product-leaf"]'
                    ];
                    
                    for (const selector of selectors) {
                        const elements = document.querySelectorAll(selector);
                        if (elements.length > 0) {
                            console.log('Found products with selector:', selector);
                            return {selector: selector, count: elements.length};
                        }
                    }
                    
                    return {selector: null, count: 0};
                }
            """)
            
            logger.info(f"Found {products_count['count']} products with selector: {products_count['selector']}")
            
            # If products were found, extract some basic info
            if products_count['count'] > 0 and products_count['selector']:
                product_info = page.evaluate(f"""
                    () => {{
                        const selector = '{products_count['selector']}';
                        const products = document.querySelectorAll(selector);
                        const results = [];
                        
                        // Get the first 3 products
                        const limit = Math.min(3, products.length);
                        
                        for (let i = 0; i < limit; i++) {{
                            const product = products[i];
                            
                            // Try to find name
                            let name = '';
                            const nameSelectors = ['.product-name', '.name', 'h2', 'h3', '[data-test="product-title"]', '.title'];
                            for (const s of nameSelectors) {{
                                const el = product.querySelector(s);
                                if (el && el.textContent.trim()) {{
                                    name = el.textContent.trim();
                                    break;
                                }}
                            }}
                            
                            // Try to find price
                            let price = '';
                            const priceSelectors = ['.price', '.product-price', '[data-test="price"]', '[data-test="product-price"]'];
                            for (const s of priceSelectors) {{
                                const el = product.querySelector(s);
                                if (el && el.textContent.trim()) {{
                                    price = el.textContent.trim();
                                    break;
                                }}
                            }}
                            
                            results.push({{ name, price }});
                        }}
                        
                        return results;
                    }}
                """)
                
                for i, product in enumerate(product_info):
                    logger.info(f"Product {i+1}: {product.get('name', 'Unknown')} - {product.get('price', 'Unknown')}")
            
        except Exception as e:
            logger.error(f"Error during scraping: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
        finally:
            browser.close()

if __name__ == "__main__":
    logger.info("Starting test script")
    test_playwright_scraping()
    logger.info("Test script completed")
