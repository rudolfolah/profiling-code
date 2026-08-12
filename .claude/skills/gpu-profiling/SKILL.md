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

## Additional resources

Reference the supporting file that matches the target hardware, API, and question so Claude knows when to load detailed workflows:

- [nvidia.md](nvidia.md): NVIDIA Visual Profiler legacy CUDA workflow, Nsight Systems timelines, and Nsight Compute kernel analysis.
- [android.md](android.md): Android GPU Inspector system and frame profiling for Android Vulkan/OpenGL ES workloads.
- [metal.md](metal.md): Xcode Metal debugger capture/replay and `gpudebug` inspection for Metal workloads.
- [amd.md](amd.md): AMD uProf CPU, threading, power, and supported AMD accelerator profiling.
- [intel.md](intel.md): Intel VTune CPU hotspots, threading, microarchitecture, GPU offload, and GPU compute/media analysis.

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
