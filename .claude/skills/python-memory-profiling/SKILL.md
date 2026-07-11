# Python memory profiling

Use this skill when Claude needs to explain, reproduce, or investigate memory growth in this repository's Python example. The target is `python/program.py`, a CPython 3.11.5 program that downloads a Wikipedia page, writes a temporary copy, parses it with BeautifulSoup, and counts words. Its network response and import/cache state can vary, so compare runs made with the same interpreter, dependencies, input/network conditions, and workload.

## Prepare a reproducible run

The repository pins Python 3.11.5 in `python/.python-version` and the profiling dependencies in `python/requirements.txt` (`guppy3==3.1.4.post1`, `memray==1.11.0`, `psutil==5.9.8`, and `filprofiler==2023.3.1`). The README setup is:

```bash
cd python
pyenv install "$(cat .python-version)"
pyenv local
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run from `python/`, not the repository root: the runner scripts import `program` as a local module. The program performs a live HTTP request, so a failed request is an input/environment failure rather than a profiler result. Do not treat one run's absolute byte counts as a benchmark; repeat the same command when comparing a change.

Before changing a profiler runner, inspect the existing scripts. They intentionally print a simple before/after view:

- `python/run_tracemalloc.py`: starts `tracemalloc`, snapshots before/after `main()`, and prints `snapshot2.compare_to(snapshot1, "lineno")`.
- `python/run_guppy3.py`: prints `hpy().heap()` before and after `main()`.
- `python/run_psutil.py`: prints `psutil.Process().memory_info()` before and after `main()`.

The runner imports `program` before starting tracemalloc. If import-time allocations matter, start tracing before imports with the interpreter option (the program itself still remains unchanged):

```bash
cd python
python -X tracemalloc=25 run_tracemalloc.py
# Equivalent environment form:
PYTHONTRACEMALLOC=25 python run_tracemalloc.py
```

## First decide what “memory” means

| Question | Tool and repository command | Artifact/view | Main limitation |
|---|---|---|---|
| Which Python source lines retain or allocate traced Python blocks between two points? | `python run_tracemalloc.py` | Text top-10 diff; optional serialized snapshots | Does not see native allocations that bypass Python's traced allocators; not RSS |
| Which Python/native call stacks account for allocations and peak/live memory? | `memray run program.py`; then `memray flamegraph ...` | Memray binary plus HTML flame graph/table | Higher runtime/storage overhead; native symbol reports are machine-specific |
| Which Python objects and types exist, and how large are they now? | `python run_guppy3.py` | Heapy object census on stdout | No allocation history or source-line attribution; Python objects only |
| How much memory does the OS report for this process? | `python run_psutil.py` | `memory_info()` text (RSS/VMS and platform fields) | No allocation stack or object ownership; RSS includes shared/native/interpreter memory |
| What call stacks account for memory at the high-water mark, including native extensions? | `fil-profile --no-browser run program.py` | Interactive SVG report in `fil-result/` | Offline profiler with substantial overhead; not a production or multiprocessing profiler |

Do not add numbers from these tools together. A `tracemalloc` size, a Memray allocation, a Heapy object size, and RSS measure different populations and points in time. Use a process-level tool (psutil or Fil) to establish impact, then an allocation/object tool to explain it.

## `tracemalloc`: Python allocation snapshots and diffs

Use the standard-library `tracemalloc` when a suspected growth is in Python-managed objects and source-line attribution is useful. The repository's exact baseline command is:

```bash
cd python
python run_tracemalloc.py
```

The existing runner does this around `main()`:

```python
import tracemalloc
from program import main

tracemalloc.start()
before = tracemalloc.take_snapshot()
main()
after = tracemalloc.take_snapshot()
for stat in after.compare_to(before, "lineno")[:10]:
    print(stat)
```

Interpret output as `size=... (+/-...), count=... (+/-...), average=...`. Positive entries are more traced blocks/bytes in the second snapshot; negative entries indicate blocks freed between snapshots. The `"lineno"` key groups by filename and line. For call-chain attribution, start with more frames and group by traceback:

```python
tracemalloc.start(25)
# ... code under test ...
snapshot = tracemalloc.take_snapshot()
for stat in snapshot.statistics("traceback")[:10]:
    print(stat)
    for frame in stat.traceback.format():
        print("  ", frame)
```

Avoid blaming import overhead or profiler bookkeeping. Start the snapshot immediately before the operation being compared, and optionally collect first if the question is about retained objects rather than transient garbage:

```python
import gc

gc.collect()
before = tracemalloc.take_snapshot()
main()
gc.collect()
after = tracemalloc.take_snapshot()
```

Filter third-party noise before ranking application lines:

```python
only_program = snapshot.filter_traces(
    (tracemalloc.Filter(True, "*program.py"),)
)
for stat in only_program.statistics("lineno")[:10]:
    print(stat)
```

For a temporary allocation/high-water check, `get_traced_memory()` returns `(current, peak)` bytes for traced blocks. Reset the peak immediately before the operation if the process has already done setup:

```python
tracemalloc.reset_peak()
main()
current, peak = tracemalloc.get_traced_memory()
print(f"traced current={current / 1024**2:.2f} MiB peak={peak / 1024**2:.2f} MiB")
```

Snapshots can be retained for offline comparison without keeping both large objects in memory:

```python
before.dump("/tmp/program-before.snapshot")
after.dump("/tmp/program-after.snapshot")
# In a later process:
import tracemalloc
old = tracemalloc.Snapshot.load("/tmp/program-before.snapshot")
new = tracemalloc.Snapshot.load("/tmp/program-after.snapshot")
for stat in new.compare_to(old, "lineno")[:10]:
    print(stat)
```

`tracemalloc` records Python allocation traces, not the process's resident memory. A large RSS increase can come from a C/C++ extension, a shared-library mapping, allocator arenas retained for reuse, memory-mapped files, or the OS; none necessarily appears in a `tracemalloc` diff. Conversely, a positive traced diff can be reclaimed later and need not explain peak RSS. The tracing tables and traceback metadata also impose runtime and memory overhead, increasing with the frame limit; use the smallest frame depth that answers the question.

Save text outside the repository while experimenting:

```bash
python run_tracemalloc.py | tee /tmp/program-tracemalloc.txt
```

## Memray: allocation lifetimes and native call stacks

Use Memray when Python-only attribution is insufficient, especially when an extension or allocator is involved, or when you need a peak/live allocation flame graph. The README's default workflow is:

```bash
cd python
memray run program.py
memray flamegraph memray-program.py.*.bin
open memray-flamegraph-program.py.*.html  # macOS
```

Prefer deterministic paths for automation and artifact handoff:

```bash
memray run --force --output /tmp/program-memray.bin program.py
memray stats /tmp/program-memray.bin
memray summary /tmp/program-memray.bin
memray flamegraph --force --output /tmp/program-memray.html /tmp/program-memray.bin
open /tmp/program-memray.html
```

`memray run` starts a new process and records allocation/deallocation events. The default capture name is `memray-<script>.<pid>.bin`; `--output` avoids shell-glob ambiguity. Memray refuses to overwrite an existing capture or report unless `--force` is supplied, so deterministic automation paths need `--force` to be repeatable. Copy any artifact that must be preserved before rerunning these commands. `stats`, `summary`, `table`, `tree`, and `flamegraph` are reporters, not additional profiling runs. A flame graph is centered on allocations live at the peak; use its wide frames to find the call paths responsible for the high-water mark. The binary is the source artifact, while the HTML is a derived report. Keep the binary and report from the same run.

Native and Python allocator modes answer different questions:

```bash
# Python frames plus normal system-allocation tracking:
memray run --force --output /tmp/program-memray.bin program.py

# Resolve C/C++ frames (slower, and reports must be generated on this machine):
memray run --native --force --output /tmp/program-memray-native.bin program.py
memray flamegraph --force --output /tmp/program-memray-native.html /tmp/program-memray-native.bin

# Include individual Python allocator-pool events (much larger/slower capture):
memray run --trace-python-allocators --force --output /tmp/program-memray-python.bin program.py
```

Normal Memray tracking sees requests made to the system allocator; CPython's object allocator pools many individual objects, so those individual object events are not visible unless `--trace-python-allocators` is used. That option is useful for leak investigations but produces much larger files and materially more overhead. `--native` resolves native stack frames and has moderate overhead because instruction pointers are resolved per allocation; generate reports on the same machine as capture so loaded-library symbols match. Memray allocation bytes are not the same as RSS: the process can hold allocator arenas, shared pages, interpreter state, or mappings that do not appear as currently-live user allocations. Use psutil alongside it when the question is the OS-visible footprint.

Memray records can be lost if an OOM-killed process/container disappears before the file is copied. Write to persistent storage (for example `/tmp` mounted outside a disposable container) and post-process immediately when possible. `--follow-fork` requires an explicit output path and creates child capture files; the example program does not fork, so do not add it without a process-tree reason.

The repository's `python/.gitignore` ignores `memray-*.bin` and `memray-*.html`. This keeps the README's default artifacts out of Git, but ignored does not mean disposable: copy a needed binary/report to durable storage before cleanup, and treat it as potentially sensitive because reports include file paths and allocation call stacks.

## `guppy3`/Heapy: object census

Use `guppy3` when the question is “what Python objects are present now?” rather than “where was each byte allocated?” The exact repository workflow is:

```bash
cd python
python run_guppy3.py
python run_guppy3.py | tee /tmp/program-guppy3.txt
```

The runner uses the installed `guppy` compatibility import:

```python
from guppy import hpy
from program import main

h = hpy()
print("Initial")
print(h.heap())
main()
print("After")
print(h.heap())
```

`h.heap()` is a point-in-time census. Its partition rows show object count and size by kind (for example `str`, `bytes`, `dict`, or `types.CodeType`) and cumulative totals. Compare the `Initial` and `After` sections while remembering that imports, BeautifulSoup's parse tree, strings, and module caches all contribute. For retained-object questions, make collection state explicit:

```python
import gc
from guppy import hpy
from program import main

gc.collect()
h = hpy()
before = h.heap()
main()
gc.collect()
after = h.heap()
print("before\n", before)
print("after\n", after)
```

Heapy is not a tracemalloc snapshot diff: it does not show the source line that allocated a surviving object or the lifetime of a freed object. A larger object census may be legitimate reachable data; a stable census with rising RSS can instead indicate native buffers or allocator retention. Heapy itself inspects the heap and can perturb both object counts and process memory, so use it for diagnosis rather than exact production limits. Keep stdout captures in `/tmp` (there is no repository ignore rule for arbitrary `.txt` files).

## `psutil`: process memory and before/after RSS

Use psutil as the low-overhead process-level check. The exact repository workflow is:

```bash
cd python
python run_psutil.py
python run_psutil.py | tee /tmp/program-psutil.txt
```

The existing script prints `psutil.Process().memory_info()` before and after `main()` (and CPU times). Its `pmem` fields are bytes; `rss` is resident physical memory currently attributed to the process, while `vms` is virtual address space. Fields such as page faults are platform-dependent. A minimal delta pattern is:

```python
import psutil
from program import main

p = psutil.Process()
before = p.memory_info()
main()
after = p.memory_info()
print(f"rss: {before.rss / 1024**2:.2f} -> {after.rss / 1024**2:.2f} MiB")
print(f"vms: {before.vms / 1024**2:.2f} -> {after.vms / 1024**2:.2f} MiB")
```

`memory_info()` is cheap and portable for `rss` and `vms`. On supported platforms, `memory_full_info()` can add `uss`, `pss`, and `swap`:

```python
full = p.memory_full_info()
print(full)
```

USS is private memory that would be freed if this process exited; PSS divides shared pages among processes. Full information walks the address space, is slower, and may require permission, so handle `psutil.AccessDenied` and do not use it in a tight sampling loop. A before/after RSS increase is evidence of process footprint growth, not proof of a Python leak: shared libraries, network/TLS buffers, C-extension allocations, CPython arenas, and delayed OS reclamation all contribute. `memory_info()` also excludes memory held solely by children; inspect child processes separately if the workload launches them.

For a transient high-water problem, sample periodically (or use Fil/Memray) rather than relying only on the final `after` reading. A final RSS delta can be near zero even when peak RSS exceeded a limit and later fell. Use the same process and same warm-up state for before/after comparisons; for independent runs, record initial RSS and peak RSS separately.

## Filprofiler: peak-memory call-stack visualization

Use Filprofiler for an offline visualization of the high-water mark, especially when native extension allocations are suspected. The README provides both forms:

```bash
cd python
fil-profile run program.py
python -m filprofiler run program.py
```

For non-interactive/CI-safe runs, use the option already exercised by `python/timing.sh`:

```bash
fil-profile --no-browser run program.py
```

Fil writes reports under `fil-result/` in the current working directory and normally attempts to open a browser. Reports include an interactive SVG memory graph/flame graph; wide/red frames represent more of the memory live at peak. Inspect the generated directory, then open the generated SVG on macOS. The timestamped subdirectory and report filename are run/version-dependent:

```bash
open fil-result/*/*.svg
```

If the shell glob does not match, list `fil-result/` with a file browser and open the generated `.svg`; do not assume an exact timestamp or filename. Preserve a report before cleaning it:

```bash
tar -czf /tmp/program-fil-result.tgz fil-result
```

Fil tracks allocations over the run and attributes memory present at the peak to call stacks, including native extension paths that Python-only tracemalloc can miss. It is therefore complementary to psutil: Fil explains the peak's allocation paths, while psutil reports the OS footprint. Fil is an offline profiler with substantial all-allocation overhead, not a production monitor; avoid drawing performance conclusions from a profiled run. Its target is a complete program run, and the pinned older version should be used with the repository's Python 3.11.5 environment. Be cautious with multiprocessing workloads (the example program does not use multiprocessing) and verify support before applying it to a process tree.

The repository's `python/.gitignore` ignores `fil-result/`, so generated reports stay out of Git. Preserve a needed report before removing it, and do not rely on the ignore rule as a backup policy. SVG reports may include source paths and code context, so do not publish them blindly.

## A safe investigation sequence

1. Establish process impact with `python run_psutil.py`; repeat if the network response is variable.
2. If RSS grows, run `python run_tracemalloc.py` to identify Python line-level retained bytes. Start with `-X tracemalloc=25` if imports are relevant.
3. Use `python run_guppy3.py` after an explicit `gc.collect()` when object type/count growth is the key question.
4. If traced Python bytes do not explain RSS, run Memray's normal capture and then `--native`; use `--trace-python-allocators` only when individual CPython object-pool events are necessary.
5. Use `fil-profile --no-browser run program.py` for a visual high-water call-stack view, particularly for native allocations or large temporary peaks.
6. Keep stdout, binaries, and reports in `/tmp` or another deliberate artifact directory. The repository ignores `*.out`, `memray-*.bin`, `memray-*.html`, and `fil-result/`, but do not rely on ignore rules as a backup policy.
7. Compare like with like: same Python/dependency versions, same command-line options, same network/input, same warm-up, and multiple runs. A profiler changes timing and allocation behavior; report overhead separately (the repository's `./timing.sh` is a coarse comparison, not a memory benchmark).
