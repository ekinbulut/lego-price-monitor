#!/usr/bin/env python3
"""
Test script to validate the main application flow without external dependencies.
This tests that the CrewAI integration and tool implementations work correctly.
"""

import os
import json
import logging
from unittest.mock import Mock, patch
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_config_loading():
    """Test that configuration can be loaded"""
    from main import load_config
    config = load_config()
    assert "lego_categories" in config
    assert len(config["lego_categories"]) > 0
    logger.info("✅ Configuration loading works")
    return config

def test_tool_instantiation():
    """Test that all tools can be instantiated"""
    from tools.lego_scraper_tools import LegoWebNavigationTool, LegoDataExtractionTool
    from tools.parser_tools import DataNormalizationTool, SchemaDetectionTool
    from tools.analyzer_tools import PriceComparisonTool, ChangeDetectionTool
    
    tools = [
        LegoWebNavigationTool(),
        LegoDataExtractionTool(),
        DataNormalizationTool(),
        SchemaDetectionTool(),
        PriceComparisonTool(),
        ChangeDetectionTool()
    ]
    
    for tool in tools:
        assert hasattr(tool, 'name')
        assert hasattr(tool, 'description')
        assert hasattr(tool, '_run')
    
    logger.info(f"✅ All {len(tools)} tools instantiated successfully")
    return tools

def test_llm_initialization():
    """Test LLM initialization with mock"""
    from main import initialize_llm
    config = {"ollama_host": "localhost", "ollama_port": "11434", "ollama_model": "test"}
    
    # Mock the OllamaLLM to avoid actual connection
    with patch('main.OllamaLLM') as mock_llm:
        mock_instance = Mock()
        mock_llm.return_value = mock_instance
        
        llm = initialize_llm(config)
        assert llm is not None
        mock_llm.assert_called_once()
        
    logger.info("✅ LLM initialization works (mocked)")
    return mock_instance

def test_agent_initialization():
    """Test agent initialization"""
    from main import initialize_agents
    
    # Create a mock LLM
    mock_llm = Mock()
    mock_llm.temperature = 0
    
    agents = initialize_agents(mock_llm, "Architecture")
    assert len(agents) == 3
    
    roles = [agent.role for agent in agents]
    expected_roles = ["LEGO Architecture Scraper", "LEGO Architecture Parser", "LEGO Architecture Analyzer"]
    
    for expected_role in expected_roles:
        assert expected_role in roles
    
    # Check that each agent has tools
    for agent in agents:
        assert len(agent.tools) == 2  # Each agent should have 2 tools
    
    logger.info("✅ Agent initialization works")
    return agents

def test_crew_creation():
    """Test that a Crew can be created with the agents and tasks"""
    from crewai import Crew, Task, Process
    from main import initialize_agents
    
    # Create mock LLM and agents
    mock_llm = Mock()
    agents = initialize_agents(mock_llm, "Architecture")
    
    # Create simple test tasks
    test_tasks = []
    for i, agent in enumerate(agents):
        task = Task(
            description=f"Test task {i+1} for {agent.role}",
            agent=agent,
            expected_output="Test output"
        )
        test_tasks.append(task)
    
    # Create crew
    crew = Crew(
        agents=agents,
        tasks=test_tasks,
        verbose=False,
        process=Process.sequential
    )
    
    assert crew is not None
    assert len(crew.agents) == 3
    assert len(crew.tasks) == 3
    
    logger.info("✅ Crew creation works")
    return crew

def test_data_flow():
    """Test that tools can process mock data"""
    from tools.lego_scraper_tools import LegoDataExtractionTool
    from tools.parser_tools import DataNormalizationTool
    from tools.analyzer_tools import PriceComparisonTool
    
    # Mock HTML data
    mock_category_data = json.dumps({
        "category_name": "Architecture",
        "url": "https://test.com",
        "pages_scraped": 1,
        "html_content": """
        <div class="product-item">
            <img alt="10001 Test LEGO Set" src="test.jpg">
            <div class="product-price">₺299.99</div>
        </div>
        """
    })
    
    # Test data extraction
    extraction_tool = LegoDataExtractionTool()
    extracted_data = extraction_tool._run(
        category_data=mock_category_data,
        product_selector=".product-item",
        name_selector="img[alt]",
        price_selector=".product-price",
        id_selector="img[alt]",
        image_selector="img"
    )
    
    extracted_result = json.loads(extracted_data)
    assert "products" in extracted_result
    assert len(extracted_result["products"]) > 0
    
    # Test data normalization
    normalization_tool = DataNormalizationTool()
    normalized_data = normalization_tool._run(json.dumps(extracted_result["products"]))
    
    normalized_result = json.loads(normalized_data)
    assert isinstance(normalized_result, list)
    assert len(normalized_result) > 0
    
    logger.info("✅ Data flow works")
    return extracted_result, normalized_result

def test_historical_data_functions():
    """Test historical data save/load functions"""
    from main import save_historical_data, load_historical_data
    
    # Test data
    test_data = {
        "products": [
            {"id": "10001", "name": "Test Set", "price": 299.99}
        ]
    }
    
    # Save data
    save_historical_data(test_data, "Test")
    
    # Load data
    loaded_data = load_historical_data("Test")
    assert "products" in loaded_data
    assert len(loaded_data["products"]) == 1
    assert loaded_data["products"][0]["id"] == "10001"
    
    logger.info("✅ Historical data functions work")
    
    # Clean up
    import os
    try:
        os.remove("data/lego_test_historical.json")
    except:
        pass

def main():
    """Run all tests"""
    logger.info("=== Testing LEGO Price Monitor Application ===")
    
    try:
        # Create required directories
        os.makedirs("data", exist_ok=True)
        os.makedirs("logs", exist_ok=True)
        
        # Run tests
        config = test_config_loading()
        tools = test_tool_instantiation()
        llm = test_llm_initialization()
        agents = test_agent_initialization()
        crew = test_crew_creation()
        extracted, normalized = test_data_flow()
        test_historical_data_functions()
        
        logger.info("=== ALL TESTS PASSED ===")
        logger.info("✅ The application structure and CrewAI integration are working correctly")
        logger.info("✅ To run the full application, you need:")
        logger.info("   1. Ollama server running with a language model")
        logger.info("   2. Playwright browsers installed (playwright install chromium)")
        logger.info("   3. Run: python main.py")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)