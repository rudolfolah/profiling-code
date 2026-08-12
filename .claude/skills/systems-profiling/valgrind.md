# Valgrind

Valgrind runs a native program through dynamic binary translation. Its tools are excellent for correctness and attribution but normally impose large slowdowns and memory expansion. Build with `-g`, keep optimizations representative when possible, and use a deterministic, reduced workload. Do not use Valgrind timing as production timing. Check the installed Valgrind release's supported OS/architecture before relying on it: Linux support is generally strongest, while macOS and especially newer ARM64 combinations can lag or be unavailable. It is not a native Windows workflow.

Common setup:

```bash
cc -O1 -g -fno-omit-frame-pointer -o app main.c
# Keep each output file separate when running concurrently.
mkdir -p profile-out
```

Use `--num-callers=30` when deeper ownership matters, but expect more overhead and larger output. Suppressions should be narrowly reviewed and version-controlled with the test setup; never suppress an error merely to make a report clean.

## Memcheck: invalid memory and leaks

**Capture:**

```bash
valgrind --tool=memcheck \
  --leak-check=full --show-leak-kinds=all --track-origins=yes \
  --num-callers=30 --log-file=profile-out/memcheck.%p.log \
  ./app < fixed-input > /dev/null
```

**Interpretation:** fix the first invalid read/write, use-after-free, uninitialized-value report, or invalid free first; later failures may be cascades. `definitely lost` means no remaining pointer can reach the allocation, while `indirectly lost` is reachable only through a definitely lost block. `still reachable` is not automatically a leak (many runtimes retain caches at exit). Stack traces need matching symbols and enough callers. `--track-origins=yes` improves uninitialized-value diagnosis at additional cost.

Memcheck instruments loads, stores, and allocator behavior, so reports are detailed but execution can be roughly an order of magnitude slower or more. It cannot prove absence of races, find every leak in code it cannot observe, or faithfully reproduce timing-sensitive behavior. Use a focused test and compare an uninstrumented run for behavior.

## Cachegrind: simulated cache and branch behavior

**Capture and inspect:**

```bash
valgrind --tool=cachegrind --cachegrind-out-file=profile-out/cachegrind.%p.out \
  ./app < fixed-input > /dev/null
cg_annotate --auto=yes profile-out/cachegrind.*.out
```

Cachegrind reports instruction/data references and simulated cache misses by function and source line. Compare inclusive versus self costs and focus on changes in misses or references for the same binary and input. Its cache model is a simulation based on configured/default parameters, not a replacement for the target CPU's hardware counters; use `perf stat` to validate real cache behavior. Dynamic translation and cache simulation are high overhead, and the altered code layout/schedule can change locality.

## Callgrind: instrumented call graph

**Capture and inspect:**

```bash
valgrind --tool=callgrind --callgrind-out-file=profile-out/callgrind.%p.out \
  ./app < fixed-input > /dev/null
callgrind_annotate --inclusive=yes profile-out/callgrind.*.out
```

Open the output in `kcachegrind` or `qcachegrind` when available for an interactive caller/callee graph. Callgrind provides deterministic event counts for the translated execution (and can collect cache-like events), not wall-clock latency. Read self versus inclusive cost, callers, callees, and cycles in the specific scenario. Use callgrind's runtime controls or a smaller workload when only one phase matters. Its instrumentation can be dramatically slower than the target and is unsuitable for latency-sensitive conclusions.

## Massif: heap growth over time

**Capture and inspect:**

```bash
valgrind --tool=massif --time-unit=ms --detailed-freq=1 \
  --massif-out-file=profile-out/massif.%p.out \
  ./app < fixed-input > /dev/null
ms_print profile-out/massif.*.out
```

Massif's graph shows heap size over its sampled timeline; snapshots and allocation stacks explain which paths own peaks. `--stacks=yes` includes thread stacks when stack growth is relevant, at additional cost. Distinguish live heap from allocator overhead and retained caches, and correlate a peak with the application phase rather than assuming the final snapshot represents the maximum. Massif is a heap profiler, not a leak proof: use Memcheck for reachability and invalid accesses. Sampling snapshots reduces output but can miss a short-lived spike; increase detail only for a focused run.

Official documentation: [Valgrind tool overview](https://valgrind.org/info/tools.html), [Memcheck manual](https://valgrind.org/docs/manual/mc-manual.html), [Cachegrind manual](https://valgrind.org/docs/manual/cg-manual.html), [Callgrind manual](https://valgrind.org/docs/manual/cl-manual.html), and [Massif manual](https://valgrind.org/docs/manual/ms-manual.html).
