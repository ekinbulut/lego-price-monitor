#!/usr/bin/env python3
"""
URL Test Script - Tests if a specific LEGO URL is accessible and can be scraped
"""

import logging
import sys
import os
import time
from playwright.sync_api import sync_playwright
import requests
from urllib.parse import urlparse
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/url_test.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create log directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

def test_url(url):
    """Test if a URL is accessible using requests."""
    logger.info(f"Testing URL accessibility with requests: {url}")
    
    try:
        response = requests.get(url, timeout=10)
        logger.info(f"Response status code: {response.status_code}")
        
        if response.status_code == 200:
            logger.info("URL is accessible with requests!")
            return True
        else:
            logger.warning(f"URL returned non-200 status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Error accessing URL with requests: {str(e)}")
        return False

def check_url_redirect(url):
    """Check if URL redirects to another location."""
    logger.info(f"Checking for redirects: {url}")
    
    try:
        response = requests.get(url, allow_redirects=False, timeout=10)
        
        if response.status_code in (301, 302, 303, 307, 308):
            redirect_url = response.headers.get('Location')
            logger.info(f"URL redirects to: {redirect_url}")
            
            # If it's a relative URL, make it absolute
            if redirect_url and not redirect_url.startswith('http'):
                parsed_url = urlparse(url)
                base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
                redirect_url = f"{base_url}{redirect_url}"
                logger.info(f"Absolute redirect URL: {redirect_url}")
            
            return redirect_url
        
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error checking redirects: {str(e)}")
        return None

def test_url_with_playwright(url):
    """Test if a URL is accessible using Playwright."""
    logger.info(f"Testing URL with Playwright: {url}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            logger.info(f"Navigating to: {url}")
            response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            if response:
                logger.info(f"Playwright response status: {response.status}")
                
                # Take a screenshot for verification
                screenshot_path = "data/url_test_screenshot.png"
                page.screenshot(path=screenshot_path)
                logger.info(f"Screenshot saved to: {screenshot_path}")
                
                # Get the final URL (after any client-side redirects)
                final_url = page.url
                logger.info(f"Final URL after any client-side redirects: {final_url}")
                
                # Get page title
                title = page.title()
                logger.info(f"Page title: {title}")
                
                # Check for common LEGO page elements
                page.wait_for_timeout(5000)  # Wait for any dynamic content to load
                
                # Try to detect LEGO products on the page
                product_info = page.evaluate("""
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
                                return {
                                    selector: selector, 
                                    count: elements.length
                                };
                            }
                        }
                        
                        return {selector: null, count: 0};
                    }
                """)
                
                logger.info(f"Product detection: {product_info}")
                
                html_content = page.content()
                with open("data/page_content.html", "w", encoding="utf-8") as f:
                    f.write(html_content)
                logger.info("Saved page content to data/page_content.html")
                
                return True
            else:
                logger.error("No response received from Playwright")
                return False
                
        except Exception as e:
            logger.error(f"Error accessing URL with Playwright: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
        finally:
            browser.close()

def suggest_alternative_urls(url):
    """Suggest alternative URLs based on the original URL."""
    logger.info(f"Suggesting alternatives for: {url}")
    
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    path = parsed_url.path
    
    alternatives = []
    
    # Check if it's a country-specific domain
    if domain == "lego.tr":
        # Try official LEGO domain
        alternatives.append(f"https://www.lego.com/en-us{path}")
        # Try other possible formats
        alternatives.append(f"https://www.lego.com/tr-tr{path}")
        alternatives.append(f"https://www.lego.com/tr{path}")
    
    logger.info(f"Alternative URLs to try: {alternatives}")
    return alternatives

def main():
    # Create data directory if it doesn't exist
    os.makedirs("data", exist_ok=True)
    
    # URL from config
    url = "https://lego.tr/themes/architecture"
    logger.info(f"Starting URL test for: {url}")
    
    # First, test with requests
    is_accessible = test_url(url)
    
    # Check for redirects
    redirect_url = check_url_redirect(url)
    
    # Test with Playwright
    is_accessible_playwright = test_url_with_playwright(url)
    
    # If both tests fail, suggest alternatives
    if not is_accessible and not is_accessible_playwright:
        logger.warning("URL is not accessible with either method. Suggesting alternatives.")
        alternative_urls = suggest_alternative_urls(url)
        
        results = {
            "original_url": url,
            "is_accessible": is_accessible,
            "redirect_url": redirect_url,
            "is_accessible_playwright": is_accessible_playwright,
            "alternative_urls": []
        }
        
        # Test alternative URLs
        for alt_url in alternative_urls:
            logger.info(f"Testing alternative URL: {alt_url}")
            alt_accessible = test_url(alt_url)
            alt_accessible_playwright = test_url_with_playwright(alt_url)
            
            results["alternative_urls"].append({
                "url": alt_url,
                "is_accessible": alt_accessible,
                "is_accessible_playwright": alt_accessible_playwright
            })
        
        # Save test results
        with open("data/url_test_results.json", "w") as f:
            json.dump(results, f, indent=2)
        logger.info("Test results saved to data/url_test_results.json")
    
    logger.info("URL test completed")

if __name__ == "__main__":
    main()
