#!/bin/bash
# Script to run the LEGO Price Monitor application

echo "==============================================="
echo "   LEGO Price Monitor - Podman Deployment    "
echo "==============================================="
echo

# Check if Podman is installed
if ! command -v podman &> /dev/null; then
    echo "❌ Error: Podman is not installed. Please install Podman first."
    exit 1
fi

# Check if Podman Compose is installed
if ! command -v podman-compose &> /dev/null; then
    echo "⚠️ Warning: podman-compose is not found. Will try using 'podman play kube' instead."
    USE_PODMAN_PLAY=true
else
    USE_PODMAN_PLAY=false
fi

# Function to build and start the Podman containers
start_containers() {
    echo "🚀 Starting LEGO Price Monitor..."
    
    if [ "$USE_PODMAN_PLAY" = true ]; then
        # Use podman directly if podman-compose is not available
        podman pod create --name lego-price-monitor
        podman build -t lego-price-monitor .
        podman run -d --pod lego-price-monitor --name lego-monitor lego-price-monitor
    else
        # Use podman-compose if available
        podman-compose up --build -d
    fi
    
    if [ $? -eq 0 ]; then
        echo "✅ LEGO Price Monitor is now running in the background."
        echo "📊 To view logs: ./run.sh logs"
        echo "🛑 To stop: ./run.sh stop"
    else
        echo "❌ Failed to start Podman containers."
        exit 1
    fi
}

# Function to stop the Podman containers
stop_containers() {
    echo "🛑 Stopping LEGO Price Monitor..."
    
    if [ "$USE_PODMAN_PLAY" = true ]; then
        # Use podman directly if podman-compose is not available
        podman pod stop lego-price-monitor
        podman pod rm lego-price-monitor
    else
        # Use podman-compose if available
        podman-compose down
    fi
    
    if [ $? -eq 0 ]; then
        echo "✅ LEGO Price Monitor has been stopped."
    else
        echo "❌ Failed to stop Podman containers."
        exit 1
    fi
}

# Function to run in development mode
run_dev() {
    echo "� Starting LEGO Price Monitor in development mode..."
    
    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        echo "Creating Python virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment and install dependencies
    source venv/bin/activate
    echo "Installing dependencies..."
    pip install -r requirements.txt
    
    # Install Playwright browsers if needed
    if ! python -c "from playwright.sync_api import sync_playwright; exit(0)" &>/dev/null; then
        echo "Installing Playwright browsers..."
        playwright install chromium
    fi
    
    # Run the scraper test
    echo "Running scraper test..."
    python scraper_test.py
    
    echo "✅ Development test completed."
    deactivate
}

# Function to show Podman container status
show_status() {
    echo "📊 LEGO Price Monitor Status:"
    
    if [ "$USE_PODMAN_PLAY" = true ]; then
        # Use podman directly if podman-compose is not available
        podman pod ps | grep lego-price-monitor
        podman ps --pod --filter pod=lego-price-monitor
    else
        # Use podman-compose if available
        podman-compose ps
    fi
}

# Function to show the help message
show_help() {
    echo "Usage: ./run.sh [command]"
    echo
    echo "Commands:"
    echo "  dev      - Run in development mode (virtual environment)"
    echo "  start    - Build and start the Podman containers"
    echo "  stop     - Stop the Podman containers"
    echo "  restart  - Restart the Podman containers"
    echo "  status   - Show the status of the Podman containers"
    echo "  logs     - Show the logs of the Podman containers"
    echo "  help     - Show this help message"
    echo
    echo "If no command is provided, the containers will be started."
}
# Check if a command was provided
if [ $# -eq 0 ]; then
    start_containers
else
    case "$1" in
        dev)
            run_dev
            ;;
        start)
            start_containers
            ;;
        stop)
            stop_containers
            ;;
        restart)
            stop_containers
            start_containers
            ;;
        status)
            show_status
            ;;
        logs)
            echo "📊 LEGO Price Monitor Logs:"
            if [ "$USE_PODMAN_PLAY" = true ]; then
                # Use podman directly if podman-compose is not available
                podman logs -f $(podman ps -q --filter name=lego-monitor)
            else
                # Use podman-compose if available
                podman-compose logs -f
            fi
            ;;
        help)
            show_help
            ;;
        *)
            echo "❌ Unknown command: $1"
            show_help
            exit 1
            ;;
    esac
fi

exit 0
