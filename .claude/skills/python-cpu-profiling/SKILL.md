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

## Additional resources

Reference the supporting file that matches the profiler question so Claude knows when to load detailed workflows:

- [cprofile.md](cprofile.md): deterministic function-call attribution with `cProfile` and `pstats`.
- [pyinstrument.md](pyinstrument.md): wall-clock stack sampling and readable call trees.
- [py-spy.md](py-spy.md): external sampling, live summaries, dumps, and flame graphs.
- [yappi.md](yappi.md): CPU/wall-clock function and thread profiling from Python code.
- [pyperformance.md](pyperformance.md): benchmark regression comparisons; not a substitute for a profiler when a hot call path is needed.

## A repeatable investigation workflow

1. Activate `.venv` from `python/`, verify `python`, and run `time python program.py` once. Save the `real`, `user`, and `sys` values and note network conditions.
2. Decide whether the question is CPU consumption (`user`/`sys`, [yappi](yappi.md) `cpu`, [cProfile](cprofile.md), or [py-spy](py-spy.md) hot stacks) or user-visible latency (`real`, yappi `wall`, [pyinstrument](pyinstrument.md)).
3. Start with py-spy when you need a low-overhead view of a live/production-like process. Use its launched `record` form for this short script and its PID form only for an authorized long-running process.
4. Use pyinstrument for an approachable elapsed-time call tree and to expose blocking/waiting phases. Use `--show-all` when library frames matter.
5. Use cProfile when exact function counts and caller/callee attribution are needed. Inspect `profile.out` with `pstats`; sort by cumulative time, then check self time and call counts.
6. Use yappi when CPU versus wall or per-thread attribution is the deciding question. Keep the clock type beside the report and stop profiling before printing stats.
7. Repeat the same profiler under the same workload when a conclusion matters. A single HTTP response and a short script can produce sparse samples and high run-to-run variance.
8. Compare profiler overhead to the unprofiled shell timing. Do not use any of these profiled commands as a benchmark, and do not add profiler output redirects when the purpose is report interpretation.

Keep generated artifacts (`profile.out`, `profile.svg`, `pyinstrument.html`) separate from source changes. No profiling command should be described as having run unless its output was actually observed; examples in this skill are instructions only.
