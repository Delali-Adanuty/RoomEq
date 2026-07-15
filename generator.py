import numpy as np
from scipy.io import wavfile
from scipy.fft import fft, ifft
import matplotlib.pyplot as plt


sample_rate, room_impulse_response = wavfile.read("data/physical_ir.wav")

H_transfer_function = fft(room_impulse_response)


#Calculate the inverse filter with Kirkeby Regularization
# --- 0. FREQUENCY-DEPENDENT REGULARIZATION (Smooth Ramps) ---
N = len(H_transfer_function)
beta_array = np.full(N, 0.005)

# --- Define Frequency Boundaries ---
sub_bass_start_idx = int(np.round(40 * (N / sample_rate)))
sub_bass_end_idx = int(np.round(80 * (N / sample_rate)))

high_freq_start_idx = int(np.round(16000 * (N / sample_rate)))
high_freq_end_idx = int(np.round(18000 * (N / sample_rate)))


beta_array[0:sub_bass_start_idx] = 0.1

# Smooth ramp from 40 Hz down to 80 Hz
sub_bass_ramp_length = sub_bass_end_idx - sub_bass_start_idx
beta_array[sub_bass_start_idx:sub_bass_end_idx] = np.linspace(0.1, 0.005, sub_bass_ramp_length)


# Smooth ramp from 16 kHz up to 18 kHz
high_freq_ramp_length = high_freq_end_idx - high_freq_start_idx
beta_array[high_freq_start_idx:high_freq_end_idx] = np.linspace(0.005, 0.1, high_freq_ramp_length)

# Hard penalty from 18 kHz to Nyquist
beta_array[high_freq_end_idx:N // 2] = 0.1


# Mirror Sub-Bass
beta_array[N - sub_bass_start_idx:N] = 0.1
beta_array[N - sub_bass_end_idx:N - sub_bass_start_idx] = np.linspace(0.005, 0.1, sub_bass_ramp_length)

# Mirror High-Frequency
beta_array[N // 2:N - high_freq_end_idx] = 0.1
beta_array[N - high_freq_end_idx:N - high_freq_start_idx] = np.linspace(0.1, 0.005, high_freq_ramp_length)


H_inv_transfer_function = np.conj(H_transfer_function) / (np.abs(H_transfer_function)**2 + beta_array)

gain_ceiling_value = 8 #dB
gain_ceiling_value_linear = 10**(gain_ceiling_value/20)

inv_magnitude = np.abs(H_inv_transfer_function)
inv_phase = np.angle(H_inv_transfer_function)

clipped_inv_magnitude = np.clip(inv_magnitude, 0, gain_ceiling_value_linear)



magnitude_smoothed = np.copy(clipped_inv_magnitude)

N = len(clipped_inv_magnitude)

#For a schoeder frequency 500
starting_index = int(np.round(500 * (N/sample_rate)))

for i in range(starting_index, N//2):
    center_frequency = i * (sample_rate/N)
    lower_frequency = center_frequency * 2**(-1/6)
    higher_frequency = center_frequency * 2**(1/6)

    lower_frequency_index = int(np.round(lower_frequency *  (N/sample_rate)))
    higher_frequency_index = int(np.round(higher_frequency *  (N/sample_rate)))


    current_window = clipped_inv_magnitude[lower_frequency_index:higher_frequency_index]
    
    if len(current_window) > 0:
        smoothed_val = np.mean(current_window)
        magnitude_smoothed[i] = smoothed_val
        magnitude_smoothed[N-i] = smoothed_val


H_inv_clipped = magnitude_smoothed * np.exp(1j * inv_phase)



# Change to time domain
correction_filter = np.real(ifft(H_inv_clipped))



shift_amount = N//2

causal_filter = np.roll(correction_filter, shift_amount)


#Normalize filter
max_amp = np.max(np.abs(causal_filter))

if max_amp > 0:
    causal_filter = causal_filter / max_amp

#find the dirac spike
peak_idx = np.argmax(np.abs(causal_filter))


pre_len = 44
post_len = 8148


start_idx = peak_idx - pre_len
end_idx = peak_idx + post_len


if start_idx < 0 or end_idx > len(causal_filter):
    raise ValueError("peak is too close ot end of audio file to truncate")

raw_slice = causal_filter[start_idx:end_idx]

left_window = np.hanning(2 * pre_len)[:pre_len]
right_window = np.hanning(2 * post_len)[post_len:]

asymmetric_window = np.concatenate((left_window, right_window))

final_filter = raw_slice * asymmetric_window


stereo_filter = np.column_stack((final_filter, final_filter)).astype(np.float32)
wavfile.write("data/correction_filter.wav", sample_rate, stereo_filter)

latency = pre_len
print(f"setLatencySamples({latency}); ")


#  Plot the filter
filter_fft = fft(final_filter)
frequencies = np.fft.fftfreq(len(final_filter), 1/sample_rate)
filter_db = 20 * np.log10(np.abs(filter_fft) + 1e-10)

plt.figure(figsize=(10, 4))
plt.plot(frequencies[:len(final_filter)//2], filter_db[:len(final_filter)//2], color='orange')

plt.title("Inverse Filter Frequency Response")
plt.xlabel("Frequency (Hertz)")
plt.ylabel("Magnitude (dB)")
plt.xscale('log')
plt.xlim(20, 20000)
plt.grid(True, which="both", ls="-", color='0.8')
plt.show()

transfer_function_db = 20 * np.log10(np.abs(H_transfer_function))
plt.figure(figsize=(10,4))
plt.plot(transfer_function_db)
plt.xlabel("Freq(Hz)")
plt.ylabel("Magnitude(dB)")
plt.xscale('log')
plt.title("Transfer function")
plt.grid(True, which="both")
plt.show()