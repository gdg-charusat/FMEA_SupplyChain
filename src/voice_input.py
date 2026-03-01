"""
Voice Input Processor for FMEA Generator
Uses OpenAI Whisper (local, offline) for speech-to-text transcription
"""

import tempfile
import os
import logging

logger = logging.getLogger(__name__)


class VoiceInputProcessor:
    """
    Handles voice-to-text transcription using OpenAI Whisper.
    Runs entirely offline — no API key required.
    """

    def __init__(self, model_size: str = "base"):
        """
        Initialize the Voice Input Processor.

        Args:
            model_size: Whisper model size — 'tiny', 'base', 'small', or 'medium'
        """
        self.model_size = model_size
        self.model = None

    def load_model(self):
        """Load the Whisper model (downloads on first run)."""
        import whisper

        if self.model is None:
            logger.info(f"Loading Whisper '{self.model_size}' model...")
            self.model = whisper.load_model(self.model_size)
            logger.info("Whisper model loaded successfully.")
        return self.model

    def transcribe(self, audio_bytes: bytes, language: str = "en") -> str:
        """
        Transcribe audio bytes to text using Whisper.

        Uses soundfile to decode audio and passes a numpy array directly
        to Whisper, bypassing the need for ffmpeg on the system.

        Args:
            audio_bytes: Raw audio data from the Streamlit recorder
            language: Language code (default 'en')

        Returns:
            Transcribed text string
        """
        import numpy as np
        import soundfile as sf
        import whisper

        model = self.load_model()

        # Write audio bytes to a temporary file so soundfile can read it
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name

            # Read audio with soundfile (no ffmpeg needed)
            audio_data, sample_rate = sf.read(tmp_path, dtype="float32")

            # Convert stereo to mono if necessary
            if audio_data.ndim > 1:
                audio_data = audio_data.mean(axis=1)

            # Resample to 16000 Hz if needed (Whisper requirement)
            if sample_rate != 16000:
                from scipy.signal import resample
                num_samples = int(len(audio_data) * 16000 / sample_rate)
                audio_data = resample(audio_data, num_samples).astype(np.float32)

            # Pass numpy array directly to Whisper — bypasses ffmpeg entirely
            result = model.transcribe(audio_data, language=language)
            text = result.get("text", "").strip()
            return text
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)

    def validate_transcription(self, text: str) -> dict:
        """
        Validate that the transcribed text is usable for FMEA generation.

        Args:
            text: Transcribed text to validate

        Returns:
            dict with keys 'valid' (bool) and 'reason' (str or None)
        """
        if text is None:
            return {"valid": False, "reason": "No transcription produced."}

        cleaned = text.strip()

        if len(cleaned) < 10:
            return {"valid": False, "reason": "Recording too short or inaudible. Please try again."}

        if len(cleaned.split()) < 4:
            return {"valid": False, "reason": "Recording too short or inaudible. Please try again."}

        return {"valid": True, "reason": None}
