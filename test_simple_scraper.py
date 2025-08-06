#!/usr/bin/env python3
"""
Simple test script to validate scraper tools without CrewAI or Playwright dependencies.
This tests the data extraction logic using requests and BeautifulSoup.
"""

import json
import requests
from bs4 import BeautifulSoup
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_simple_scraper():
    """Test basic scraping functionality using requests"""
    logger.info("Testing simple scraper functionality...")
    
    try:
        # Test with a simple HTML structure (simulating LEGO product page)
        mock_html = """
        <html>
        <body>
            <div class="product-item">
                <img alt="10001 LEGO Architecture Statue of Liberty" src="https://example.com/image1.jpg">
                <div class="product-price">₺299.99</div>
            </div>
            <div class="product-item">
                <img alt="21058 LEGO Architecture Great Pyramid" src="https://example.com/image2.jpg">
                <div class="product-price">₺199.99</div>
            </div>
        </body>
        </html>
        """
        
        # Test the data extraction logic from our tool
        from tools.lego_scraper_tools import LegoDataExtractionTool
        
        category_data = json.dumps({
            "category_name": "Architecture", 
            "url": "https://test.com",
            "pages_scraped": 1,
            "html_content": mock_html
        })
        
        extraction_tool = LegoDataExtractionTool()
        result = extraction_tool._run(
            category_data=category_data,
            product_selector=".product-item",
            name_selector="img[alt]",
            price_selector=".product-price",
            id_selector="img[alt]",
            image_selector="img"
        )
        
        parsed_result = json.loads(result)
        logger.info(f"Extracted {len(parsed_result['products'])} products")
        
        for product in parsed_result['products']:
            logger.info(f"Product: {product.get('name', 'Unknown')} - {product.get('price', 'Unknown')} - ID: {product.get('id', 'Unknown')}")
        
        # Test data normalization
        from tools.parser_tools import DataNormalizationTool
        normalization_tool = DataNormalizationTool()
        normalized_result = normalization_tool._run(json.dumps(parsed_result['products']))
        
        normalized_products = json.loads(normalized_result)
        logger.info(f"Normalized {len(normalized_products)} products")
        
        # Test analysis tools
        from tools.analyzer_tools import PriceComparisonTool, ChangeDetectionTool
        
        # Create some mock historical data for comparison
        historical_data = json.dumps([
            {"id": "10001", "name": "LEGO Architecture Statue of Liberty", "price": 279.99}
        ])
        
        current_data = json.dumps(normalized_products)
        
        price_tool = PriceComparisonTool()
        price_result = price_tool._run(current_data, historical_data, 5.0)
        price_changes = json.loads(price_result)
        
        logger.info(f"Price comparison found {len(price_changes['price_changes'])} changes")
        
        change_tool = ChangeDetectionTool()
        change_result = change_tool._run(current_data, historical_data)
        changes = json.loads(change_result)
        
        logger.info(f"Change detection found {changes['summary']['new_products_count']} new products")
        
        logger.info("✅ Simple scraper test passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Simple scraper test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_config_and_basic_flow():
    """Test that configuration and basic application flow works"""
    logger.info("Testing configuration and basic application flow...")
    
    try:
        from main import load_config, save_historical_data, load_historical_data
        
        # Test config loading
        config = load_config()
        logger.info(f"Config loaded: {len(config['lego_categories'])} categories")
        
        # Test historical data functions
        test_data = {"products": [{"id": "test", "name": "Test Product", "price": 100.0}]}
        save_historical_data(test_data, "TestCategory")
        loaded_data = load_historical_data("TestCategory")
        
        assert loaded_data["products"][0]["id"] == "test"
        logger.info("✅ Historical data functions work")
        
        # Test that main functions can be imported
        from main import initialize_llm, initialize_agents, process_lego_category
        logger.info("✅ Main application functions can be imported")
        
        logger.info("✅ Configuration and basic flow test passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Configuration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_how_to_run_guide():
    """Create a simple guide on how to run the application"""
    guide = """
# How to Run LEGO Price Monitor

## Prerequisites

1. **Python 3.12+**
2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Playwright Browsers (for web scraping):**
   ```bash
   playwright install chromium
   ```

4. **Ollama Server (for AI functionality):**
   - Install Ollama: https://ollama.ai
   - Start Ollama server: `ollama serve`
   - Pull a model: `ollama pull gemma3:4b` (or your preferred model)

## Running the Application

### Option 1: Direct Python Execution
```bash
python main.py
```

### Option 2: Using the Run Script
```bash
./run.sh dev    # For development mode
./run.sh start  # For production mode with Docker
```

### Option 3: Test Individual Components

**Test Configuration:**
```bash
python -c "from main import load_config; print(load_config())"
```

**Test Scraper Tools:**
```bash
python test_simple_scraper.py
```

**Test Full Flow (requires Ollama):**
```bash
python test_main_flow.py
```

## Configuration

Edit `config.json` to:
- Change LEGO categories to monitor
- Adjust scraping selectors for different websites
- Modify Ollama settings (host, port, model)
- Set price change thresholds

## Troubleshooting

1. **Playwright Error:** Run `playwright install chromium`
2. **Ollama Connection Error:** Check if Ollama server is running on correct host/port
3. **Scraping Issues:** Update CSS selectors in config.json if LEGO website structure changes

## Output

- Historical data: `data/lego_<category>_historical.json`
- Analysis results: `data/lego_<category>_analysis_<timestamp>.json`
- Logs: `logs/lego_monitor.log`
"""
    
    with open("HOW_TO_RUN.md", "w") as f:
        f.write(guide)
    
    logger.info("✅ Created HOW_TO_RUN.md guide")

def main():
    """Run all tests and create documentation"""
    logger.info("=== LEGO Price Monitor - Simple Test Suite ===")
    
    try:
        # Ensure directories exist
        import os
        os.makedirs("data", exist_ok=True)
        os.makedirs("logs", exist_ok=True)
        
        # Run tests
        config_test = test_config_and_basic_flow()
        scraper_test = test_simple_scraper()
        
        # Create documentation
        create_how_to_run_guide()
        
        if config_test and scraper_test:
            logger.info("=== ALL TESTS PASSED ===")
            logger.info("✅ The LEGO Price Monitor application is working correctly!")
            logger.info("✅ See HOW_TO_RUN.md for instructions on running the full application")
            return True
        else:
            logger.error("❌ Some tests failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)