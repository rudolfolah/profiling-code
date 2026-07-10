# GPU Profiling Tools Skill

Use this skill when the question involves GPU frame time, GPU/CPU overlap, graphics API behavior, kernel throughput, GPU counters, mobile graphics, heterogeneous CPU/GPU execution, or power/thermal effects. Start by identifying the target device, graphics/compute API, and the question being asked; do not select a profiler solely because it is installed.

This skill covers the seven tools listed in this repository's GPU profiling section:

- [NVIDIA Visual Profiler](https://developer.nvidia.com/nvidia-visual-profiler)
- [NVIDIA Nsight Systems](https://developer.nvidia.com/nsight-systems)
- [NVIDIA Nsight Compute](https://developer.nvidia.com/nsight-compute)
- [Android GPU Inspector (AGI)](https://developer.android.com/agi)
- [Metal debugger](https://developer.apple.com/documentation/xcode/metal-debugger)
- [AMD uProf](https://www.amd.com/en/developer/uprof.html)
- [Intel VTune Profiler](https://www.intel.com/content/www/us/en/developer/tools/oneapi/vtune-profiler.html)

The commands below are examples for an installed tool; adapt executable paths, options, target API, and result names to the installed version. Claude must not claim to have run any command unless it actually did so.

## Choose the measurement first

| Question | Start with | Why | Do not infer from it alone |
|---|---|---|---|
| Is a frame slow, stuttering, or serialized? | A system/timeline profile | Shows CPU threads, graphics/compute queues, API calls, synchronization, transfers, and idle gaps on one time axis | A busy GPU does not prove that a particular shader is the cause |
| Which CUDA/HIP/OpenCL/SYCL kernel is slow? | Kernel or GPU-hotspot analysis | Ranks kernels and exposes throughput, stalls, memory, occupancy, and source correlation | A kernel percentage is not the same as frame contribution; account for invocation count and overlap |
| Which draw, pass, resource, or shader caused a rendering result? | A graphics API frame capture | Replays a bounded frame and exposes command order, attachments, resources, pipeline state, and shader data | Capture timing is representative of the shipping workload; capture can perturb it substantially |
| Is the Android game CPU-, GPU-, memory-, battery-, or driver-bound? | AGI system profile, then AGI frame profile | System trace establishes cross-device context; frame trace narrows to Vulkan/OpenGL ES work | A counter from one Android GPU is not necessarily comparable to a counter with the same name on another GPU |
| Is the workload limited by AMD or Intel CPU/GPU hardware? | AMD uProf or Intel VTune, respectively | Their sampling, hardware-event, accelerator, and power analyses match the vendor's PMU and driver | Vendor metrics and derived percentages do not transfer directly across architectures |
| Is the issue specifically Metal command behavior? | Xcode Metal debugger | It can capture/replay Metal workloads and inspect dependencies, counters, resources, and shaders | A GPU trace is not a substitute for measuring an uninstrumented run |

### Timeline/system profiling versus kernel counters

Keep these analyses separate:

- **Timeline/system profiling** answers *when* work happened and *what was waiting*. Look for CPU submission gaps, queue bubbles, synchronization, copies, page faults, thermal throttling, context switches, and frame-to-frame variance. It is the first pass for game stutter and end-to-end latency.
- **Kernel counters** answer *why a selected GPU program is inefficient*. Look for arithmetic or memory throughput, occupancy, cache behavior, wave/warp stalls, instruction mix, and source-line correlation. They are a second pass after the timeline proves that the kernel matters.
- **Graphics API captures** answer *which commands and state produced a frame*. They are bounded replay/debug captures, not low-overhead production measurements.

A GPU can show high utilization while the frame is still slow because of poor scheduling, a long queue, copies, or synchronization. A GPU can show low utilization because the CPU is late, the workload is too small, the queue is blocked, or the application is waiting on presentation. Correlate CPU submission time, GPU execution time, queue wait time, and frame percentile data before naming a bottleneck.

## A repeatable workflow

1. **Define the acceptance metric.** Record the unprofiled baseline: frame-time percentiles (not only average FPS), CPU and GPU frame duration, kernel duration or throughput, and power/temperature if relevant.
2. **Describe the target.** Record GPU model and memory, driver/firmware, OS and device build, API (CUDA, HIP, Vulkan, OpenGL ES, Metal, DirectX, SYCL/OpenCL), display mode, resolution, refresh/vsync, compiler flags, and profiler version.
3. **Make the workload deterministic.** Use a fixed scene/input, seed, asset set, camera, resolution, workload size, and run duration. Warm up shader compilation, caches, asset streaming, and the runtime before capture. Use the same power/performance mode and background-load policy.
4. **Capture a narrow interval.** Prefer a representative 2–20 second timeline or one to a few representative frames. Use API markers (for example, NVTX or application labels) and explicit frame boundaries where the tool supports them. Avoid capturing the whole game session by default.
5. **Start broad, then narrow.** Use a timeline/system view to locate the bad frame, queue, or phase. Then profile only the relevant kernel, range, pass, or counter set. Do not start with an exhaustive counter set on every kernel.
6. **Repeat the baseline and capture.** Run at least three comparable unprofiled and profiled trials when the effect is noisy. Treat a profiler-induced change as overhead until it survives a lighter collection and an unprofiled measurement.
7. **Compare like with like.** Keep tool/driver/device, metric set, clock mode, input, and warm-up identical. A derived metric, percentage of peak, or occupancy number must be interpreted against the exact architecture and collection mode.
8. **Record evidence.** Preserve the report/trace, command line or GUI settings, application commit, symbols/shader binaries, tool version, and a short note describing the selected interval and expected result.

## Tool selection and workflows

### NVIDIA Visual Profiler (legacy CUDA workflow)

**Use when:** an existing CUDA project still depends on `nvprof`/`nvvp`, or an old `.nvprof` session must be inspected. The tool provides a GUI view of CUDA API calls, kernel launches, memory transfers, a CPU/GPU timeline, and configurable hardware metrics.

**Important lifecycle constraint:** NVIDIA's current page says Visual Profiler was discontinued as of CUDA Toolkit 13.0. Prefer Nsight Systems for system/timeline analysis and Nsight Compute for kernel analysis on new work. Do not recommend installing a legacy profiler merely to investigate a new workload. CUDA 11 and later do not support developing or running applications on macOS; NVIDIA's macOS-host Visual Profiler was available only through CUDA 12.4 and macOS host packages were dropped in CUDA 12.5. Targets are CUDA-capable NVIDIA platforms supported by the corresponding legacy toolkit (commonly Linux or Windows; ARM support depends on that toolkit).

**Minimal legacy collection (CLI, only if the installed toolkit provides it):**

```bash
nvprof --export-profile=legacy.nvprof ./cuda-app [args]
nvvp legacy.nvprof
```

If option spelling differs in an older toolkit, use `nvprof --help`; do not silently substitute an Nsight report format. Open the resulting profile in the Visual Profiler GUI and inspect the unified CPU/GPU timeline before running metric experiments.

**Interpretation:**

- Start with host API launch and synchronization time, device kernel intervals, and host-to-device/device-to-host copies.
- A large gap between a host launch and device execution suggests submission, dependency, or synchronization issues; a long device interval makes the kernel a candidate for Nsight Compute.
- Use occupancy and memory/SM counters as architecture-specific evidence. Compare the same kernel and launch configuration across sessions, not raw counter values across GPU generations.
- Metric collection may replay kernels or serialize activity. A metric result can describe a replayed kernel and may not represent concurrent production behavior.

**Overhead and limits:** tracing, instrumentation, metric experiments, and replay can materially change launch order, overlap, clocks, and wall time. Visual Profiler is not a modern Vulkan/DirectX/Metal frame debugger. Keep it for legacy CUDA evidence and migrate the question to Nsight Systems or Nsight Compute when possible.

### NVIDIA Nsight Systems

**Use when:** the question is end-to-end scheduling and overlap on an NVIDIA system: game frame stutter, CPU submission, CUDA/graphics queue occupancy, copies, synchronization, library calls, network/OS activity, or GPU metrics over time. It traces CUDA and can trace Vulkan, OpenGL, DirectX 11/12, DXR, and OptiX API activity; this is an API/system timeline, not a full draw-state debugger.

**CLI collection:**

```bash
# CUDA and application markers; keep the interval short and name the report.
nsys profile --trace=cuda,nvtx -o nsys-cuda-run ./cuda-app [args]

# Choose the graphics API used by the target; do not enable unrelated APIs.
nsys profile --trace=vulkan,nvtx -o nsys-vulkan-run ./game [args]
# For another supported target, replace vulkan with opengl, dx11, or dx12.

# Open the report in the GUI and optionally generate summary statistics.
nsys-ui nsys-cuda-run.nsys-rep
nsys stats nsys-cuda-run.nsys-rep
```

`nsys profile` starts and collects in one command. For an application with reliable markers, bound collection to a marker rather than tracing startup:

```bash
nsys profile --trace=cuda,nvtx --capture-range=nvtx \
  --nvtx-capture=profile-range@* -o nsys-range ./app [args]
```

Check `nsys profile --help` for version-specific option names. GPU metric sampling and system-wide sampling can require root/administrator privileges or special driver permissions; request the smallest permission and metric set needed.

**GUI workflow:** launch `nsys-ui`, configure the local or remote target, select only the needed CPU/GPU/API traces, start the app after the target is configured (especially for Vulkan), and inspect the unified timeline. Zoom to a bad frame or marker, correlate CPU thread submission with the graphics/compute queue, then inspect API calls, memory operations, synchronization, and GPU metrics. Use the CLI for repeatable runs and the GUI for interactive correlation.

**Interpretation:**

- A long CPU interval with no GPU work often means CPU submission, synchronization, or an application-side bottleneck.
- A queue gap after a launch can indicate dependencies, a late producer, or a host wait; verify the corresponding API and thread rather than blaming the next kernel.
- A continuously busy queue with high frame time means the workload is GPU-limited at that phase; hand the dominant kernel to Nsight Compute or use a graphics frame debugger for draw/pipeline state.
- GPU metrics are sampled over time and are not a replacement for per-kernel counters. Sampling frequency, metric set, and available hardware vary by GPU.

**Overhead and limits:** Nsight Systems is designed for low-overhead system analysis, but tracing every API, backtrace, OS event, or high-frequency GPU metric increases overhead and report size. Disable CPU sampling or reduce sampling frequency for a GPU-only question. It does not provide the detailed resource/shader/pipeline replay of a graphics frame debugger, and it cannot turn a timeline into proof of a particular shader's cause. Keep CLI and GUI versions aligned; a newer report may not open correctly in an older GUI.

### NVIDIA Nsight Compute

**Use when:** the NVIDIA CUDA or OptiX timeline identifies a kernel worth optimizing and the question is kernel throughput, memory behavior, occupancy, warp stalls, instruction mix, source/SASS correlation, or roofline-style limits. It is not a Vulkan/OpenGL/DirectX frame debugger and should not be the first tool for unexplained game stutter.

**CLI collection and GUI review:**

```bash
# The basic set is a practical first pass; use a report name for comparison.
ncu -o ncu-basic ./cuda-app [args]

# Limit collection to one named kernel when the application has many launches.
ncu --kernel-name regex:myKernel --launch-count 1 -o ncu-kernel ./cuda-app [args]

# Open the report in the GUI (the report extension is produced by ncu).
ncu-ui ncu-basic.ncu-rep
```

Use `ncu --list-sets`, `ncu --list-sections`, and `ncu --query-metrics` before selecting architecture-specific sections or metrics. NVTX range filtering can restrict collection to a phase, but the exact filter syntax is version-specific; check the installed CLI help. For an interactive GUI run, select the application, kernel/range filters, and the smallest section set that answers the current question.

**Interpretation:**

- Begin with GPU throughput and the roofline/memory workload view. Distinguish arithmetic saturation from memory bandwidth, cache, latency, or launch-bound behavior.
- Inspect occupancy together with register/shared-memory usage and launch dimensions; low occupancy is a clue, not automatically a defect.
- Use warp-state/stall metrics to ask what the warp is waiting on (memory, dependency, barrier, instruction issue, or another cause); then correlate to source/PTX/SASS.
- Check total frame contribution: a fast kernel called thousands of times may dominate a slower kernel called once.
- Compare one kernel, input, launch configuration, metric set, and GPU architecture before attributing an improvement.

**Overhead and limits:** Nsight Compute commonly replays a kernel multiple times to collect mutually exclusive hardware counters. It can serialize concurrent work, perturb caches and clocks, expose nondeterminism, or fail to make progress for mandatory concurrent kernels. Limit launches, use deterministic input, avoid profiling a whole training/game session, and treat replayed timings as diagnostic rather than shipping latency. Many counters are unavailable or renamed on different compute capabilities; use the tool's metric query and report warnings.

### Android GPU Inspector (AGI)

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

### Metal debugger

**Use when:** the target is an Apple Metal workload and the question is command order, render/compute pass dependencies, resources, attachments, pipeline state, shader behavior, GPU timeline, or Apple GPU counters. The Metal debugger is part of Xcode and supports GPU frame capture/replay; it is the graphics API capture workflow for Metal.

**Xcode GUI capture:**

1. In the Run scheme, open **Edit Scheme > Run > Options** and set **GPU Frame Capture** to **Metal** (or **Automatically** when appropriate).
2. Run the app, click the **Metal Capture** button in the debug bar, select a frame/command queue/device/custom capture scope and count, and click **Capture**.
3. Inspect the replayed GPU trace: command buffers, encoders/passes, dependencies, attachments, resources, pipeline state, shader source, timeline, and counters. Export with **File > Export** when a `.gputrace` artifact is needed.

To capture a bounded workload from code, use `MTLCaptureManager` and `MTLCaptureDescriptor` around the desired command buffers. The capture destination can be a GPU trace (`.gputrace`) when supported. On macOS 14 and later, `MTL_CAPTURE_ENABLED=1` enables programmatic capture support; it has a small but measurable CPU effect, so keep it out of release builds.

**CLI trace inspection:** current Xcode versions provide the interactive `gpudebug` command for GPU traces:

```bash
gpudebug -t /path/to/Scene.gputrace
# At the gpudebug prompt, navigate and inspect a node:
# go commands/cb1/re0
# info pipeline
# fetch color0
```

The exact trace node paths depend on the capture; use `man gpudebug` and the tool's `list`/`go` commands rather than hard-coding paths. CLI replay is useful for scripted inspection and resource extraction, while Xcode is better for visual exploration and shader debugging.

**Interpretation:**

- Use the timeline to find long encoders, gaps, and pass dependencies; then inspect the command that owns the cost.
- Use counter statistics and per-line shader profiling only for the captured pass/command and the exact Apple GPU; counters are not portable across Apple GPU generations or to non-Apple GPUs.
- A frame capture can reveal incorrect attachments or state even when the performance symptom is elsewhere. Pair the capture with uninstrumented frame-time data.

**Overhead and limits:** frame capture and replay can add CPU work, memory, disk, synchronization, and shader instrumentation effects. The debugger may replay on a different device than the one that produced the trace unless configured otherwise. Capture only a small reproducible scope, record device/OS/Xcode versions, and do not use a capture-enabled build as the performance baseline.

### AMD uProf

**Use when:** the target is an AMD Zen-based CPU or AMD Instinct MI accelerator and the question spans CPU sampling, hardware events/IBS, thread and OS timelines, power/thermal behavior, or supported MI GPU/HIP/HSA activity. uProf is useful for heterogeneous application behavior and for connecting CPU-side submission or waiting to AMD hardware activity.

**Target constraints:** current AMD documentation describes uProf for 64-bit x86 applications on Windows, Linux, and FreeBSD, with metrics for AMD Zen processors and AMD Instinct MI accelerators. The feature matrix is important: GUI and CLI coverage differs by OS, and GPU profiling/tracing is documented for Linux rather than Windows/FreeBSD. Check the installed release's system requirements and supported processor/accelerator before promising a metric. Hardware-event and IBS collection may require elevated privileges, kernel support, compatible firmware, or bare-metal access; virtualization can hide or multiplex counters.

**CLI workflow (version-stable shape, version-specific configurations):**

```bash
# Discover the configurations supported by this installed uProf build.
AMDuProfCLI info --list collect-configs

# A CPU sampling collection; config names and options are release-specific.
AMDuProfCLI collect --config overview -o uprof-overview ./app [args]
AMDuProfCLI report -i uprof-overview/<session-directory>
```

For a supported MI GPU workload, select the GPU configuration shown by `info --list collect-configs` and run the same `collect` form. Do not assume a `gpu` configuration or a counter set exists on every uProf release, OS, or accelerator. Use `AMDuProfCLI --help` and the [AMD uProf user guide](https://docs.amd.com/go/en-US/57368-uProf-user-guide) for exact options.

**GUI workflow:** on supported Windows or Linux installations, select CPU **Hotspots**, **Threading**, **Microarchitecture**, **System**, **Power**, or the supported GPU analysis, configure a short interval and sampling/counter set, launch or attach to the target, then inspect hotspots, thread states, system timeline, source correlation, GPU dispatches, and power/thermal trends. Remote profiling can collect on a remote Linux system and translate/view on a Windows host when supported.

**Interpretation:**

- Sampling hotspots show where CPU time is observed; they are statistical and need enough samples before ranking close functions.
- Threading/OS traces reveal runnable, blocked, synchronization, I/O, and scheduling time; use them to explain why a GPU queue is starved or why CPU work misses a frame deadline.
- IBS/PMC metrics are AMD-architecture-specific. Explain cache/TLB/branch or memory findings with the event definition and collection mode, not with a generic counter name.
- MI GPU profiling/tracing can expose HIP/HSA API and GPU activity, kernels, dispatch, and hardware statistics. Validate that the selected process and accelerator are actually included before interpreting an empty GPU view.

**Overhead and limits:** sampling is usually lower overhead than tracing, while OS/runtime tracing, call-stack stitching, IBS, and GPU counters increase cost and result size. Counter availability, call-stack quality, and GPU analysis depend on kernel/driver privileges and application symbols. Run a matching unprofiled baseline, keep sessions on local storage when possible, and do not treat a remote or virtualized session as equivalent to bare metal.

### Intel VTune Profiler

**Use when:** the target uses an Intel CPU, Intel GPU, or supported Intel accelerator path and the question is CPU hotspots/microarchitecture, threading, memory, GPU offload, GPU compute/media hotspots, power, or CPU/GPU interaction. VTune can analyze SYCL, OpenCL, OpenMP offload, DirectX, and other supported application paths; select the analysis type that matches the actual API and hardware.

**Target constraints:** VTune analyses and drivers are OS-, processor-, GPU-, and version-dependent. Current documentation covers Windows/Linux hosts and targets for the main workflows, with additional target support (including FreeBSD) for selected analyses. GPU hardware metrics may require administrator/root privileges, a sampling driver, i915/GPU setup, or an allowed debugfs/perf configuration. A missing driver or permission can produce an incomplete analysis rather than a zero-cost result; read collection diagnostics.

**CLI examples:**

```bash
# CPU user-mode sampling; use hardware sampling only when the platform permits it.
vtune -collect hotspots -result-dir vtune-cpu \
  -knob sampling-mode=sw -- ./app [args]

# Intel GPU compute/media hotspots and GPU/CPU correlation.
vtune -collect gpu-hotspots -result-dir vtune-gpu \
  -knob enable-gpu-runtimes=true -- ./intel-gpu-app [args]

# Produce a text summary; open the same result in vtune-gui for exploration.
vtune -report summary -result-dir vtune-gpu
vtune-gui vtune-gpu
```

Use `vtune -help collect gpu-hotspots` and `vtune -help collect hotspots` for current knobs. Characterization presets can require multiple runs and elevated privileges; source/basic-block or memory-latency modes can have much higher overhead than sampling. For reproducible automation, set a unique `-result-dir`, preserve the command and knobs, and use the same binary/symbols and device power state.

**GUI workflow:** launch VTune GUI, choose the local or remote target, select **Hotspots**, **Microarchitecture Exploration**, **GPU Offload**, **GPU Compute/Media Hotspots**, **Threading**, or **System Overview**, configure the sampling/counter/characterization mode, collect a short interval, and inspect Summary, Timeline, Bottom-up/Top-down, GPU, and source views. Use the GUI to discover an analysis configuration, then export or reproduce it with the CLI when it will run in CI or on a remote host.

**Interpretation:**

- CPU hotspots are sampled execution observations, not a complete trace of every call. Use call stacks and source/assembly correlation to distinguish inclusive from exclusive cost.
- Microarchitecture views relate pipeline, cache, branch, memory, and bandwidth metrics to Intel CPU execution; verify that the metric set applies to the exact CPU generation.
- GPU offload analysis first answers whether host-to-device transfers, synchronization, or a kernel dominate. GPU Compute/Media Hotspots then explores Intel GPU utilization, EU occupancy/stalls, memory bandwidth, engine loading, and kernel source modes.
- GPU metrics such as EU active/stalled, occupancy, memory bandwidth, and GPU cycles describe Intel GPU hardware; they are not interchangeable with NVIDIA SM/warp or AMD CU/wave metrics.

**Overhead and limits:** stack collection, hardware event sampling, GPU characterization, source/basic-block latency, and multiple-run presets alter runtime or require replay. Hardware event multiplexing and missing privileges can reduce precision. Use low-overhead hotspots/system analysis to locate the phase, then one focused GPU analysis. Confirm improvements with an unprofiled run and preserve the result database, symbols, tool version, driver, and analysis knobs.

## Graphics API capture guidance

A graphics API capture is a different artifact from a system timeline or kernel-counter report:

- **Metal debugger:** use Xcode GPU Frame Capture or `MTLCaptureManager` to capture Metal command buffers, then inspect/replay the `.gputrace` in Xcode or `gpudebug`.
- **AGI:** use Frame Profiler and choose **Vulkan** or **OpenGL on ANGLE** exactly as the app uses it. Use System Profiler alongside it to verify that the selected frame is representative on the Android device.
- **Nsight Systems:** trace supported NVIDIA graphics APIs to correlate API submission and GPU workload with CPU/system activity. It is not a complete per-draw resource/pipeline debugger; move a confirmed graphics bottleneck to the platform's dedicated graphics debugger when draw-state inspection is required.
- **NVIDIA Nsight Compute, AMD uProf, and Intel VTune Profiler:** use them for CUDA/OptiX kernels, AMD supported GPU/CPU activity, or Intel GPU/CPU/offload analyses respectively. They do not replace a graphics frame capture when the question is attachment contents, draw ordering, resource binding, or shader debugging.
- **NVIDIA Visual Profiler:** treat its CUDA API/kernel timeline as a legacy compute trace only; it is not a modern cross-API graphics capture tool.

For every frame capture, record API, device, OS/driver, app build, capture scope/count, debug-layer or validation-layer state, and whether replay occurred on the original device. Never compare a captured frame's wall time directly to a production frame without an uninstrumented check.

## Overhead, permissions, and safety

- Sampling, tracing, hardware counters, replay, shader instrumentation, validation layers, and frame capture have different overhead. State which one is enabled; do not call all profilers “low overhead.”
- Counters may be privileged or unavailable under a hypervisor/container. Ask for the least privilege that enables the chosen analysis; record when root/administrator/debugfs/driver permissions were used.
- Never leave Android global GPU-debug settings, Metal capture enablement, debug layers, or elevated profiling services enabled in a release/test device after the experiment. Clean up settings and terminate sessions.
- Traces can contain source paths, symbol names, shader source/binaries, textures, frame contents, process arguments, device identifiers, and application data. Store them securely and redact before sharing.
- A profiler result is an observation under a collection configuration. Distinguish “the queue was idle while the CPU waited” from “this function caused the wait”; establish causality by changing the suspected work and checking the resulting unprofiled metric.
- When reporting a result, include the exact command or GUI settings, target and API, tool/driver versions, permissions, warm-up policy, capture interval, metric set, number of trials, and the baseline/profiling overhead.
