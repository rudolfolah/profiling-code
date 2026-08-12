# AMD GPU and CPU/GPU profiling

## AMD uProf

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
