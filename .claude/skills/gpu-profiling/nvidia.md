# NVIDIA GPU profiling

## NVIDIA Visual Profiler (legacy CUDA workflow)

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

## NVIDIA Nsight Systems

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

## NVIDIA Nsight Compute

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
