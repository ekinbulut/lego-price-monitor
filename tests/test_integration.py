"""
Test script to verify the updated configuration with minimal dependencies.
This script directly tests the scraping functionality without relying on the CrewAI tools.
"""

import json
import os
import sys
from playwright.sync_api import sync_playwright
import re
import time

def load_config():
    """Load the configuration from config.json"""
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
            print("✅ Config loaded successfully")
            return config
    except json.JSONDecodeError as e:
        print(f"❌ Error loading config: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("❌ config.json not found")
        sys.exit(1)

def test_scraping(config):
    """Test the scraping functionality with the updated selectors"""
    print("\n--- Testing scraping with updated selectors ---")
    category = config['lego_categories'][0]
    print(f"Testing category: {category['name']} - {category['url']}")
    
    # Get selectors from config
    use_js = config.get('use_javascript', True)
    product_selector = config.get('product_selector', '.product-item')
    name_selector = config.get('name_selector', 'img[alt]')
    price_selector = config.get('price_selector', '.product-price')
    id_selector = config.get('id_selector', 'img[alt]')
    image_selector = config.get('image_selector', '.lazyloaded')
    
    print(f"Using selectors:")
    print(f"  Product: {product_selector}")
    print(f"  Name: {name_selector}")
    print(f"  Price: {price_selector}")
    print(f"  ID: {id_selector}")
    print(f"  Image: {image_selector}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            # Navigate to the page
            print(f"\nNavigating to {category['url']}...")
            page.goto(category['url'], wait_until='networkidle')
            time.sleep(2)  # Allow any JavaScript to execute
            
            # Extract products
            products = page.query_selector_all(product_selector)
            print(f"Found {len(products)} products")
            
            if len(products) == 0:
                print("❌ No products found. Selector might be incorrect.")
                return
            
            print("\nProduct details:")
            # Process first 3 products
            for i, product in enumerate(products[:3]):
                # Extract product name
                name_elem = product.query_selector(name_selector)
                name = name_elem.get_attribute('alt') if name_elem else "Unknown"
                
                # Clean up the name if it contains product ID
                if name and '-' in name:
                    name = name.split('-')[0].strip()
                
                # Extract product ID
                id_elem = product.query_selector(id_selector)
                product_id = "Unknown"
                if id_elem and id_elem.get_attribute('alt'):
                    alt_text = id_elem.get_attribute('alt')
                    # Try to extract the ID from the alt text using regex
                    id_match = re.search(r'(\d{5})', alt_text)
                    if id_match:
                        product_id = id_match.group(1)
                
                # Extract price
                price_elem = product.query_selector(price_selector)
                price = price_elem.text_content().strip() if price_elem else "Unknown"
                
                # Extract image URL
                img_elem = product.query_selector(image_selector)
                img_url = img_elem.get_attribute('src') if img_elem else "Unknown"
                
                print(f"Product {i+1}:")
                print(f"  Name: {name}")
                print(f"  ID: {product_id}")
                print(f"  Price: {price}")
                print(f"  Image: {img_url}")
                print()
            
            print("✅ Scraping test completed successfully")
        except Exception as e:
            print(f"❌ Error during scraping: {e}")
        finally:
            browser.close()

def test_main_file():
    """Test if main.py can be imported without errors"""
    print("\n--- Testing main.py import ---")
    try:
        # Just check if it can be imported
        import main
        print("✅ main.py imported successfully")
    except Exception as e:
        print(f"❌ Error importing main.py: {e}")

def main():
    """Main test function"""
    print("=== LEGO Price Monitor Integration Test ===")
    
    # Load configuration
    config = load_config()
    
    # Test scraping with our config
    test_scraping(config)
    
    # Test if main.py can be imported
    test_main_file()
    
    print("\n=== Test Completed ===")

if __name__ == "__main__":
    main()
