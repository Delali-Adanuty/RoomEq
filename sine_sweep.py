import numpy as np
from scipy.signal import chirp
from scipy.io import wavfile

#Generating Sine Sweep


#Defining Audio Parameters
sample_rate = 44100 #Hz
duration = 5 #seconds


#Generate the timeline
total_samples = sample_rate * duration
t = np.linspace(0, duration, total_samples, endpoint=False)

#Audio waveform
sweep = chirp(t, f0 = 20, f1= 20000, t1 = duration, method="logarithmic")

sweep_32bit = sweep.astype(np.float32)
wavfile.write("data/original_sweep.wav", sample_rate, sweep_32bit)