# yappi: programmatic CPU/wall and thread profiles

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
