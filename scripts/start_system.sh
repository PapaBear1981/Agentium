#!/bin/bash

# Jarvis Multi-Agent AI System Startup Script
# This script starts all services in the correct order

set -e

echo "🤖 Starting Jarvis Multi-Agent AI System..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker first."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    print_error "docker-compose is not installed. Please install it first."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    print_warning ".env file not found. Creating from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        print_warning "Please edit .env file with your API keys and configuration."
    else
        print_error ".env.example file not found. Please create .env file manually."
        exit 1
    fi
fi

# Create necessary directories
print_status "Creating necessary directories..."
mkdir -p data/docs
mkdir -p logs
mkdir -p mcp_tools
mkdir -p backups

# Pull latest images
print_status "Pulling latest Docker images..."
docker-compose pull

# Start infrastructure services first
print_status "Starting infrastructure services..."
docker-compose up -d postgres qdrant ollama redis

# Wait for infrastructure to be ready
print_status "Waiting for infrastructure services to be ready..."
sleep 10

# Check PostgreSQL
print_status "Checking PostgreSQL connection..."
for i in {1..30}; do
    if docker-compose exec -T postgres pg_isready -U jarvis_user -d jarvis > /dev/null 2>&1; then
        print_success "PostgreSQL is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        print_error "PostgreSQL failed to start"
        exit 1
    fi
    sleep 2
done

# Check Qdrant
print_status "Checking Qdrant connection..."
for i in {1..30}; do
    if curl -f http://localhost:6333/health > /dev/null 2>&1; then
        print_success "Qdrant is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        print_error "Qdrant failed to start"
        exit 1
    fi
    sleep 2
done

# Check Ollama and pull models
print_status "Checking Ollama and pulling models..."
for i in {1..60}; do
    if curl -f http://localhost:11434/api/tags > /dev/null 2>&1; then
        print_success "Ollama is ready"
        break
    fi
    if [ $i -eq 60 ]; then
        print_error "Ollama failed to start"
        exit 1
    fi
    sleep 2
done

# Pull Ollama models
print_status "Pulling Ollama models (this may take a while)..."
OLLAMA_MODELS=${OLLAMA_MODELS:-"gemma2:7b,llama3.2:8b"}
IFS=',' read -ra MODELS <<< "$OLLAMA_MODELS"
for model in "${MODELS[@]}"; do
    print_status "Pulling model: $model"
    docker-compose exec -T ollama ollama pull "$model" || print_warning "Failed to pull $model"
done

# Start application services
print_status "Starting application services..."
docker-compose up -d voice_adapter agent_service fastapi_ws

# Wait for services to be ready
print_status "Waiting for application services to be ready..."
sleep 15

# Check Voice Service
print_status "Checking Voice Service..."
for i in {1..30}; do
    if curl -f http://localhost:8002/health > /dev/null 2>&1; then
        print_success "Voice Service is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        print_warning "Voice Service may not be ready"
    fi
    sleep 2
done

# Check Agent Service
print_status "Checking Agent Service..."
for i in {1..30}; do
    if curl -f http://localhost:8001/health > /dev/null 2>&1; then
        print_success "Agent Service is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        print_warning "Agent Service may not be ready"
    fi
    sleep 2
done

# Check FastAPI WebSocket Service
print_status "Checking FastAPI WebSocket Service..."
for i in {1..30}; do
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        print_success "FastAPI WebSocket Service is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        print_warning "FastAPI WebSocket Service may not be ready"
    fi
    sleep 2
done

# Optional: Start Nginx for production
if [ "$1" = "--production" ]; then
    print_status "Starting Nginx reverse proxy..."
    docker-compose --profile production up -d nginx
fi

# Show system status
print_status "System Status:"
echo "===================="
docker-compose ps

print_success "🎉 Jarvis Multi-Agent AI System is now running!"
echo ""
echo "📊 Service URLs:"
echo "  • FastAPI WebSocket: http://localhost:8000"
echo "  • Agent Service: http://localhost:8001"
echo "  • Voice Service: http://localhost:8002"
echo "  • Qdrant Dashboard: http://localhost:6333/dashboard"
echo "  • PostgreSQL: localhost:5432"
echo ""
echo "🔧 Management Commands:"
echo "  • View logs: docker-compose logs -f [service_name]"
echo "  • Stop system: docker-compose down"
echo "  • Restart service: docker-compose restart [service_name]"
echo ""
echo "📝 Next Steps:"
echo "  1. Test the WebSocket connection at ws://localhost:8000/ws/test-session"
echo "  2. Check service health at http://localhost:8000/health"
echo "  3. Upload documents to data/docs/ for RAG functionality"
echo "  4. Configure your frontend to connect to the WebSocket API"
echo ""

# Optional: Run basic health checks
if [ "$1" = "--test" ]; then
    print_status "Running basic health checks..."
    
    # Test WebSocket endpoint
    if command -v wscat &> /dev/null; then
        print_status "Testing WebSocket connection..."
        echo '{"type":"heartbeat","data":{"timestamp":"'$(date +%s)'"}}' | wscat -c ws://localhost:8000/ws/test-session -w 5 || print_warning "WebSocket test failed"
    else
        print_warning "wscat not installed, skipping WebSocket test"
    fi
    
    # Test voice processing
    print_status "Testing voice service..."
    curl -X GET http://localhost:8002/providers || print_warning "Voice service test failed"
    
    # Test agent service
    print_status "Testing agent service..."
    curl -X GET http://localhost:8001/agents || print_warning "Agent service test failed"
fi

print_success "Startup complete! 🚀"
