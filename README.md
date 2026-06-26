# Room Correction DSP Pipeline

**Author:** Van-Dyck Adanuty

A Python-based digital signal processing toolchain designed to extract physical room impulse responses, calculate stable inverse filters, and format the resulting data for strict real-time C++ (JUCE) convolution.

---

## Core Architecture

The pipeline is divided into two primary execution scripts, representing the transition from physical acoustic capture to mathematical inversion.

### 1. Impulse Response Extraction (Deconvolution)

Translates a raw acoustic sweep recording into a pure room impulse response (IR).

- **Methodology:** Divides the raw recording by the reference sine sweep in the frequency domain.
- **Regularization:** Utilizes an epsilon value (`1e-3`) added to the squared magnitude of the sweep to prevent mathematical blowup and high-frequency noise in areas with low sweep energy.

### 2. Inverse Filter Generation (Kirkeby Regularization)

Strips down the extracted IR and calculates the exact counter-frequencies needed to neutralize the room's acoustic signature.

- **Methodology:** Inverts the phase and frequency anomalies using Kirkeby Regularization.
- **Denominator Stabilization:** Applies a beta value (`0.1`) to cap infinite gain at frequency extremes (sub-bass and Nyquist regions), preventing convolution clipping and out-of-band hash.

---

## Mathematical & Formatting Constraints

To ensure the theoretical mathematics translate flawlessly into the physical constraints of the JUCE `juce::dsp::Convolution` engine, the pipeline enforces several rigid formatting stages.

- **Length Truncation (8192 Samples):** The filter is strictly truncated to 8192 samples (~185ms). This isolates the spatially stable direct sound and early reflections while discarding chaotic, diffuse late-stage reverberation. It maximizes the physical "sweet spot" and minimizes CPU overhead.
- **Circular Time Shift (`np.roll`):** Forces causality by shifting the wrapped data from the edges of the FFT array back to the center, aligning the main Dirac spike on a linear timeline.
- **Asymmetric Windowing:** Solves the physical byproduct of phase correction (pre-ringing). An asymmetric Hanning window is applied:
  - **1024-sample left ramp:** Acts as an aggressive mathematical gate, ruthlessly amputating metallic pre-ringing and time-domain wash before the transient.
  - **7168-sample right ramp:** Respects physical room decay, allowing the reverberant tail to smoothly release to absolute zero, preventing DC offset and spectral leakage.
- **Stereo Stacking:** The mono IR array is vertically stacked (`np.column_stack`) into a 2-channel matrix to satisfy the strict stereo processing contract of the C++ host.
- **Normalization Guard:** A dynamic safety check (`max_amp > 0`) ensures the filter is consistently peak-normalized prior to integer scaling to prevent clipping while preserving structural data.

---

## Pipeline Execution

1. **Capture:** Record a logarithmic sine sweep through the physical room (Studio Monitors -> Measurement Mic).
2. **Deconvolve:** Run the extraction script to generate the raw room IR.
3. **Invert & Format:** Run the Kirkeby inversion script. This will output the `correction_filter.wav` file.
4. **Compile:** Update the CMake `juce_add_binary_data` target in your C++ repository to point to the new 16-bit WAV file and execute a clean build to bake the filter into memory.

## Dependencies

- `numpy` - Core mathematical operations and matrix manipulations.
- `scipy` - FFT execution and WAV file standard I/O.
