"""
Voice Processing Service - FastAPI application for STT and TTS operations.

This service provides HTTP endpoints for speech-to-text and text-to-speech
processing using multiple providers.
"""

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from models.voice import (
    VoiceConfig, STTRequest, STTResponse, TTSRequest, TTSResponse,
    STTProvider, TTSProvider, VoiceSystemStatus, VoiceMetrics
)
from voice import VoiceProcessor, VoiceProcessingError

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Global voice processor instance
voice_processor: Optional[VoiceProcessor] = None
startup_time = time.time()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global voice_processor
    
    logger.info("Starting Voice Processing Service")
    
    # Initialize voice processor
    try:
        config = VoiceConfig(
            stt_provider=STTProvider(os.getenv("STT_PROVIDER", "elevenlabs")),
            tts_provider=TTSProvider(os.getenv("TTS_PROVIDER", "elevenlabs")),
            stt_model=os.getenv("WHISPER_MODEL", "large-v3"),
            provider_config={
                "elevenlabs_api_key": os.getenv("ELEVENLABS_API_KEY"),
                "use_gpu": os.getenv("USE_GPU", "false").lower() == "true",
                "tts_model": os.getenv("COQUI_MODEL", "tts_models/en/ljspeech/tacotron2-DDC"),
                "batch_size": int(os.getenv("FASTER_WHISPER_BATCH_SIZE", "16")),
                "use_batched": os.getenv("FASTER_WHISPER_USE_BATCHED", "true").lower() == "true",
                "compute_type": os.getenv("FASTER_WHISPER_COMPUTE_TYPE", "auto")
            }
        )
        
        voice_processor = VoiceProcessor(config)
        logger.info("Voice processor initialized successfully")
        
        # Perform health check
        health_status = await voice_processor.health_check()
        logger.info("Voice processor health check", status=health_status)
        
    except Exception as e:
        logger.error("Failed to initialize voice processor", error=str(e))
        raise
    
    yield
    
    logger.info("Shutting down Voice Processing Service")

# Create FastAPI app
app = FastAPI(
    title="Jarvis Voice Processing Service",
    description="STT and TTS processing service for the Jarvis multi-agent AI system",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    if voice_processor is None:
        raise HTTPException(status_code=503, detail="Voice processor not initialized")
    
    try:
        health_status = await voice_processor.health_check()
        overall_health = "healthy" if all(health_status.values()) else "degraded"
        
        return {
            "status": overall_health,
            "uptime_seconds": int(time.time() - startup_time),
            "providers": health_status,
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Health check failed: {e}")

@app.post("/stt", response_model=STTResponse)
async def speech_to_text(request: STTRequest, background_tasks: BackgroundTasks):
    """Convert speech to text."""
    if voice_processor is None:
        raise HTTPException(status_code=503, detail="Voice processor not initialized")
    
    try:
        logger.info("Processing STT request", 
                   provider=request.provider, 
                   format=request.format,
                   sample_rate=request.sample_rate)
        
        response = await voice_processor.transcribe(request)
        
        # Log metrics in background
        background_tasks.add_task(
            log_stt_metrics, 
            request.provider or voice_processor.config.stt_provider,
            response.processing_time_ms,
            response.success
        )
        
        return response
        
    except VoiceProcessingError as e:
        logger.error("STT processing error", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Unexpected STT error", error=str(e))
        raise HTTPException(status_code=500, detail=f"STT processing failed: {e}")

@app.post("/tts", response_model=TTSResponse)
async def text_to_speech(request: TTSRequest, background_tasks: BackgroundTasks):
    """Convert text to speech."""
    if voice_processor is None:
        raise HTTPException(status_code=503, detail="Voice processor not initialized")
    
    try:
        logger.info("Processing TTS request",
                   provider=request.provider,
                   text_length=len(request.text),
                   voice=request.voice,
                   speed=request.speed)
        
        response = await voice_processor.synthesize(request)
        
        # Log metrics in background
        background_tasks.add_task(
            log_tts_metrics,
            request.provider or voice_processor.config.tts_provider,
            response.processing_time_ms,
            response.duration_ms,
            response.success
        )
        
        return response
        
    except VoiceProcessingError as e:
        logger.error("TTS processing error", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Unexpected TTS error", error=str(e))
        raise HTTPException(status_code=500, detail=f"TTS processing failed: {e}")

@app.get("/status", response_model=VoiceSystemStatus)
async def get_system_status():
    """Get comprehensive system status."""
    if voice_processor is None:
        raise HTTPException(status_code=503, detail="Voice processor not initialized")
    
    try:
        health_status = await voice_processor.health_check()
        metrics = voice_processor.get_metrics()
        
        # Convert health status to provider status list
        stt_providers = []
        tts_providers = []
        
        for provider_key, is_healthy in health_status.items():
            if provider_key.startswith("stt_"):
                provider_name = provider_key[4:]  # Remove "stt_" prefix
                stt_providers.append({
                    "provider": provider_name,
                    "available": is_healthy,
                    "latency_ms": None,  # Could be calculated from metrics
                    "error_rate": 0.0,  # Could be calculated from metrics
                    "last_check": time.time(),
                    "config": {}
                })
            elif provider_key.startswith("tts_"):
                provider_name = provider_key[4:]  # Remove "tts_" prefix
                tts_providers.append({
                    "provider": provider_name,
                    "available": is_healthy,
                    "latency_ms": None,
                    "error_rate": 0.0,
                    "last_check": time.time(),
                    "config": {}
                })
        
        # Aggregate metrics
        total_metrics = VoiceMetrics()
        for metric in metrics.values():
            total_metrics.stt_requests += metric.stt_requests
            total_metrics.tts_requests += metric.tts_requests
            total_metrics.errors += metric.errors
        
        # Calculate success rates
        if total_metrics.stt_requests > 0:
            total_metrics.stt_success_rate = (total_metrics.stt_requests - total_metrics.errors) / total_metrics.stt_requests
        if total_metrics.tts_requests > 0:
            total_metrics.tts_success_rate = (total_metrics.tts_requests - total_metrics.errors) / total_metrics.tts_requests
        
        overall_health = "healthy" if all(health_status.values()) else "degraded"
        
        return VoiceSystemStatus(
            stt_providers=stt_providers,
            tts_providers=tts_providers,
            active_sessions=0,  # Would track active WebSocket sessions
            processing_queue_size=0,  # Would track queued requests
            system_health=overall_health,
            uptime_seconds=int(time.time() - startup_time),
            metrics=total_metrics
        )
        
    except Exception as e:
        logger.error("Failed to get system status", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get system status: {e}")

@app.get("/metrics")
async def get_metrics():
    """Get detailed metrics from all providers."""
    if voice_processor is None:
        raise HTTPException(status_code=503, detail="Voice processor not initialized")
    
    try:
        return voice_processor.get_metrics()
    except Exception as e:
        logger.error("Failed to get metrics", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {e}")

@app.get("/providers")
async def get_available_providers():
    """Get list of available providers and their capabilities."""
    return {
        "stt_providers": [provider.value for provider in STTProvider],
        "tts_providers": [provider.value for provider in TTSProvider],
        "supported_formats": ["wav", "mp3", "webm", "ogg", "flac"],
        "features": {
            "streaming_stt": False,  # Would be True when implemented
            "streaming_tts": False,  # Would be True when implemented
            "voice_activity_detection": False,
            "real_time_processing": True
        }
    }

# Background task functions
async def log_stt_metrics(provider: STTProvider, processing_time_ms: int, success: bool):
    """Log STT metrics."""
    logger.info("STT metrics",
               provider=provider.value,
               processing_time_ms=processing_time_ms,
               success=success)

async def log_tts_metrics(provider: TTSProvider, processing_time_ms: int, duration_ms: int, success: bool):
    """Log TTS metrics."""
    logger.info("TTS metrics",
               provider=provider.value,
               processing_time_ms=processing_time_ms,
               duration_ms=duration_ms,
               success=success)

# Error handlers
@app.exception_handler(VoiceProcessingError)
async def voice_processing_error_handler(request, exc):
    """Handle voice processing errors."""
    logger.error("Voice processing error", error=str(exc))
    return JSONResponse(
        status_code=400,
        content={"error": "Voice processing error", "detail": str(exc)}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error("Unexpected error", error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": "An unexpected error occurred"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "voice_service:app",
        host="0.0.0.0",
        port=8002,
        reload=True,
        log_level="info"
    )
