# pyinstrument: wall-clock sampling

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

The report is a sampled call tree. A wide/high-percentage branch means many samples observed that stack, so it is an estimate of elapsed activity rather than an exact call count. Repeated frames may be condensed in the normal view. Use `--timeline` when the order of phases matters, or `--show-all` if the default filtering hides library frames that are relevant to this target:

```bash
pyinstrument --timeline program.py
pyinstrument --show-all program.py
```

Run those modes separately with the repository's pinned pyinstrument 4.6.2. Combining `--timeline --show-all` can produce an effectively empty terminal report even when the header reports many samples.

The default sampling interval is designed for general profiling. A shorter interval can resolve shorter calls but increases profiler overhead and report size; a longer interval reduces overhead and memory use but loses detail. For a very short `program.py` run, “no samples” or a sparse tree is a sampling limitation, not evidence that the program did no work. Prefer a longer representative workload when available, or compare several runs rather than making a conclusion from one sample.

Because pyinstrument is an elapsed-time profiler, a `requests.get` wait or file operation can occupy a large branch even when it consumes little CPU. That is exactly the signal to use for user-visible latency. If the question is “which Python code burns CPU while the request is already available?”, pair the report with `time` or use yappi's CPU clock/cProfile rather than treating a wall-time branch as CPU cost.
