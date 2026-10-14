# Room Correction DSP Pipeline

This is a set of Python scripts that converts a measured room impulse response (IR) into an inverse FIR filter. A separate JUCE plugin ([RoomEqPlugin](https://github.com/Delali-Adanuty/RoomEqPlugin)) applies the filter in real time with `juce::dsp::Convolution`.

## Purpose

A loudspeaker in a room has peaks and dips in its frequency response. A graphic EQ changes only the magnitude at fixed bands. An inverse FIR filter can change the magnitude and the phase at each frequency bin.

## Method

1. **Peak alignment:** Moves the direct sound of the IR to sample 0.
2. **Selective smoothing:** Applies 1/3-octave complex smoothing from 80 Hz to 20 kHz. Below 80 Hz, the room modes stay unsmoothed.
3. **Kirkeby inversion:** Calculates `H* / (|H|² + β)` with a frequency-dependent β. β is 0.1 below 40 Hz and above 18 kHz, and 0.005 from 80 Hz to 16 kHz.
4. **Level anchor and ceiling:** Sets the 500 Hz–2 kHz mean gain to 0 dB and limits boosts to +12 dB.
5. **Truncation and window:** Keeps 8192 samples (1024 before the peak, 7168 after). A Hann half-window decreases pre-ringing. A 512-sample fade ends the filter.
6. **Export:** Writes a 2-channel, 32-bit float WAV file. The plugin build puts this file into the binary.

## Filter Properties

| Property | Value |
| :--- | :--- |
| Length | 8192 taps (185.8 ms at 44.1 kHz) |
| Latency | 1024 samples (23.2 ms at 44.1 kHz) |
| Maximum boost | +12 dB relative to the 500 Hz–2 kHz level |
| Target curve | None |

## Current Results

I measured the room with REW, with the filter bypassed and with the filter active.

- **Sub-bass:** The filter cuts the sub-bass (approximately −28 dB at 50 Hz). It does not correct the room modes.
- **Midrange:** From 200 Hz to 2 kHz, the corrected response is within approximately 4 dB of the baseline.
- **Upper midrange:** The filter has a notch near 6 kHz. The measured response has a dip near 5 kHz.

**Cause of the sub-bass cut:** β is an absolute value. Where |H| < √β, the Kirkeby gain decreases with |H|, so the filter makes dips deeper. The measured sub-bass level is far below √0.1. Thus, the filter cuts it.

## Next Steps

- Make β relative to the response: divide H by its midrange RMS level before the inversion.
- Smooth the magnitude only, because the complex mean can make false dips.
- Measure again at three to five level-matched microphone positions.

## Limitations

- The filter is correct for one microphone position.
- A filter cannot fill a null from destructive interference.
- A filter cannot extend the low-frequency limit of the speaker.
- The filter adds 23.2 ms of latency at 44.1 kHz.

## How to Run

1. Install Python 3 with numpy, scipy, and matplotlib.
2. Measure the room IR with REW. Export it to `data/physical_ir_2.wav`.
3. Run `python generator.py`. Close each plot window to continue.
4. Copy `data/correction_filter.wav` into the plugin project and build the plugin again.

## Technical Documentation

For the full method, the measurements, the gain analysis, and the next steps, read the **[technical documentation](https://delali-adanuty.github.io/RoomEq/)**.

---

**Author:** Van-Dyck Adanuty
