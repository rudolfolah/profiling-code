# Systems Performance Profiling Skill

Use this skill to investigate CPU time, call paths, cache behavior, memory errors, heap growth, and frame or scheduling latency in native programs. It covers the systems tools listed in this repository's root README: **gprof**, **Linux perf**, **Tracy**, **Valgrind Memcheck/Cachegrind/Callgrind/Massif**, and **Apple Instruments**.

## Start with a reproducible baseline

1. Define one question and one workload: for example, “which call path consumes CPU during level loading?” or “which allocation remains live after ten requests?” Do not mix startup, warm-up, and steady-state measurements.
2. Build a profiling binary with symbols and a known build identity. For GCC/Clang, a useful baseline is `-g -O2`; keep frame pointers (`-fno-omit-frame-pointer`) when stack quality matters and disable or account for LTO/inlining when symbol attribution is more important than production fidelity. Use the same optimization mode as the target when validating a fix.
3. Warm up once, then capture several identical runs. Record OS/kernel, CPU, compiler and linker versions, flags, input data, tool version, and whether the run was under a debugger, VM, container, or emulator.
4. Prefer a release-like build with debug information over an unoptimized debug build. Optimization changes inlining, code layout, locking, and cache behavior; an unoptimized binary can answer “where is work?” but not reliably “what will production do?”
5. Keep the exact executable, shared libraries, dSYM/DWARF files, and source revision that produced a capture. A profile without matching symbols can still show addresses, but function names, source lines, and inline frames may be wrong or missing.

A profile is evidence, not a diagnosis. First compare total runtime, CPU utilization, allocations, cache misses, or frame time with an unprofiled baseline. Then inspect the hottest or most rapidly growing paths, change one thing, and repeat the same workload.

## Sampling versus instrumentation

- **Sampling** periodically interrupts or observes a running process (Linux perf's normal `record`, Time Profiler, and gprof's timer component). It usually has lower overhead and better timing fidelity, but it can miss very short functions, under-sample blocked threads, and depends on usable unwind information. A percentage is an estimate over samples, not an exact count of calls.
- **Instrumentation/tracing** inserts hooks or observes individual events (gprof's `-pg` call hooks, Tracy zones, Valgrind's dynamic translation, and Instruments Allocations/Leaks templates). It exposes call counts, lifetimes, and event order, but can add substantial CPU, memory, synchronization, and I/O overhead. Use it for causality and memory correctness, not absolute latency comparisons.
- **Hybrid tools** should be read as such: gprof uses instrumented call edges and timer samples; Instruments has sampled and event-based templates; perf can also collect tracepoints or hardware events in addition to sampling. State which mode produced a result.

When comparing runs, compare like with like. Do not rank a 30x-slower Valgrind run against an unprofiled run as if the slowdown were application behavior. Use relative hot-path or allocation changes within the same tool and configuration, and validate promising changes without the profiler.

## Additional resources

Reference the supporting file that matches the target platform and question so Claude knows when to load detailed workflows:

- [gprof.md](gprof.md): GNU gprof instrumentation and flat/call-graph reports.
- [linux-perf.md](linux-perf.md): Linux perf sampling, hardware counters, and call stacks.
- [tracy.md](tracy.md): Tracy timeline instrumentation for zones, locks, frames, and allocations.
- [valgrind.md](valgrind.md): Valgrind Memcheck, Cachegrind, Callgrind, and Massif.
- [apple-instruments.md](apple-instruments.md): Apple Instruments, `xctrace`, and `sample` workflows.

## Choosing a tool quickly

| Question | First tool | Why | Main caveat |
|---|---|---|---|
| Which native functions consume CPU on Linux? | [`perf record`/`perf report`](linux-perf.md) | Low-overhead system and user sampling | Statistical stacks and permissions |
| Which simple batch functions are hot after a rebuild? | [`gprof`](gprof.md) | Minimal flat/call-graph report | `-pg` perturbs execution; weak for threads |
| Which frame/lock/worker span causes a hitch? | [Tracy](tracy.md) | Timeline and explicit zones | Instrumentation overhead and integration |
| Which access is invalid or which allocation is unreachable? | [Valgrind Memcheck](valgrind.md) | Detailed memory diagnostics | Very high slowdown; timing changes |
| Which paths generate simulated cache misses? | [Cachegrind/Callgrind](valgrind.md) | Per-function and per-line event attribution | Simulated counters, not target hardware |
| Where does heap usage peak? | [Massif](valgrind.md) | Heap timeline and ownership stacks | Not a leak proof; snapshot sampling |
| Which Apple-platform template shows CPU, allocations, or scheduling? | [Instruments](apple-instruments.md) | Integrated Apple timeline and symbolication | macOS/Xcode/device restrictions |

## Safe, reproducible artifact handling

- Keep captures, logs, `perf.data`, `gmon.out`, Valgrind outputs, `.tracy` files, `.trace` packages, executables, and symbols outside the source tree unless the project explicitly tracks them. They can be large and may include command-line arguments, source paths, symbol names, zone/log strings, addresses, and application data.
- Treat debug information and dSYM/DWARF files as sensitive build artifacts. Archive them with the exact binary UUID/build ID under access control; do not ship them merely because a profile needs them.
- Do not profile untrusted inputs with a privileged profiler or loosen kernel/security settings on a shared host. Use a disposable environment for hostile data and stop collection before sharing a remote port or trace.
- Record profiler options, workload revision, machine identity, and tool versions next to a private capture. Keep raw data immutable; derive text reports separately so another engineer can reproduce the interpretation.
- Delete or securely expire captures after the retention period. Before sharing, inspect logs and reports for secrets, customer data, absolute paths, addresses, and embedded source or allocation contents; symbol stripping alone does not scrub a capture.
