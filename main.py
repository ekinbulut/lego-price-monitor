import os
import json
import logging
from datetime import datetime
import time
import schedule
from crewai import Agent, Crew, Task, Process
from langchain_ollama import OllamaLLM  # Corrected import

# Import our tools
from tools.lego_scraper_tools import LegoWebNavigationTool, LegoDataExtractionTool
from tools.parser_tools import DataNormalizationTool, SchemaDetectionTool
from tools.analyzer_tools import PriceComparisonTool, ChangeDetectionTool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/lego_monitor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create log directory if it doesn't exist
os.makedirs("logs", exist_ok=True)
os.makedirs("data", exist_ok=True)

# Load configuration
def load_config():
    print("Loading configuration...")
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
            "scrape_interval_hours": 6,
            "product_selector": ".product-item, .product-card, .ProductGridstyles__StyledWrapper-sc-*",
            "name_selector": ".product-item__title, .product-name, .ProductLeafSharedstyles__Title-*",
            "price_selector": ".product-price, .product-item__price, .ProductPricestyles__StyledText-*",
            "id_selector": ".product-id, [data-test='product-item-number']",
            "image_selector": ".product-item__image img, .product-image img, .ProductImagestyles__Img-*",
            "description_selector": ".product-item__short-description, .product-description",
            "ollama_host": "host.docker.internal",
            "ollama_port": "11434",
            "ollama_model": "gemma3:4b",
            "use_javascript": True,
            "max_pages": 5
        }

# Initialize Ollama LLM
def initialize_llm(config):
    ollama_host = os.getenv("OLLAMA_HOST", config.get("ollama_host", "host.docker.internal"))
    ollama_port = os.getenv("OLLAMA_PORT", config.get("ollama_port", "11434"))
    ollama_model = os.getenv("OLLAMA_MODEL", config.get("ollama_model", "gemma3:4b"))
    
    ollama_base_url = f"http://{ollama_host}:{ollama_port}"
    logger.info(f"Connecting to Ollama at {ollama_base_url} using model {ollama_model}")
    
    return OllamaLLM(base_url=ollama_base_url, model=ollama_model)

# Load historical data for a specific category
def load_historical_data(category_name):
    filename = f'data/lego_{category_name.lower().replace(" ", "_")}_historical.json'
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.info(f"No historical data found for {category_name}, will create new dataset")
        return {"products": []}

# Save data as historical for a specific category
def save_historical_data(data, category_name):
    filename = f'data/lego_{category_name.lower().replace(" ", "_")}_historical.json'
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    logger.info(f"Saved historical data for {category_name} with {len(data.get('products', []))} products")

# Save analysis results for a specific category
def save_analysis_results(analysis_data, category_name):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"data/lego_{category_name.lower().replace(' ', '_')}_analysis_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(analysis_data, f, indent=2)
    logger.info(f"Saved LEGO {category_name} analysis results to {filename}")

# Initialize AI agents
def initialize_agents(llm, category_name):
    # Create tool instances
    lego_web_navigation_tool = LegoWebNavigationTool()
    lego_data_extraction_tool = LegoDataExtractionTool()
    data_normalization_tool = DataNormalizationTool()
    schema_detection_tool = SchemaDetectionTool()
    price_comparison_tool = PriceComparisonTool()
    change_detection_tool = ChangeDetectionTool()
    
    # Create specialized agents with tools directly (no conversion needed for newer CrewAI)
    scraper_agent = Agent(
        role=f"LEGO {category_name} Scraper",
        goal=f"Extract accurate product data from the LEGO {category_name} collection",
        backstory=f"I'm specialized in navigating LEGO websites and extracting {category_name} product information",
        verbose=True,
        llm=llm,
        tools=[lego_web_navigation_tool, lego_data_extraction_tool]
    )

    parser_agent = Agent(
        role=f"LEGO {category_name} Parser",
        goal=f"Transform raw LEGO {category_name} data into structured product information",
        backstory=f"I excel at parsing LEGO {category_name} data and identifying product details",
        verbose=True,
        llm=llm,
        tools=[data_normalization_tool, schema_detection_tool]
    )

    analyzer_agent = Agent(
        role=f"LEGO {category_name} Analyzer",
        goal=f"Detect price changes and new/removed LEGO {category_name} sets",
        backstory=f"I'm an analytical expert who finds patterns and changes in LEGO {category_name} product data",
        verbose=True,
        llm=llm,
        tools=[price_comparison_tool, change_detection_tool]
    )
    
    return scraper_agent, parser_agent, analyzer_agent

# Process a single LEGO category
def process_lego_category(category_info, config, llm):
    category_name = category_info["name"]
    category_url = category_info["url"]
    
    logger.info(f"Starting monitoring process for LEGO {category_name} collection")
    
    # Initialize agents for this category
    scraper_agent, parser_agent, analyzer_agent = initialize_agents(llm, category_name)
    
    # Load historical data for this category
    historical_data = load_historical_data(category_name)
    
    # Define tasks
    scraping_task = Task(
        description=f"""
        Scrape the LEGO {category_name} collection page at {category_url}.
        
        Use these CSS selectors as a starting point, but be prepared to adapt if the site structure doesn't match:
        - Product container: {config['product_selector']}
        - Product name: {config['name_selector']}
        - Product price: {config['price_selector']}
        - Product ID (set number): {config['id_selector']}
        - Product image: {config['image_selector']}
        - Product description: {config['description_selector']}
        
        Extract as much information as possible, including:
        - Set number (e.g., "10997" for Architecture sets or "75330" for Star Wars sets)
        - Complete set name
        - Current price in TRY (Turkish Lira)
        - Availability status
        - Any "New" or special badges
        - Product URL for direct linking
        
        Be thorough and use alternative approaches if the specified selectors don't work.
        Make sure to include that this is the {category_name} category in your data.
        """,
        agent=scraper_agent,
        expected_output=f"JSON containing comprehensive LEGO {category_name} product data"
    )

    parsing_task = Task(
        description=f"""
        Convert the raw scraped LEGO {category_name} data into a standardized product database format.
        
        Focus on these fields:
        - id: The LEGO set number
        - name: The complete set name
        - price: The numeric price (as a float, without currency symbols)
        - currency: The currency code (likely "TRY" for Turkish Lira)
        - image_url: URL to the product image
        - availability: Product availability status
        - badges: Any promotional badges or "New" indicators
        - category: Should be "{category_name}"
        - url: Direct link to the product page
        
        Ensure consistent data types and handle any special characters in product names.
        """,
        agent=parser_agent,
        expected_output=f"Structured LEGO {category_name} product database entries ready for comparison",
        context=[scraping_task]
    )

    analysis_task = Task(
        description=f"""
        Compare the current LEGO {category_name} data with historical records to identify changes.
        
        Look for:
        1. Price increases and decreases for existing sets
        2. Newly added LEGO {category_name} sets
        3. Removed LEGO {category_name} sets (sets that were previously available but no longer appear)
        4. Changes in availability status
        
        Provide detailed analysis including:
        - Percentage changes for prices
        - Complete list of new sets with their details
        - Complete list of removed sets with their last known details
        - Sets with significant price changes (more than {config.get('price_threshold_percent', 5)}%)
        
        Historical data is available for comparison.
        """,
        agent=analyzer_agent,
        expected_output=f"Comprehensive analysis of LEGO {category_name} set changes",
        context=[parsing_task]
    )

    # Create the crew with a sequential process
    category_monitoring_crew = Crew(
        agents=[scraper_agent, parser_agent, analyzer_agent],
        tasks=[scraping_task, parsing_task, analysis_task],
        verbose=2,
        process=Process.sequential  # Tasks will run in the defined order
    )

    # Execute the crew's work
    try:
        logger.info(f"Starting AI crew for LEGO {category_name} monitoring")
        result = category_monitoring_crew.kickoff()
        
        # Process results
        try:
            # Save analysis results
            analysis_data = json.loads(result)
            save_analysis_results(analysis_data, category_name)
            
            # Save current product data as historical for next run
            for task in category_monitoring_crew.tasks:
                if task.agent.role == f"LEGO {category_name} Parser" and hasattr(task, "output"):
                    try:
                        parser_output = json.loads(task.output)
                        save_historical_data(parser_output, category_name)
                    except Exception as e:
                        logger.error(f"Could not parse and save parser output as historical data for {category_name}: {e}")
            
            # Log a summary of the analysis
            if "price_changes" in analysis_data:
                logger.info(f"Found {len(analysis_data['price_changes'])} price changes in LEGO {category_name} sets")
            if "new_products" in analysis_data:
                logger.info(f"Found {len(analysis_data['new_products'])} new LEGO {category_name} sets")
            if "removed_products" in analysis_data:
                logger.info(f"Found {len(analysis_data['removed_products'])} removed LEGO {category_name} sets")
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LEGO {category_name} analysis result as JSON: {e}")
    
    except Exception as e:
        logger.error(f"Error during LEGO {category_name} monitoring process: {e}")

# Main monitoring process that handles all categories
def run_lego_monitoring():
    logger.info("Starting LEGO product monitoring process for all categories")
    config = load_config()
    llm = initialize_llm(config)
    
    # Process each category
    categories = config.get("lego_categories", [])
    
    if not categories:
        logger.error("No LEGO categories defined in configuration")
        return
    
    for category_info in categories:
        try:
            process_lego_category(category_info, config, llm)
            # Add a delay between categories to avoid overloading the server
            time.sleep(30)
        except Exception as e:
            logger.error(f"Error processing category {category_info.get('name', 'Unknown')}: {e}")

# Schedule the monitoring task
def schedule_monitoring():
    config = load_config()
    interval_hours = config.get("scrape_interval_hours", 6)
    
    logger.info(f"Scheduling LEGO product monitoring every {interval_hours} hours")
    schedule.every(interval_hours).hours.do(run_lego_monitoring)
    
    # Also run immediately on startup
    run_lego_monitoring()
    
    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    logger.info("LEGO product monitoring service starting up")
    schedule_monitoring()