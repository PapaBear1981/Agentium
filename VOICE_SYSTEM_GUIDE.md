# 🎤 Jarvis Voice System Guide

## Overview

The Jarvis Voice System provides comprehensive Speech-to-Text (STT) and Text-to-Speech (TTS) capabilities with multiple provider support, optimized for both accuracy and performance.

## 🚀 Quick Start

### 1. Start the Voice System
```bash
./start_voice_system.sh
```

### 2. Test the System
```bash
python test_voice_system.py
```

### 3. Run Examples
```bash
python voice_example.py
```

## 📊 Supported Providers

### Speech-to-Text (STT)
- **ElevenLabs** ⭐ (Default) - Premium cloud-based STT with excellent accuracy
- **Faster-Whisper** - High performance with CTranslate2 optimization
- **WhisperX** - Word-level timestamps and speaker diarization
- **AssemblyAI** - Real-time streaming STT
- **OpenAI Whisper** - Original Whisper implementation

### Text-to-Speech (TTS)
- **ElevenLabs** ⭐ (Default) - Premium voice cloning and synthesis
- **Coqui TTS** - Open-source, high-quality synthesis
- **pyttsx3** - Lightweight offline TTS
- **OpenAI TTS** - Cloud-based TTS

## ⚙️ Configuration

### Environment Variables (.env)

```bash
# STT Configuration
STT_PROVIDER=elevenlabs
WHISPER_MODEL=large-v3
FASTER_WHISPER_BATCH_SIZE=16
FASTER_WHISPER_USE_BATCHED=true
FASTER_WHISPER_COMPUTE_TYPE=auto

# TTS Configuration
TTS_PROVIDER=elevenlabs
COQUI_MODEL=tts_models/en/ljspeech/tacotron2-DDC

# Hardware
USE_GPU=true

# API Keys (optional)
ELEVENLABS_API_KEY=your_key_here
ASSEMBLYAI_API_KEY=your_key_here
```

### Model Options

#### Whisper Models (STT)
- `tiny` - Fastest, lowest accuracy (~39 MB)
- `base` - Good balance (~74 MB)
- `small` - Better accuracy (~244 MB)
- `medium` - High accuracy (~769 MB)
- `large-v2` - Very high accuracy (~1550 MB)
- `large-v3` ⭐ - Best accuracy (~1550 MB)
- `distil-large-v3` - Optimized for Faster-Whisper

#### Coqui TTS Models
- `tts_models/en/ljspeech/tacotron2-DDC` ⭐ - Default English
- `tts_models/en/ljspeech/glow-tts` - Fast synthesis
- `tts_models/multilingual/multi-dataset/xtts_v2` - Voice cloning

## 🔧 API Usage

### Health Check
```bash
curl http://localhost:8002/health
```

### Speech-to-Text
```python
import httpx
import base64

# Read audio file
with open("audio.wav", "rb") as f:
    audio_data = base64.b64encode(f.read()).decode()

# Send STT request
async with httpx.AsyncClient() as client:
    response = await client.post("http://localhost:8002/stt", json={
        "audio_data": audio_data,
        "format": "wav",
        "sample_rate": 16000,
        "language": "en",
        "provider": "elevenlabs"
    })
    
    result = response.json()
    print(f"Transcription: {result['text']}")
```

### Text-to-Speech
```python
import httpx
import base64

# Send TTS request
async with httpx.AsyncClient() as client:
    response = await client.post("http://localhost:8002/tts", json={
        "text": "Hello, this is a test of the voice system.",
        "voice": "default",
        "language": "en",
        "speed": 1.0,
        "provider": "elevenlabs"
    })
    
    result = response.json()
    
    # Save audio file
    audio_bytes = base64.b64decode(result['audio_data'])
    with open("output.wav", "wb") as f:
        f.write(audio_bytes)
```

## 🎯 Performance Optimization

### Faster-Whisper Settings

#### CPU Optimization
```bash
STT_PROVIDER=faster_whisper
WHISPER_MODEL=distil-large-v3
FASTER_WHISPER_COMPUTE_TYPE=int8
USE_GPU=false
OMP_NUM_THREADS=4  # Set based on your CPU cores
```

#### GPU Optimization
```bash
STT_PROVIDER=faster_whisper
WHISPER_MODEL=large-v3
FASTER_WHISPER_COMPUTE_TYPE=float16
FASTER_WHISPER_USE_BATCHED=true
FASTER_WHISPER_BATCH_SIZE=16
USE_GPU=true
```

### Memory Management
- Use smaller models for limited memory
- Enable batched processing for throughput
- Use Voice Activity Detection (VAD) to skip silence

## 📈 Features

### Advanced STT Features
- **Word-level timestamps** - Precise timing for each word
- **Speaker diarization** - Identify different speakers
- **Voice Activity Detection** - Skip silent segments
- **Batch processing** - Process multiple files efficiently
- **Language detection** - Automatic language identification

### Advanced TTS Features
- **Voice cloning** - Clone voices from samples
- **Multi-language support** - 100+ languages
- **Speed control** - Adjust speech rate
- **Pitch control** - Modify voice pitch
- **Streaming synthesis** - Real-time audio generation

## 🔍 Monitoring

### System Status
```bash
curl http://localhost:8002/status
```

### Metrics
```bash
curl http://localhost:8002/metrics
```

### Available Providers
```bash
curl http://localhost:8002/providers
```

## 🐛 Troubleshooting

### Common Issues

#### Model Download Fails
```bash
# Pre-download models
python -c "from faster_whisper import WhisperModel; WhisperModel('large-v3')"
```

#### GPU Not Detected
```bash
# Check CUDA availability
python -c "import torch; print(torch.cuda.is_available())"
```

#### Memory Issues
```bash
# Use smaller model or CPU
STT_PROVIDER=faster_whisper
WHISPER_MODEL=base
USE_GPU=false
```

### Logs
```bash
# View service logs
docker-compose logs voice_adapter

# Follow logs in real-time
docker-compose logs -f voice_adapter
```

## 🔒 Security

### API Key Management
- Store API keys in `.env` file
- Never commit API keys to version control
- Use environment-specific configurations

### Network Security
- Configure CORS origins appropriately
- Use HTTPS in production
- Implement authentication if needed

## 🚀 Production Deployment

### Docker Compose Production
```yaml
voice_adapter:
  deploy:
    resources:
      limits:
        memory: 4G
        cpus: '2.0'
      reservations:
        memory: 2G
        cpus: '1.0'
  restart: unless-stopped
```

### Scaling Considerations
- Use load balancer for multiple instances
- Implement request queuing for high load
- Monitor memory usage and model loading
- Consider model caching strategies

## 📚 Integration Examples

### WebSocket Integration
```python
# Real-time voice processing
import websockets
import json

async def voice_websocket():
    uri = "ws://localhost:8000/ws/session_123"
    async with websockets.connect(uri) as websocket:
        # Send voice input
        await websocket.send(json.dumps({
            "type": "voice_input",
            "audio_data": base64_audio,
            "format": "wav"
        }))
        
        # Receive transcription
        response = await websocket.recv()
        data = json.loads(response)
        print(f"Transcription: {data['text']}")
```

### Frontend Integration
```javascript
// Browser audio recording and processing
navigator.mediaDevices.getUserMedia({ audio: true })
  .then(stream => {
    const recorder = new MediaRecorder(stream);
    recorder.ondataavailable = async (event) => {
      const audioBlob = event.data;
      const base64Audio = await blobToBase64(audioBlob);
      
      // Send to voice service
      const response = await fetch('/api/stt', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          audio_data: base64Audio,
          format: 'webm',
          provider: 'faster_whisper'
        })
      });
      
      const result = await response.json();
      console.log('Transcription:', result.text);
    };
  });
```

## 🎉 Next Steps

1. **Test the system** with your audio files
2. **Experiment with different models** for your use case
3. **Integrate with your applications** using the API
4. **Monitor performance** and optimize settings
5. **Scale up** for production workloads

For more examples and advanced usage, check the `voice_example.py` file!
