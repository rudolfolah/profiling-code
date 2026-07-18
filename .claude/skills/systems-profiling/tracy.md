# Tracy

**When to use:** interactive, timeline-oriented tracing of frame boundaries, zones, locks, messages, allocations, and selected plots in a native or game process. Tracy is especially useful when a sampled profile cannot explain frame hitches, synchronization, or the ordering of work across threads.

**Prerequisites and instrumentation:** integrate the Tracy client using the project's supported package/submodule or the official repository, compile the client and application with Tracy enabled (commonly `TRACY_ENABLE`), and add scoped zones around meaningful work. Exact source and linker settings depend on the language/build system; follow the integration section of the official repository rather than copying a platform-specific make rule. Typical C++ instrumentation looks like:

```cpp
#include <tracy/Tracy.hpp>

void update_world() {
    ZoneScopedN("update_world");
    // Work being measured.
}

void render_frame() {
    ZoneScopedN("render_frame");
    FrameMark;
}
```

Build a profiling configuration that retains symbols and ensure the client and profiler agree on the Tracy protocol/version. Start the Tracy Profiler GUI (the executable is commonly named `tracy-profiler` in packaged/build outputs), run the instrumented program, and connect to it from the GUI. Select the timeline, frame, zone, lock, memory, and plot views to inspect the interval of interest. For a remote target, configure the documented connection/address and firewall rules explicitly; do not expose a profiling listener to an untrusted network.

**Read the output:** use frame time and the frame-distribution view to identify missed deadlines, then expand zones on the affected thread and correlate them with worker threads, waits, locks, messages, and context switches. A long parent zone may mostly be child work; inspect both inclusive and self portions. Look for serialized spans, producer/consumer gaps, and repeated allocations rather than treating the visually largest zone as automatically causal. Capture a stable interval after warm-up and compare the same frame or scenario across builds.

**Costs and limitations:** Tracy is event instrumentation/tracing, so every zone, message, allocation, and callstack capture adds overhead and memory. Dense tiny zones, callstack collection, and remote streaming can perturb scheduling and frame pacing. Start with coarse zones, enable detailed capture only for a short interval, and validate changes with instrumentation disabled. Tracy requires client integration and a compatible GUI; it is not a drop-in system-wide sampler. Language support beyond C/C++ uses the repository's maintained bindings and may have different feature/overhead limits. Platform support follows the current Tracy client and profiler builds; check the official repository for the target OS/architecture.

**Capture safety:** Tracy captures can include zone names, log strings, source paths, thread names, allocation metadata, and values intentionally sent as messages. Keep captures private, avoid logging secrets, and do not upload a `.tracy` capture or symbols to a public issue without review. Prefer a localhost-only or otherwise access-controlled connection for development.

Official documentation and source: [Tracy Profiler](https://github.com/wolfpld/tracy).
