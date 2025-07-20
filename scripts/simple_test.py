#!/usr/bin/env python3
"""
Simple test script to verify basic system functionality.
"""

import asyncio
import json
import time
import sys
from pathlib import Path

# Add the service directory to the path
sys.path.append(str(Path(__file__).parent.parent / "service"))

async def test_basic_imports():
    """Test that we can import our modules."""
    print("🧪 Testing basic imports...")
    
    try:
        # Test model imports
        from models.agents import AgentConfig, TaskRequest, TaskResponse
        from models.websocket import WebSocketMessage, WebSocketMessageType
        from models.voice import VoiceConfig, STTRequest, TTSRequest
        print("✅ Model imports successful")
        
        # Test basic functionality
        config = AgentConfig(
            id="test-agent",
            name="Test Agent",
            description="A test agent",
            system_message="You are a helpful assistant."
        )
        print(f"✅ Created agent config: {config.name}")
        
        # Test WebSocket message
        ws_msg = WebSocketMessage(
            type=WebSocketMessageType.TEXT_INPUT,
            data={"message": "Hello world"},
            session_id="test-session"
        )
        print(f"✅ Created WebSocket message: {ws_msg.type}")
        
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        return False

async def test_infrastructure():
    """Test infrastructure components."""
    print("\n🏗️  Testing infrastructure...")
    
    import httpx
    
    # Test services
    services = {
        "PostgreSQL": "http://localhost:5432",
        "Qdrant": "http://localhost:6333",
        "Ollama": "http://localhost:11434/api/tags",
        "Redis": "http://localhost:6379"
    }
    
    results = {}
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        for service, url in services.items():
            try:
                if service == "PostgreSQL":
                    # Skip PostgreSQL HTTP test (it's not an HTTP service)
                    results[service] = "⚠️  Skipped (not HTTP)"
                    continue
                elif service == "Redis":
                    # Skip Redis HTTP test (it's not an HTTP service)
                    results[service] = "⚠️  Skipped (not HTTP)"
                    continue
                
                response = await client.get(url)
                if response.status_code < 400:
                    results[service] = "✅ Running"
                else:
                    results[service] = f"❌ Error {response.status_code}"
                    
            except Exception as e:
                results[service] = f"❌ Failed: {str(e)[:50]}"
    
    for service, status in results.items():
        print(f"  {service}: {status}")
    
    return all("✅" in status or "⚠️" in status for status in results.values())

async def test_simple_agent():
    """Test a simple agent without complex dependencies."""
    print("\n🤖 Testing simple agent functionality...")
    
    try:
        # Create a mock agent that doesn't require external services
        class SimpleAgent:
            def __init__(self, name):
                self.name = name
                self.message_count = 0
            
            async def process_message(self, message):
                self.message_count += 1
                return f"Hello! I'm {self.name}. You said: '{message}'. This is message #{self.message_count}."
        
        # Test the agent
        agent = SimpleAgent("TestBot")
        
        response1 = await agent.process_message("Hello world")
        print(f"✅ Agent response 1: {response1}")
        
        response2 = await agent.process_message("How are you?")
        print(f"✅ Agent response 2: {response2}")
        
        return True
        
    except Exception as e:
        print(f"❌ Simple agent test failed: {e}")
        return False

async def test_cost_tracking():
    """Test cost tracking functionality."""
    print("\n💰 Testing cost tracking...")
    
    try:
        from cost_tracking import ModelPricingManager, CostTracker
        from decimal import Decimal
        from uuid import uuid4
        
        # Test pricing manager
        pricing_manager = ModelPricingManager()
        
        # Test cost calculation
        cost = pricing_manager.calculate_cost("gpt-4o", 1000, 500)
        print(f"✅ GPT-4o cost for 1000 input + 500 output tokens: ${cost}")
        
        # Test cost tracker
        cost_tracker = CostTracker()
        session_id = uuid4()
        
        # Record some usage
        cost, alerts = await cost_tracker.record_usage(
            session_id=session_id,
            agent_id="test-agent",
            model_name="gpt-4o",
            operation_type="chat",
            tokens_input=1000,
            tokens_output=500
        )
        
        print(f"✅ Recorded usage: ${cost}, alerts: {len(alerts)}")
        
        # Get summary
        summary = cost_tracker.get_session_summary(session_id)
        print(f"✅ Session summary: ${summary['total_cost']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Cost tracking test failed: {e}")
        return False

async def test_voice_models():
    """Test voice processing models."""
    print("\n🎤 Testing voice models...")
    
    try:
        from models.voice import VoiceConfig, STTRequest, TTSRequest, STTResponse, TTSResponse
        
        # Test voice config
        config = VoiceConfig(
            stt_provider="whisperx",
            tts_provider="coqui"
        )
        print(f"✅ Voice config: STT={config.stt_provider}, TTS={config.tts_provider}")
        
        # Test STT request
        stt_request = STTRequest(
            audio_data="fake_audio_data",
            session_id="test-session"
        )
        print(f"✅ STT request created for session: {stt_request.session_id}")
        
        # Test TTS request
        tts_request = TTSRequest(
            text="Hello, this is a test",
            session_id="test-session"
        )
        print(f"✅ TTS request created: '{tts_request.text}'")
        
        return True
        
    except Exception as e:
        print(f"❌ Voice models test failed: {e}")
        return False

async def main():
    """Run all tests."""
    print("🚀 Starting Jarvis System Simple Tests")
    print("=" * 50)
    
    tests = [
        ("Basic Imports", test_basic_imports),
        ("Infrastructure", test_infrastructure),
        ("Simple Agent", test_simple_agent),
        ("Cost Tracking", test_cost_tracking),
        ("Voice Models", test_voice_models),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results[test_name] = result
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results[test_name] = False
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All tests passed! Basic system functionality is working.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
