#!/usr/bin/env python3
"""
Jarvis Multi-Agent AI System Test Suite

This script provides comprehensive testing for all system components.
"""

import asyncio
import json
import time
import websockets
import httpx
import base64
from pathlib import Path
from typing import Dict, Any, List

class JarvisSystemTester:
    """Comprehensive system tester for Jarvis AI."""
    
    def __init__(self):
        self.base_urls = {
            "fastapi": "http://localhost:8000",
            "agent": "http://localhost:8001", 
            "voice": "http://localhost:8002"
        }
        self.websocket_url = "ws://localhost:8000/ws/test-session"
        self.test_results = []
        
    async def run_all_tests(self):
        """Run all system tests."""
        print("🧪 Starting Jarvis System Tests...")
        print("=" * 50)
        
        # Test infrastructure
        await self.test_infrastructure()
        
        # Test services
        await self.test_services()
        
        # Test WebSocket communication
        await self.test_websocket()
        
        # Test voice processing
        await self.test_voice_processing()
        
        # Test agent system
        await self.test_agent_system()
        
        # Test integration
        await self.test_integration()
        
        # Print results
        self.print_results()
    
    async def test_infrastructure(self):
        """Test infrastructure components."""
        print("\n🏗️  Testing Infrastructure...")
        
        # Test PostgreSQL
        await self.test_endpoint("PostgreSQL Health", "GET", f"{self.base_urls['fastapi']}/health")
        
        # Test Qdrant (uses /healthz endpoint, not /health)
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:6333/healthz")
                self.record_result("Qdrant Health", response.status_code == 200, 
                                 f"Status: {response.status_code}")
        except Exception as e:
            self.record_result("Qdrant Health", False, str(e))
        
        # Test Ollama
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:11434/api/tags")
                self.record_result("Ollama Health", response.status_code == 200,
                                 f"Status: {response.status_code}")
        except Exception as e:
            self.record_result("Ollama Health", False, str(e))
    
    async def test_services(self):
        """Test individual services."""
        print("\n🔧 Testing Services...")
        
        # Test FastAPI service
        await self.test_endpoint("FastAPI Health", "GET", f"{self.base_urls['fastapi']}/health")
        await self.test_endpoint("FastAPI Connections", "GET", f"{self.base_urls['fastapi']}/connections")
        
        # Test Agent service
        await self.test_endpoint("Agent Service Health", "GET", f"{self.base_urls['agent']}/health")
        await self.test_endpoint("Agent Service Status", "GET", f"{self.base_urls['agent']}/status")
        await self.test_endpoint("Agent List", "GET", f"{self.base_urls['agent']}/agents")
        await self.test_endpoint("Tool List", "GET", f"{self.base_urls['agent']}/tools")
        
        # Test Voice service
        await self.test_endpoint("Voice Service Health", "GET", f"{self.base_urls['voice']}/health")
        await self.test_endpoint("Voice Providers", "GET", f"{self.base_urls['voice']}/providers")
        await self.test_endpoint("Voice Status", "GET", f"{self.base_urls['voice']}/status")
    
    async def test_websocket(self):
        """Test WebSocket communication."""
        print("\n🔌 Testing WebSocket...")
        
        try:
            async with websockets.connect(self.websocket_url) as websocket:
                # Test connection
                self.record_result("WebSocket Connection", True, "Connected successfully")
                
                # Read initial connection status message
                initial_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                initial_data = json.loads(initial_response)
                
                # Verify connection status
                connection_ok = initial_data.get("type") == "connection_status"
                self.record_result("WebSocket Connection Status", connection_ok,
                                 f"Initial message type: {initial_data.get('type')}")
                
                # Test heartbeat
                heartbeat_msg = {
                    "type": "heartbeat",
                    "data": {"timestamp": time.time()}
                }
                await websocket.send(json.dumps(heartbeat_msg))
                
                # Wait for heartbeat response
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response_data = json.loads(response)
                
                self.record_result("WebSocket Heartbeat", 
                                 response_data.get("type") == "heartbeat",
                                 f"Response type: {response_data.get('type')}")
                
                # Test system command
                status_msg = {
                    "type": "system_command",
                    "data": {"command": "status"}
                }
                await websocket.send(json.dumps(status_msg))
                
                # Wait for status response
                status_response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                status_data = json.loads(status_response)
                
                self.record_result("WebSocket System Status",
                                 status_data.get("type") == "system_status",
                                 f"Response type: {status_data.get('type')}")
                
        except Exception as e:
            self.record_result("WebSocket Connection", False, str(e))
    
    async def test_voice_processing(self):
        """Test voice processing capabilities."""
        print("\n🎤 Testing Voice Processing...")
        
        # Create dummy audio data (silence)
        sample_rate = 16000
        duration = 1  # 1 second
        samples = sample_rate * duration
        audio_data = b'\x00' * (samples * 2)  # 16-bit audio
        audio_b64 = base64.b64encode(audio_data).decode('utf-8')
        
        # Test STT
        stt_request = {
            "audio_data": audio_b64,
            "format": "wav",
            "sample_rate": sample_rate,
            "session_id": "test-session"
        }
        
        await self.test_endpoint("Voice STT", "POST", f"{self.base_urls['voice']}/stt", 
                               json_data=stt_request)
        
        # Test TTS
        tts_request = {
            "text": "Hello, this is a test of the text to speech system.",
            "session_id": "test-session"
        }
        
        await self.test_endpoint("Voice TTS", "POST", f"{self.base_urls['voice']}/tts",
                               json_data=tts_request)
    
    async def test_agent_system(self):
        """Test agent system functionality."""
        print("\n🤖 Testing Agent System...")
        
        # Test task processing
        task_request = {
            "content": "Hello, can you help me with a simple math problem? What is 2 + 2?",
            "session_id": "test-session",
            "context": {"test": True},
            "priority": "medium"
        }
        
        await self.test_endpoint("Agent Task Processing", "POST", 
                               f"{self.base_urls['agent']}/tasks/process",
                               json_data=task_request)
        
        # Test metrics
        await self.test_endpoint("Agent Metrics", "GET", f"{self.base_urls['agent']}/metrics")
    
    async def test_integration(self):
        """Test end-to-end integration."""
        print("\n🔗 Testing Integration...")
        
        try:
            async with websockets.connect(self.websocket_url) as websocket:
                # Read initial connection status message
                initial_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                initial_data = json.loads(initial_response)
                
                # Test text input through WebSocket
                text_msg = {
                    "type": "text_input",
                    "data": {
                        "message": "What is the capital of France?",
                        "context": {"test": True}
                    }
                }
                
                await websocket.send(json.dumps(text_msg))
                
                # Wait for agent response
                response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                response_data = json.loads(response)
                
                self.record_result("End-to-End Text Processing",
                                 response_data.get("type") == "agent_response",
                                 f"Response type: {response_data.get('type')}")
                
                # Check if we got a reasonable response
                if response_data.get("type") == "agent_response":
                    agent_message = response_data.get("data", {}).get("message", "")
                    has_paris = "paris" in agent_message.lower()
                    self.record_result("Agent Response Quality", has_paris,
                                     f"Response contains 'Paris': {has_paris}")
                
        except Exception as e:
            self.record_result("End-to-End Integration", False, str(e))
    
    async def test_endpoint(self, test_name: str, method: str, url: str, json_data: Dict = None):
        """Test a specific HTTP endpoint."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method == "GET":
                    response = await client.get(url)
                elif method == "POST":
                    response = await client.post(url, json=json_data)
                else:
                    raise ValueError(f"Unsupported method: {method}")
                
                success = 200 <= response.status_code < 300
                details = f"Status: {response.status_code}"
                
                if success and response.headers.get("content-type", "").startswith("application/json"):
                    try:
                        data = response.json()
                        if isinstance(data, dict):
                            details += f", Keys: {list(data.keys())[:5]}"
                    except:
                        pass
                
                self.record_result(test_name, success, details)
                
        except Exception as e:
            self.record_result(test_name, False, str(e))
    
    def record_result(self, test_name: str, success: bool, details: str = ""):
        """Record a test result."""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "timestamp": time.time()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} {test_name}: {details}")
    
    def print_results(self):
        """Print test summary."""
        print("\n" + "=" * 50)
        print("📊 Test Results Summary")
        print("=" * 50)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n❌ Failed Tests:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  • {result['test']}: {result['details']}")
        
        print("\n🎯 Recommendations:")
        if failed_tests == 0:
            print("  • All tests passed! System is ready for use.")
        else:
            print("  • Check failed services and ensure all dependencies are running")
            print("  • Verify API keys and configuration in .env file")
            print("  • Check Docker container logs for detailed error information")
        
        # Save results to file
        results_file = Path("test_results.json")
        with open(results_file, "w") as f:
            json.dump(self.test_results, f, indent=2)
        print(f"  • Detailed results saved to {results_file}")

async def main():
    """Main test function."""
    tester = JarvisSystemTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
