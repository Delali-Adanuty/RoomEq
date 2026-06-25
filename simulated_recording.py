import numpy as np
from scipy.signal import convolve, firwin
from scipy.io import wavfile

#Simulating a physical room

sample_rate, sweep = wavfile.read("data/original_sweep.wav")

#Building a fake room's impulse response

#Create an array of zeros(total silence)
fake_ir = np.zeros(sample_rate)

# Lowpass the room at 3kHz and kill highs
lpf = firwin(255, 3000, fs=sample_rate)
fake_ir[:len(lpf)] = lpf

#Add a single distinct echo, half a second later at 30% volume.
echo_index = int(sample_rate * 0.5)
fake_ir[echo_index] += 0.3


#Play the sweep through the room
#This smears the room with our fake IR
simulated_recording = convolve(sweep, fake_ir, mode="full")


#Write the simulated file
wavfile.write("data/simulated_recording.wav", sample_rate, simulated_recording.astype(np.float32))