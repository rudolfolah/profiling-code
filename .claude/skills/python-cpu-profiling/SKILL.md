# Python CPU and Runtime Profiling

Use this skill when you need to explain, investigate, or improve Python execution time in this repository. It covers the four profilers that are relevant here: **cProfile**, **pyinstrument**, **py-spy**, and **yappi**. The target program is `python/program.py`; commands below assume they are run from the `python/` directory unless stated otherwise.

## Scope and selection

Choose the clock and profiler based on the question, not on the smallest reported number. This program performs an HTTP request, parses HTML with Beautiful Soup, and counts words, so network wait, imports, and parsing can show up differently in each profile.

| Tool | Method and clock | Use it when you need | Primary output | Cost and important limits |
|---|---|---|---|---|
| `cProfile` | Deterministic function-call instrumentation; the CLI's default timer is elapsed real time (the profiler's built-in real-time clock) | Exact call counts and inclusive/self timing for Python functions | `profile.out`, inspected with `pstats` | More overhead for call-heavy code; it changes the execution it measures and is not a benchmark. It profiles the interpreter process that starts the script, not child interpreters automatically. |
| `pyinstrument` | Statistical stack sampling at an interval; its normal report represents wall-clock/elapsed activity | A readable call tree showing where user-perceived time, including waits, is spent | Terminal tree, or HTML/JSON/etc. report | Usually less intrusive than deterministic tracing, but samples can miss very short functions; a smaller interval costs more CPU and memory. |
| `py-spy` | External OS-level sampling profiler; samples the running process without importing code into it and normally focuses on active/on-CPU threads | A low-overhead view of a running or production-like process, including stacks without changing the target | Live `top`, one-shot `dump`, or SVG flame graph from `record` | Requires OS permission to read another process (especially on macOS and for PID attach on Linux). Sampling is approximate, and a short script may finish before enough samples are collected. |
| `yappi` | Deterministic in-process function/thread profiling; clock is explicitly selectable (`cpu` or `wall`) | CPU-vs-wall comparisons, per-function totals, and thread-aware reports from Python code | Function and thread tables printed by `print_all()` | Instrumentation can be substantial, especially with many calls or threads; child processes need their own profiler setup. |

### CPU time versus wall-clock time

- **CPU time** answers “How much processor time did this process consume?” It excludes time sleeping or waiting for the network, although kernel CPU time can still appear separately in the shell's `sys` measurement. Use it for CPU-bound Python work and algorithmic cost.
- **Wall-clock time** answers “How long did a user wait?” It includes scheduling, network, file, lock, and sleep delays. Use it for request latency and end-to-end responsiveness.
- The shell's `time` command is the baseline for the distinction: `real` is elapsed wall time, `user` is user-mode CPU time, and `sys` is kernel-mode CPU time. Do not compare a profiler's function total directly to a shell `real` value without checking that profiler's clock.
- `cProfile`'s repository command uses its default real-time timer. `yappi` is the clearest way in this set to run the same code with either `cpu` or `wall`. `pyinstrument` is normally used here as an elapsed-time sampler. `py-spy`'s default active-thread samples are most useful for CPU hot spots; use a wall-time profiler when blocked time is the question.

## Setup and safe baseline

The repository README sets up a Python virtual environment and installs the pinned dependencies in `python/requirements.txt` (`pyinstrument==4.6.2`, `py-spy==0.3.14`, and `yappi==1.6.0` among them). From the repository root, the README's setup commands are:

```bash
cd python
pyenv install $(cat .python-version)
pyenv local
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If the environment already exists, the minimum assumption for every command is:

```bash
cd python
source .venv/bin/activate
```

Verify that `python` and the console tools resolve from the intended environment before profiling:

```bash
python --version
command -v python
command -v pyinstrument
command -v py-spy
```

Do not silently use a system interpreter: the target imports `requests` and `bs4`, and the pinned virtual environment is what makes those imports and profiler versions reproducible. The target fetches `https://en.wikipedia.org/wiki/Intuitive_Machines_Nova-C`, writes a temporary file, and prints its result. Run only when network access and that side effect are acceptable. The response, server latency, DNS, proxy settings, import caches, and machine load can all change the profile; compare runs under the same conditions and treat one short run as directional evidence.

Establish an unprofiled timing before interpreting profiler overhead:

```bash
time python program.py
```

The repository's `python/timing.sh` activates `.venv`, runs each command with `time`, and redirects program output to `/dev/null`. Its complete profiling-relevant commands are:

```bash
time pyinstrument program.py > /dev/null
time python -m cProfile -o profile.out program.py > /dev/null
time python run_yappi.py > /dev/null
```

The README also runs the whole comparison with:

```bash
./timing.sh
```

That script includes other memory/profiling tools and performs multiple network requests; use it only when that full comparison is intended. The redirection is for timing, not report inspection: run the profiler without `> /dev/null` when you need to read its text output.

## cProfile: deterministic call attribution

### Run the repository command

The README's exact command writes a binary profile database:

```bash
python -m cProfile -o profile.out program.py
```

Inspect it with the standard-library statistics browser, using the README's exact interaction:

```bash
python -m pstats profile.out
profile.out% sort cumulative
profile.out% stats 10
```

`sort cumulative` puts the functions with the largest inclusive (`cumtime`) totals first; `stats 10` limits the displayed report to ten rows. The file is not source text, so do not try to read `profile.out` with a text editor. Keep the artifact if a later analysis needs the same run, and remove or ignore it when it is no longer needed.

### Read the report

The standard report columns mean:

- `ncalls`: number of calls; `151/1` means 151 total calls caused by one primitive call through recursion.
- `tottime`: time spent in that function body, excluding its callees (self time).
- First `percall`: `tottime / ncalls`.
- `cumtime`: time in the function and all functions it called (inclusive time). It is the useful sort for finding an expensive path, but parent and child rows overlap and must not be added together.
- Second `percall`: `cumtime / primitive calls`.
- `filename:lineno(function)`: the source location and function name.

A high `cumtime` in `program.py:main` is a boundary, not automatically the defect: follow its children and compare `tottime`. A function with high `tottime` is a candidate for direct optimization; a function with low self time but high cumulative time is often an orchestrator or an expensive call boundary. Library rows such as `requests` or Beautiful Soup can be legitimate contributors, and the target's HTTP wait may dominate a wall-clock profile.

### Clock and overhead cautions

`cProfile` records every Python function-call/return event, which gives exact counts but perturbs call-heavy code. C-level work is not charged the same way as Python call dispatch, so do not use a profiled run as a microbenchmark or infer production latency from it. Compare the unprofiled `time` output with the profiled `time` output, and make decisions from repeated profiles and relative hot spots.

If a CPU-only call profile is required for a controlled experiment, use a custom timer around the code under investigation rather than changing the repository command:

```python
import cProfile
import time

profiler = cProfile.Profile(timer=time.process_time)
profiler.enable()
try:
    # call the code under investigation
    pass
finally:
    profiler.disable()
profiler.print_stats(sort="cumulative")
```

This is an example of the standard `cProfile.Profile` API, not a modification requested for `program.py`. A custom timer changes what the numbers mean and should be documented alongside the result. For this repository's unmodified target, use the README command and the shell's `user`/`sys` values when you need the normal baseline.

## pyinstrument: wall-clock sampling

The repository's exact `python/timing.sh` invocation is:

```bash
time pyinstrument program.py > /dev/null
```

For an inspectable terminal report, omit the redirect:

```bash
pyinstrument program.py
```

For a saved interactive report, use the installed CLI renderer explicitly:

```bash
pyinstrument -r html -o pyinstrument.html program.py
```

The report is a sampled call tree. A wide/high-percentage branch means many samples observed that stack, so it is an estimate of elapsed activity rather than an exact call count. Repeated frames may be condensed in the normal view. Use `--timeline` when the order of phases matters, and `--show-all` if the default filtering hides library frames that are relevant to this target:

```bash
pyinstrument --timeline --show-all program.py
```

The default sampling interval is designed for general profiling. A shorter interval can resolve shorter calls but increases profiler overhead and report size; a longer interval reduces overhead and memory use but loses detail. For a very short `program.py` run, “no samples” or a sparse tree is a sampling limitation, not evidence that the program did no work. Prefer a longer representative workload when available, or compare several runs rather than making a conclusion from one sample.

Because pyinstrument is an elapsed-time profiler, a `requests.get` wait or file operation can occupy a large branch even when it consumes little CPU. That is exactly the signal to use for user-visible latency. If the question is “which Python code burns CPU while the request is already available?”, pair the report with `time` or use yappi's CPU clock/cProfile rather than treating a wall-time branch as CPU cost.

## py-spy: external sampling and flame graphs

`py-spy` appears in `python/requirements.txt` as version `0.3.14`, but the repository README and `timing.sh` do not provide a py-spy run. The following are CLI examples for the installed dependency; they do not replace the repository's exact commands above.

Launch and record the target in one command:

```bash
py-spy record -o profile.svg -- python program.py
```

This writes an interactive SVG flame graph. The `--` separates py-spy's options from the target command. To watch a live summary instead:

```bash
py-spy top -- python program.py
```

To inspect a process that is already running, first obtain the PID from a process you own and then use:

```bash
py-spy top --pid <PID>
py-spy dump --pid <PID>
py-spy record -o profile.svg --pid <PID>
```

`top` is useful for a long-lived process; `dump` is useful for a one-time stack snapshot, such as diagnosing a hang. `program.py` is short and performs one request, so a launched `record` run is generally more useful than trying to attach after it has already exited.

A flame graph's horizontal width is proportional to sampled time, not to exact invocation count. Read from the bottom (the process/thread root) upward: broad branches are the stacks that occupied the most samples; narrow branches may still be important if they are latency-sensitive or under-sampled. A missing short function is expected with sampling. The default view attempts to omit idle threads, so a missing network wait should not be interpreted as proof that no wall time was spent waiting. Use pyinstrument or yappi with `wall` when blocked time is the question.

For a process that creates Python child processes, ask py-spy to follow them when supported by the installed version:

```bash
py-spy record --subprocesses -o profile.svg -- python program.py
py-spy top --subprocesses -- python program.py
```

Without `--subprocesses`, a parent profile does not automatically explain work done in a child interpreter. `cProfile`, pyinstrument, and yappi similarly require profiling code in each child or a separately launched profiler; do not assume that an in-process profile covers multiprocessing workers.

### Permission and safety caveats

py-spy reads another interpreter's memory from outside the target process, which is why it has low in-process overhead but also why OS security rules matter. On macOS, attaching commonly requires root; on Linux, attaching to an unrelated PID can require root or ptrace permission. If a PID attach fails with an access/permission error, first prefer the launched form (`py-spy ... -- python program.py`) for a process you own. If the OS still requires elevation, rerun only the specific command with `sudo` and use an explicit path so the intended installed binary is selected, for example:

```bash
sudo "$(command -v py-spy)" record -o profile.svg -- python program.py
```

Do not attach to an unrelated process or use `sudo` to bypass a policy without authorization. A root-run target may have different environment, proxy, file permissions, and output ownership, so record that fact with the profile. `--locals` (where supported) can expose application data; avoid it for this target unless the data is safe to disclose.

## yappi: programmatic CPU/wall and thread profiles

The repository's runner is `python/run_yappi.py`, and the README's exact command is:

```bash
python run_yappi.py
```

`python/timing.sh` expands its `run run_yappi.py` helper to:

```bash
time python run_yappi.py > /dev/null
```

Run without redirection to inspect the report. The existing runner does the following:

```python
import yappi

from program import main

yappi.set_clock_type("cpu")
yappi.start()
main()
yappi.get_func_stats().print_all()
yappi.get_thread_stats().print_all()
print(f"Memory usage {yappi.get_mem_usage()}")
```

The important choices are `set_clock_type("cpu")` and starting before `main()`. A controlled version should stop in a `finally` block before reading stats, so a failure does not leave profiling enabled:

```python
import yappi

from program import main

yappi.set_clock_type("cpu")       # processor time; excludes network sleep
# Use "wall" instead when end-to-end elapsed time is the question.
yappi.start()
try:
    main()
finally:
    yappi.stop()

yappi.get_func_stats().print_all()
yappi.get_thread_stats().print_all()
```

Use `yappi.set_clock_type("wall")` for the same function/thread report with elapsed time. Do not mix CPU-clock and wall-clock runs when comparing totals. If the target uses threads, retain the thread report: it can reveal a worker that the aggregate function table obscures. Yappi's `get_mem_usage()` output in `run_yappi.py` is an auxiliary value printed by the repository runner; it is not a replacement for a memory profiler.

Interpret the function table shown by the README (`Clock type: CPU`, `Ordered by: totaltime, desc`) as follows:

- `ncall`: number of function calls.
- `tsub`: time spent in the function body itself (self time).
- `ttot`: total time attributed to that function, including callees.
- `tavg`: average total time per call.
- Thread rows include a thread name/id and total time plus a switch/count field; use them to identify uneven work or scheduling.

Yappi is deterministic instrumentation, so it can be more disruptive than pyinstrument or py-spy on code with very high call rates. Its exact function totals are valuable for a CPU-vs-wall experiment, but the profiler's own cost must be checked against `time python program.py`. Start and stop around the smallest meaningful region when profiling a larger application; for this repository's complete target, use the runner so imports and `main()` are consistent with the README.

A child process has a separate interpreter and does not inherit useful yappi samples merely because the parent called `yappi.start()`. Initialize yappi in the child, or use py-spy's `--subprocesses` mode for an external view.

## pyperformance: benchmark comparisons

The repository root links to [pyperformance](https://github.com/psf/pyperformance), a benchmark suite rather than a replacement for cProfile or a flame graph. Use it when the question is whether a repeatable benchmark regressed across Python builds or commits; use the profilers above when you need to explain a hot function or allocation. It is not pinned in `python/requirements.txt`, so install and invoke the version approved by the project, then check its local `--help` for version-specific options:

```bash
python -m pyperf system tune  # optional; use only on an authorized benchmark host
pyperformance run --python="$(command -v python)" -o pyperformance.json <benchmark>
pyperformance compare baseline.json pyperformance.json
```

Run a benchmark suite for long enough to reduce noise, keep CPU frequency/power state and workload configuration stable, and compare distributions rather than one elapsed time. Record the Python executable, pyperformance version, benchmark selection, warm-up, calibration, and machine state. A benchmark result can establish a regression; it does not identify the responsible call path. Follow a significant result with cProfile, pyinstrument, py-spy, or yappi under a controlled reproduction.

## A repeatable investigation workflow

1. Activate `.venv` from `python/`, verify `python`, and run `time python program.py` once. Save the `real`, `user`, and `sys` values and note network conditions.
2. Decide whether the question is CPU consumption (`user`/`sys`, yappi `cpu`, cProfile, or py-spy hot stacks) or user-visible latency (`real`, yappi `wall`, pyinstrument).
3. Start with py-spy when you need a low-overhead view of a live/production-like process. Use its launched `record` form for this short script and its PID form only for an authorized long-running process.
4. Use pyinstrument for an approachable elapsed-time call tree and to expose blocking/waiting phases. Use `--show-all` when library frames matter.
5. Use cProfile when exact function counts and caller/callee attribution are needed. Inspect `profile.out` with `pstats`; sort by cumulative time, then check self time and call counts.
6. Use yappi when CPU versus wall or per-thread attribution is the deciding question. Keep the clock type beside the report and stop profiling before printing stats.
7. Repeat the same profiler under the same workload when a conclusion matters. A single HTTP response and a short script can produce sparse samples and high run-to-run variance.
8. Compare profiler overhead to the unprofiled shell timing. Do not use any of these profiled commands as a benchmark, and do not add profiler output redirects when the purpose is report interpretation.

Keep generated artifacts (`profile.out`, `profile.svg`, `pyinstrument.html`) separate from source changes. No profiling command should be described as having run unless its output was actually observed; examples in this skill are instructions only.
