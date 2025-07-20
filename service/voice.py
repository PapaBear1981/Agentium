"""
Voice Processing System for Jarvis Multi-Agent AI System.

This module provides STT (Speech-to-Text) and TTS (Text-to-Speech) capabilities
with support for multiple providers including WhisperX, Coqui, ElevenLabs, and more.
"""

import asyncio
import base64
import io
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, AsyncIterator

import numpy as np
from pydantic import BaseModel

from models.voice import (
    STTProvider, TTSProvider, AudioFormat, VoiceConfig,
    STTRequest, STTResponse, TTSRequest, TTSResponse,
    StreamingSTTChunk, StreamingTTSChunk, VoiceMetrics
)

logger = logging.getLogger(__name__)

class VoiceProcessingError(Exception):
    """Base exception for voice processing errors."""
    pass

class STTProviderError(VoiceProcessingError):
    """Exception for STT provider errors."""
    pass

class TTSProviderError(VoiceProcessingError):
    """Exception for TTS provider errors."""
    pass

# Abstract base classes for providers
class STTProviderBase(ABC):
    """Abstract base class for STT providers."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.metrics = VoiceMetrics()
    
    @abstractmethod
    async def transcribe(self, request: STTRequest) -> STTResponse:
        """Transcribe audio to text."""
        pass
    
    @abstractmethod
    async def transcribe_streaming(self, audio_stream) -> AsyncIterator[StreamingSTTChunk]:
        """Transcribe audio stream in real-time."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is healthy."""
        pass

class TTSProviderBase(ABC):
    """Abstract base class for TTS providers."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.metrics = VoiceMetrics()
    
    @abstractmethod
    async def synthesize(self, request: TTSRequest) -> TTSResponse:
        """Synthesize text to speech."""
        pass
    
    @abstractmethod
    async def synthesize_streaming(self, request: TTSRequest) -> AsyncIterator[StreamingTTSChunk]:
        """Synthesize text to speech with streaming."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is healthy."""
        pass

# WhisperX STT Provider
class WhisperXSTTProvider(STTProviderBase):
    """WhisperX STT provider implementation."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.model = None
        self.device = config.get("device", "cpu")
        self.model_name = config.get("model", "base")
        self.batch_size = config.get("batch_size", 16)
        
    async def _load_model(self):
        """Load WhisperX model if not already loaded."""
        if self.model is None:
            try:
                import whisperx
                self.model = whisperx.load_model(
                    self.model_name, 
                    self.device,
                    compute_type="float16" if self.device != "cpu" else "int8"
                )
                logger.info(f"Loaded WhisperX model: {self.model_name}")
            except ImportError:
                raise STTProviderError("WhisperX not installed. Install with: pip install whisperx")
            except Exception as e:
                raise STTProviderError(f"Failed to load WhisperX model: {e}")
    
    async def transcribe(self, request: STTRequest) -> STTResponse:
        """Transcribe audio using WhisperX."""
        start_time = time.time()
        
        try:
            await self._load_model()
            
            # Decode base64 audio
            audio_bytes = base64.b64decode(request.audio_data)
            
            # Convert to numpy array (WhisperX expects this format)
            audio_array = self._bytes_to_audio_array(audio_bytes, request.sample_rate)
            
            # Transcribe
            result = self.model.transcribe(
                audio_array,
                batch_size=self.batch_size,
                language=request.language
            )
            
            processing_time = int((time.time() - start_time) * 1000)
            
            # Extract segments for detailed results
            segments = []
            if "segments" in result:
                for segment in result["segments"]:
                    segments.append({
                        "start": segment.get("start", 0),
                        "end": segment.get("end", 0),
                        "text": segment.get("text", ""),
                        "confidence": segment.get("confidence", 0.0)
                    })
            
            response = STTResponse(
                text=result.get("text", ""),
                confidence=result.get("confidence", 0.0),
                language=result.get("language", request.language),
                processing_time_ms=processing_time,
                provider=STTProvider.WHISPERX,
                model=self.model_name,
                segments=segments,
                success=True
            )
            
            # Update metrics
            self.metrics.stt_requests += 1
            self.metrics.stt_avg_processing_time_ms = (
                (self.metrics.stt_avg_processing_time_ms * (self.metrics.stt_requests - 1) + processing_time) 
                / self.metrics.stt_requests
            )
            
            return response
            
        except Exception as e:
            logger.error(f"WhisperX transcription failed: {e}")
            self.metrics.errors += 1
            return STTResponse(
                text="",
                processing_time_ms=int((time.time() - start_time) * 1000),
                provider=STTProvider.WHISPERX,
                model=self.model_name,
                success=False,
                error=str(e)
            )


# Faster-Whisper STT Provider
class FasterWhisperSTTProvider(STTProviderBase):
    """Faster-Whisper STT provider implementation."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.model = None
        self.model_name = config.get("model", "large-v3")
        self.device = config.get("device", "cpu")
        self.compute_type = config.get("compute_type", "int8")
        self.batch_size = config.get("batch_size", 16)
        self.use_batched = config.get("use_batched", False)
        self.batched_model = None

    async def _load_model(self):
        """Load Faster-Whisper model if not already loaded."""
        if self.model is None:
            try:
                from faster_whisper import WhisperModel, BatchedInferencePipeline

                # Load the base model
                self.model = WhisperModel(
                    self.model_name,
                    device=self.device,
                    compute_type=self.compute_type
                )

                # Optionally create batched pipeline for better performance
                if self.use_batched:
                    self.batched_model = BatchedInferencePipeline(model=self.model)

                logger.info(f"Loaded Faster-Whisper model: {self.model_name}")

            except ImportError:
                raise STTProviderError("Faster-Whisper not installed. Install with: pip install faster-whisper")
            except Exception as e:
                raise STTProviderError(f"Failed to load Faster-Whisper model: {e}")

    async def transcribe(self, request: STTRequest) -> STTResponse:
        """Transcribe audio using Faster-Whisper."""
        start_time = time.time()

        try:
            await self._load_model()

            # Decode base64 audio and save to temporary file
            audio_bytes = base64.b64decode(request.audio_data)

            # Create temporary file for audio
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_file.write(audio_bytes)
                temp_file_path = temp_file.name

            try:
                # Choose model based on configuration
                model_to_use = self.batched_model if self.use_batched else self.model

                # Transcribe with appropriate parameters
                if self.use_batched:
                    segments, info = model_to_use.transcribe(
                        temp_file_path,
                        batch_size=self.batch_size,
                        language=request.language,
                        word_timestamps=True,
                        vad_filter=True  # Enable voice activity detection
                    )
                else:
                    segments, info = model_to_use.transcribe(
                        temp_file_path,
                        beam_size=5,
                        language=request.language,
                        condition_on_previous_text=False,
                        word_timestamps=True,
                        vad_filter=True
                    )

                # Convert generator to list to get all segments
                segments = list(segments)

                # Combine all segment texts
                full_text = " ".join([segment.text.strip() for segment in segments])

                # Calculate average confidence (if available)
                confidence = getattr(info, 'language_probability', 0.0)

                processing_time = int((time.time() - start_time) * 1000)

                # Create detailed segments for response
                detailed_segments = []
                for segment in segments:
                    segment_data = {
                        "start": segment.start,
                        "end": segment.end,
                        "text": segment.text.strip(),
                        "confidence": getattr(segment, 'confidence', confidence)
                    }

                    # Add word-level timestamps if available
                    if hasattr(segment, 'words') and segment.words:
                        segment_data["words"] = [
                            {
                                "start": word.start,
                                "end": word.end,
                                "word": word.word,
                                "confidence": getattr(word, 'probability', confidence)
                            }
                            for word in segment.words
                        ]

                    detailed_segments.append(segment_data)

                response = STTResponse(
                    text=full_text,
                    confidence=confidence,
                    processing_time_ms=processing_time,
                    provider=STTProvider.FASTER_WHISPER,
                    model=self.model_name,
                    language=info.language,
                    segments=detailed_segments,
                    success=True
                )

            finally:
                # Clean up temporary file
                import os
                try:
                    os.unlink(temp_file_path)
                except:
                    pass

            return response

        except Exception as e:
            logger.error(f"Faster-Whisper STT failed: {e}")
            return STTResponse(
                text="",
                processing_time_ms=int((time.time() - start_time) * 1000),
                provider=STTProvider.FASTER_WHISPER,
                model=request.model or self.model_name,
                success=False,
                error=str(e)
            )
    
    async def transcribe_streaming(self, audio_stream) -> AsyncIterator[StreamingSTTChunk]:
        """Stream transcription (placeholder - WhisperX doesn't natively support streaming)."""
        # This would require implementing a sliding window approach
        # For now, we'll process chunks as they come
        chunk_id = 0
        async for audio_chunk in audio_stream:
            try:
                # Process chunk
                request = STTRequest(audio_data=audio_chunk)
                response = await self.transcribe(request)
                
                yield StreamingSTTChunk(
                    chunk_id=chunk_id,
                    text=response.text,
                    is_final=True,
                    confidence=response.confidence,
                    session_id=request.session_id or ""
                )
                chunk_id += 1
            except Exception as e:
                logger.error(f"Streaming transcription error: {e}")
                yield StreamingSTTChunk(
                    chunk_id=chunk_id,
                    text="",
                    is_final=True,
                    session_id=request.session_id or ""
                )
    
    async def health_check(self) -> bool:
        """Check WhisperX health."""
        try:
            await self._load_model()
            return self.model is not None
        except Exception:
            return False
    
    def _bytes_to_audio_array(self, audio_bytes: bytes, sample_rate: int) -> np.ndarray:
        """Convert audio bytes to numpy array."""
        try:
            import librosa
            audio_io = io.BytesIO(audio_bytes)
            audio_array, _ = librosa.load(audio_io, sr=sample_rate, mono=True)
            return audio_array
        except ImportError:
            raise STTProviderError("librosa not installed. Install with: pip install librosa")
        except Exception as e:
            raise STTProviderError(f"Failed to convert audio: {e}")

# Coqui TTS Provider
class CoquiTTSProvider(TTSProviderBase):
    """Coqui TTS provider implementation."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.tts = None
        self.model_name = config.get("model", "tts_models/en/ljspeech/tacotron2-DDC")
        self.device = config.get("device", "cpu")
    
    async def _load_model(self):
        """Load Coqui TTS model if not already loaded."""
        if self.tts is None:
            try:
                from TTS.api import TTS
                self.tts = TTS(self.model_name).to(self.device)
                logger.info(f"Loaded Coqui TTS model: {self.model_name}")
            except ImportError:
                raise TTSProviderError("Coqui TTS not installed. Install with: pip install TTS")
            except Exception as e:
                raise TTSProviderError(f"Failed to load Coqui TTS model: {e}")
    
    async def synthesize(self, request: TTSRequest) -> TTSResponse:
        """Synthesize speech using Coqui TTS."""
        start_time = time.time()
        
        try:
            await self._load_model()
            
            # Generate audio
            audio_array = self.tts.tts(
                text=request.text,
                speed=request.speed
            )
            
            # Convert to bytes
            audio_bytes = self._audio_array_to_bytes(
                audio_array, 
                request.sample_rate, 
                request.format
            )
            
            # Encode to base64
            audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
            
            processing_time = int((time.time() - start_time) * 1000)
            duration_ms = int(len(audio_array) / request.sample_rate * 1000)
            
            response = TTSResponse(
                audio_data=audio_b64,
                format=request.format,
                sample_rate=request.sample_rate,
                duration_ms=duration_ms,
                processing_time_ms=processing_time,
                provider=TTSProvider.COQUI,
                voice=request.voice,
                success=True
            )
            
            # Update metrics
            self.metrics.tts_requests += 1
            self.metrics.tts_avg_processing_time_ms = (
                (self.metrics.tts_avg_processing_time_ms * (self.metrics.tts_requests - 1) + processing_time) 
                / self.metrics.tts_requests
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Coqui TTS synthesis failed: {e}")
            self.metrics.errors += 1
            return TTSResponse(
                audio_data="",
                format=request.format,
                sample_rate=request.sample_rate,
                duration_ms=0,
                processing_time_ms=int((time.time() - start_time) * 1000),
                provider=TTSProvider.COQUI,
                voice=request.voice,
                success=False,
                error=str(e)
            )
    
    async def synthesize_streaming(self, request: TTSRequest) -> AsyncIterator[StreamingTTSChunk]:
        """Stream synthesis (placeholder - implement chunked synthesis)."""
        # For now, generate full audio and stream in chunks
        response = await self.synthesize(request)
        
        if response.success:
            # Split audio into chunks
            chunk_size = 1024  # Adjust based on needs
            audio_data = response.audio_data
            
            for i in range(0, len(audio_data), chunk_size):
                chunk = audio_data[i:i + chunk_size]
                is_final = i + chunk_size >= len(audio_data)
                
                yield StreamingTTSChunk(
                    chunk_id=i // chunk_size,
                    audio_data=chunk,
                    is_final=is_final,
                    duration_ms=response.duration_ms // (len(audio_data) // chunk_size + 1),
                    session_id=request.session_id or ""
                )
    
    async def health_check(self) -> bool:
        """Check Coqui TTS health."""
        try:
            await self._load_model()
            return self.tts is not None
        except Exception:
            return False
    
    def _audio_array_to_bytes(self, audio_array: np.ndarray, sample_rate: int, format: AudioFormat) -> bytes:
        """Convert audio array to bytes."""
        try:
            import soundfile as sf
            audio_io = io.BytesIO()
            
            # Normalize audio
            audio_array = audio_array / np.max(np.abs(audio_array))
            
            # Write to bytes
            sf.write(audio_io, audio_array, sample_rate, format=format.value)
            audio_io.seek(0)
            return audio_io.read()
            
        except ImportError:
            raise TTSProviderError("soundfile not installed. Install with: pip install soundfile")
        except Exception as e:
            raise TTSProviderError(f"Failed to convert audio: {e}")

# Voice Processing Manager
class VoiceProcessor:
    """Main voice processing manager that coordinates STT and TTS providers."""
    
    def __init__(self, config: VoiceConfig):
        self.config = config
        self.stt_providers: Dict[STTProvider, STTProviderBase] = {}
        self.tts_providers: Dict[TTSProvider, TTSProviderBase] = {}
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize voice processing providers."""
        # Initialize STT providers
        if self.config.stt_provider == STTProvider.WHISPERX:
            self.stt_providers[STTProvider.WHISPERX] = WhisperXSTTProvider({
                "model": self.config.stt_model,
                "device": "cuda" if self.config.provider_config.get("use_gpu", False) else "cpu"
            })
        elif self.config.stt_provider == STTProvider.FASTER_WHISPER:
            device = "cuda" if self.config.provider_config.get("use_gpu", False) else "cpu"
            compute_type = "float16" if device == "cuda" else "int8"
            self.stt_providers[STTProvider.FASTER_WHISPER] = FasterWhisperSTTProvider({
                "model": self.config.stt_model,
                "device": device,
                "compute_type": compute_type,
                "batch_size": self.config.provider_config.get("batch_size", 16),
                "use_batched": self.config.provider_config.get("use_batched", False)
            })
        elif self.config.stt_provider == STTProvider.ELEVENLABS:
            elevenlabs_provider = ElevenLabsProvider({
                "api_key": self.config.provider_config.get("elevenlabs_api_key")
            })
            self.stt_providers[STTProvider.ELEVENLABS] = elevenlabs_provider

        # Initialize TTS providers
        if self.config.tts_provider == TTSProvider.COQUI:
            self.tts_providers[TTSProvider.COQUI] = CoquiTTSProvider({
                "model": self.config.provider_config.get("tts_model", "tts_models/en/ljspeech/tacotron2-DDC"),
                "device": "cuda" if self.config.provider_config.get("use_gpu", False) else "cpu"
            })
        elif self.config.tts_provider == TTSProvider.ELEVENLABS:
            if STTProvider.ELEVENLABS in self.stt_providers:
                # Reuse the same ElevenLabs provider instance
                self.tts_providers[TTSProvider.ELEVENLABS] = self.stt_providers[STTProvider.ELEVENLABS]
            else:
                self.tts_providers[TTSProvider.ELEVENLABS] = ElevenLabsProvider({
                    "api_key": self.config.provider_config.get("elevenlabs_api_key")
                })
    
    async def transcribe(self, request: STTRequest) -> STTResponse:
        """Transcribe audio to text."""
        provider = request.provider or self.config.stt_provider
        
        if provider not in self.stt_providers:
            raise STTProviderError(f"STT provider {provider} not available")
        
        return await self.stt_providers[provider].transcribe(request)
    
    async def synthesize(self, request: TTSRequest) -> TTSResponse:
        """Synthesize text to speech."""
        provider = request.provider or self.config.tts_provider
        
        if provider not in self.tts_providers:
            raise TTSProviderError(f"TTS provider {provider} not available")
        
        return await self.tts_providers[provider].synthesize(request)
    
    async def health_check(self) -> Dict[str, bool]:
        """Check health of all providers."""
        health_status = {}
        
        for provider_type, provider in self.stt_providers.items():
            health_status[f"stt_{provider_type}"] = await provider.health_check()
        
        for provider_type, provider in self.tts_providers.items():
            health_status[f"tts_{provider_type}"] = await provider.health_check()
        
        return health_status
    
    def get_metrics(self) -> Dict[str, VoiceMetrics]:
        """Get metrics from all providers."""
        metrics = {}
        
        for provider_type, provider in self.stt_providers.items():
            metrics[f"stt_{provider_type}"] = provider.metrics
        
        for provider_type, provider in self.tts_providers.items():
            metrics[f"tts_{provider_type}"] = provider.metrics
        
        return metrics

# ElevenLabs STT/TTS Provider
class ElevenLabsProvider(STTProviderBase, TTSProviderBase):
    """ElevenLabs provider for both STT and TTS."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key")
        self.base_url = config.get("base_url", "https://api.elevenlabs.io/v1")

        if not self.api_key:
            raise VoiceProcessingError("ElevenLabs API key is required")

    async def transcribe(self, request: STTRequest) -> STTResponse:
        """Transcribe using ElevenLabs STT."""
        start_time = time.time()

        try:
            import httpx

            headers = {
                "xi-api-key": self.api_key,
                "Content-Type": "application/json"
            }

            data = {
                "audio": request.audio_data,
                "model": request.model or "whisper-1"
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/speech-to-text",
                    headers=headers,
                    json=data,
                    timeout=60.0
                )
                response.raise_for_status()
                result = response.json()

            processing_time = int((time.time() - start_time) * 1000)

            return STTResponse(
                text=result.get("text", ""),
                confidence=result.get("confidence", 0.0),
                processing_time_ms=processing_time,
                provider=STTProvider.ELEVENLABS,
                model=request.model or "whisper-1",
                success=True
            )

        except Exception as e:
            logger.error(f"ElevenLabs STT failed: {e}")
            return STTResponse(
                text="",
                processing_time_ms=int((time.time() - start_time) * 1000),
                provider=STTProvider.ELEVENLABS,
                model=request.model or "whisper-1",
                success=False,
                error=str(e)
            )

    async def synthesize(self, request: TTSRequest) -> TTSResponse:
        """Synthesize using ElevenLabs TTS."""
        start_time = time.time()

        try:
            import httpx

            headers = {
                "xi-api-key": self.api_key,
                "Content-Type": "application/json"
            }

            data = {
                "text": request.text,
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.5,
                    "speed": request.speed
                }
            }

            voice_id = request.voice if request.voice != "default" else "21m00Tcm4TlvDq8ikWAM"

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/text-to-speech/{voice_id}",
                    headers=headers,
                    json=data,
                    timeout=60.0
                )
                response.raise_for_status()
                audio_bytes = response.content

            # Encode to base64
            audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')

            processing_time = int((time.time() - start_time) * 1000)

            return TTSResponse(
                audio_data=audio_b64,
                format=AudioFormat.MP3,  # ElevenLabs returns MP3
                sample_rate=request.sample_rate,
                duration_ms=0,  # Would need to calculate from audio
                processing_time_ms=processing_time,
                provider=TTSProvider.ELEVENLABS,
                voice=request.voice,
                success=True
            )

        except Exception as e:
            logger.error(f"ElevenLabs TTS failed: {e}")
            return TTSResponse(
                audio_data="",
                format=request.format,
                sample_rate=request.sample_rate,
                duration_ms=0,
                processing_time_ms=int((time.time() - start_time) * 1000),
                provider=TTSProvider.ELEVENLABS,
                voice=request.voice,
                success=False,
                error=str(e)
            )

    async def transcribe_streaming(self, audio_stream) -> AsyncIterator[StreamingSTTChunk]:
        """ElevenLabs streaming STT (if available)."""
        # Placeholder - implement if ElevenLabs supports streaming
        chunk_id = 0
        async for audio_chunk in audio_stream:
            request = STTRequest(audio_data=audio_chunk)
            response = await self.transcribe(request)

            yield StreamingSTTChunk(
                chunk_id=chunk_id,
                text=response.text,
                is_final=True,
                confidence=response.confidence,
                session_id=request.session_id or ""
            )
            chunk_id += 1

    async def synthesize_streaming(self, request: TTSRequest) -> AsyncIterator[StreamingTTSChunk]:
        """ElevenLabs streaming TTS."""
        # Generate full audio and stream in chunks
        response = await self.synthesize(request)

        if response.success:
            chunk_size = 1024
            audio_data = response.audio_data

            for i in range(0, len(audio_data), chunk_size):
                chunk = audio_data[i:i + chunk_size]
                is_final = i + chunk_size >= len(audio_data)

                yield StreamingTTSChunk(
                    chunk_id=i // chunk_size,
                    audio_data=chunk,
                    is_final=is_final,
                    duration_ms=response.duration_ms // (len(audio_data) // chunk_size + 1),
                    session_id=request.session_id or ""
                )

    async def health_check(self) -> bool:
        """Check ElevenLabs API health."""
        try:
            import httpx

            headers = {"xi-api-key": self.api_key}

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/voices",
                    headers=headers,
                    timeout=10.0
                )
                return response.status_code == 200
        except Exception:
            return False
