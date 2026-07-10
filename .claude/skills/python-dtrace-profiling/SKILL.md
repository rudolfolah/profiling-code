# Python DTrace Profiling Skill

Use this skill when you need an event-by-event view of CPython execution on macOS: Python function entry/return events, source-line events, and their ordering in a real process. This repository's DTrace programs are `python/call_stack.d` and `python/lines.d`; run them from the `python/` directory against `program.py`.

DTrace is **instrumentation tracing**, not a replacement name for every Python profiler. It observes CPython's static probes and prints a timestamped text stream. Use `cProfile`/`yappi` for function call timing, `pyinstrument` for sampled call stacks, `tracemalloc`/`memray`/`guppy3` for Python memory behavior, and `psutil` for process resource snapshots. DTrace is useful when the exact sequence and nesting of interpreter events matters.

## When to use it

Choose DTrace when you need to answer questions such as:

- Which Python functions were entered and returned around a particular operation?
- Which source lines in `program.py` executed, and in what order?
- Did an event happen before or after another event in the running process?
- Are native/interpreter-level boundaries relevant, rather than only an aggregate profile?

Do not start with DTrace for a broad “what is slow?” question. Begin with the repository's lower-overhead or purpose-built profilers, then use a short DTrace run to explain a specific behavior. DTrace output is raw and often needs filtering or aggregation after the run.

## Prerequisites: an instrumented Python

The checked-in `.python-version` is **3.11.5**. DTrace probes are not enabled in an ordinary prebuilt Python. CPython must be configured and compiled with `--with-dtrace`; this also applies when the interpreter is built in a Docker image. `--with-dtrace` is a build-time option, not a flag that can be added to `python3.11` later.

From this repository's `python/` directory, a fresh pyenv setup is:

```bash
cd python
PYTHON_CONFIGURE_OPTS="--with-dtrace" pyenv install $(cat .python-version)
pyenv local
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The first command builds the pinned version with DTrace support. If that version is already installed by pyenv without the option, installing it again will not convert the existing build; rebuild the version in a controlled pyenv environment (without deleting an environment you still need), then recreate the virtual environment if necessary. Verify the active interpreter before tracing:

```bash
python --version
command -v python3.11
```

The repository README's regular setup uses the same `pyenv local`, virtualenv, and requirements commands. The DTrace scripts themselves do not require a Python package beyond the instrumented interpreter, but `program.py` needs the dependencies installed by `requirements.txt` (`requests` and `beautifulsoup4`).

### Confirm that probes exist

DTrace's Python provider name includes the target process ID. Start the exact interpreter in a quiet interactive shell, list its probes, then return to the shell and exit it:

```bash
source .venv/bin/activate
python3.11 -q &
sudo dtrace -l -P python$!
fg # press Ctrl+D to exit the Python shell
```

`$!` is the shell's PID for the background Python process, so `python$!` expands to a provider such as `python22133`. Look for at least `function-entry`, `function-return`, and `line` in the probe list. The provider may also expose audit, import, and garbage-collection probes. The scripts in this repository use the target wildcard (`python$target`) and therefore attach to the process launched by DTrace's `-c` option rather than requiring you to copy a PID.

Probe availability must be checked on the actual interpreter. CPython's static-marker implementation varies by release; `--with-dtrace` is necessary but does not make unsupported or missing probes appear. In particular, this repository pins an older 3.11.x build, so treat the probe listing and a small smoke run as authoritative. If the required probes are absent, rebuild with the option or use a CPython release/build that provides them; changing the `.d` file cannot fix a missing provider.

## Run the repository scripts

Run these commands from `python/`, with the virtual environment activated, so `program.py` and the checked-in `.d` files resolve as shown in the README:

```bash
sudo dtrace -s call_stack.d -c 'python3.11 program.py'
sudo dtrace -s lines.d -c 'python3.11 program.py'
```

These are the exact repository workflows:

- `-s call_stack.d` loads `call_stack.d`.
- `-s lines.d` loads `lines.d`.
- `-c 'python3.11 program.py'` makes DTrace launch the target and stop tracing when it exits. The single quotes protect the command from the outer shell; they are not part of the Python command.
- `sudo` is normally required on macOS to enable DTrace and access the process. Expect a password prompt.

The `-c` command assumes `python3.11` is visible to the environment used by DTrace. If `sudo` or pyenv changes `PATH` on a particular machine, keep the same command shape but substitute the absolute path printed by `command -v python3.11`, for example:

```bash
sudo dtrace -s lines.d -c '/absolute/path/to/python3.11 program.py'
```

The target's own output (the word counts printed by `program.py`) can appear alongside DTrace output. Redirect DTrace's combined output when a run is large:

```bash
sudo dtrace -s lines.d -c 'python3.11 program.py' > lines.trace
sudo dtrace -s call_stack.d -c 'python3.11 program.py' > call-stack.trace
```

## What the scripts trace

Python's DTrace marker arguments used by these scripts are:

- `arg0`: source filename
- `arg1`: Python function name (for a module body this may be the module-level code name)
- `arg2`: source line number

Both scripts call `copyinstr()` to read the string arguments and use `basename()` for filename filtering. Their output is deliberately plain text:

```text
<Timestamp>\t<probe name padded to 15 columns>:<optional indentation><file>:<function>:<line>
```

`timestamp` is DTrace's monotonic timestamp (use differences between events for elapsed time; it is not a wall-clock date). The probe name identifies the event: `function-entry`, `function-return`, or `line`.

### `call_stack.d`

`call_stack.d` combines function and line events:

1. A `function-entry` whose `arg0` basename is `program.py` sets the per-thread `self->trace` flag.
2. While that flag is set, every subsequent function entry is printed, including nested calls into libraries. The current per-thread indentation is printed, then incremented.
3. A matching `function-return` decrements indentation before printing, so returns line up with the caller's depth.
4. A `function-return` for `program.py` clears the trace flag.
5. `line` events are printed only when `basename(copyinstr(arg0)) == "program.py"`, with the current indentation.

Thus the call events show the nested call activity reached from `program.py`, while line events are limited to that basename. The script's predicates are basename filters, not full-path filters: another file also named `program.py` could match. Repeated line events are expected in loops. With multiple threads, `self->trace` and `self->indent` are per-thread, while output lines can still interleave.

### `lines.d`

`lines.d` listens only to `python$target:::line` and applies the same `program.py` basename predicate. It prints every matching line event without indentation. It is the smaller script when the question is strictly “which lines executed?”; it is not a duration or line-cost profiler. A loop or parser can produce a very large number of repeated events.

### Interpreting entry, return, and line events

- Pair a `function-entry` and `function-return` at the same nesting level to identify an invocation's interval. Subtract their timestamps for an approximate observed interval, remembering that output and other threads affect the trace.
- A `function-entry` is an observation that CPython entered a Python function; it is not itself proof that the function consumed most of the runtime.
- A `function-return` marks the corresponding function exit event. Match events by per-thread nesting and function/file/line rather than by adjacent lines if multiple threads are active.
- A `line` event marks a source-line execution event from CPython. It is useful for control-flow evidence, but repeated events count executions, not exclusive time.
- DTrace's printed source is the filename basename, function name, and line number supplied by the static marker. C-extension work may appear only as surrounding Python events; these scripts do not turn native functions into Python source-line events.

## Filtering and overhead

The scripts already filter line events to `program.py` and use `call_stack.d`'s trace flag to avoid printing function events before the target program enters. They still print every matching line, including lines executed many times, and `call_stack.d` also prints nested library function entries and returns. Filtering is therefore not free: the DTrace predicates avoid irrelevant events in the output, but `printf()` for each selected event and the cost of formatting/reading strings can dominate the run.

The README records one run with “Tracing every line” at **0m35.006s real, 0m7.995s user, and 0m28.952s system**, compared with an unprofiled run around 0m0.344s real. Treat those numbers as an illustration rather than a benchmark—the program performs a network request and timings vary—but expect line tracing to be orders of magnitude slower for event-heavy workloads. Never trace every line casually in production or on a long-running service. Prefer a short workload, a narrow source predicate, and redirected output; only enable `lines.d` when line-level evidence is actually needed.

## macOS permissions and System Integrity Protection

On macOS, DTrace may print:

```text
dtrace: system integrity protection is on, some features will not be available
```

SIP can restrict parts of DTrace, especially probes or operations involving protected system processes. In a hosted environment you generally cannot disable SIP. For this repository's own, user-launched Python process, the warning is not automatically fatal: continue if the probe listing contains the needed Python probes and the smoke run emits events. If `dtrace` reports that a probe is unavailable, permission is denied, or no events are emitted, check the build and provider listing before changing SIP. Do not disable SIP merely to obtain a larger trace; doing so changes system security and requires Apple's supported recovery procedure.

Use `sudo` for the DTrace commands, trace a process you own, and avoid including secrets in either command arguments or traced program output. macOS may still refuse tracing protected, hardened, or otherwise restricted processes even with `sudo`; use a local non-protected interpreter for this repository. A missing `function-entry`, `function-return`, or `line` probe is different from a `sudo` failure: the former is a Python build/version issue, while the latter is an authorization or system-policy issue.

## DTrace versus the repository's other profilers

| Tool | Best question | Difference from these DTrace scripts |
| --- | --- | --- |
| `call_stack.d` / `lines.d` | What exact Python events and source lines occurred, and in what order? | macOS DTrace; requires a `--with-dtrace` CPython, `sudo`, and emits high-volume text. |
| `python -m cProfile -o profile.out program.py` + `python -m pstats profile.out` | Which functions accumulated CPU/cumulative time and how many calls? | Deterministic Python profiler with an aggregate report; no DTrace build or root tracing required. |
| `pyinstrument program.py` | Which call stacks are hot over time with sampling overhead? | Statistical sampling rather than an event for every function/line. |
| `python run_yappi.py` | Function timing and call statistics (the repository's Yappi example) | Aggregated profiler output, not a source-line event stream. |
| `python run_tracemalloc.py` | Where Python allocations grew between snapshots? | Allocation tracking; DTrace scripts do not identify memory growth. |
| `memray run program.py`, `python run_guppy3.py`, `fil-profile run program.py` | Native/Python allocation or heap shape | Memory-oriented reports/flamegraphs; not call/line chronology. |
| `python run_psutil.py` | Process CPU and RSS/page-fault snapshots | Coarse resource measurements; no CPython probe stream. |

For a first pass on a performance regression, use an aggregate or sampling profiler. Use DTrace after you have a bounded hypothesis that requires chronology or exact event counts.

## Cleanup

DTrace instrumentation from `-c` is attached only for that command; it does not permanently modify Python or leave probes enabled after the target exits. If you started the probe-listing shell, return it to the foreground with `fg` and press `Ctrl+D` as shown above. If a run was interrupted, confirm that the child is no longer running before starting another trace. Remove any redirected `*.trace` files when they contain sensitive output, and leave the virtual environment with:

```bash
deactivate
```

No DTrace-specific Python package needs to be uninstalled. Keep the instrumented pyenv build if you will trace again; otherwise switch `pyenv local` to the interpreter you normally use rather than expecting a runtime option to disable instrumentation.
