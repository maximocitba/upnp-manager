#!/bin/bash
# Development startup script for UPnP Port Manager

# Create required directories
mkdir -p logs ports_data

# Set development environment variables
export SECRET_KEY=${SECRET_KEY:-"dev-secret-key-change-in-production"}
export PORT=${PORT:-5000}
export FLASK_ENV=${FLASK_ENV:-"development"}

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

echo "Starting UPnP Port Manager in development mode..."
echo "Access the application at: http://localhost:$PORT"
echo "Health check at: http://localhost:$PORT/health"
echo ""
echo "Press Ctrl+C to stop the application"

python app.py