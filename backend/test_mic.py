import sounddevice as sd
import numpy as np

def test():
    print("Testing mic for 2 seconds...")
    audio = sd.rec(int(16000 * 2), samplerate=16000, channels=1, dtype='int16')
    sd.wait()
    max_amp = np.max(np.abs(audio))
    print(f"Max amplitude: {max_amp}")

test()
