from langchain.tools import BaseTool
from typing import Optional, Type, List, Dict, Any
from pydantic import BaseModel, Field
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import time
import random
import logging
import re
import json
import os

logger = logging.getLogger(__name__)

class LegoWebNavigationInput(BaseModel):
    url: str = Field(..., description="The URL of the LEGO website to navigate to")
    category_name: str = Field("Uncategorized", description="The name of the LEGO category being scraped")
    use_javascript: bool = Field(True, description="Whether to use a headless browser for JavaScript rendering")
    pagination_selector: Optional[str] = Field(None, description="CSS selector for pagination links, if any")
    max_pages: int = Field(5, description="Maximum number of pages to scrape")

class LegoWebNavigationTool(BaseTool):
    name: str = "lego_web_navigation_tool"
    description: str = "Navigate to LEGO website and handle pagination. Returns HTML content."
    args_schema: Type[BaseModel] = LegoWebNavigationInput
    
    def _run(
        self, 
        url: str, 
        category_name: str = "Uncategorized",
        use_javascript: bool = True, 
        pagination_selector: Optional[str] = None, 
        max_pages: int = 5
    ) -> str:
        logger.info(f"Navigating to LEGO {category_name} category: {url} with max_pages={max_pages}")
        all_html = []
        
        # For LEGO website, we should always use JavaScript rendering as it's a heavily JS-based site
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
                viewport={"width": 1920, "height": 1080}
            )
            
            # Add cookie consent handling
            page = context.new_page()
            page.goto(url)
            
            # Handle cookie consent if it appears (common on European LEGO sites)
            try:
                # Wait for cookie dialog to appear
                cookie_accept_button = page.wait_for_selector(
                    "button[data-test='cookie-accept-all'], .cookie-banner__button--accept", 
                    timeout=5000
                )
                if cookie_accept_button:
                    cookie_accept_button.click()
                    logger.info(f"Accepted cookies on LEGO {category_name} page")
                    # Wait for page to reload after cookie acceptance
                    page.wait_for_load_state("networkidle")
            except Exception as e:
                logger.info(f"No cookie consent dialog found or error handling it: {e}")
            
            # Wait for products to load
            try:
                page.wait_for_selector(".product-item, .product-card, .ProductGridstyles__StyledWrapper-sc-*", timeout=10000)
            except Exception as e:
                logger.warning(f"Timeout waiting for product elements on {category_name} page: {e}")
            
            # Capture the initial page
            all_html.append(page.content())
            
            # Determine pagination strategy
            # LEGO sites typically use "Load More" buttons or traditional pagination
            current_page = 1
            
            while current_page < max_pages:
                # Try to find "Load More" button first (common on LEGO sites)
                load_more_button = None
                try:
                    load_more_button = page.query_selector(
                        "button[data-test='load-more-button'], .load-more-button, .LoadMorestyles__Button-*"
                    )
                except:
                    pass
                
                if load_more_button:
                    try:
                        load_more_button.click()
                        logger.info(f"Clicked 'Load More' button on {category_name} page")
                        # Wait for new products to load
                        page.wait_for_load_state("networkidle")
                        # Wait a bit more to ensure products are rendered
                        time.sleep(2)
                        all_html.append(page.content())
                        current_page += 1
                    except Exception as e:
                        logger.error(f"Error clicking 'Load More' button on {category_name} page: {e}")
                        break
                else:
                    # Try traditional pagination (less common on modern LEGO sites)
                    try:
                        next_button = page.query_selector(
                            "a[data-test='pagination-next'], .pagination__next, .Paginationstyles__NextButton-*"
                        )
                        if next_button:
                            next_button.click()
                            logger.info(f"Clicked pagination 'Next' button on {category_name} page")
                            page.wait_for_load_state("networkidle")
                            all_html.append(page.content())
                            current_page += 1
                        else:
                            logger.info(f"No more pagination buttons found on {category_name} page")
                            break
                    except Exception as e:
                        logger.error(f"Error with pagination on {category_name} page: {e}")
                        break
                
                # Random delay to avoid detection
                time.sleep(random.uniform(1, 3))
            
            browser.close()
        
        # Return HTML content with category metadata
        result = {
            "category_name": category_name,
            "url": url,
            "pages_scraped": len(all_html),
            "html_content": "\n".join(all_html)
        }
        
        return json.dumps(result)

class LegoDataExtractionInput(BaseModel):
    category_data: str = Field(..., description="JSON string containing category metadata and HTML content")
    product_selector: str = Field(..., description="CSS selector to identify LEGO product elements")
    name_selector: Optional[str] = Field(None, description="CSS selector for LEGO product name")
    price_selector: Optional[str] = Field(None, description="CSS selector for LEGO product price")
    id_selector: Optional[str] = Field(None, description="CSS selector for LEGO product ID/set number")
    image_selector: Optional[str] = Field(None, description="CSS selector for LEGO product image")
    description_selector: Optional[str] = Field(None, description="CSS selector for LEGO product description")

class LegoDataExtractionTool(BaseTool):
    name: str = "lego_data_extraction_tool"
    description: str = "Extract LEGO product data from HTML content using BeautifulSoup or Playwright."
    args_schema: Type[BaseModel] = LegoDataExtractionInput
    
    def _run(
        self, 
        category_data: str, 
        product_selector: str,
        name_selector: Optional[str] = None,
        price_selector: Optional[str] = None,
        id_selector: Optional[str] = None,
        image_selector: Optional[str] = None,
        description_selector: Optional[str] = None
    ) -> str:
        try:
            # Parse the category data
            category_info = json.loads(category_data)
            category_name = category_info.get("category_name", "Uncategorized")
            url = category_info.get("url", "")
            html_content = category_info.get("html_content", "")
            
            logger.info(f"Extracting product data from LEGO {category_name} category")
            
            soup = BeautifulSoup(html_content, "html.parser")
            products = []
            seen_ids = set()  # To avoid duplicates from multiple pages
            
            product_elements = soup.select(product_selector)
            logger.info(f"Found {len(product_elements)} LEGO product elements in {category_name} category")
            
            for product_element in product_elements:
                product = {
                    "category": category_name,
                    "category_url": url
                }
                
                # Extract product name
                if name_selector:
                    name_element = product_element.select_one(name_selector)
                    if name_element:
                        product["name"] = name_element.text.strip()
                
                # Try alternative methods to find name if selector didn't work
                if "name" not in product:
                    # Try common attribute patterns for LEGO sites
                    for element in product_element.select("[data-test='product-title'], [data-product-name], .name, .title"):
                        if element.text.strip():
                            product["name"] = element.text.strip()
                            break
                
                # Extract price
                if price_selector:
                    price_element = product_element.select_one(price_selector)
                    if price_element:
                        price_text = price_element.text.strip()
                        # Clean price (remove currency symbols, etc.)
                        product["price"] = self._clean_price(price_text)
                        product["price_raw"] = price_text
                        product["currency"] = self._extract_currency(price_text)
                
                # Try alternative methods to find price
                if "price" not in product:
                    # Try common price patterns for LEGO sites
                    for element in product_element.select("[data-test='product-price'], [data-product-price], .price"):
                        if element.text.strip():
                            price_text = element.text.strip()
                            product["price"] = self._clean_price(price_text)
                            product["price_raw"] = price_text
                            product["currency"] = self._extract_currency(price_text)
                            break
                
                # Extract product ID (set number for LEGO)
                if id_selector:
                    id_element = product_element.select_one(id_selector)
                    if id_element:
                        product["id"] = id_element.text.strip()
                
                # Try to extract set number from various attributes and patterns
                if "id" not in product:
                    # Look for set number in data attributes
                    for attr in product_element.attrs:
                        if "item" in attr.lower() or "product" in attr.lower() or "set" in attr.lower():
                            product["id"] = product_element[attr]
                            break
                    
                    # Try to extract from URL
                    link_element = product_element.select_one("a[href*='/products/'], a[href*='/product/']")
                    if link_element and link_element.has_attr("href"):
                        href = link_element["href"]
                        # LEGO product URLs often contain the set number
                        set_match = re.search(r'/products?/([a-zA-Z0-9-]+)', href)
                        if set_match:
                            product["id"] = set_match.group(1)
                    
                    # Check for product number in text
                    for element in product_element.select("[data-test='product-number'], .product-number, .set-number"):
                        if element.text.strip():
                            # Extract digits from text like "Item #10997" or "Set 10997"
                            set_match = re.search(r'(\d+)', element.text)
                            if set_match:
                                product["id"] = set_match.group(1)
                                break
                
                # Extract image URL
                if image_selector:
                    image_element = product_element.select_one(image_selector)
                    if image_element and image_element.has_attr("src"):
                        product["image_url"] = image_element["src"]
                    elif image_element and image_element.has_attr("data-src"):
                        product["image_url"] = image_element["data-src"]
                
                # Try alternative methods to find image
                if "image_url" not in product:
                    # Look for common image patterns
                    for img in product_element.select("img[data-test='product-image'], img.product-image, img.main-image"):
                        if img.has_attr("src") and img["src"]:
                            product["image_url"] = img["src"]
                            break
                        elif img.has_attr("data-src") and img["data-src"]:
                            product["image_url"] = img["data-src"]
                            break
                
                # Extract description if available (not always present on listing pages)
                if description_selector:
                    desc_element = product_element.select_one(description_selector)
                    if desc_element:
                        product["description"] = desc_element.text.strip()
                
                # Extract availability information
                availability_element = product_element.select_one(
                    "[data-test='product-availability'], .availability, .product-availability"
                )
                if availability_element:
                    product["availability"] = availability_element.text.strip()
                
                # Extract any promotional or "New" badges
                badges = []
                for badge in product_element.select(".product-badge, .product-flag, [data-test='product-flag']"):
                    badges.append(badge.text.strip())
                if badges:
                    product["badges"] = badges
                
                # Extract product URL for direct linking
                product_link = product_element.select_one("a[href*='/products/'], a[href*='/product/']")
                if product_link and product_link.has_attr("href"):
                    href = product_link["href"]
                    if href.startswith("/"):
                        base_url = "https://lego.tr"
                        product["url"] = base_url + href
                    else:
                        product["url"] = href
                
                # Add product if we have at least a name or ID and it's not a duplicate
                product_id = product.get("id", "")
                if (product.get("name") or product_id) and product_id not in seen_ids:
                    if product_id:
                        seen_ids.add(product_id)
                    products.append(product)
            
            # Add additional metadata
            result = {
                "products": products,
                "total_products": len(products),
                "category": category_name,
                "source_url": url,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
            }
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            logger.error(f"Error extracting LEGO product data: {e}")
            return json.dumps({
                "error": str(e),
                "category": category_info.get("category_name", "Unknown") if 'category_info' in locals() else "Unknown",
                "products": [],
                "total_products": 0
            })
    
    def _clean_price(self, price_text: str) -> float:
        """Extract numeric price from text with currency symbols, etc."""
        # LEGO specific price cleaning
        if not price_text:
            return 0.0
            
        # Convert Turkish Lira (₺) format if present
        price_text = price_text.replace(".", "").replace(",", ".")
        
        # Extract just the digits and decimal point
        import re
        # Find the first price-like pattern
        price_match = re.search(r'(\d+(?:[.,]\d+)?)', price_text)
        if price_match:
            price_str = price_match.group(1)
            # Handle both comma and period as decimal separators
            price_str = price_str.replace(',', '.')
            try:
                return float(price_str)
            except ValueError:
                return 0.0
        return 0.0
    
    def _extract_currency(self, price_text: str) -> str:
        """Extract currency symbol or code from price text"""
        if not price_text:
            return ""
            
        # Look for currency symbols
        currency_map = {
            '₺': 'TRY',  # Turkish Lira
            '€': 'EUR',  # Euro
            '$': 'USD',  # US Dollar
            '£': 'GBP',  # British Pound
            '¥': 'JPY',  # Japanese Yen
        }
        
        for symbol, code in currency_map.items():
            if symbol in price_text:
                return code
                
        # If no symbol found, try to extract currency code
        currency_codes = ['TRY', 'TL', 'EUR', 'USD', 'GBP']
        for code in currency_codes:
            if code in price_text:
                return code
                
        # Default for Turkish LEGO site
        return "TRY"

# Instantiate the tools
lego_web_navigation_tool = LegoWebNavigationTool()
lego_data_extraction_tool = LegoDataExtractionTool()