# cProfile: deterministic call attribution

## Run the repository command

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

## Read the report

The standard report columns mean:

- `ncalls`: number of calls; `151/1` means 151 total calls caused by one primitive call through recursion.
- `tottime`: time spent in that function body, excluding its callees (self time).
- First `percall`: `tottime / ncalls`.
- `cumtime`: time in the function and all functions it called (inclusive time). It is the useful sort for finding an expensive path, but parent and child rows overlap and must not be added together.
- Second `percall`: `cumtime / primitive calls`.
- `filename:lineno(function)`: the source location and function name.

A high `cumtime` in `program.py:main` is a boundary, not automatically the defect: follow its children and compare `tottime`. A function with high `tottime` is a candidate for direct optimization; a function with low self time but high cumulative time is often an orchestrator or an expensive call boundary. Library rows such as `requests` or Beautiful Soup can be legitimate contributors, and the target's HTTP wait may dominate a wall-clock profile.

## Clock and overhead cautions

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
