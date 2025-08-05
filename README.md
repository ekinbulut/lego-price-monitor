# LEGO Price Monitor

A web scraping and monitoring system for LEGO product prices using AI agents.

## Project Overview

This project is a LEGO price monitoring system that scrapes LEGO product information from various websites, tracks price changes, and sends notifications when significant price drops occur. It uses the CrewAI framework to orchestrate different agents for web scraping, data analysis, and notifications.

[![GitHub Repository](https://img.shields.io/badge/GitHub-lego--price--monitor-blue?logo=github)](https://github.com/ekinbulut/lego-price-monitor)
[![Python Version](https://img.shields.io/badge/python-3.12-blue)](https://www.python.org/downloads/)

## Key Features

- Scrapes LEGO product data from configured websites
- Tracks price changes over time
- Analyzes price trends and detects significant drops
- Sends notifications for important price changes
- Supports multiple LEGO categories and product types

## Project Structure

- `main.py`: Main application orchestrating CrewAI agents
- `config.json`: Configuration file for scraping settings
- `tools/`: Contains tools used by the agents
  - `lego_scraper_tools.py`: Web scraping tools
  - `analyzer_tools.py`: Price analysis tools
  - `notifier_tools.py`: Notification tools
  - `parser_tools.py`: Data parsing and normalization tools
- `data/`: Storage for scraped product data
- `logs/`: Application logs

## Configuration

The `config.json` file contains the following settings:

```json
{
  "lego_categories": [
    {
      "name": "Architecture",
      "url": "https://lego.tr/themes/architecture"
    }
  ],
  "scrape_interval_hours": 6,
  "product_selector": ".product-item",
  "name_selector": "img[alt]",
  "price_selector": ".product-price",
  "id_selector": "img[alt]",
  "image_selector": ".lazyloaded",
  "description_selector": ".product-description",
  "ollama_host": "host.docker.internal",
  "ollama_port": "11434",
  "ollama_model": "llama3",
  "price_threshold_percent": 5.0,
  "use_javascript": true,
  "max_pages": 5
}
```

### Key Configuration Options

- `lego_categories`: List of LEGO categories to monitor
- `scrape_interval_hours`: How often to scrape for updates
- `product_selector`: CSS selector for product items
- `name_selector`: CSS selector for product names
- `price_selector`: CSS selector for product prices
- `id_selector`: CSS selector for product IDs
- `image_selector`: CSS selector for product images
- `price_threshold_percent`: Threshold for price change notifications

## Setup and Installation

### Prerequisites

- Python 3.12+
- Ollama server (for AI agent capabilities)
- Podman and Podman Compose (for containerized deployment)

### Clone the Repository

```bash
git clone https://github.com/ekinbulut/lego-price-monitor.git
cd lego-price-monitor
```

### Local Development Setup

1. Create a Python virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Install Playwright browsers:
   ```bash
   playwright install chromium
   ```

### Running Tests

To test the scraper functionality:

```bash
python3 scraper_test.py
```

## Running the Application

### Using Python Directly

```bash
python main.py
```

### Using Docker

1. Build and start the container:
   ```bash
   docker-compose up -d
   ```

2. Check the logs:
   ```bash
   docker-compose logs -f
   ```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
This will scrape the configured LEGO categories and save the results to the `data/` directory.

## Podman Deployment

You can run the entire application using Podman:

```bash
./run.sh start
```

This will start the LEGO price monitor service along with the PostgreSQL database.

Other useful commands:
```bash
./run.sh status  # Check the status of the containers
./run.sh logs    # View the logs
./run.sh stop    # Stop the containers
```

## Current Status and Testing

The scraper functionality has been tested and works correctly for the LEGO Architecture category. The CSS selectors have been verified to extract the following information:

- Product names
- Product IDs
- Prices
- Image URLs

Tests have confirmed that the configuration is correctly loaded and the scraper can successfully retrieve product data from the configured URL.

## Troubleshooting

If you encounter issues with the application:

1. Check the logs in the `logs/` directory
2. Verify the CSS selectors in `config.json` match the target website
3. Ensure Playwright is installed correctly with `playwright install chromium`

## License

This project is licensed under the MIT License - see the LICENSE file for details.
