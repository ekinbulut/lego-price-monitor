
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
