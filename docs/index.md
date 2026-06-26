# Room Correction DSP: Python Toolchain

**Author:** Van-Dyck Adanuty

Welcome to the documentation for the Room Correction DSP pipeline. This toolchain handles the mathematical heavy lifting of physical room correction: extracting an acoustic signature from a physical space, calculating a stable inverse filter, and formatting the data for zero-latency execution in a C++ (JUCE) convolution engine.

This architecture is built on the philosophy of systematic isolation. By stripping the acoustic mathematics down to their absolute bare bones and verifying each piece independently, the pipeline guarantees causality, mathematical stability, and strict host-compliance without relying on black-box external libraries.

---

## The Architectural Philosophy

In digital signal processing, mathematical perfection often directly conflicts with physical reality. Calculating a "perfect" inverse of a room yields an unstable, non-causal filter that causes severe pre-ringing, destroys transients, and possesses a microscopic physical "sweet spot."

This toolchain bridges the gap between theoretical math and acoustic engineering by rigorously enforcing physical boundaries:

1. **Truncating acoustic chaos** by focusing exclusively on early reflections.
2. **Eliminating mathematical pre-ringing** using custom asymmetric windowing.
3. **Preventing out-of-band amplification** through denominator stabilization.

---

## Phase 1: Acoustic Capture & Deconvolution

The pipeline begins by translating the physical room into pure mathematical data.

### The Mechanism

A logarithmic sine sweep is played through a speaker. and captured via a measurement microphone. The script does not use the raw recording; instead, it extracts the pure impulse response (IR) of the room through frequency-domain deconvolution.

$$H_{room} = \text{IFFT}\left( \frac{\text{FFT}(Recording) \cdot \text{FFT}(Sweep)^*}{|\text{FFT}(Sweep)|^2 + \epsilon} \right)$$

- **Regularization Epsilon ($\epsilon = 1e-3$):** Added to the magnitude of the sweep to prevent division-by-zero errors in regions where the speaker lacks physical energy (e.g., sub-bass). This stabilizes near-zero frequencies and prevents high-frequency noise blowout.

---

## Phase 2: Mathematical Inversion (Kirkeby)

Once the raw room IR is extracted, the engine calculates the exact counter-frequencies necessary to neutralize it.

### The Classroom Trap vs. Kirkeby Regularization

In a standard academic DSP environment, the inverse transfer function is taught as an elegant, straightforward equation:

$$H_{inv} = \frac{1}{H_{room}}$$

Applying this textbook theory to a physical room results in immediate, catastrophic clipping. Real rooms have deep acoustic nulls—frequencies that violently cancel each other out. If the microphone captures near-zero energy at 150 Hz, the theoretical formula attempts to divide by zero, demanding infinite gain from the speakers.

To bridge the gap between classroom theory and physical reality, this pipeline abandons the pure inverse and employs Kirkeby Regularization, calculating a least-squares optimized inverse filter:

$$H_{inv} = \frac{H_{room}^*}{|H_{room}|^2 + \beta}$$

- **Denominator Stabilization ($\beta = 0.1$):** This parameter is the physical safety net. It caps the infinite gain required to correct uncorrectable acoustic nulls. By mathematically stabilizing the denominator, it prevents the convolver from blowing out the speaker cones and eliminates out-of-band hash at the extreme ends of the frequency spectrum.

---

## Phase 3: The Physical-Digital Boundary

The raw output of the Kirkeby inversion is mathematically correct but physically unusable. It contains wrap-around artifacts, destructive pre-ringing, and uncorrectable late-stage reverberation. The pipeline applies three strict transformations.

### 1. The 8192-Sample Truncation (Spatial Stability)

The raw inverted signal is aggressively truncated to 8192 samples (~185 milliseconds).

- **Why:** Sound travels roughly 1 foot per millisecond. Attempting to correct 1,000 milliseconds of chaotic, diffuse room reverb creates a filter with high "spatial fragility" (moving your head an inch breaks the phase correction). 8192 samples restricts the DSP strictly to the direct sound and early desk reflections, maximizing the physical sweet spot while keeping CPU overhead minimal.

### 2. Circular Time Shift (Causality)

Because FFT operations assume circular, infinitely looping signals, the Kirkeby output wraps "negative time" data around to the end of the array. `np.roll` is used to drag this wrapped data to the center, realigning the main Dirac spike onto a linear timeline.

### 3. Asymmetric Windowing (Transient Clarity)

Phase correction inherently requires pre-ringing (energy that occurs _before_ the main sound). To prevent transients (like snare hits) from sounding metallic or "washed out," an asymmetric Hanning window is applied:

- **Left Side (1024 samples):** An aggressive mathematical gate. It rapidly scales from `0.0` to `1.0`, ruthlessly amputating the pre-ringing right up until the microsecond the physical transient hits.
- **Right Side (7168 samples):** A gentle physical release. It smoothly curves from `1.0` to `0.0`, allowing the physical tail of the room to ring out naturally, preventing DC offsets and spectral leakage.

---

## Phase 4: JUCE C++ Export Compliance

The final filter must be ingested by the JUCE `juce::dsp::Convolution` engine. JUCE's lightweight internal memory parser enforces strict constraints. The Python script formats the data to guarantee instantaneous, static binary compilation.

1. **Strict Stereo Stacking:** The 1D mono filter is vertically stacked (`np.column_stack`) into a `(8192, 2)` matrix to fulfill the strict `Stereo::yes` contract of the C++ convolver.
2. **32-Bit Float Casting:** The stereo matrix is explicitly cast to `np.float32`. This preserves the microscopic structural integrity of the FIR coefficients natively without requiring destructive integer scaling or quantization.
3. **Peak Normalization:** A dynamic guard (`max_amp > 0`) guarantees the filter is peak-normalized, preventing mathematical clipping during live sum-of-products convolution.

### Final Output

The script generates `correction_filter.wav`. This file is not intended to be read from a file system at runtime. It is designed to be injected directly into the VST3 binary via CMake's `juce_add_binary_data` module, effectively turning the mathematical array into a hardcoded C++ memory block.

---

## Engineering Challenges

Building a DSP pipeline that spans from theoretical Python math to real-time C++ execution required navigating severe mathematical and architectural traps. The following critical issues were systematically isolated and resolved during development:

- **The Convolution Engine "Passthrough" Anomaly:** The JUCE convolver acted as a dry passthrough, ignoring the impulse response. This was isolated to a strict channel mismatch: the Python script was exporting a 1-channel mono array, which violated the `Stereo::yes` contract of the C++ engine. Stacking the array vertically via `np.column_stack` resolved the bypass.
- **The Normalization Bypass:** The safety guard intended to prevent floating-point clipping (`if max_amp > 1:`) silently failed because the raw Kirkeby output naturally falls well below an amplitude of 1.0. This was corrected to trigger dynamically (`if max_amp > 0:`), ensuring consistent peak normalization regardless of the input scale.
- **Regularization Epsilon Blowout:** During deconvolution, an epsilon of `1e-10` was initially used. This was mathematically too small, causing high-frequency energy to blow up in regions where the sine sweep lacked physical acoustic energy, resulting in severe audible noise. Increasing $\epsilon$ to a standard `1e-3` threshold stabilized the frequency boundaries.
- **Mathematical Reference Errors:** The initial deconvolution logic inadvertently added the regularization epsilon to the complex frequency data instead of its magnitude, failing to stabilize the denominator. The formula was explicitly corrected to divide by the squared magnitude plus epsilon ($|S|^2 + \epsilon$).
- **Synthetic Testing Limitations:** Initial verification of the C++ engine was severely bottlenecked by a fake impulse response that was too rudimentary. Because it featured a dominant direct-sound spike with no coloration, the calculated inverse filter was virtually identical to a dry signal, making the DSP processing perceptually inaudible. The test environment had to be upgraded to use heavily colored synthetic responses to definitively prove audio thread interception.

---

## Core Learning Experiences

Beyond the codebase, engineering this pipeline forced a permanent shift from theoretical, textbook mathematics to physical, instinctive DSP engineering.

### 1. Absolute Frequency Domain Analysis

Prior to this architecture, analyzing frequency domain graphs (FFTs) was largely a comparative exercise—looking at Graph A next to Graph B to spot relative differences. Developing the inverse filter demanded a strict, absolute understanding of the frequency domain. Analyzing a single FFT plot is now sufficient to instantly identify physical acoustic nulls, hazardous out-of-band energy, and the exact bandwidth limitations of the physical hardware without needing a reference comparison.

### 2. Windowing: From Theory to Instinct

While DSP windowing is standard academic theory, calculating a mathematically perfect, non-causal inverse filter demonstrated exactly _why_ windowing is mandatory in the physical world. Encountering metallic pre-ringing (time-domain wash) provided the crucial context. Splicing an asymmetric Hanning window using a steep 1024-sample left ramp as an aggressive mathematical gate, and a 7168-sample right slope to respect physical room decay transformed windowing from a textbook formula into an understandable engineering tool.

### 3. The Illusion of the Perfect Inverse

Coming from a traditional DSP academic background, the concept of system inversion was understood strictly through the lens of ideal transfer functions: $H_{inv} = 1/Y(s)$. Running that exact classroom theory into a physical audio engine and watching it violently fail was a pivotal moment. When the textbook inverse hit physical acoustic nulls and blew out the convolution engine with infinite gain, it forced a complete re-evaluation of the math. Learning Kirkeby Regularization as a fix to that was a not so nice but nice experience.
