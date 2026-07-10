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

## gprof (GNU Profiler)

**When to use:** a simple CPU flat profile and estimated call graph for a native executable when rebuilding with compiler instrumentation is acceptable. It is useful for batch programs and a quick first pass, not for low-perturbation production measurements, precise wall-clock latency, or modern asynchronous/thread-heavy workloads.

**Build and capture:**

```bash
# Compile and link every relevant object with -pg (not only the final link).
cc -O2 -g -pg -o app main.c other.c
./app < fixed-input > /dev/null
# The process normally writes gmon.out on normal exit in its working directory.
gprof -b ./app gmon.out > gprof.txt
# Optional focused reports:
gprof -p ./app gmon.out       # flat profile
gprof -q ./app gmon.out      # call-graph profile
```

For a multi-file build, apply `-pg` consistently to compilation and linking, and place each run's `gmon.out` in a separate directory. A crash, `_exit`, or forced termination may prevent the profile from being written. If the executable forks, consult the platform's gprof documentation for how child output is handled rather than assuming one complete file.

**Read the output:** the flat profile reports sampled time and the number of calls attributed to functions; the call-graph section reports callers, callees, and propagated time. Timer samples estimate time, while call counts/edges come from `mcount`-style instrumentation. “Self” time is work in that function; propagated/children time includes descendants. A high call count with little self time may still matter through allocation, locking, or cache effects. Missing symbols or aggressive inlining can collapse work into a parent or show `??`; verify the binary and debug information before acting.

**Costs and limitations:** `-pg` changes every instrumented call and can materially alter short functions, recursion, synchronization, and cache layout. Timer resolution is platform-dependent; percentages are statistical. gprof's call graph is a poor fit for threads, signals, JIT code, and event-loop latency, and support depends on the GNU binutils build. It is primarily a Unix-like native tool; it is not a native Windows workflow. Prefer perf or Instruments for low-overhead sampling and Tracy or targeted tracing for event timing.

Official documentation: [GNU gprof](https://sourceware.org/binutils/docs/gprof/).

## Linux perf

**When to use:** low-overhead CPU sampling, hardware/software performance counters, kernel/user attribution, scheduling, and call stacks on Linux. It is the default first choice when the question is “where does CPU time or a hardware resource go?”

**Prerequisites:** install the distribution's `perf` package (often part of `linux-tools`), use a kernel and CPU with the desired events, and ensure the current user is allowed to access performance counters. A restrictive `perf_event_paranoid` setting, container permissions, missing `CAP_PERFMON`, or kernel lockdown can block collection; ask an administrator rather than weakening system policy casually. Build with `-g`, and prefer `-fno-omit-frame-pointer` or DWARF unwinding for reliable stacks. Kernel symbols and debuginfo are needed for meaningful kernel attribution.

**Minimal commands:**

```bash
# Counters: elapsed time, cycles, instructions, branches, and cache events when supported.
perf stat -d -- ./app < fixed-input > /dev/null

# Sample user and kernel stacks. DWARF is more tolerant of omitted frame pointers but costs more.
perf record -g --call-graph dwarf -o perf.data -- ./app < fixed-input > /dev/null
perf report --stdio -i perf.data
perf annotate --stdio -i perf.data

# Lower-overhead frame-pointer collection when the binary was built accordingly.
perf record -g --call-graph fp -o perf-fp.data -- ./app < fixed-input > /dev/null
```

Use `perf list` to discover events on the current machine; event names and availability vary by CPU. Narrow a question with `-e cycles:u`, `-e instructions:u`, or a supported cache event instead of assuming generic event names. For a long-running process, attach with `perf record -p PID -g -- sleep 30`, stopping the command with the normal signal. Save the command line and `perf report` settings with the data.

**Read the output:** `perf stat` reports aggregate counts and derived rates such as instructions per cycle (IPC); compare counters to a same-machine baseline because frequency scaling and event multiplexing affect results. In `perf report`, percentages are usually the fraction of collected samples; “Children” includes descendants and “Self” is attributed to the displayed frame. A hot `libc`, allocator, lock, kernel, or scheduler frame may be a symptom of caller behavior. `perf annotate` combines samples with instructions, but source lines require matching DWARF and inline information. A low sample count, `[unknown]`, or truncated call chain is a collection-quality problem, not proof that the code is cold.

**Costs and limitations:** normal sampling is low overhead but statistical and can miss short bursts. Hardware counter multiplexing, interrupt skid, CPU frequency changes, migrations, and scheduler noise make tiny differences unreliable. DWARF unwinding increases overhead; frame pointers are cheaper but require compatible builds. perf is Linux-specific (including its kernel and permissions model); do not present it as a portable macOS or Windows command. Use `perf stat` and `record` on a quiescent host when possible, and avoid changing system-wide counter policy on shared machines.

Official documentation: [Linux perf documentation](https://perf.wiki.kernel.org/index.php/Main_Page) and the [kernel perf subsystem documentation](https://www.kernel.org/doc/html/latest/tools/perf/index.html).

## Tracy

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

## Valgrind

Valgrind runs a native program through dynamic binary translation. Its tools are excellent for correctness and attribution but normally impose large slowdowns and memory expansion. Build with `-g`, keep optimizations representative when possible, and use a deterministic, reduced workload. Do not use Valgrind timing as production timing. Check the installed Valgrind release's supported OS/architecture before relying on it: Linux support is generally strongest, while macOS and especially newer ARM64 combinations can lag or be unavailable. It is not a native Windows workflow.

Common setup:

```bash
cc -O1 -g -fno-omit-frame-pointer -o app main.c
# Keep each output file separate when running concurrently.
mkdir -p profile-out
```

Use `--num-callers=30` when deeper ownership matters, but expect more overhead and larger output. Suppressions should be narrowly reviewed and version-controlled with the test setup; never suppress an error merely to make a report clean.

### Memcheck: invalid memory and leaks

**Capture:**

```bash
valgrind --tool=memcheck \
  --leak-check=full --show-leak-kinds=all --track-origins=yes \
  --num-callers=30 --log-file=profile-out/memcheck.%p.log \
  ./app < fixed-input > /dev/null
```

**Interpretation:** fix the first invalid read/write, use-after-free, uninitialized-value report, or invalid free first; later failures may be cascades. `definitely lost` means no remaining pointer can reach the allocation, while `indirectly lost` is reachable only through a definitely lost block. `still reachable` is not automatically a leak (many runtimes retain caches at exit). Stack traces need matching symbols and enough callers. `--track-origins=yes` improves uninitialized-value diagnosis at additional cost.

Memcheck instruments loads, stores, and allocator behavior, so reports are detailed but execution can be roughly an order of magnitude slower or more. It cannot prove absence of races, find every leak in code it cannot observe, or faithfully reproduce timing-sensitive behavior. Use a focused test and compare an uninstrumented run for behavior.

### Cachegrind: simulated cache and branch behavior

**Capture and inspect:**

```bash
valgrind --tool=cachegrind --cachegrind-out-file=profile-out/cachegrind.%p.out \
  ./app < fixed-input > /dev/null
cg_annotate --auto=yes profile-out/cachegrind.*.out
```

Cachegrind reports instruction/data references and simulated cache misses by function and source line. Compare inclusive versus self costs and focus on changes in misses or references for the same binary and input. Its cache model is a simulation based on configured/default parameters, not a replacement for the target CPU's hardware counters; use `perf stat` to validate real cache behavior. Dynamic translation and cache simulation are high overhead, and the altered code layout/schedule can change locality.

### Callgrind: instrumented call graph

**Capture and inspect:**

```bash
valgrind --tool=callgrind --callgrind-out-file=profile-out/callgrind.%p.out \
  ./app < fixed-input > /dev/null
callgrind_annotate --inclusive=yes profile-out/callgrind.*.out
```

Open the output in `kcachegrind` or `qcachegrind` when available for an interactive caller/callee graph. Callgrind provides deterministic event counts for the translated execution (and can collect cache-like events), not wall-clock latency. Read self versus inclusive cost, callers, callees, and cycles in the specific scenario. Use callgrind's runtime controls or a smaller workload when only one phase matters. Its instrumentation can be dramatically slower than the target and is unsuitable for latency-sensitive conclusions.

### Massif: heap growth over time

**Capture and inspect:**

```bash
valgrind --tool=massif --time-unit=ms --detailed-freq=1 \
  --massif-out-file=profile-out/massif.%p.out \
  ./app < fixed-input > /dev/null
ms_print profile-out/massif.*.out
```

Massif's graph shows heap size over its sampled timeline; snapshots and allocation stacks explain which paths own peaks. `--stacks=yes` includes thread stacks when stack growth is relevant, at additional cost. Distinguish live heap from allocator overhead and retained caches, and correlate a peak with the application phase rather than assuming the final snapshot represents the maximum. Massif is a heap profiler, not a leak proof: use Memcheck for reachability and invalid accesses. Sampling snapshots reduces output but can miss a short-lived spike; increase detail only for a focused run.

Official documentation: [Valgrind tool overview](https://valgrind.org/info/tools.html), [Memcheck manual](https://valgrind.org/docs/manual/mc-manual.html), [Cachegrind manual](https://valgrind.org/docs/manual/cg-manual.html), [Callgrind manual](https://valgrind.org/docs/manual/cl-manual.html), and [Massif manual](https://valgrind.org/docs/manual/ms-manual.html).

## Apple Instruments

**When to use:** macOS and Apple-platform applications when you need a polished timeline for CPU, allocations, leaks, scheduling, I/O, energy, or framework activity. Instruments templates differ in collection mode, so confirm whether a result is sampled or event/instrumentation based.

**Prerequisites and GUI entry point:** install Xcode or the matching Command Line Tools and launch **Xcode > Open Developer Tool > Instruments** (or run `open -a Instruments`). For a macOS executable, choose a template such as **Time Profiler**, **Allocations**, **Leaks**, or **System Trace**, select the target process, and click **Record**. For iOS/iPadOS/watchOS/tvOS targets, select a provisioned device/simulator and a signed app; device permissions, entitlements, and OS/Xcode compatibility can prevent attaching. Build with DWARF debug information and preserve the matching `.dSYM` bundle; use an optimized, release-like configuration for realistic behavior.

**Repeatable CLI entry point:** modern Xcode installations provide `xcrun xctrace`; template names vary by Xcode release, so list the available templates first and use the exact displayed name:

```bash
xcrun xctrace list templates
xcrun xctrace record --template 'Time Profiler' \
  --output profile-out/time-profiler.trace --launch -- ./app < fixed-input > /dev/null
```

Open the resulting `.trace` in Instruments for call-tree, timeline, and statistics views. For an already running, permitted process use the GUI's target/attach flow; do not assume every template supports every launch mode. Keep `xctrace` and Xcode versions with the capture because the schema and template names can change.

**Read the output:** Time Profiler samples stacks, so the heaviest call tree is a statistical estimate; inspect self versus total time and expand system/framework frames back to the first actionable application caller. Allocations shows allocation/deallocation histories and growth; Leaks reports objects it cannot reach at its scan point, not every lifetime bug. System Trace correlates threads, scheduling, waits, and wakeups. Use signposts/points of interest to mark phases, then compare the same interval after a change. A missing source name or `???` generally means the matching dSYM is unavailable or has a UUID mismatch; restore the exact symbols before interpreting.

**Costs and limitations:** Time Profiler is usually low overhead sampling but can miss brief work and is affected by stack unwinding. Allocations, Leaks, signposts, and other event instruments add runtime and memory overhead; simulator results do not represent device CPU, GPU, thermal, or I/O behavior. Instruments is an Apple-platform tool and requires compatible macOS/Xcode tooling; use Linux perf or Valgrind on Linux rather than attempting to port the command. Code signing, hardened runtime, sandboxing, and privacy permissions may restrict attach or system-wide collection.

**Artifact safety:** `.trace` packages and dSYMs can contain source paths, binary UUIDs, symbol names, strings, process arguments, and app/runtime data. Store them in access-controlled locations, avoid recording secrets, and review before sharing. Keep symbols separate from release bundles where possible; stripping a shipped binary does not make a captured trace safe to publish.

Official documentation: [Apple Instruments User Guide](https://help.apple.com/instruments/mac/current/) and [`xctrace` documentation](https://developer.apple.com/documentation/xcode/recording-performance-data).

## Choosing a tool quickly

| Question | First tool | Why | Main caveat |
|---|---|---|---|
| Which native functions consume CPU on Linux? | `perf record`/`perf report` | Low-overhead system and user sampling | Statistical stacks and permissions |
| Which simple batch functions are hot after a rebuild? | `gprof` | Minimal flat/call-graph report | `-pg` perturbs execution; weak for threads |
| Which frame/lock/worker span causes a hitch? | Tracy | Timeline and explicit zones | Instrumentation overhead and integration |
| Which access is invalid or which allocation is unreachable? | Valgrind Memcheck | Detailed memory diagnostics | Very high slowdown; timing changes |
| Which paths generate simulated cache misses? | Cachegrind/Callgrind | Per-function and per-line event attribution | Simulated counters, not target hardware |
| Where does heap usage peak? | Massif | Heap timeline and ownership stacks | Not a leak proof; snapshot sampling |
| Which Apple-platform template shows CPU, allocations, or scheduling? | Instruments | Integrated Apple timeline and symbolication | macOS/Xcode/device restrictions |

## Safe, reproducible artifact handling

- Keep captures, logs, `perf.data`, `gmon.out`, Valgrind outputs, `.tracy` files, `.trace` packages, executables, and symbols outside the source tree unless the project explicitly tracks them. They can be large and may include command-line arguments, source paths, symbol names, zone/log strings, addresses, and application data.
- Treat debug information and dSYM/DWARF files as sensitive build artifacts. Archive them with the exact binary UUID/build ID under access control; do not ship them merely because a profile needs them.
- Do not profile untrusted inputs with a privileged profiler or loosen kernel/security settings on a shared host. Use a disposable environment for hostile data and stop collection before sharing a remote port or trace.
- Record profiler options, workload revision, machine identity, and tool versions next to a private capture. Keep raw data immutable; derive text reports separately so another engineer can reproduce the interpretation.
- Delete or securely expire captures after the retention period. Before sharing, inspect logs and reports for secrets, customer data, absolute paths, addresses, and embedded source or allocation contents; symbol stripping alone does not scrub a capture.
