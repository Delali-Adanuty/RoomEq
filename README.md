# Room Correction DSP Pipeline

**Author:** Van-Dyck Adanuty

A Python-based digital signal processing toolchain designed to extract physical room impulse responses, calculate stable inverse filters, and format the resulting data for strict real-time C++ (JUCE) convolution.

Read more about the behind the scenes **[here](https://delali-adanuty.github.io/RoomEq/)**

---

## Core Architecture

The pipeline is divided into three primary stages: physical acoustic capture, frequency-domain analysis and smoothing, and Kirkeby inversion.

### 1. Impulse Response Extraction (Deconvolution)

Translates a raw acoustic sweep recording into a pure room impulse response (IR).

- **Methodology:** Divides the raw recording by the reference sine sweep in the frequency domain.
- **Regularization:** Utilizes an epsilon value (`1e-3`) added to the squared magnitude of the sweep to prevent mathematical blowup and high-frequency noise in areas with low sweep energy.
- **Zero-Phase Alignment:** Anchors the exact peak of the impulse response to index 0 and circularly wraps the tail before the RFFT, preventing time-of-flight phase explosion.

### 2. Selective Fractional-Octave Smoothing

Averages complex frequency data in 1/3-octave bands to flatten chaotic high-frequency comb filtering — but **only above the ≈80 Hz Schroeder frequency**. Below that boundary, and above 20 kHz, the raw spectrum is left untouched so the algorithm can make precise, surgical corrections to real room modes instead of smoothing them away.

### 3. Inverse Filter Generation (Kirkeby Regularization)

Calculates the exact counter-frequencies needed to neutralize the room's acoustic signature.

- **Methodology:** Inverts the phase and frequency anomalies using Kirkeby Regularization.
- **Dynamic Beta Array:** Instead of a single flat regularization constant, a frequency-dependent `beta_array` is applied — `0.1` at the sub-bass and ultra-treble extremes, `0.005` through the midrange — so the filter is aggressively conservative where the room is unfixable and precise where it isn't.
- **Brickwall Ceiling:** A hard `np.clip` limits any single band to a maximum of +12 dB of boost, as a final failsafe independent of the Kirkeby penalties upstream.
- **Decoupled from Tone:** No target curve (Harman-style bass shelf / treble tilt) is baked in. This plugin corrects physics only; tonal shaping is left to downstream EQ, matching standard mixing workflow separation of concerns.

---

## Mathematical & Formatting Constraints

To ensure the theoretical mathematics translate flawlessly into the physical constraints of the JUCE `juce::dsp::Convolution` engine, the pipeline enforces several rigid formatting stages.

- **Length Truncation (8192 Samples):** The filter is strictly truncated to 8192 samples (~185ms), split as 1024 pre-transient + 7168 post-transient. This isolates the spatially stable direct sound and early reflections, discards chaotic diffuse reverberation, and lands on a power-of-two boundary for SIMD/cache-aligned convolution performance.
- **Circular Time Shift (`np.roll`):** Forces causality by shifting wrapped data from the edges of the FFT array back to the center, aligning the main Dirac spike on a linear timeline.
- **Asymmetric Windowing:** Solves the physical byproduct of phase correction (pre-ringing) via an asymmetric Hanning window:
  - **1024-sample left ramp:** An aggressive gate that amputates metallic pre-ringing before the transient.
  - **7168-sample right ramp:** A gentle release that lets the reverberant tail decay to zero without spectral leakage.
- **Stereo Stacking:** The mono IR array is vertically stacked (`np.column_stack`) into a 2-channel matrix to satisfy the C++ host's stereo contract.
- **Normalization Guard:** A dynamic safety check (`max_amp > 0`) ensures the filter is consistently peak-normalized prior to export.

---

## Pipeline Execution

1. **Capture:** Record a logarithmic sine sweep through the physical room (Studio Monitors → Measurement Mic).
2. **Deconvolve:** Run the extraction script to generate the raw room IR.
3. **Invert & Format:** Run the Kirkeby inversion script. This will output the `correction_filter.wav` file.
4. **Compile:** Update the CMake `juce_add_binary_data` target in your C++ repository to point to the new WAV file and execute a clean build to bake the filter into memory.

## Dependencies

- `numpy` — Core mathematical operations and matrix manipulations.
- `scipy` — FFT execution and WAV file standard I/O.

---

Explore the JUCE plugin **[here](https://github.com/Delali-Adanuty/RoomEqPlugin)**
