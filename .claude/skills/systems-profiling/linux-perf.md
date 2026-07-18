# Linux perf

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
