import numpy as np
from scipy.io import wavfile
from scipy.fft import fft, ifft
import matplotlib.pyplot as plt


sample_rate, room_impulse_response = wavfile.read("data/extracted_ir.wav")

H_transfer_function = fft(room_impulse_response)


#Calculate the inverse filter with Kirkeby Regularization
beta = 0.1
H_inv_transfer_function = np.conj(H_transfer_function) / (np.abs(H_transfer_function)**2 + beta)


# Change to time domain
correction_filter = np.real(ifft(H_inv_transfer_function))

N = len(correction_filter)

shift_amount = N//2

causal_filter = np.roll(correction_filter, shift_amount)


#Normalize filter
max_amp = np.max(np.abs(causal_filter))

if max_amp > 0:
    causal_filter = causal_filter / max_amp

#find the dirac spike
peak_idx = np.argmax(np.abs(causal_filter))


pre_len = 1024
post_len = 7168


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
print(f"setLatencySamples({latency});   // paste into prepareToPlay")


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