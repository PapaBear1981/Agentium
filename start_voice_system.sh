#!/bin/bash

# Voice System Startup and Test Script
# This script builds and starts the voice processing system, then runs tests

set -e  # Exit on any error

echo "🎤 Jarvis Voice System Startup"
echo "================================"

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

# Check if .env file exists
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        print_warning ".env file not found. Copying from .env.example"
        cp .env.example .env
        print_warning "Please edit .env file with your API keys if needed"
    else
        print_error ".env.example file not found. Cannot create .env file."
        exit 1
    fi
fi

# Load environment variables
if [ -f .env ]; then
    # Export variables from .env file, ignoring comments and empty lines
    export $(grep -v '^#' .env | grep -v '^$' | xargs -d '\n')
fi

print_status "Building voice processing service..."

# Build the voice service container
if docker-compose build voice_adapter; then
    print_success "Voice service built successfully"
else
    print_error "Failed to build voice service"
    exit 1
fi

print_status "Starting required services..."

# Start required services (PostgreSQL, Redis, etc.)
docker-compose up -d postgres redis qdrant

# Wait for services to be ready
print_status "Waiting for services to be ready..."
sleep 10

# Start the voice service
print_status "Starting voice processing service..."
docker-compose up -d voice_adapter

# Wait for voice service to be ready
print_status "Waiting for voice service to start..."
sleep 15

# Check if voice service is healthy
print_status "Checking voice service health..."
for i in {1..30}; do
    if curl -f http://localhost:8002/health > /dev/null 2>&1; then
        print_success "Voice service is healthy!"
        break
    else
        if [ $i -eq 30 ]; then
            print_error "Voice service failed to start properly"
            print_status "Checking logs..."
            docker-compose logs voice_adapter
            exit 1
        fi
        print_status "Waiting for voice service... ($i/30)"
        sleep 2
    fi
done

# Install test dependencies
print_status "Installing test dependencies..."
pip install httpx soundfile numpy wave

# Run the test suite
print_status "Running voice system tests..."
if python test_voice_system.py; then
    print_success "All tests completed!"
else
    print_warning "Some tests may have failed. Check output above."
fi

# Show service status
print_status "Service Status:"
echo "================================"
docker-compose ps voice_adapter

print_status "Voice service logs (last 20 lines):"
echo "================================"
docker-compose logs --tail=20 voice_adapter

print_status "Available endpoints:"
echo "================================"
echo "Health Check:    http://localhost:8002/health"
echo "Providers:       http://localhost:8002/providers"
echo "STT Endpoint:    http://localhost:8002/stt"
echo "TTS Endpoint:    http://localhost:8002/tts"
echo "System Status:   http://localhost:8002/status"
echo "Metrics:         http://localhost:8002/metrics"

print_success "Voice system startup complete!"
echo ""
echo "🎯 Next Steps:"
echo "1. Test the endpoints using the URLs above"
echo "2. Check the logs if any issues occur: docker-compose logs voice_adapter"
echo "3. Stop the system: docker-compose down"
echo ""
echo "📚 Documentation:"
echo "- STT uses WhisperX for high-quality transcription"
echo "- TTS uses Coqui for open-source speech synthesis"
echo "- ElevenLabs support available with API key"
echo "- All endpoints support JSON requests/responses"
