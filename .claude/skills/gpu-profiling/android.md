# Android GPU profiling

## Android GPU Inspector (AGI)

**Use when:** the target is a supported Android device and the problem involves mobile game frame pacing, Vulkan/OpenGL ES commands, CPU/GPU scheduling, memory, battery, thermal behavior, or vendor GPU counters. AGI's system profiler is a Perfetto-like system-wide view; its frame profiler captures one application frame for in-depth Vulkan or OpenGL-on-ANGLE analysis.

**Target constraints:** the AGI quickstart requires a supported device running Android 11 or later, USB/ADB access, and a debuggable application (`android:debuggable="true"`). Supported GPU families and exact driver/device combinations are version-dependent; the AGI landing page calls out Qualcomm Adreno, Arm Mali, and Imagination PowerVR for system profiling. If using native Vulkan, enable validation layers as required by the installed AGI release and fix validation errors before interpreting performance data. The desktop host and device must meet the current AGI quickstart requirements.

The current AGI quickstart notes that Android Performance Analyzer is the newer recommended choice for system profiling. Use AGI when its frame profiler, supported counters, existing traces, or graphics workflow is the requirement; do not present AGI system profiling as the only current Android system-tracing option.

**GUI system-profile workflow:**

1. Connect the device by USB, enable ADB/Install via USB, launch AGI, and select the `adb` executable.
2. Choose **Capture a new trace** and select **System profile**. Select only relevant CPU, GPU, memory, battery, and GPU counter options; use a short manual duration.
3. Start the trace, reproduce the same scene/input, stop after the chosen interval, and open the trace.
4. Correlate app/render threads, scheduling, GPU queue activity, memory pressure, thermal or battery events, and frame-time outliers.

**GUI frame-profile workflow:**

1. Choose **Capture a new trace** and select **Vulkan** or **OpenGL on ANGLE** to match the app's actual graphics path.
2. Select manual start and a short capture, choose the app/process (including a separate graphics process if the app uses one), start it, and press **Start** at a known frame.
3. Open the trace and inspect the frame's API calls, render passes, dependencies, GPU work, and counters. Use the system profile to check whether the captured frame is representative.

AGI is primarily a GUI workflow; do not invent a command-line interface for frame capture. `adb` is used for device setup and diagnostics, not as a replacement for AGI's capture UI. If Vulkan validation layers must be forced for a debuggable app, the documented setup is analogous to:

```bash
app_package=<package>
abi=arm64v8a
adb shell settings put global enable_gpu_debug_layers 1
adb shell settings put global gpu_debug_app "$app_package"
adb shell settings put global gpu_debug_layer_app "com.google.android.gapid.$abi"
adb shell settings put global gpu_debug_layers VK_LAYER_KHRONOS_validation
```

After profiling, remove the temporary global settings and restore the device's prior state:

```bash
adb shell settings delete global enable_gpu_debug_layers
adb shell settings delete global gpu_debug_app
adb shell settings delete global gpu_debug_layers
adb shell settings delete global gpu_debug_layer_app
```

**Interpretation:**

- System profile: use scheduling and queue timelines to separate CPU starvation, GPU saturation, memory bandwidth/pressure, synchronization, and thermal throttling.
- Frame profile: identify expensive passes and API submissions, then inspect dependencies and counters for the selected frame. API calls are evidence of recorded work, not automatically the root cause.
- GPU counter names and availability are vendor/driver-specific. Compare a change on the same device and driver; never compare an Adreno counter directly with a Mali or PowerVR counter.

**Overhead and limits:** AGI instrumentation, Vulkan validation, frame capture, and counters can change CPU/GPU timing, memory usage, driver behavior, and thermal state. Validation is especially unsuitable for final frame-time claims. Captures may include app resources, shader data, and device identifiers. Keep traces short, rerun without instrumentation, and use a production-like non-debug build for final measurements while retaining a debuggable build for capture.
