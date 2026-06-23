import numpy as np
from scipy.signal import convolve
from scipy.io import wavfile

#Simulating a physical room

sample_rate, sweep = wavfile.read("data/original_sweep.wav")

#Building a fake room's impulse response

#Create an array of zeros(total silence)
fake_ir = np.zeros(sample_rate)

#Add the direct sound (60% to leave headroom)
fake_ir[0] = 0.6

#Add a single distinct echo, half a second later at 30% volume.
echo_index = int(sample_rate * 0.5)
fake_ir[echo_index] = 0.3


#Play the sweep through the room
#This smears the room with our fake IR
simulated_recording = convolve(sweep, fake_ir, mode="full")


#Write the simulated file
wavfile.write("data/simulated_recording.wav", sample_rate, simulated_recording.astype(np.float32))