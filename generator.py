import numpy as np
from scipy.io import wavfile
from scipy.fft import rfft, irfft, rfftfreq
import matplotlib.pyplot as plt


sample_rate, raw_audio = wavfile.read("data/physical_ir_2.wav")
N = len(raw_audio)

# Find the exact moment the speaker's direct sound hits the microphone
peak_idx = np.argmax(np.abs(raw_audio))

# Anchor the exact peak to index 0 and wrap the tail circularly.
# This prevents the time-of-flight phase explosion and preserves sharp transients.
ir_aligned = np.zeros(N)
ir_aligned[:N - peak_idx] = raw_audio[peak_idx:]
ir_aligned[N - peak_idx:] = raw_audio[:peak_idx]

# Calculate the raw complex frequency response using Real FFT
H_raw = rfft(ir_aligned)
frequencies = rfftfreq(N, 1 / sample_rate)


# FRACTIONAL-OCTAVE COMPLEX SMOOTHING
H_smoothed = np.copy(H_raw)
schroeder_hz = 80.0


# Smooth only above the Schroeder frequency to kill high-frequency comb filtering
# while leaving the massive bass modes completely raw and exposed for the inversion.
for i, f in enumerate(frequencies):
    if f <= schroeder_hz or f >= 20000.0:
        continue

    # Calculate 1/3 octave boundaries
    lower_frequency = f * 2**(-1/6)
    higher_frequency = f * 2**(1/6)

    low_idx = int(np.round(lower_frequency * (N / sample_rate)))
    high_idx = int(np.round(higher_frequency * (N / sample_rate)))

    # Ensure indices stay within bounds
    low_idx = max(0, min(low_idx, len(H_raw) - 1))
    high_idx = max(0, min(high_idx, len(H_raw) - 1))

    if high_idx > low_idx:
        # Averaging complex numbers directly flattens both chaotic amplitude and phase wraps
        H_smoothed[i] = np.mean(H_raw[low_idx:high_idx])


# KIRKEBY REGULARIZATION
N_half = len(frequencies)
beta_array = np.full(N_half, 0.005)

sub_bass_start_idx = min(int(np.round(40 * (N / sample_rate))), N_half - 1)
sub_bass_end_idx = min(int(np.round(schroeder_hz * (N / sample_rate))), N_half - 1)
high_freq_start_idx = min(int(np.round(16000 * (N / sample_rate))), N_half - 1)
high_freq_end_idx = min(int(np.round(18000 * (N / sample_rate))), N_half - 1)

# Apply dynamic penalties to protect the speakers from unfixable nulls
beta_array[0:sub_bass_start_idx] = 0.1
beta_array[sub_bass_start_idx:sub_bass_end_idx] = np.linspace(0.1, 0.005, sub_bass_end_idx - sub_bass_start_idx)
beta_array[high_freq_start_idx:high_freq_end_idx] = np.linspace(0.005, 0.1, high_freq_end_idx - high_freq_start_idx)
beta_array[high_freq_end_idx:N_half] = 0.1

# Calculate the true inverse
H_inv_raw = np.conj(H_smoothed) / (np.abs(H_smoothed)**2 + beta_array)


# BRICKWALL CLIPPING & PHASE RECOMBINATION

# Anchor Midrange to 0 dB
mid_start = int(np.round(500 * (N / sample_rate)))
mid_end = int(np.round(2000 * (N / sample_rate)))
midrange_avg_gain = np.mean(np.abs(H_inv_raw[mid_start:mid_end]))

H_inv_anchored = H_inv_raw / midrange_avg_gain

# Enforce the absolute brickwall ceiling (+12 dB limit) directly on anchored inversion
max_boost_linear = 10 ** (12.0 / 20.0)
inv_mag_clipped = np.clip(np.abs(H_inv_anchored), 0, max_boost_linear)
inv_phase = np.angle(H_inv_anchored)

H_inv_transfer_function = inv_mag_clipped * np.exp(1j * inv_phase)



pretrunc_db = 20 * np.log10(np.abs(H_inv_transfer_function) + 1e-10)

plt.figure(figsize=(10, 4))
plt.plot(frequencies, pretrunc_db, color='seagreen')
plt.title("Pre-Truncation Inverse Filter Response (before windowing)")
plt.xlabel("Frequency (Hz)")
plt.ylabel("Magnitude (dB)")
plt.xscale('log')
plt.xlim(20, 20000)
plt.ylim(-30, 30)
plt.grid(True, which="both", ls="-", color='0.8')
plt.show()


# Convert back to time domain
correction_filter = irfft(H_inv_transfer_function, n=N)

# Re-center the mathematical spike
shift_amount = N // 2
causal_filter = np.roll(correction_filter, shift_amount)

peak_idx = np.argmax(np.abs(causal_filter))

# Standard configuration for JUCE Convolution block
pre_len = 1024
post_len = 7168

start_idx = peak_idx - pre_len
end_idx = peak_idx + post_len

if start_idx < 0 or end_idx > len(causal_filter):
    raise ValueError("Peak is too close to end of audio file to truncate")

raw_slice = causal_filter[start_idx:end_idx]

# Apply Flat-Top Windowing: Preserves bass energy, gently fades the final 512 samples
left_window = np.hanning(2 * pre_len)[:pre_len]

fade_len = 512
right_window = np.ones(post_len)
right_window[-fade_len:] = np.hanning(2 * fade_len)[fade_len:]

asymmetric_window = np.concatenate((left_window, right_window))
final_filter = raw_slice * asymmetric_window

# Export as 32-bit float stereo WAV
stereo_filter = np.column_stack((final_filter, final_filter)).astype(np.float32)
wavfile.write("data/correction_filter.wav", sample_rate, stereo_filter)



filter_fft = rfft(final_filter)
freqs_plot = rfftfreq(len(final_filter), 1 / sample_rate)
filter_db = 20 * np.log10(np.abs(filter_fft) + 1e-10)

plt.figure(figsize=(10, 4))
plt.plot(freqs_plot, filter_db, color='orange')
plt.title("Final Inverse Filter Frequency Response")
plt.xlabel("Frequency (Hz)")
plt.ylabel("Magnitude (dB)")
plt.xscale('log')
plt.xlim(20, 20000)
plt.grid(True, which="both", ls="-", color='0.8')
plt.show()