# Apple Instruments

**When to use:** macOS and Apple-platform applications when you need a polished timeline for CPU, allocations, leaks, scheduling, I/O, energy, or framework activity. Instruments templates differ in collection mode, so confirm whether a result is sampled or event/instrumentation based.

**Prerequisites and GUI entry point:** Instruments and `xctrace` require a full Xcode installation; the standalone Command Line Tools can provide Clang and other utilities without either profiler. Check the active developer directory and the CLI before prescribing a capture:

```bash
xcode-select -p
xcrun --find xctrace
```

If the selected directory is `/Library/Developer/CommandLineTools` or `xcrun` cannot find `xctrace`, do not keep retrying the recording command. Install/select a compatible full Xcode, then launch **Xcode > Open Developer Tool > Instruments** (or run `open -a Instruments`). Change the active developer directory with `xcode-select` only when that Xcode is already installed and the user is authorized to alter the machine's developer-tool configuration. For a macOS executable, choose a template such as **Time Profiler**, **Allocations**, **Leaks**, or **System Trace**, select the target process, and click **Record**. For iOS/iPadOS/watchOS/tvOS targets, select a provisioned device/simulator and a signed app; device permissions, entitlements, and OS/Xcode compatibility can prevent attaching. Build with DWARF debug information and preserve the matching `.dSYM` bundle; use an optimized, release-like configuration for realistic behavior.

**Repeatable CLI entry point:** modern Xcode installations provide `xcrun xctrace`; template names vary by Xcode release, so list the available templates first and use the exact displayed name:

```bash
xcrun xctrace list templates
xcrun xctrace record --template 'Time Profiler' \
  --output profile-out/time-profiler.trace --launch -- ./app < fixed-input > /dev/null
```

Open the resulting `.trace` in Instruments for call-tree, timeline, and statistics views. For an already running, permitted process use the GUI's target/attach flow; do not assume every template supports every launch mode. Keep `xctrace` and Xcode versions with the capture because the schema and template names can change.

**Command Line Tools fallback for a CPU-stack smoke test:** macOS also ships `/usr/bin/sample`, which can sample an already-running process even when full Xcode and `xctrace` are unavailable. It produces a text call graph rather than an Instruments timeline, so use it only to confirm stack symbolication or identify a coarse CPU hot path:

```bash
./app < fixed-input > /dev/null &
app_pid=$!
/usr/bin/sample "$app_pid" 5 1 -file /tmp/app.sample.txt
wait "$app_pid"
```

The target must remain alive for the requested duration; shorten the duration for a brief workload or make the workload repeat deterministically. Inspect the report's **Call graph**, source lines, and **Sort by top of stack** section. Missing application symbols indicate a build/symbolication problem. `sample` is statistical, may require permission to inspect the target, and does not replace Instruments templates for allocations, leaks, scheduling, I/O, energy, or framework events. Treat its report as sensitive and remove it from `/tmp` when finished.

**Read the output:** Time Profiler samples stacks, so the heaviest call tree is a statistical estimate; inspect self versus total time and expand system/framework frames back to the first actionable application caller. Allocations shows allocation/deallocation histories and growth; Leaks reports objects it cannot reach at its scan point, not every lifetime bug. System Trace correlates threads, scheduling, waits, and wakeups. Use signposts/points of interest to mark phases, then compare the same interval after a change. A missing source name or `???` generally means the matching dSYM is unavailable or has a UUID mismatch; restore the exact symbols before interpreting.

**Costs and limitations:** Time Profiler is usually low overhead sampling but can miss brief work and is affected by stack unwinding. Allocations, Leaks, signposts, and other event instruments add runtime and memory overhead; simulator results do not represent device CPU, GPU, thermal, or I/O behavior. Instruments is an Apple-platform tool and requires compatible macOS/Xcode tooling; use Linux perf or Valgrind on Linux rather than attempting to port the command. Code signing, hardened runtime, sandboxing, and privacy permissions may restrict attach or system-wide collection.

**Artifact safety:** `.trace` packages and dSYMs can contain source paths, binary UUIDs, symbol names, strings, process arguments, and app/runtime data. Store them in access-controlled locations, avoid recording secrets, and review before sharing. Keep symbols separate from release bundles where possible; stripping a shipped binary does not make a captured trace safe to publish.

Official documentation: [Apple Instruments User Guide](https://help.apple.com/instruments/mac/current/) and [`xctrace` documentation](https://developer.apple.com/documentation/xcode/recording-performance-data).
