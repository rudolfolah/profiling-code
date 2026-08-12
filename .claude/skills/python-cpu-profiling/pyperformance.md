# pyperformance: benchmark comparisons

The repository root links to [pyperformance](https://github.com/psf/pyperformance), a benchmark suite rather than a replacement for cProfile or a flame graph. Use it when the question is whether a repeatable benchmark regressed across Python builds or commits; use the profilers above when you need to explain a hot function or allocation. It is not pinned in `python/requirements.txt`, so install and invoke the version approved by the project, then check its local `--help` for version-specific options:

```bash
python -m pyperf system tune  # optional; use only on an authorized benchmark host
pyperformance run --python="$(command -v python)" -o pyperformance.json <benchmark>
pyperformance compare baseline.json pyperformance.json
```

Run a benchmark suite for long enough to reduce noise, keep CPU frequency/power state and workload configuration stable, and compare distributions rather than one elapsed time. Record the Python executable, pyperformance version, benchmark selection, warm-up, calibration, and machine state. A benchmark result can establish a regression; it does not identify the responsible call path. Follow a significant result with cProfile, pyinstrument, py-spy, or yappi under a controlled reproduction.
