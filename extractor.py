import numpy as np
from scipy.io import wavfile
from scipy.fft import fft, ifft
import matplotlib.pyplot as plt

#Load the file
sample_rate, sweep = wavfile.read("data/original_sweep.wav")
_, recording = wavfile.read("data/simulated_recording.wav")

#Change to frequency domain

fft_length = len(recording)
sweep_fft = fft(sweep, n = fft_length)
recording_fft = fft(recording, n = fft_length)


#Deconvolution
epsilon = 1e-10
recording_fft = recording_fft / (sweep_fft + epsilon)

#Change back to time
extracted_ir = np.real(ifft(ir_fft))

wavfile.write("data/extracted_ir.wav", sample_rate, extracted_ir.astype(np.float32) )


#Plot frequencies
plt.figure(figsize=(10, 4))

plt.plot(extracted_ir)

plt.title("Extracted Impulse Response")
plt.xlabel("Samples (44100 = 1 second)")
plt.ylabel("Amplitude")
plt.grid(True)

plt.xlim(0, 44100)
plt.show()


#Plot sweep fft

frequencies = np.fft.fftfreq(fft_length, 1/sample_rate)


#Figure plots
sweep_magnitude = np.abs(sweep_fft)
sweep_db = 20 * np.log10(sweep_magnitude + 1e-10)

recording_magnitude = np.abs(recording_fft)
recording_db = 20 * np.log10(recording_magnitude + 1e-10)



plt.figure(figsize=(10,4))

plt.plot(frequencies[:fft_length//2], recording_db[:fft_length//2])

plt.title("Frequency Domain (Decibels)")
plt.xlabel("Frequency (Hertz)")
plt.ylabel("Magnitude (dB)")

# 2. Stretch the X-Axis Logarithmically
plt.xscale('log')

# Add a tighter grid so we can see the logarithmic spacing
plt.grid(True, which="both", ls="-", color='0.8')

# Limit our view from 20 Hz (lowest human hearing) to 20,000 Hz
plt.xlim(20, 20000) 

plt.show()