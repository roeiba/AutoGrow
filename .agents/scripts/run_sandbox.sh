#!/bin/bash
# Script to run the sandbox environment (API + Frontend)

set -e

echo "🚀 Starting SeedGPT Sandbox Environment"
echo "========================================"

# Check if running from project root
if [ ! -d "sandbox-api" ] || [ ! -d "sandbox-frontend" ]; then
    echo "❌ Error: Must run from project root directory"
    exit 1
fi

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down services..."
    kill $API_PID $FRONTEND_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start API
echo ""
echo "📡 Starting Sandbox API..."
cd sandbox-api

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Creating from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit sandbox-api/.env with your credentials"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment and install dependencies
source venv/bin/activate
pip install -q -r requirements.txt

# Start API in background
cd src
python main.py &
API_PID=$!
cd ../..

echo "✅ API started on http://localhost:8000"

# Wait for API to be ready
echo "⏳ Waiting for API to be ready..."
sleep 3

# Start Frontend
echo ""
echo "🎨 Starting Sandbox Frontend..."
cd sandbox-frontend

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Creating from .env.example..."
    cp .env.example .env
fi

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing Node.js dependencies..."
    npm install
fi

# Start frontend in background
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ Frontend started on http://localhost:3000"
echo ""
echo "========================================"
echo "🎉 Sandbox environment is ready!"
echo "========================================"
echo ""
echo "📍 Frontend: http://localhost:3000"
echo "📍 API: http://localhost:8000"
echo "📍 API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for processes
wait
