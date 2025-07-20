#!/usr/bin/env python3
"""
Voice System Test Script

This script tests the STT/TTS system implementation to ensure
all components are working correctly.
"""

import asyncio
import base64
import json
import os
import sys
import time
import wave
from pathlib import Path
from typing import Dict, Any

import httpx
import numpy as np
import soundfile as sf

# Add service directory to path
sys.path.append('service')

from models.voice import (
    STTRequest, TTSRequest, STTProvider, TTSProvider, 
    AudioFormat, create_stt_request, create_tts_request
)

class VoiceSystemTester:
    """Test suite for the voice processing system."""
    
    def __init__(self, base_url: str = "http://localhost:8002"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=60.0)
        self.test_results = {}
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    def create_test_audio(self, duration: float = 2.0, sample_rate: int = 16000) -> str:
        """Create a test audio signal (sine wave) and return as base64."""
        # Generate a 440Hz sine wave (A note)
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio = np.sin(2 * np.pi * 440 * t) * 0.3  # 440Hz sine wave
        
        # Convert to 16-bit PCM
        audio_int16 = (audio * 32767).astype(np.int16)
        
        # Create WAV file in memory
        import io
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_int16.tobytes())
        
        # Return base64 encoded audio
        buffer.seek(0)
        return base64.b64encode(buffer.read()).decode('utf-8')
    
    async def test_health_check(self) -> bool:
        """Test the health check endpoint."""
        print("🔍 Testing health check...")
        try:
            response = await self.client.get(f"{self.base_url}/health")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Health check passed: {data['status']}")
                print(f"   Uptime: {data['uptime_seconds']}s")
                print(f"   Providers: {data['providers']}")
                return True
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False
    
    async def test_providers_endpoint(self) -> bool:
        """Test the providers endpoint."""
        print("\n🔍 Testing providers endpoint...")
        try:
            response = await self.client.get(f"{self.base_url}/providers")
            if response.status_code == 200:
                data = response.json()
                print("✅ Providers endpoint working")
                print(f"   STT Providers: {data['stt_providers']}")
                print(f"   TTS Providers: {data['tts_providers']}")
                print(f"   Supported Formats: {data['supported_formats']}")
                return True
            else:
                print(f"❌ Providers endpoint failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Providers endpoint error: {e}")
            return False
    
    async def test_stt_elevenlabs(self) -> bool:
        """Test STT with ElevenLabs provider."""
        print("\n🔍 Testing STT with ElevenLabs...")
        try:
            # Create test audio
            audio_data = self.create_test_audio(duration=3.0)

            # Create STT request
            request = create_stt_request(
                audio_data=audio_data,
                format=AudioFormat.WAV,
                sample_rate=16000,
                language="en",
                provider=STTProvider.ELEVENLABS
            )

            # Send request
            response = await self.client.post(
                f"{self.base_url}/stt",
                json=request.dict()
            )

            if response.status_code == 200:
                data = response.json()
                print(f"✅ ElevenLabs STT successful")
                print(f"   Text: '{data['text']}'")
                print(f"   Confidence: {data['confidence']}")
                print(f"   Processing time: {data['processing_time_ms']}ms")
                print(f"   Provider: {data['provider']}")
                return True
            else:
                print(f"❌ ElevenLabs STT failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False

        except Exception as e:
            print(f"❌ ElevenLabs STT error: {e}")
            return False

    async def test_stt_faster_whisper(self) -> bool:
        """Test STT with Faster-Whisper provider."""
        print("\n🔍 Testing STT with Faster-Whisper...")
        try:
            # Create test audio
            audio_data = self.create_test_audio(duration=2.0)

            # Create STT request
            request = create_stt_request(
                audio_data=audio_data,
                format=AudioFormat.WAV,
                sample_rate=16000,
                language="en",
                provider=STTProvider.FASTER_WHISPER
            )

            # Send request
            response = await self.client.post(
                f"{self.base_url}/stt",
                json=request.dict()
            )

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Faster-Whisper STT successful")
                print(f"   Text: '{data['text']}'")
                print(f"   Confidence: {data['confidence']}")
                print(f"   Processing time: {data['processing_time_ms']}ms")
                print(f"   Model: {data['model']}")
                if 'segments' in data and data['segments']:
                    print(f"   Segments: {len(data['segments'])}")
                return True
            else:
                print(f"❌ Faster-Whisper STT failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False

        except Exception as e:
            print(f"❌ Faster-Whisper STT error: {e}")
            return False

    async def test_stt_whisperx(self) -> bool:
        """Test STT with WhisperX provider."""
        print("\n🔍 Testing STT with WhisperX...")
        try:
            # Create test audio
            audio_data = self.create_test_audio(duration=1.0)

            # Create STT request
            request = create_stt_request(
                audio_data=audio_data,
                format=AudioFormat.WAV,
                sample_rate=16000,
                language="en",
                provider=STTProvider.WHISPERX
            )

            # Send request
            response = await self.client.post(
                f"{self.base_url}/stt",
                json=request.dict()
            )

            if response.status_code == 200:
                data = response.json()
                print(f"✅ WhisperX STT successful")
                print(f"   Text: '{data['text']}'")
                print(f"   Confidence: {data['confidence']}")
                print(f"   Processing time: {data['processing_time_ms']}ms")
                return True
            else:
                print(f"❌ WhisperX STT failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False

        except Exception as e:
            print(f"❌ WhisperX STT error: {e}")
            return False
    
    async def test_tts_elevenlabs(self) -> bool:
        """Test TTS with ElevenLabs provider."""
        print("\n🔍 Testing TTS with ElevenLabs...")
        try:
            # Create TTS request
            request = create_tts_request(
                text="Hello, this is a test of the ElevenLabs text-to-speech system.",
                voice="default",
                language="en",
                speed=1.0,
                provider=TTSProvider.ELEVENLABS
            )

            # Send request
            response = await self.client.post(
                f"{self.base_url}/tts",
                json=request.dict()
            )

            if response.status_code == 200:
                data = response.json()
                print(f"✅ ElevenLabs TTS successful")
                print(f"   Audio format: {data['format']}")
                print(f"   Sample rate: {data['sample_rate']}")
                print(f"   Duration: {data['duration_ms']}ms")
                print(f"   Processing time: {data['processing_time_ms']}ms")
                print(f"   Provider: {data['provider']}")

                # Save audio file for verification
                if data['audio_data']:
                    audio_bytes = base64.b64decode(data['audio_data'])
                    with open('test_elevenlabs_output.wav', 'wb') as f:
                        f.write(audio_bytes)
                    print(f"   Audio saved to: test_elevenlabs_output.wav")

                return True
            else:
                print(f"❌ ElevenLabs TTS failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False

        except Exception as e:
            print(f"❌ ElevenLabs TTS error: {e}")
            return False

    async def test_tts_coqui(self) -> bool:
        """Test TTS with Coqui provider."""
        print("\n🔍 Testing TTS with Coqui...")
        try:
            # Create TTS request
            request = create_tts_request(
                text="Hello, this is a test of the Coqui text-to-speech system.",
                voice="default",
                language="en",
                speed=1.0,
                provider=TTSProvider.COQUI
            )
            
            # Send request
            response = await self.client.post(
                f"{self.base_url}/tts",
                json=request.dict()
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Coqui TTS successful")
                print(f"   Audio format: {data['format']}")
                print(f"   Sample rate: {data['sample_rate']}")
                print(f"   Duration: {data['duration_ms']}ms")
                print(f"   Processing time: {data['processing_time_ms']}ms")
                
                # Save audio file for verification
                if data['audio_data']:
                    audio_bytes = base64.b64decode(data['audio_data'])
                    with open('test_output.wav', 'wb') as f:
                        f.write(audio_bytes)
                    print(f"   Audio saved to: test_output.wav")
                
                return True
            else:
                print(f"❌ Coqui TTS failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Coqui TTS error: {e}")
            return False
    
    async def test_system_status(self) -> bool:
        """Test the system status endpoint."""
        print("\n🔍 Testing system status...")
        try:
            response = await self.client.get(f"{self.base_url}/status")
            if response.status_code == 200:
                data = response.json()
                print("✅ System status working")
                print(f"   System health: {data['system_health']}")
                print(f"   STT providers: {len(data['stt_providers'])}")
                print(f"   TTS providers: {len(data['tts_providers'])}")
                print(f"   Uptime: {data['uptime_seconds']}s")
                return True
            else:
                print(f"❌ System status failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ System status error: {e}")
            return False
    
    async def run_all_tests(self) -> Dict[str, bool]:
        """Run all tests and return results."""
        print("🚀 Starting Voice System Tests\n")
        
        tests = [
            ("Health Check", self.test_health_check),
            ("Providers Endpoint", self.test_providers_endpoint),
            ("STT ElevenLabs", self.test_stt_elevenlabs),
            ("TTS ElevenLabs", self.test_tts_elevenlabs),
            ("STT Faster-Whisper", self.test_stt_faster_whisper),
            ("TTS Coqui", self.test_tts_coqui),
            ("System Status", self.test_system_status),
        ]
        
        results = {}
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            try:
                result = await test_func()
                results[test_name] = result
                if result:
                    passed += 1
            except Exception as e:
                print(f"❌ {test_name} failed with exception: {e}")
                results[test_name] = False
        
        print(f"\n📊 Test Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
        
        if passed == total:
            print("🎉 All tests passed! Voice system is working correctly.")
        else:
            print("⚠️  Some tests failed. Check the output above for details.")
        
        return results

async def main():
    """Main test function."""
    # Check if voice service is running
    print("🔧 Voice System Test Suite")
    print("=" * 50)
    
    async with VoiceSystemTester() as tester:
        results = await tester.run_all_tests()
    
    return results

if __name__ == "__main__":
    asyncio.run(main())
