#!/bin/bash

# WebRTC VLM Object Detection Starter Script
set -e

# Default values
MODE="wasm"
NGROK_ENABLED="false"
DEBUG="false"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --mode)
            MODE="$2"
            shift 2
            ;;
        --ngrok)
            NGROK_ENABLED="true"
            shift
            ;;
        --debug)
            DEBUG="true"
            shift
            ;;
        --help)
            echo "WebRTC VLM Object Detection Starter"
            echo ""
            echo "Usage: ./start.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --mode [wasm|server]    Set inference mode (default: wasm)"
            echo "  --ngrok                 Enable ngrok for external access"
            echo "  --debug                 Enable debug logging"
            echo "  --help                  Show this help message"
            echo ""
            echo "Examples:"
            echo "  ./start.sh                    # Start with WASM mode"
            echo "  ./start.sh --mode server      # Start with server-side inference"
            echo "  ./start.sh --ngrok            # Start with ngrok for phone access"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Export environment variables
export MODE
export NGROK_ENABLED
export DEBUG

echo "🚀 Starting WebRTC VLM Object Detection Demo"
echo "📱 Mode: $MODE"
echo "🌐 Ngrok: $NGROK_ENABLED"
echo "🐛 Debug: $DEBUG"
echo ""

# Create necessary directories
mkdir -p metrics logs models

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker and Docker Compose."
    echo "   Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not available. Please install Docker Compose."
    exit 1
fi

# Use docker compose or docker-compose based on availability
DOCKER_COMPOSE_CMD="docker-compose"
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker compose"
fi

# Build and start services
echo "🔨 Building and starting services..."
if [ "$NGROK_ENABLED" = "true" ]; then
    echo "🌍 Starting with ngrok for external access..."
    $DOCKER_COMPOSE_CMD --profile ngrok up --build -d
    
    echo "⏳ Waiting for services to start..."
    sleep 10
    
    # Get ngrok URL
    echo "🔗 Getting ngrok URL..."
    NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | grep -o '"public_url":"https://[^"]*' | cut -d'"' -f4 | head -1)
    
    if [ -n "$NGROK_URL" ]; then
        echo "📱 Phone Access URL: $NGROK_URL"
        echo "💻 Local Access: http://localhost:3000"
        echo "🔧 Ngrok Dashboard: http://localhost:4040"
    else
        echo "⚠️  Could not get ngrok URL. Check ngrok service status."
        echo "💻 Falling back to local access: http://localhost:3000"
    fi
else
    $DOCKER_COMPOSE_CMD up --build -d
    
    echo "⏳ Waiting for services to start..."
    sleep 5
    
    echo "💻 Local Access: http://localhost:3000"
    echo "📱 Phone Access: http://$(hostname -I | awk '{print $1}'):3000"
    echo "   (Make sure phone and laptop are on same network)"
fi

echo ""
echo "✅ Demo is running!"
echo ""
echo "📋 Next Steps:"
echo "   1. Open the URL above in your laptop browser"
echo "   2. Scan the QR code with your phone camera"
echo "   3. Allow camera access on your phone"
echo "   4. See live object detection overlays!"
echo ""
echo "🔧 Commands:"
echo "   ./bench/run_bench.sh --duration 30 --mode $MODE  # Run benchmark"
echo "   docker-compose logs -f                           # View logs"
echo "   docker-compose down                              # Stop services"
echo ""
echo "📚 For troubleshooting, check README.md"