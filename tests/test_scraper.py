#!/usr/bin/env python3
"""
LEGO Scraper Test - Tests if the scraper can extract products from the URL specified in config.json
"""

import os
import json
import logging
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import sys
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/scraper_test.log"),
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
        with open('config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning("Config file not found, using defaults")
        return {
            "lego_categories": [
                {
                    "name": "Architecture",
                    "url": "https://lego.tr/themes/architecture"
                }
            ],
            "use_javascript": True,
            "max_pages": 1
        }

def scrape_lego_products():
    """Test the scraper's ability to extract LEGO products."""
    config = load_config()
    category = config["lego_categories"][0]
    
    logger.info(f"Testing scraper on {category['name']}: {category['url']}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            logger.info(f"Navigating to {category['url']}")
            page.goto(category['url'], wait_until="networkidle", timeout=60000)
            
            # Wait for any dynamic content to load
            page.wait_for_timeout(5000)
            
            # Get page title
            title = page.title()
            logger.info(f"Page title: {title}")
            
            # Get page content
            content = page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract product elements
            product_selector = config.get("product_selector", ".product-item")
            products = soup.select(product_selector)
            
            logger.info(f"Found {len(products)} products on the page")
            
            # Extract product details
            extracted_products = []
            for i, product in enumerate(products[:5]):  # Get first 5 products
                try:
                    # Extract product name
                    name_selector = config.get("name_selector", ".product-item__title, .product-name")
                    name_elem = product.select_one(name_selector)
                    name = name_elem.text.strip() if name_elem else "Unknown"
                    
                    # Extract price
                    price_selector = config.get("price_selector", ".product-price, .product-item__price")
                    price_elem = product.select_one(price_selector)
                    price = price_elem.text.strip() if price_elem else "Unknown"
                    
                    # Extract ID
                    id_selector = config.get("id_selector", ".product-id, [data-test='product-item-number']")
                    id_elem = product.select_one(id_selector)
                    product_id = id_elem.text.strip() if id_elem else "Unknown"
                    
                    # Extract image URL
                    image_selector = config.get("image_selector", ".product-item__image img, .product-image img")
                    image_elem = product.select_one(image_selector)
                    image_url = image_elem['src'] if image_elem and 'src' in image_elem.attrs else "Unknown"
                    
                    # Create product data
                    product_data = {
                        "name": name,
                        "price": price,
                        "id": product_id,
                        "image_url": image_url,
                        "category": category["name"]
                    }
                    
                    extracted_products.append(product_data)
                    logger.info(f"Product {i+1}: {name} - {price}")
                    
                except Exception as e:
                    logger.error(f"Error extracting product data: {str(e)}")
            
            # Save extracted products to file
            if extracted_products:
                with open('data/extracted_products.json', 'w', encoding='utf-8') as f:
                    json.dump(extracted_products, f, indent=2, ensure_ascii=False)
                logger.info(f"Saved {len(extracted_products)} products to data/extracted_products.json")
            
            return extracted_products
            
        except Exception as e:
            logger.error(f"Error during scraping: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return []
        finally:
            browser.close()

if __name__ == "__main__":
    logger.info("Starting LEGO scraper test")
    products = scrape_lego_products()
    if products:
        logger.info(f"Successfully extracted {len(products)} LEGO products")
    else:
        logger.error("Failed to extract any LEGO products")
    logger.info("LEGO scraper test completed")
