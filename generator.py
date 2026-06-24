import numpy as np
from scipy.io import wavfile
from scipy.fft import fft, ifft
import matplotlib.pyplot as plt


sample_rate, room_impulse_response = wavfile.read("data/extracted_ir.wav")

H_transfer_function = fft(room_impulse_response)


#Calculate the inverse filter with Kirkeby Regularization
beta = 0.05
H_inv_transfer_function = np.conj(H_transfer_function) / (np.abs(H_transfer_function)**2 + beta)


# Change to time domain
correction_filter = np.real(ifft(H_inv_transfer_function))


#Normalize filter
max_amp = np.max(np.abs(correction_filter))

if max_amp > 1:
    correction_filter = correction_filter / max_amp


#Write to a wavfile
wavfile.write("data/correction_filter.wav", sample_rate, correction_filter.astype(np.float32))


#  Plot the filter
filter_fft = fft(correction_filter)
frequencies = np.fft.fftfreq(len(correction_filter), 1/sample_rate)
filter_db = 20 * np.log10(np.abs(filter_fft) + 1e-10)

plt.figure(figsize=(10, 4))
plt.plot(frequencies[:len(correction_filter)//2], filter_db[:len(correction_filter)//2], color='orange')

plt.title("The Cure: Inverse Filter Frequency Response")
plt.xlabel("Frequency (Hertz)")
plt.ylabel("Magnitude (dB)")
plt.xscale('log')
plt.xlim(20, 20000)
plt.grid(True, which="both", ls="-", color='0.8')
plt.show()