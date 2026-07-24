# Room Correction DSP Pipeline

**Author:** Van-Dyck Adanuty

This project is a Python-based digital signal processing toolchain designed to extract physical room impulse responses, calculate stable inverse filters, and format the resulting data for strict real-time C++ (JUCE) convolution.

Read more about the behind-the-scenes process **[here](https://delali-adanuty.github.io/RoomEq/)**.

---

## Core Architecture

The pipeline is divided into three primary stages: physical acoustic capture, frequency-domain analysis and smoothing, and Kirkeby inversion.

### Impulse Response Extraction (Deconvolution)

To translate a raw acoustic sweep recording into a pure room impulse response, the system divides the raw recording by a reference sine sweep in the frequency domain. To prevent mathematical blowups and high-frequency noise in areas with low sweep energy, the process utilizes an epsilon regularization value (`1e-3`) added to the squared magnitude of the sweep. Furthermore, the exact peak of the impulse response is anchored to index 0. By circularly wrapping the tail before the RFFT, the algorithm successfully prevents time-of-flight phase explosion, providing an isolated and pristine impulse response to work with.

### Selective Fractional-Octave Smoothing

Once the impulse response is extracted, the frequency data undergoes selective fractional-octave smoothing.

The system averages complex frequency data in 1/3-octave bands to flatten chaotic high-frequency comb filtering. However, this smoothing is strictly enforced only above the approximate 80 Hz Schroeder frequency. Below that boundary, and above 20 kHz, the raw spectrum is left completely untouched.

This deliberate isolation allows the algorithm to make precise, surgical corrections to actual real-world room modes rather than accidentally smoothing them away into mathematical oblivion.

### Inverse Filter Generation (Kirkeby Regularization)

Generating the inverse filter requires calculating the exact counter-frequencies needed to neutralize the room's physical response. The pipeline achieves this by inverting the phase and frequency anomalies using Kirkeby Regularization. Instead of relying on a single, flat regularization constant, it applies a frequency-dependent dynamic beta array. The beta value is set to `0.1` at the sub-bass and ultra-treble extremes, and tightened to `0.005` through the midrange. Consequently, the filter acts aggressively conservative where the room is physically unfixable, yet highly precise where correction is viable. As a final failsafe independent of the upstream Kirkeby penalties, a hard `np.clip` brickwall ceiling limits any single band to a maximum of +12 dB of boost.

Crucially, this correction is entirely decoupled from tone. No target curve, such as a Harman-style bass shelf or treble tilt, is baked into the math. This plugin corrects physics only. Tonal shaping is deliberately left to downstream EQ, matching the standard mixing workflow's separation of concerns.

---

## Mathematical & Formatting Constraints

To ensure that the theoretical mathematics translate flawlessly into the physical constraints of the JUCE `juce::dsp::Convolution` engine, the pipeline enforces several rigid formatting stages.

The filter is strictly truncated to 8192 samples (roughly 185 milliseconds), carefully split into 1024 pre-transient and 7168 post-transient samples. This truncating step isolates the spatially stable direct sound and early reflections while discarding chaotic diffuse reverberation, ultimately landing on a power-of-two boundary to ensure optimal SIMD and cache-aligned convolution performance. To force causality, a circular time shift using `np.roll` shifts wrapped data from the edges of the FFT array back to the center, aligning the main Dirac spike on a linear timeline.

Addressing the physical byproduct of phase correction—specifically, metallic pre-ringing—requires an asymmetric Hanning window. A 1024-sample left ramp acts as an aggressive gate that amputates pre-ringing before the transient, while a 7168-sample right ramp provides a gentle release that allows the reverberant tail to decay to zero without spectral leakage.

Finally, the mono impulse response array is vertically stacked into a 2-channel matrix via `np.column_stack` to satisfy the C++ host's stereo contract, and a dynamic safety check guarantees the filter is consistently peak-normalized prior to export.

---

## Verification

The filter's effect was verified with physical REW measurements rather than simulated diagnostics. Level-matched baseline versus corrected sweeps demonstrate a dramatic ~15 dB reduction in the sharp modal null at 50 Hz.

![Sub-bass correction, unsmoothed, level-matched](docs/images/20_to_200.png)

Full measurement methodology and additional plots covering treble comb-filtering, tonal balance, and filter response are available in the [detailed docs](https://delali-adanuty.github.io/RoomEq/).

## Pipeline Execution & Dependencies

Executing this pipeline relies on a minimal footprint of core dependencies: `numpy` for core mathematical operations and matrix manipulations, and `scipy` for FFT execution and standard WAV file I/O.

The execution process itself follows a strict, step-by-step sequence:

1. **Capture:** Record a logarithmic sine sweep through the physical room (Speakers → Measurement Mic).
2. **Deconvolve:** Run the extraction script to generate the raw room IR.
3. **Invert & Format:** Run the Kirkeby inversion script. This will output the `correction_filter.wav` file.
4. **Compile:** Update the CMake `juce_add_binary_data` target in your C++ repository to point to the new WAV file and execute a clean build to bake the filter into memory.

---

Explore the JUCE plugin **[here](https://github.com/Delali-Adanuty/RoomEqPlugin)**
