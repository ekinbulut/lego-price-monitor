import os
import json
import logging
from crewai import Agent, Task, Crew, Process
import time
from langchain_community.llms import Ollama
from langchain_openai import ChatOpenAI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/lego_monitor_test_crew.log"),
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
        logger.warning("Config file not found, using defaults")
        return {
            "lego_categories": [
                {
                    "name": "Architecture",
                    "url": "https://www.lego.com/en-us/themes/architecture"
                }
            ],
            "scrape_interval_hours": 1,
            "product_selector": "[data-test=\"product-item\"]",
            "name_selector": "[data-test=\"product-title\"]",
            "price_selector": "[data-test=\"price\"]",
            "id_selector": "[data-test=\"product-item-number\"]",
            "image_selector": "img",
            "description_selector": ".product-description",
            "use_javascript": True,
            "max_pages": 1
        }

def test_agents():
    """Test agent creation and basic functionality."""
    logger.info("Testing agent creation")
    
    # Create a fake LLM that just returns preset responses
    class FakeLLM:
        def invoke(self, prompt):
            return "This is a test response from the fake LLM."
    
    # Create a simple agent
    test_agent = Agent(
        role="LEGO Data Analyst",
        goal="Analyze LEGO product data and provide insights",
        backstory="You are an expert in LEGO products and pricing analysis.",
        verbose=True,
        llm=FakeLLM()
    )
    
    logger.info(f"Created agent: {test_agent.role}")
    logger.info("Agent test completed")

if __name__ == "__main__":
    logger.info("Starting CrewAI test script")
    test_agents()
    logger.info("CrewAI test script completed")
