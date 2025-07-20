"""
Voice processing models for STT and TTS operations.

These models define the structure for voice processing requests
and responses across different providers.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field

class STTProvider(str, Enum):
    WHISPERX = "whisperx"
    FASTER_WHISPER = "faster_whisper"
    ELEVENLABS = "elevenlabs"
    ASSEMBLYAI = "assemblyai"
    OPENAI_WHISPER = "openai_whisper"

class TTSProvider(str, Enum):
    COQUI = "coqui"
    ELEVENLABS = "elevenlabs"
    PYTTSX3 = "pyttsx3"
    OPENAI_TTS = "openai_tts"

class AudioFormat(str, Enum):
    WAV = "wav"
    MP3 = "mp3"
    WEBM = "webm"
    OGG = "ogg"
    FLAC = "flac"

class VoiceConfig(BaseModel):
    """Configuration for voice processing."""
    stt_provider: STTProvider = STTProvider.WHISPERX
    tts_provider: TTSProvider = TTSProvider.COQUI
    
    # STT Configuration
    stt_model: str = "base"
    stt_language: str = "en"
    stt_sample_rate: int = 16000
    stt_channels: int = 1
    
    # TTS Configuration
    tts_voice: str = "default"
    tts_speed: float = 1.0
    tts_pitch: float = 1.0
    tts_sample_rate: int = 22050
    
    # Audio Processing
    noise_reduction: bool = True
    echo_cancellation: bool = True
    auto_gain_control: bool = True
    
    # Quality Settings
    audio_quality: str = "medium"  # low, medium, high
    streaming_enabled: bool = True
    
    # Provider-specific settings
    provider_config: Dict[str, Any] = Field(default_factory=dict)

class STTRequest(BaseModel):
    """Speech-to-text request."""
    audio_data: str  # base64 encoded audio
    format: AudioFormat = AudioFormat.WAV
    sample_rate: int = 16000
    channels: int = 1
    language: Optional[str] = "en"
    model: Optional[str] = None
    provider: Optional[STTProvider] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class STTResponse(BaseModel):
    """Speech-to-text response."""
    text: str
    confidence: Optional[float] = None
    language: Optional[str] = None
    processing_time_ms: int
    provider: STTProvider
    model: str
    
    # Advanced features
    segments: Optional[List[Dict[str, Any]]] = None  # Word-level timestamps
    alternatives: Optional[List[str]] = None  # Alternative transcriptions
    
    # Metadata
    audio_duration_ms: Optional[int] = None
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class TTSRequest(BaseModel):
    """Text-to-speech request."""
    text: str
    voice: Optional[str] = "default"
    language: str = "en"
    speed: float = Field(1.0, ge=0.1, le=3.0)
    pitch: float = Field(1.0, ge=0.1, le=2.0)
    format: AudioFormat = AudioFormat.WAV
    sample_rate: int = 22050
    provider: Optional[TTSProvider] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class TTSResponse(BaseModel):
    """Text-to-speech response."""
    audio_data: str  # base64 encoded audio
    format: AudioFormat
    sample_rate: int
    duration_ms: int
    processing_time_ms: int
    provider: TTSProvider
    voice: str
    
    # Quality metrics
    audio_quality: Optional[str] = None
    file_size_bytes: Optional[int] = None
    
    # Metadata
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class VoiceActivityDetection(BaseModel):
    """Voice activity detection result."""
    is_speech: bool
    confidence: float = Field(ge=0.0, le=1.0)
    start_time_ms: Optional[int] = None
    end_time_ms: Optional[int] = None
    energy_level: Optional[float] = None

class AudioProcessingResult(BaseModel):
    """Result of audio preprocessing."""
    processed_audio: str  # base64 encoded
    original_format: AudioFormat
    processed_format: AudioFormat
    original_sample_rate: int
    processed_sample_rate: int
    noise_reduced: bool = False
    normalized: bool = False
    processing_time_ms: int
    quality_score: Optional[float] = None

class StreamingSTTChunk(BaseModel):
    """Streaming STT chunk for real-time transcription."""
    chunk_id: int
    text: str
    is_final: bool = False
    confidence: Optional[float] = None
    start_time_ms: Optional[int] = None
    end_time_ms: Optional[int] = None
    session_id: str

class StreamingTTSChunk(BaseModel):
    """Streaming TTS chunk for real-time synthesis."""
    chunk_id: int
    audio_data: str  # base64 encoded audio chunk
    is_final: bool = False
    duration_ms: int
    session_id: str

class VoiceMetrics(BaseModel):
    """Voice processing performance metrics."""
    stt_requests: int = 0
    stt_success_rate: float = 0.0
    stt_avg_processing_time_ms: float = 0.0
    stt_avg_confidence: float = 0.0
    
    tts_requests: int = 0
    tts_success_rate: float = 0.0
    tts_avg_processing_time_ms: float = 0.0
    tts_avg_audio_duration_ms: float = 0.0
    
    total_audio_processed_seconds: float = 0.0
    errors: int = 0
    last_updated: datetime = Field(default_factory=datetime.utcnow)

class VoiceProviderStatus(BaseModel):
    """Status of voice processing providers."""
    provider: Union[STTProvider, TTSProvider]
    available: bool
    latency_ms: Optional[int] = None
    error_rate: float = 0.0
    last_check: datetime = Field(default_factory=datetime.utcnow)
    config: Dict[str, Any] = Field(default_factory=dict)

class VoiceSystemStatus(BaseModel):
    """Overall voice system status."""
    stt_providers: List[VoiceProviderStatus]
    tts_providers: List[VoiceProviderStatus]
    active_sessions: int = 0
    processing_queue_size: int = 0
    system_health: str = "healthy"  # healthy, degraded, unhealthy
    uptime_seconds: int = 0
    metrics: VoiceMetrics

# Utility functions for voice processing
def create_stt_request(
    audio_data: str,
    format: AudioFormat = AudioFormat.WAV,
    sample_rate: int = 16000,
    language: str = "en",
    provider: Optional[STTProvider] = None,
    session_id: Optional[str] = None
) -> STTRequest:
    """Create an STT request."""
    return STTRequest(
        audio_data=audio_data,
        format=format,
        sample_rate=sample_rate,
        language=language,
        provider=provider,
        session_id=session_id
    )

def create_tts_request(
    text: str,
    voice: str = "default",
    language: str = "en",
    speed: float = 1.0,
    provider: Optional[TTSProvider] = None,
    session_id: Optional[str] = None
) -> TTSRequest:
    """Create a TTS request."""
    return TTSRequest(
        text=text,
        voice=voice,
        language=language,
        speed=speed,
        provider=provider,
        session_id=session_id
    )

def create_voice_config(
    stt_provider: STTProvider = STTProvider.WHISPERX,
    tts_provider: TTSProvider = TTSProvider.COQUI,
    **kwargs
) -> VoiceConfig:
    """Create a voice configuration."""
    return VoiceConfig(
        stt_provider=stt_provider,
        tts_provider=tts_provider,
        **kwargs
    )
