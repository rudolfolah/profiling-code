# Python Profiling Skill

Use this skill when investigating CPU time, wall-clock latency, Python allocations, process memory, object growth, or interpreter-level events in the examples under `python/`. The repository compares multiple profilers around `python/program.py`; choose the narrowest tool that can answer the question instead of running every profiler by default.

## Repository setup and baseline

The examples target the Python version in `python/.python-version` and use the virtual environment described in `python/README.md`:

```bash
cd python
pyenv install "$(cat .python-version)"  # only if that version is not installed
pyenv local
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run an unprofiled baseline before changing code:

```bash
python program.py
time python program.py
```

`program.py` fetches a Wikipedia page over HTTPS before parsing it. Network, DNS, TLS, server, and response-size variance can dominate timings. For repeatable comparisons, replace the network response with a checked-in/local fixture or otherwise keep the input and environment fixed; never treat one network run as a reliable regression measurement.

The repository's comparison runner is:

```bash
./timing.sh
```

It invokes cProfile, tracemalloc, Memray, pyinstrument, yappi, Filprofiler, psutil, and guppy3. Profiling changes both runtime and memory behavior, so compare profiles only under the same Python build, dependency versions, input, warm-up state, and command-line options.

## Choose by question

| Question | First tool | Why | Important limitation |
|---|---|---|---|
| Which Python functions consume CPU or cumulative time? | `cProfile` | Deterministic call counts and cumulative/tottime stats | Instrumentation overhead; timing is distorted for very short calls and I/O |
| Did a stable Python benchmark regress across builds? | pyperformance | Repeated benchmark distributions and comparisons | Benchmark suite; it does not identify the responsible call path and is not pinned in this repository |
| Where is wall time spent with low instrumentation overhead? | `pyinstrument` or `py-spy` | Sampling preserves a useful high-level call tree | Sampling can miss short functions; native frames need suitable support |
| How do threads or CPU/wall clocks differ? | `yappi` | Function and thread statistics with selectable clocks | More overhead and more setup than a simple sampler |
| Which Python source lines allocate memory? | `tracemalloc` | Snapshot-to-snapshot Python allocation diffs | Does not account for all native allocations |
| What native/Python allocations build the peak? | Memray | Allocation traces and flame graphs, including native extensions | Requires a binary artifact and can be expensive |
| How much RSS/CPU does the process consume? | `psutil` | Process-level counters before and after work | Counters do not explain the allocating line |
| Which live objects/types dominate the heap? | `guppy3` | Heap partitions and object counts | Object inspection overhead; not a native allocation tracer |
| Where does peak memory occur over time? | Filprofiler | Peak-memory timeline/flamegraph workflow | Platform/runtime support and output handling vary |
| Which interpreter events/lines execute? | DTrace | Entry/return/line probes at the interpreter boundary | Very high overhead; requires a DTrace-enabled Python build |

For detailed commands, use the focused skills `python-cpu-profiling`, `python-memory-profiling`, and `python-dtrace-profiling` in `.claude/skills/`.

## Reproducible profiling workflow

1. Define the observable: elapsed time, CPU time, peak RSS, Python allocation delta, native allocation, object count, or call sequence.
2. Record the baseline command, Python version, dependency lock/requirements, input, host, and profiler options.
3. Run the smallest profiler that measures that observable. Keep output separate from source and name artifacts with the run/configuration.
4. Inspect the profiler's own output format rather than inferring from process RSS alone. Distinguish inclusive/cumulative time from self/tottime and live memory from total allocated memory.
5. Repeat enough times to see variance. For network-bound examples, use a local fixture before comparing code changes.
6. Verify a proposed optimization with the same unprofiled command and at least one profile that explains the change. A faster profile can merely reflect a different input or warmed cache.
7. Remove generated artifacts or keep them in the existing ignored patterns (`*.out`, `memray-*.html`, and `memray-*.bin` under `python/`). Do not commit credentials, response bodies, or production memory dumps.

## Common interpretation traps

- CPU profilers report execution attribution, not automatically user-visible latency. Blocking network, disk, subprocess, and scheduler time may need wall-clock sampling or explicit timing marks.
- `cProfile` cumulative time includes descendants; `tottime` is time in the function body. Sort by both when deciding whether a caller or leaf is the useful target.
- A `tracemalloc` diff measures Python allocator traces between snapshots. It is not equivalent to RSS, and a negative diff means traced allocations were released, not that the process returned all pages to the OS.
- Memray, Filprofiler, and `psutil` answer different memory questions: allocation provenance, peak behavior, and process counters respectively. Correlate them instead of substituting one for another.
- Sampling output is statistical. Increase duration or repeat workload before concluding that a small frame is absent or faster.
- Profiling a script that performs a live HTTP request measures the remote service and transport as well as local parsing. Keep those costs explicit in reports.

## Safety and operational boundaries

Run profilers against a representative but bounded workload first. Avoid attaching `py-spy`, DTrace, or similar tools to a process without authorization; they may require elevated permissions and can expose arguments, paths, or application data. Use `sudo` only for the DTrace command that needs it, never for the application itself. Do not run heap/object inspection on sensitive production processes unless the data-handling and retention policy permits it.
