# Room Correction Pipeline: Technical Description

## 1. Scope

This document gives the calculation steps, filter properties, and measured results of my room correction pipeline. The pipeline is a set of Python scripts. It converts a measured room impulse response (IR) into an inverse FIR filter. A separate JUCE plugin ([RoomEqPlugin](https://github.com/Delali-Adanuty/RoomEqPlugin)) applies the filter with `juce::dsp::Convolution`.

The data in this document agrees with the scripts in this repository. Section 9 gives the next steps. Section 10 gives the limitations.

---

## 2. Background

A loudspeaker in a room has peaks and dips in its frequency response. An inverse filter tries to cancel them. The ideal inverse is:

$$H_{inv}(f) = \frac{1}{H(f)}$$

This inverse is not usable. Where H(f) is near zero, the inverse needs very high gain. Thus, I use Kirkeby regularization:

$$H_{inv}(f) = \frac{H^*(f)}{\lvert H(f)\rvert^2 + \beta(f)}$$

The term β(f) limits the gain where H(f) is small. Section 6 shows how β(f) controls the result.

---

## 3. Scripts

| Script | Input | Output | Function |
| :--- | :--- | :--- | :--- |
| `sine_sweep.py` | — | `data/original_sweep.wav` | Makes a 5 s logarithmic sweep, 20 Hz to 20 kHz, at 44.1 kHz. |
| `simulated_recording.py` | Sweep | `data/simulated_recording.wav` | Plays the sweep through a synthetic room: a 255-tap 3 kHz low-pass filter and one echo at 0.5 s (30% level). |
| `extractor.py` | Sweep, simulated signal | `data/extracted_ir.wav` | Calculates the IR of the synthetic room by regularized deconvolution (ε = 1e-3). |
| `generator.py` | `data/physical_ir_2.wav` | `data/correction_filter.wav` | Calculates the correction filter from a measured IR (Section 4). |
| `find_latency.py` | Correction filter | Console text | Shows the sample index of the filter peak. |

The first three scripts make a test of the method with a synthetic room. For a physical room, I use Room EQ Wizard (REW) to play the sweep, record it, and calculate the IR. `generator.py` uses the IR file from REW.

The `data/` folder is not in the repository (`.gitignore`). The file names are fixed in the scripts.

---

## 4. Filter Calculation (`generator.py`)

### 4.1 Peak Alignment

The script finds the sample with the largest absolute value. This is the direct sound. The script moves this sample to index 0. It moves the samples before the peak to the end of the array (circular shift). Then it calculates the RFFT.

### 4.2 Selective 1/3-Octave Smoothing

The script changes each frequency bin f from 80 Hz to 20 kHz. It replaces H(f) with the mean of the complex values from f × 2^(−1/6) to f × 2^(1/6). Below 80 Hz and above 20 kHz, the script does not change H(f).

The 80 Hz limit is my estimate of the Schroeder frequency of the room. I based it on the REW measurement. Below 80 Hz, the measurement showed separate resonant modes. Above 80 Hz, it showed dense comb filtering.

### 4.3 Kirkeby Inversion

The script applies the Kirkeby formula (Section 2) with this β(f) array:

| Frequency range | β |
| :--- | :--- |
| Below 40 Hz | 0.1 |
| 40 Hz to 80 Hz | Linear change from 0.1 to 0.005 |
| 80 Hz to 16 kHz | 0.005 |
| 16 kHz to 18 kHz | Linear change from 0.005 to 0.1 |
| Above 18 kHz | 0.1 |

### 4.4 Midrange Level Anchor

The script calculates the mean magnitude of H_inv from 500 Hz to 2 kHz. It divides H_inv by this value. Thus, the mean filter gain from 500 Hz to 2 kHz is 0 dB.

### 4.5 Boost Ceiling

The script limits the magnitude of H_inv to +12 dB, relative to the midrange level. It keeps the phase. There is no limit on cuts.

### 4.6 Time Domain Conversion and Truncation

1. The script calculates the inverse RFFT.
2. The script moves the array contents by N/2 samples (`np.roll`). This puts the main peak near the center of the array.
3. The script finds the new peak.
4. The script keeps 1024 samples before the peak and 7168 samples after it. The total is 8192 samples.

### 4.7 Window

The script multiplies the 8192 samples by an asymmetric window:

| Part | Length | Shape |
| :--- | :--- | :--- |
| Before the peak | 1024 samples | First half of a Hann window (0 to 1) |
| After the peak | 6656 samples | Flat (1) |
| End | 512 samples | Second half of a Hann window (1 to 0) |

The left part decreases pre-ringing before the peak. The flat part keeps the low-frequency content of the filter. The 512-sample fade stops a discontinuity at the end of the filter.

### 4.8 Export

The script copies the filter into two identical channels. It writes the result as a 32-bit float WAV file at the sample rate of the input IR. The script does not normalize the peak level. The midrange anchor (Section 4.4) sets the level.

---

## 5. Filter Properties

| Property | Value |
| :--- | :--- |
| Length | 8192 samples |
| Duration at 44.1 kHz | 185.8 ms |
| Peak position | Sample 1024 |
| Latency at 44.1 kHz | 23.2 ms (1024 samples), plus the latency of the convolution engine |
| Format | 2 channels, 32-bit float |

The durations in milliseconds change with the sample rate of the input IR.

---

## 6. Analysis: How β Controls the Gain

For one frequency bin, the Kirkeby gain is:

$$G = \frac{\lvert H\rvert}{\lvert H\rvert^2 + \beta}$$

This gain has a maximum value of 1/(2√β). The maximum occurs when |H| = √β.

| β | Maximum gain | Value of \|H\| at the maximum |
| :--- | :--- | :--- |
| 0.1 | +4.0 dB | −10 dB |
| 0.005 | +17.0 dB | −23 dB |

The result has two regions:

- **If |H| > √β:** The gain decreases when |H| increases. The filter cuts peaks. This is correct inverse behavior.
- **If |H| < √β:** The gain decreases when |H| decreases. Thus, weaker bins get less gain. The filter makes dips deeper. This is not inverse behavior.

β is an absolute value in this script. It is not relative to the level of H. In the measured IR, the sub-bass level is far below √0.1. Thus, the filter cuts the sub-bass. It does not correct it. Section 7 shows this result.

---

## 7. Results


### 7.1 Room Transfer Function

![Transfer function](images/transfer_function.png)

_Figure 1: Magnitude of the measured room transfer function._

The midrange is approximately −20 dB. Below 80 Hz, the level decreases to −40 dB or less. These levels are near or below √β in large parts of the spectrum.

### 7.2 Filter Response

![Pre-truncation inverse filter response](images/pre_window_fr.png)

_Figure 2: Filter response after the boost ceiling, before truncation and the window._

![Final filter response](images/filter_fr.png)

_Figure 3: Response of the final 8192-sample filter._

| Frequency | Filter gain (Figure 3) |
| :--- | :--- |
| 20 Hz | Approximately −47 dB |
| 50 Hz | Approximately −28 dB |
| 100 Hz | Approximately −15 dB |
| 200 Hz to 5 kHz | Approximately 0 dB, with small dips |
| 6 kHz | Notch, approximately −28 dB |
| Above 16 kHz | Decrease |

The filter cuts the sub-bass and makes a notch near 6 kHz. Section 6 gives the cause of the sub-bass cut. The 6 kHz notch is probably a result of the complex smoothing (Section 9.2).

### 7.3 Room Measurement (REW)

I measured the room with the filter bypassed (baseline). Then I measured it with the filter active (corrected). 

![Full spectrum, 1/3-octave smoothed](images/one_third_smoothing.webp)

_Figure 4: Baseline (red) and corrected (teal), 1/3-octave smoothed._

- **Below 80 Hz:** The speaker output decreases quickly. At 40 Hz, the baseline is approximately 50 dB below the midrange.
- **25 Hz to 150 Hz:** The corrected level is approximately 5 dB to 10 dB lower than the baseline.
- **200 Hz to 2 kHz:** The two traces are within approximately 4 dB.
- **3 kHz to 6 kHz:** The corrected level is up to approximately 10 dB lower, with a dip near 5 kHz.
- **Above 15 kHz:** The corrected level is lower.

From 200 Hz to 10 kHz, the corrected response is not flatter than the baseline.

![Full spectrum, unsmoothed](images/20_to_20k.png)

_Figure 5: Baseline and corrected, 20 Hz to 20 kHz, no smoothing._

![Sub-bass, unsmoothed](images/20_to_200.png)

_Figure 6: Baseline and corrected, 20 Hz to 200 Hz, no smoothing._

At 50 Hz, the baseline has a narrow null at approximately 18 dB. The corrected trace has a null at approximately 33 dB to 35 dB. I do not attribute this difference to the filter:

- The filter cuts 50 Hz by approximately 28 dB (Section 7.2). A cut cannot make a null shallower.
- At 50 Hz, the speaker output is approximately 50 dB below the midrange. The measurement is near the noise floor.
- The depth of a narrow null changes with small changes in microphone position.

---

## 8. Development Notes

### 8.1 Pre-Transient Length

**Symptom:** The final filter had much less low-frequency content than the response before truncation.

**Cause:** The pre-transient part of the slice was 44 samples. One cycle at 40 Hz is 25 ms (approximately 1100 samples at 44.1 kHz). The short slice removed the part of the filter that comes before the peak at low frequencies.

**Correction:** I increased the pre-transient length to 1024 samples.

### 8.2 Deconvolution Noise

**Symptom:** In the synthetic test, the extracted IR had high-frequency noise.

**Cause:** The first version divided the spectrum of the recorded signal by the sweep spectrum with ε = 1e-10. Where the sweep had almost no energy, the division gave very large values.

**Correction:** I changed to the regularized form, with ε = 1e-3:

```
IR spectrum = recorded × conj(sweep) / (|sweep|² + ε)
```

### 8.3 Regularization Value

I started with one β value for all frequencies (0.05, then 0.1, then 0.005). A high value gave a safe filter with little correction. A low value gave more noise. I then changed to the β array in Section 4.3.

### 8.4 Level Control

The first versions normalized the filter peak to 1.0. I replaced this with the midrange anchor (Section 4.4) and the +12 dB boost ceiling (Section 4.5).

### 8.5 Plugin Passthrough

**Symptom:** In the plugin, the convolution engine did not change the audio.

**Action:** I changed the export from one channel to two channels. After this change, the problem stopped.

**Note:** `juce::dsp::Convolution` accepts mono IRs. It applies a mono IR to all channels. Thus, the channel count was probably not the root cause. The root cause is probably in the IR load code of the plugin. I did not confirm the root cause.

---

## 9. Next Steps

### 9.1 Make β Relative to the Response

Divide H by its RMS magnitude from 500 Hz to 2 kHz before the inversion. Then β is relative to the midrange level. With β = 0.005, the filter then operates as an inverse for all bins above −23 dB relative to the midrange.

### 9.2 Change the Smoothing

The complex mean cancels where the phase changes quickly between bins. This decreases |H| and can make false dips, for example near 6 kHz. Smooth the magnitude only, and use the original phase or a minimum-phase calculation.

### 9.3 Limit the Correction Band

Do not correct frequencies where the speaker cannot make sound. Find the frequency where the baseline is 10 dB below the midrange. Set the filter gain to 0 dB below that frequency.

### 9.4 Measure Again


1. Measure the baseline and the corrected response at three to five microphone positions.
2. Level-match each pair of measurements at 500 Hz to 2 kHz.
3. Compare the average responses.

---

## 10. Limitations

- **Single position:** The filter is correct for one microphone position.
- **Linear time-invariant system:** The method assumes that the room and the speaker do not change.
- **Destructive interference:** A filter cannot fill a null that comes from two waves that cancel. More gain gives more energy to both waves.
- **Speaker bandwidth:** A filter cannot make a speaker produce frequencies below its low-frequency limit.
- **Filter length:** The filter has 8192 taps. It does not correct late reverberation.
- **Latency:** The 1024-sample pre-transient part adds 23.2 ms of latency at 44.1 kHz.

---

## 11. How to Run

1. Install Python 3 with numpy, scipy, and matplotlib.
2. Measure the room IR with REW. Export the IR as a WAV file.
3. Put the file in `data/` with the name `physical_ir_2.wav`.
4. Run `python generator.py`. Close each plot window to continue.
5. Copy `data/correction_filter.wav` into the plugin project. Update the `juce_add_binary_data` target in its CMake file.
6. Build the plugin again.

To test the method with the synthetic room, run `sine_sweep.py`, `simulated_recording.py`, and `extractor.py` in that sequence.

---

**Author:** Van-Dyck Adanuty
