import numpy as np
from scipy.io import wavfile
import matplotlib.pyplot as plt

def analyze_impulse_response(file_path):
    # 1. Load the WAV file
    try:
        sample_rate, data = wavfile.read(file_path)
    except FileNotFoundError:
        print(f"Error: Could not find '{file_path}'. Ensure it is in the same directory.")
        return

    # 2. Handle Stereo vs Mono
    # If the file is stereo, we only need to analyze one channel (e.g., Left) to find the time delay.
    if len(data.shape) > 1:
        audio_channel = data[:, 0]
    else:
        audio_channel = data

    # 3. Find the exact sample index of the maximum amplitude (The Dirac Spike)
    # We take the absolute value because the phase-inverted peak could be negative.
    peak_sample_index = np.argmax(np.abs(audio_channel))
    peak_time_ms = (peak_sample_index / sample_rate) * 1000

    print("==================================================")
    print(f"Sample Rate: {sample_rate} Hz")
    print(f"LATENCY VALUE FOR C++: {peak_sample_index} samples")
    print(f"Latency in Time: {peak_time_ms:.2f} ms")
    print("==================================================")

    # 4. Visualize the waveform around the peak to verify
    # We will plot a window of 500 samples before and after the peak.
    window_size = 500
    start_idx = max(0, peak_sample_index - window_size)
    end_idx = min(len(audio_channel), peak_sample_index + window_size)

    plt.figure(figsize=(10, 5))
    plt.plot(range(start_idx, end_idx), audio_channel[start_idx:end_idx], label="Audio Data")
    
    # Highlight the exact peak
    plt.axvline(x=peak_sample_index, color='red', linestyle='--', label=f'Peak @ {peak_sample_index}')
    
    plt.title("Impulse Response Peak Analysis")
    plt.xlabel("Sample Index")
    plt.ylabel("Amplitude")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    analyze_impulse_response("data/correction_filter.wav")