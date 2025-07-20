#!/usr/bin/env python3
"""
Voice System Performance Test

This script compares the performance of different STT and TTS providers
to help you choose the best option for your use case.
"""

import asyncio
import base64
import json
import sys
import time
import wave
from pathlib import Path
from typing import Dict, List, Tuple

import httpx
import numpy as np

# Add service directory to path
sys.path.append('service')

from models.voice import (
    STTRequest, TTSRequest, STTProvider, TTSProvider, 
    AudioFormat, create_stt_request, create_tts_request
)

class VoicePerformanceTester:
    """Performance testing for voice processing providers."""
    
    def __init__(self, base_url: str = "http://localhost:8002"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=120.0)
        self.results = {}
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    def create_test_audio(self, duration: float = 5.0, sample_rate: int = 16000, 
                         frequency: float = 440.0) -> str:
        """Create a test audio signal and return as base64."""
        # Generate a sine wave
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio = np.sin(2 * np.pi * frequency * t) * 0.3
        
        # Add some variation to make it more realistic
        audio += np.sin(2 * np.pi * frequency * 1.5 * t) * 0.1
        audio += np.random.normal(0, 0.05, len(audio))  # Add noise
        
        # Convert to 16-bit PCM
        audio_int16 = (audio * 32767).astype(np.int16)
        
        # Create WAV file in memory
        import io
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_int16.tobytes())
        
        buffer.seek(0)
        return base64.b64encode(buffer.read()).decode('utf-8')
    
    async def test_stt_provider(self, provider: STTProvider, test_name: str, 
                               audio_duration: float = 5.0) -> Dict:
        """Test a specific STT provider."""
        print(f"🔍 Testing {test_name}...")
        
        # Create test audio
        audio_data = self.create_test_audio(duration=audio_duration)
        
        # Create STT request
        request = create_stt_request(
            audio_data=audio_data,
            format=AudioFormat.WAV,
            sample_rate=16000,
            language="en",
            provider=provider
        )
        
        # Measure performance
        start_time = time.time()
        
        try:
            response = await self.client.post(f"{self.base_url}/stt", json=request.dict())
            
            if response.status_code == 200:
                data = response.json()
                total_time = time.time() - start_time
                
                result = {
                    "provider": provider.value,
                    "success": True,
                    "text": data['text'],
                    "confidence": data['confidence'],
                    "processing_time_ms": data['processing_time_ms'],
                    "total_time_ms": int(total_time * 1000),
                    "audio_duration_ms": int(audio_duration * 1000),
                    "real_time_factor": data['processing_time_ms'] / (audio_duration * 1000),
                    "model": data.get('model', 'unknown'),
                    "segments": len(data.get('segments', [])),
                    "error": None
                }
                
                print(f"✅ {test_name} successful")
                print(f"   Processing time: {result['processing_time_ms']}ms")
                print(f"   Total time: {result['total_time_ms']}ms")
                print(f"   Real-time factor: {result['real_time_factor']:.2f}x")
                print(f"   Confidence: {result['confidence']:.2f}")
                
                return result
            else:
                print(f"❌ {test_name} failed: {response.status_code}")
                return {
                    "provider": provider.value,
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "processing_time_ms": 0,
                    "total_time_ms": int((time.time() - start_time) * 1000)
                }
                
        except Exception as e:
            print(f"❌ {test_name} error: {e}")
            return {
                "provider": provider.value,
                "success": False,
                "error": str(e),
                "processing_time_ms": 0,
                "total_time_ms": int((time.time() - start_time) * 1000)
            }
    
    async def test_tts_provider(self, provider: TTSProvider, test_name: str, 
                               text: str = "This is a performance test of the text-to-speech system.") -> Dict:
        """Test a specific TTS provider."""
        print(f"🔍 Testing {test_name}...")
        
        # Create TTS request
        request = create_tts_request(
            text=text,
            voice="default",
            language="en",
            speed=1.0,
            provider=provider
        )
        
        # Measure performance
        start_time = time.time()
        
        try:
            response = await self.client.post(f"{self.base_url}/tts", json=request.dict())
            
            if response.status_code == 200:
                data = response.json()
                total_time = time.time() - start_time
                
                result = {
                    "provider": provider.value,
                    "success": True,
                    "text_length": len(text),
                    "audio_duration_ms": data['duration_ms'],
                    "processing_time_ms": data['processing_time_ms'],
                    "total_time_ms": int(total_time * 1000),
                    "real_time_factor": data['processing_time_ms'] / max(data['duration_ms'], 1),
                    "format": data['format'],
                    "sample_rate": data['sample_rate'],
                    "error": None
                }
                
                print(f"✅ {test_name} successful")
                print(f"   Processing time: {result['processing_time_ms']}ms")
                print(f"   Audio duration: {result['audio_duration_ms']}ms")
                print(f"   Real-time factor: {result['real_time_factor']:.2f}x")
                
                return result
            else:
                print(f"❌ {test_name} failed: {response.status_code}")
                return {
                    "provider": provider.value,
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "processing_time_ms": 0,
                    "total_time_ms": int((time.time() - start_time) * 1000)
                }
                
        except Exception as e:
            print(f"❌ {test_name} error: {e}")
            return {
                "provider": provider.value,
                "success": False,
                "error": str(e),
                "processing_time_ms": 0,
                "total_time_ms": int((time.time() - start_time) * 1000)
            }
    
    async def run_stt_performance_tests(self) -> Dict:
        """Run STT performance tests for all available providers."""
        print("🎤 STT Performance Tests")
        print("=" * 50)
        
        stt_tests = [
            (STTProvider.ELEVENLABS, "ElevenLabs"),
            (STTProvider.FASTER_WHISPER, "Faster-Whisper"),
            (STTProvider.WHISPERX, "WhisperX"),
        ]
        
        results = {}
        
        for provider, name in stt_tests:
            try:
                result = await self.test_stt_provider(provider, name, audio_duration=5.0)
                results[provider.value] = result
                print()
            except Exception as e:
                print(f"❌ Failed to test {name}: {e}")
                results[provider.value] = {
                    "provider": provider.value,
                    "success": False,
                    "error": str(e)
                }
        
        return results
    
    async def run_tts_performance_tests(self) -> Dict:
        """Run TTS performance tests for all available providers."""
        print("🔊 TTS Performance Tests")
        print("=" * 50)
        
        test_text = "The quick brown fox jumps over the lazy dog. This is a performance test of the text-to-speech system with multiple sentences to evaluate processing speed and quality."
        
        tts_tests = [
            (TTSProvider.ELEVENLABS, "ElevenLabs"),
            (TTSProvider.COQUI, "Coqui TTS"),
        ]
        
        results = {}
        
        for provider, name in tts_tests:
            try:
                result = await self.test_tts_provider(provider, name, text=test_text)
                results[provider.value] = result
                print()
            except Exception as e:
                print(f"❌ Failed to test {name}: {e}")
                results[provider.value] = {
                    "provider": provider.value,
                    "success": False,
                    "error": str(e)
                }
        
        return results
    
    def print_performance_summary(self, stt_results: Dict, tts_results: Dict):
        """Print a summary of performance results."""
        print("\n📊 Performance Summary")
        print("=" * 60)
        
        # STT Summary
        print("\n🎤 Speech-to-Text Performance:")
        print("-" * 40)
        successful_stt = {k: v for k, v in stt_results.items() if v.get('success', False)}
        
        if successful_stt:
            # Sort by real-time factor (lower is better)
            sorted_stt = sorted(successful_stt.items(), key=lambda x: x[1].get('real_time_factor', float('inf')))
            
            for provider, result in sorted_stt:
                rtf = result.get('real_time_factor', 0)
                processing_time = result.get('processing_time_ms', 0)
                confidence = result.get('confidence', 0)
                
                print(f"  {provider:15} | RTF: {rtf:5.2f}x | Time: {processing_time:4d}ms | Conf: {confidence:.2f}")
        else:
            print("  No successful STT tests")
        
        # TTS Summary
        print("\n🔊 Text-to-Speech Performance:")
        print("-" * 40)
        successful_tts = {k: v for k, v in tts_results.items() if v.get('success', False)}
        
        if successful_tts:
            # Sort by real-time factor (lower is better)
            sorted_tts = sorted(successful_tts.items(), key=lambda x: x[1].get('real_time_factor', float('inf')))
            
            for provider, result in sorted_tts:
                rtf = result.get('real_time_factor', 0)
                processing_time = result.get('processing_time_ms', 0)
                audio_duration = result.get('audio_duration_ms', 0)
                
                print(f"  {provider:15} | RTF: {rtf:5.2f}x | Time: {processing_time:4d}ms | Audio: {audio_duration:4d}ms")
        else:
            print("  No successful TTS tests")
        
        print("\n💡 Notes:")
        print("  - RTF (Real-Time Factor): Lower is better (< 1.0 means faster than real-time)")
        print("  - Processing time includes model loading and inference")
        print("  - First run may be slower due to model loading")

async def main():
    """Main performance test function."""
    print("🚀 Voice System Performance Test")
    print("This test compares different STT and TTS providers")
    print()
    
    try:
        # Check if service is running
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8002/health")
            if response.status_code != 200:
                print("❌ Voice service is not running!")
                print("   Please run: ./start_voice_system.sh")
                return
        
        async with VoicePerformanceTester() as tester:
            # Run STT tests
            stt_results = await tester.run_stt_performance_tests()
            
            # Run TTS tests
            tts_results = await tester.run_tts_performance_tests()
            
            # Print summary
            tester.print_performance_summary(stt_results, tts_results)
            
            # Save results to file
            results = {
                "timestamp": time.time(),
                "stt_results": stt_results,
                "tts_results": tts_results
            }
            
            with open("voice_performance_results.json", "w") as f:
                json.dump(results, f, indent=2)
            
            print(f"\n💾 Results saved to: voice_performance_results.json")
        
    except Exception as e:
        print(f"❌ Performance test failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
