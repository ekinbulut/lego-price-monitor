"""
A dedicated test script for the LEGO price monitor scraper functionality.
This script tests the basic scraping without the CrewAI framework.
"""

import json
import os
import sys
import time
from playwright.sync_api import sync_playwright
import logging
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_config():
    """Load the configuration from config.json"""
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
            logger.info("✅ Config loaded successfully")
            return config
    except json.JSONDecodeError as e:
        logger.error(f"❌ Error loading config: {e}")
        sys.exit(1)
    except FileNotFoundError:
        logger.error("❌ config.json not found")
        sys.exit(1)

def scrape_lego_products(url, config, max_products=5):
    """Scrape LEGO products from the given URL"""
    logger.info(f"Scraping products from: {url}")
    
    # Get selectors from config
    product_selector = config.get('product_selector', '.product-item')
    name_selector = config.get('name_selector', 'img[alt]')
    price_selector = config.get('price_selector', '.product-price')
    id_selector = config.get('id_selector', 'img[alt]')
    image_selector = config.get('image_selector', '.lazyloaded')
    
    products = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            # Navigate to the page
            logger.info(f"Navigating to {url}...")
            page.goto(url, wait_until='networkidle')
            time.sleep(2)  # Allow any JavaScript to execute
            
            # Take a screenshot for debugging
            page.screenshot(path="debug_screenshot.png")
            logger.info("Screenshot saved to debug_screenshot.png")
            
            # Extract products
            product_elements = page.query_selector_all(product_selector)
            logger.info(f"Found {len(product_elements)} products")
            
            # Process limited number of products
            for i, product_elem in enumerate(product_elements[:max_products]):
                product = {}
                
                # Extract product name
                name_elem = product_elem.query_selector(name_selector)
                if name_elem and name_elem.get_attribute('alt'):
                    product['name'] = name_elem.get_attribute('alt')
                    # Clean up the name if it contains product ID
                    if '-' in product['name']:
                        product['name'] = product['name'].split('-')[0].strip()
                else:
                    product['name'] = "Unknown"
                
                # Extract product ID
                id_elem = product_elem.query_selector(id_selector)
                if id_elem and id_elem.get_attribute('alt'):
                    alt_text = id_elem.get_attribute('alt')
                    # Try to extract the ID from the alt text using regex
                    id_match = re.search(r'(\d{5})', alt_text)
                    if id_match:
                        product['id'] = id_match.group(1)
                    else:
                        product['id'] = "Unknown"
                else:
                    product['id'] = "Unknown"
                
                # Extract price
                price_elem = product_elem.query_selector(price_selector)
                if price_elem:
                    product['price'] = price_elem.text_content().strip()
                else:
                    product['price'] = "Unknown"
                
                # Extract image URL
                img_elem = product_elem.query_selector(image_selector)
                if img_elem and img_elem.get_attribute('src'):
                    product['image_url'] = img_elem.get_attribute('src')
                else:
                    product['image_url'] = "Unknown"
                
                products.append(product)
                logger.info(f"Product {i+1}: {product['name']} - {product['price']} - {product['id']}")
            
        except Exception as e:
            logger.error(f"Error during scraping: {e}")
        finally:
            browser.close()
    
    return products

def save_products_to_file(products, category_name):
    """Save scraped products to a JSON file"""
    filename = f"data/{category_name.lower()}_products.json"
    os.makedirs("data", exist_ok=True)
    
    try:
        with open(filename, 'w') as f:
            json.dump(products, f, indent=2)
        logger.info(f"Saved {len(products)} products to {filename}")
    except Exception as e:
        logger.error(f"Error saving products to file: {e}")

def main():
    """Main function to run the test"""
    logger.info("=== LEGO Price Monitor Scraper Test ===")
    
    # Load configuration
    config = load_config()
    
    # Get categories to scrape
    categories = config.get('lego_categories', [])
    
    if not categories:
        logger.error("No LEGO categories found in config")
        return
    
    # Scrape each category
    for category in categories:
        category_name = category.get('name', 'Unknown')
        url = category.get('url', '')
        
        if not url:
            logger.warning(f"No URL provided for category: {category_name}")
            continue
        
        logger.info(f"Processing category: {category_name}")
        products = scrape_lego_products(url, config)
        
        if products:
            save_products_to_file(products, category_name)
    
    logger.info("=== Scraping Test Completed ===")

if __name__ == "__main__":
    main()
