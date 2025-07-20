#!/usr/bin/env python3
"""
Voice System Usage Examples

This script demonstrates how to use the STT/TTS system
with practical examples.
"""

import asyncio
import base64
import json
import sys
from pathlib import Path

import httpx

# Add service directory to path
sys.path.append('service')

from models.voice import (
    STTRequest, TTSRequest, STTProvider, TTSProvider, 
    AudioFormat, create_stt_request, create_tts_request
)

class VoiceSystemClient:
    """Client for interacting with the voice processing system."""
    
    def __init__(self, base_url: str = "http://localhost:8002"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def transcribe_audio_file(self, audio_file_path: str, provider: STTProvider = STTProvider.ELEVENLABS) -> str:
        """Transcribe an audio file to text."""
        print(f"🎤 Transcribing audio file: {audio_file_path}")
        
        # Read and encode audio file
        with open(audio_file_path, 'rb') as f:
            audio_data = base64.b64encode(f.read()).decode('utf-8')
        
        # Create STT request
        request = create_stt_request(
            audio_data=audio_data,
            format=AudioFormat.WAV,  # Adjust based on your file format
            sample_rate=16000,
            language="en",
            provider=provider
        )
        
        # Send request
        response = await self.client.post(f"{self.base_url}/stt", json=request.dict())
        
        if response.status_code == 200:
            data = response.json()
            text = data['text']
            confidence = data['confidence']
            processing_time = data['processing_time_ms']
            
            print(f"✅ Transcription successful!")
            print(f"   Text: '{text}'")
            print(f"   Confidence: {confidence:.2f}")
            print(f"   Processing time: {processing_time}ms")
            
            return text
        else:
            print(f"❌ Transcription failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return ""
    
    async def synthesize_speech(self, text: str, output_file: str = "output.wav",
                              provider: TTSProvider = TTSProvider.ELEVENLABS) -> bool:
        """Synthesize text to speech and save to file."""
        print(f"🔊 Synthesizing speech: '{text[:50]}{'...' if len(text) > 50 else ''}'")
        
        # Create TTS request
        request = create_tts_request(
            text=text,
            voice="default",
            language="en",
            speed=1.0,
            provider=provider
        )
        
        # Send request
        response = await self.client.post(f"{self.base_url}/tts", json=request.dict())
        
        if response.status_code == 200:
            data = response.json()
            
            # Save audio file
            if data['audio_data']:
                audio_bytes = base64.b64decode(data['audio_data'])
                with open(output_file, 'wb') as f:
                    f.write(audio_bytes)
                
                print(f"✅ Speech synthesis successful!")
                print(f"   Output file: {output_file}")
                print(f"   Format: {data['format']}")
                print(f"   Duration: {data['duration_ms']}ms")
                print(f"   Processing time: {data['processing_time_ms']}ms")
                
                return True
            else:
                print("❌ No audio data received")
                return False
        else:
            print(f"❌ Speech synthesis failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
    
    async def get_system_info(self):
        """Get system information and available providers."""
        print("📊 Getting system information...")
        
        # Get providers
        response = await self.client.get(f"{self.base_url}/providers")
        if response.status_code == 200:
            providers = response.json()
            print("✅ Available providers:")
            print(f"   STT: {', '.join(providers['stt_providers'])}")
            print(f"   TTS: {', '.join(providers['tts_providers'])}")
            print(f"   Formats: {', '.join(providers['supported_formats'])}")
        
        # Get system status
        response = await self.client.get(f"{self.base_url}/status")
        if response.status_code == 200:
            status = response.json()
            print(f"✅ System status: {status['system_health']}")
            print(f"   Uptime: {status['uptime_seconds']}s")
        
        # Get health check
        response = await self.client.get(f"{self.base_url}/health")
        if response.status_code == 200:
            health = response.json()
            print(f"✅ Health check: {health['status']}")

async def demo_text_to_speech():
    """Demonstrate text-to-speech functionality."""
    print("\n" + "="*60)
    print("🔊 TEXT-TO-SPEECH DEMO")
    print("="*60)
    
    async with VoiceSystemClient() as client:
        # Example texts to synthesize
        texts = [
            "Hello! This is a test of the Jarvis voice system.",
            "The quick brown fox jumps over the lazy dog.",
            "Welcome to the future of AI-powered voice processing!",
        ]
        
        for i, text in enumerate(texts, 1):
            output_file = f"demo_output_{i}.wav"
            success = await client.synthesize_speech(text, output_file)
            if success:
                print(f"   🎵 Audio saved to: {output_file}")
            print()

async def demo_speech_to_text():
    """Demonstrate speech-to-text functionality."""
    print("\n" + "="*60)
    print("🎤 SPEECH-TO-TEXT DEMO")
    print("="*60)
    
    # Note: This would require actual audio files
    print("📝 To test STT, you would need audio files.")
    print("   Example usage:")
    print("   await client.transcribe_audio_file('your_audio.wav')")
    print()
    print("💡 You can record audio using:")
    print("   - Audacity (free audio editor)")
    print("   - Your phone's voice recorder")
    print("   - Online voice recorders")
    print("   - Python libraries like pyaudio")

async def demo_system_info():
    """Demonstrate system information retrieval."""
    print("\n" + "="*60)
    print("📊 SYSTEM INFORMATION DEMO")
    print("="*60)
    
    async with VoiceSystemClient() as client:
        await client.get_system_info()

async def main():
    """Main demo function."""
    print("🎯 Jarvis Voice System Demo")
    print("This demo shows how to use the STT/TTS system")
    print()
    
    try:
        # Check if service is running
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8002/health")
            if response.status_code != 200:
                print("❌ Voice service is not running!")
                print("   Please run: ./start_voice_system.sh")
                return
        
        # Run demos
        await demo_system_info()
        await demo_text_to_speech()
        await demo_speech_to_text()
        
        print("\n" + "="*60)
        print("🎉 Demo completed!")
        print("="*60)
        print()
        print("📚 Next steps:")
        print("1. Check the generated audio files")
        print("2. Try transcribing your own audio files")
        print("3. Integrate with your applications")
        print("4. Explore different providers (WhisperX, Coqui, ElevenLabs)")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        print("   Make sure the voice service is running: ./start_voice_system.sh")

if __name__ == "__main__":
    asyncio.run(main())
