# Intel GPU and CPU/GPU profiling

## Intel VTune Profiler

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
