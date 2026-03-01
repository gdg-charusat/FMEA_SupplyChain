import wave
import struct
import math

def create_speech_wav(filename, duration=2, sample_rate=16000):
    """Create a realistic speech-like WAV file with formant patterns."""
    samples = []
    
    # Create speech-like patterns by combining formants (typical speech frequencies)
    for i in range(int(sample_rate * duration)):
        t = i / sample_rate
        
        # Simulate vowel 'a' - formants around 700Hz, 1200Hz, 2500Hz
        f1, f2, f3 = 700, 1200, 2500
        # Envelope to make it more natural (attack, sustain, release)
        envelope = min(1.0, t * 4) * max(0.0, 1.0 - (t - 1.5) / 0.5)
        
        # Combine formants with different amplitudes
        sample = (
            int(2000 * math.sin(2 * math.pi * f1 * t) * envelope) +
            int(1500 * math.sin(2 * math.pi * f2 * t) * envelope) +
            int(800 * math.sin(2 * math.pi * f3 * t) * envelope)
        )
        samples.append(min(32767, max(-32768, sample)))
    
    with wave.open(filename, 'wb') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        f.writeframes(struct.pack(f'<{len(samples)}h', *samples))

create_speech_wav('tests/fixtures/speech.wav')
print('Created tests/fixtures/speech.wav')
