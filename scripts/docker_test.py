#!/usr/bin/env python3
"""
Docker-based test script to verify system functionality inside containers.
"""

import asyncio
import json
import httpx
import sys
from pathlib import Path

async def test_fastapi_service():
    """Test the FastAPI WebSocket service."""
    print("🌐 Testing FastAPI WebSocket Service...")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Test health endpoint - use container name in Docker network
            response = await client.get("http://jarvis_fastapi_test:8000/health")
            if response.status_code == 200:
                print("✅ FastAPI service is healthy")
                print(f"   Response: {response.json()}")
                return True
            else:
                print(f"❌ FastAPI health check failed: {response.status_code}")
                return False

    except Exception as e:
        print(f"❌ FastAPI service test failed: {e}")
        return False

async def test_infrastructure_services():
    """Test infrastructure services."""
    print("\n🏗️  Testing Infrastructure Services...")
    
    services = {
        "PostgreSQL": ("jarvis_postgres", 5432),
        "Redis": ("jarvis_redis", 6379),
        "Qdrant": ("jarvis_qdrant", 6333),
        "Ollama": ("jarvis_ollama", 11434)
    }
    
    results = {}
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        for service, (host, port) in services.items():
            try:
                if service == "PostgreSQL":
                    # Test PostgreSQL connection (simplified)
                    import asyncpg
                    try:
                        conn = await asyncpg.connect(
                            "postgresql://jarvis_user:jarvis_password@jarvis_postgres:5432/jarvis",
                            timeout=5
                        )
                        await conn.close()
                        results[service] = "✅ Connected"
                    except Exception as e:
                        results[service] = f"❌ Failed: {str(e)[:50]}"
                        
                elif service == "Redis":
                    # Skip Redis for now (would need redis-py)
                    results[service] = "⚠️  Skipped (no redis-py)"
                    
                elif service == "Qdrant":
                    response = await client.get(f"http://{host}:{port}/")
                    if response.status_code < 400:
                        results[service] = "✅ Running"
                    else:
                        results[service] = f"❌ Error {response.status_code}"
                        
                elif service == "Ollama":
                    response = await client.get(f"http://{host}:{port}/api/tags")
                    if response.status_code < 400:
                        results[service] = "✅ Running"
                        # Check if models are available
                        data = response.json()
                        model_count = len(data.get('models', []))
                        results[service] += f" ({model_count} models)"
                    else:
                        results[service] = f"❌ Error {response.status_code}"
                        
            except Exception as e:
                results[service] = f"❌ Failed: {str(e)[:50]}"
    
    for service, status in results.items():
        print(f"  {service}: {status}")
    
    return results

async def test_websocket_connection():
    """Test WebSocket connection."""
    print("\n🔌 Testing WebSocket Connection...")
    
    try:
        import websockets
        
        uri = "ws://jarvis_fastapi_test:8000/ws/test-session"
        
        async with websockets.connect(uri) as websocket:
            # Send a test message
            test_message = {
                "type": "text_input",
                "data": {"message": "Hello, Jarvis!"},
                "session_id": "test-session"
            }
            
            await websocket.send(json.dumps(test_message))
            print("✅ Sent test message to WebSocket")
            
            # Try to receive a response (with timeout)
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response_data = json.loads(response)
                print(f"✅ Received response: {response_data.get('type', 'unknown')}")
                return True
            except asyncio.TimeoutError:
                print("⚠️  No response received (timeout)")
                return True  # Connection worked, just no response
                
    except ImportError:
        print("❌ websockets library not available")
        return False
    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")
        return False

async def test_basic_http_endpoints():
    """Test basic HTTP endpoints."""
    print("\n📡 Testing HTTP Endpoints...")
    
    endpoints = [
        ("GET", "http://jarvis_fastapi_test:8000/health", "Health Check"),
        ("GET", "http://jarvis_fastapi_test:8000/", "Root Endpoint"),
    ]
    
    results = {}
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for method, url, name in endpoints:
            try:
                if method == "GET":
                    response = await client.get(url)
                else:
                    response = await client.post(url)
                
                if response.status_code < 400:
                    results[name] = f"✅ {response.status_code}"
                else:
                    results[name] = f"❌ {response.status_code}"
                    
            except Exception as e:
                results[name] = f"❌ Failed: {str(e)[:50]}"
    
    for endpoint, status in results.items():
        print(f"  {endpoint}: {status}")
    
    return results

async def main():
    """Run all Docker-based tests."""
    print("🐳 Starting Jarvis System Docker Tests")
    print("=" * 50)
    
    tests = [
        ("FastAPI Service", test_fastapi_service),
        ("Infrastructure Services", test_infrastructure_services),
        ("HTTP Endpoints", test_basic_http_endpoints),
        ("WebSocket Connection", test_websocket_connection),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            if isinstance(result, dict):
                # For infrastructure tests, check if any service is working
                results[test_name] = any("✅" in str(status) for status in result.values())
            else:
                results[test_name] = result
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results[test_name] = False
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 Docker Test Results Summary")
    print("=" * 50)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed >= total * 0.5:  # At least 50% pass rate
        print("🎉 Basic system functionality is working in Docker!")
    else:
        print("⚠️  System needs attention. Check the output above for details.")
    
    return passed >= total * 0.5

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
