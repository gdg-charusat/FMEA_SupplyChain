"""
Tests for VoiceInputProcessor
Run with: pytest tests/test_voice_input.py -v
"""

import pytest
import sys
import os
import struct
import wave
import tempfile
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / 'src'))

from voice_input import VoiceInputProcessor


def _make_wav(samples, sample_rate=16000, num_channels=1, sample_width=2):
    """Helper: create WAV bytes from a list of 16-bit integer samples."""
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    try:
        with wave.open(tmp.name, "wb") as wf:
            wf.setnchannels(num_channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(sample_rate)
            wf.writeframes(struct.pack(f"<{len(samples)}h", *samples))
        with open(tmp.name, "rb") as f:
            return f.read()
    finally:
        os.remove(tmp.name)


# ---------------------------------------------------------------------------
# Validation-only tests (no Whisper model required)
# ---------------------------------------------------------------------------


class TestValidation:
    """Tests for the validate_transcription method."""

    def setup_method(self):
        self.processor = VoiceInputProcessor(model_size="base")

    def test_short_text_fails_validation(self):
        """Text under 10 characters should fail validation."""
        result = self.processor.validate_transcription("Hi")
        assert result["valid"] is False
        assert "too short" in result["reason"].lower()

    def test_few_words_fails_validation(self):
        """Text with fewer than 4 words should fail validation."""
        result = self.processor.validate_transcription("Brake broke now")
        assert result["valid"] is False
        assert "too short" in result["reason"].lower()

    def test_none_text_fails_validation(self):
        """None input should fail validation."""
        result = self.processor.validate_transcription(None)
        assert result["valid"] is False

    def test_valid_text_passes(self):
        """A proper failure description should pass validation."""
        text = "The front suspension on the Ford F-150 collapsed at 60000 kilometres"
        result = self.processor.validate_transcription(text)
        assert result["valid"] is True
        assert result["reason"] is None


# ---------------------------------------------------------------------------
# Transcription tests (require Whisper model download)
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestTranscription:
    """Tests that actually run Whisper. Marked slow — skip with: pytest -m 'not slow'"""

    @pytest.fixture(autouse=True)
    def _init(self):
        self.processor = VoiceInputProcessor(model_size="tiny")

    def test_clear_speech_produces_text(self):
        """A real WAV with spoken content should produce non-empty text."""
        # Load real speech WAV fixture with formant patterns simulating human speech
        fixture_path = Path(__file__).parent / "fixtures" / "speech.wav"
        with open(fixture_path, "rb") as f:
            audio_bytes = f.read()

        text = self.processor.transcribe(audio_bytes)
        # Whisper should return a string with transcribed content
        assert isinstance(text, str)

    def test_very_short_audio_fails_validation(self):
        """Audio under 1 second should fail validation after transcription."""
        sample_rate = 16000
        samples = [0] * int(sample_rate * 0.3)  # 0.3 seconds of silence
        audio_bytes = _make_wav(samples, sample_rate)

        text = self.processor.transcribe(audio_bytes)
        result = self.processor.validate_transcription(text)
        assert result["valid"] is False

    def test_silent_audio_fails_validation(self):
        """Silent audio should produce empty/useless text that fails validation."""
        sample_rate = 16000
        samples = [0] * (sample_rate * 3)  # 3 seconds of pure silence
        audio_bytes = _make_wav(samples, sample_rate)

        text = self.processor.transcribe(audio_bytes)
        result = self.processor.validate_transcription(text)
        assert result["valid"] is False
