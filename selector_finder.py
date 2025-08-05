#!/usr/bin/env python3
"""
LEGO Selector Finder - Analyzes the page to find the correct selectors
"""

import os
import json
import logging
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import sys
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/selector_finder.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create log directory if it doesn't exist
os.makedirs("logs", exist_ok=True)
os.makedirs("data", exist_ok=True)

def find_selectors():
    """Find the correct selectors for the LEGO page."""
    url = "https://lego.tr/themes/architecture"
    logger.info(f"Analyzing page: {url}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            logger.info(f"Navigating to {url}")
            page.goto(url, wait_until="networkidle", timeout=60000)
            
            # Wait for any dynamic content to load
            page.wait_for_timeout(5000)
            
            # Use JavaScript to identify potential selectors
            selectors = page.evaluate("""
                () => {
                    // Find product containers
                    const productContainers = document.querySelectorAll('.product-item');
                    if (productContainers.length === 0) return { error: 'No product containers found' };
                    
                    // Get a sample product
                    const sampleProduct = productContainers[0];
                    
                    // Find all meaningful elements in the product
                    const results = {
                        container: '.product-item',
                        products_found: productContainers.length,
                        selectors: {}
                    };
                    
                    // Function to find potential selectors for a specific type of data
                    const findPotentialSelectors = (element, attrNames) => {
                        if (!element) return [];
                        
                        const selectors = [];
                        
                        // Try to find by classes
                        if (element.className) {
                            const classNames = element.className.split(' ').filter(c => c.trim());
                            if (classNames.length > 0) {
                                selectors.push('.' + classNames.join('.'));
                            }
                        }
                        
                        // Try to find by attribute (data-test, etc)
                        for (const attr of attrNames) {
                            if (element.hasAttribute(attr)) {
                                selectors.push(`[${attr}="${element.getAttribute(attr)}"]`);
                            }
                        }
                        
                        // Try by tag name and position
                        selectors.push(element.tagName.toLowerCase());
                        
                        return selectors;
                    };
                    
                    // Try to find the title/name
                    const titleElement = 
                        sampleProduct.querySelector('h3') || 
                        sampleProduct.querySelector('h2') || 
                        sampleProduct.querySelector('.product-name') ||
                        sampleProduct.querySelector('[data-test="product-title"]');
                    
                    if (titleElement) {
                        results.selectors.title = {
                            potential_selectors: findPotentialSelectors(titleElement, ['data-test', 'id']),
                            text_content: titleElement.textContent.trim()
                        };
                    }
                    
                    // Try to find the price
                    const priceElement = 
                        sampleProduct.querySelector('.price') || 
                        sampleProduct.querySelector('.product-price') || 
                        sampleProduct.querySelector('[data-test="price"]');
                    
                    if (priceElement) {
                        results.selectors.price = {
                            potential_selectors: findPotentialSelectors(priceElement, ['data-test', 'id']),
                            text_content: priceElement.textContent.trim()
                        };
                    }
                    
                    // Try to find the product ID
                    const idElement = 
                        sampleProduct.querySelector('.product-id') || 
                        sampleProduct.querySelector('[data-test="product-item-number"]') ||
                        sampleProduct.querySelector('[data-element="product-number"]');
                    
                    if (idElement) {
                        results.selectors.id = {
                            potential_selectors: findPotentialSelectors(idElement, ['data-test', 'data-element', 'id']),
                            text_content: idElement.textContent.trim()
                        };
                    }
                    
                    // Try to find the image
                    const imageElement = sampleProduct.querySelector('img');
                    
                    if (imageElement) {
                        results.selectors.image = {
                            potential_selectors: findPotentialSelectors(imageElement, ['data-test', 'id']),
                            src: imageElement.src,
                            alt: imageElement.alt
                        };
                    }
                    
                    // Try to find additional product information
                    const titleLinkElement = 
                        sampleProduct.querySelector('a[href*="products"]') || 
                        sampleProduct.querySelector('a[title]');
                    
                    if (titleLinkElement) {
                        results.selectors.title_link = {
                            potential_selectors: findPotentialSelectors(titleLinkElement, ['data-test', 'id']),
                            href: titleLinkElement.href,
                            text_content: titleLinkElement.textContent.trim()
                        };
                    }
                    
                    return results;
                }
            """)
            
            logger.info(f"Found selectors: {json.dumps(selectors, indent=2)}")
            
            # Save selectors to file
            with open('data/found_selectors.json', 'w', encoding='utf-8') as f:
                json.dump(selectors, f, indent=2, ensure_ascii=False)
            logger.info("Saved selectors to data/found_selectors.json")
            
            # Create recommended config
            recommended_config = {
                "lego_categories": [
                    {
                        "name": "Architecture",
                        "url": "https://lego.tr/themes/architecture"
                    }
                ],
                "scrape_interval_hours": 6,
                "product_selector": selectors.get("container", ".product-item"),
                "price_selector": ", ".join(selectors.get("selectors", {}).get("price", {}).get("potential_selectors", [".price"]))
            }
            
            # Add title selector if found
            if "title" in selectors.get("selectors", {}):
                recommended_config["name_selector"] = ", ".join(selectors.get("selectors", {}).get("title", {}).get("potential_selectors", []))
            elif "title_link" in selectors.get("selectors", {}):
                recommended_config["name_selector"] = ", ".join(selectors.get("selectors", {}).get("title_link", {}).get("potential_selectors", []))
            
            # Add id selector if found
            if "id" in selectors.get("selectors", {}):
                recommended_config["id_selector"] = ", ".join(selectors.get("selectors", {}).get("id", {}).get("potential_selectors", []))
            
            # Add image selector if found
            if "image" in selectors.get("selectors", {}):
                recommended_config["image_selector"] = ", ".join(selectors.get("selectors", {}).get("image", {}).get("potential_selectors", ["img"]))
            
            # Add other config fields
            recommended_config["description_selector"] = ".product-description"
            recommended_config["ollama_host"] = "localhost"
            recommended_config["ollama_port"] = "11434"
            recommended_config["ollama_model"] = "llama3"
            recommended_config["price_threshold_percent"] = 5.0
            recommended_config["use_javascript"] = True
            recommended_config["max_pages"] = 5
            
            # Save recommended config
            with open('data/recommended_config.json', 'w', encoding='utf-8') as f:
                json.dump(recommended_config, f, indent=2, ensure_ascii=False)
            logger.info("Saved recommended config to data/recommended_config.json")
            
            return selectors
            
        except Exception as e:
            logger.error(f"Error finding selectors: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
        finally:
            browser.close()

if __name__ == "__main__":
    logger.info("Starting selector finder")
    selectors = find_selectors()
    if selectors:
        logger.info("Successfully found potential selectors")
    else:
        logger.error("Failed to find selectors")
    logger.info("Selector finder completed")
