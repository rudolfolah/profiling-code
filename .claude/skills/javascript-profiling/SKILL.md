---
name: javascript-profiling
description: Profile Node.js CPU usage, allocation churn, retained heap, garbage collection, event-loop latency, and scoped operations with built-in Node and V8 tooling.
---

# JavaScript and Node.js performance profiling

Use this skill for Node.js workloads. For browser JavaScript, rendering, network waterfalls, or browser main-thread work, use `browser-javascript-profiling` instead.

Prefer built-in Node.js facilities before native profiler packages. A useful profile requires a representative workload that finishes successfully; validate that first.

## Choose the profiler by question

| Question | First tool | Artifact | Important limitation |
|---|---|---|---|
| Which JavaScript/native call paths consume CPU? | `node --cpu-prof` | `.cpuprofile` | Sampling can miss short work; CPU attribution is not wall-clock latency |
| Which call paths allocate the most bytes? | `node --heap-prof` | `.heapprofile` | Samples allocations, not the objects still retaining memory |
| Which objects retain memory at one point in time? | `v8.writeHeapSnapshot()` | `.heapsnapshot` | Stops the main thread and can require roughly twice the current heap |
| Is garbage collection frequent or expensive? | `node --trace-gc` | Diagnostic text | Adds logging overhead and needs representative allocation pressure |
| Is the event loop delayed? | `perf_hooks.monitorEventLoopDelay()` | Histogram values | Reports delay, not the responsible call path |
| How long does one operation take? | `performance.mark()` / `performance.measure()` | Performance entries | Instrumentation measures only the marked scope |

Do not treat RSS, heap allocation, retained heap, and total allocated bytes as interchangeable. External memory such as `Buffer` backing stores can increase RSS without appearing as ordinary V8 heap growth.

## Reproducible workflow

1. Define the observable: CPU time, end-to-end latency, allocation rate, retained objects, GC pauses, event-loop delay, or peak RSS.
2. Run the workload without profiling. Confirm correct output and record the Node version, command, input, concurrency, warm-up state, and environment.
3. Make the workload long enough to produce useful samples. Repeat or loop short operations rather than profiling process startup alone.
4. Capture the narrowest relevant profile. Keep generated artifacts outside source directories or in ignored output directories.
5. Check that the artifact is non-empty and contains samples before interpreting it. A valid but sample-free `.heapprofile` is not evidence that the workload allocates nothing.
6. Inspect self time and total/inclusive time separately. A hot parent can merely contain the expensive descendant.
7. Change one variable, then rerun the same unprofiled workload and the same profiler. Use repeated measurements; one run is not a regression result.

Profilers perturb execution. Compare runs only when Node version, input, process flags, workload duration, and profiler settings match.

## CPU profiling

Capture a V8 CPU sample profile:

```bash
mkdir -p profiles
node \
  --cpu-prof \
  --cpu-prof-dir=profiles \
  --cpu-prof-name=app.cpuprofile \
  your-app.js
```

For an npm script, invoke the actual Node entry point when practical so the profile covers the target rather than the package manager. Preserve all application arguments after the entry script.

Load `profiles/app.cpuprofile` in Chrome DevTools using **Performance > Load profile**. Confirm that it has samples and that the intended workload appears in the call tree. Use bottom-up view for expensive leaves and call-tree view for their calling context.

CPU samples answer where on-CPU execution occurred. Waiting on sockets, timers, filesystem operations, worker results, or scheduling may dominate wall time without becoming a hot JavaScript frame. Pair the CPU profile with operation timing or event-loop diagnostics when latency is the real symptom.

### Deno and Bun CPU profiles

Deno and Bun also expose V8 CPU-profile output through `--cpu-prof`. Use these only for the process started by that runtime; they do not replace browser Performance traces for a page.

```bash
mkdir -p profiles

deno run --cpu-prof --cpu-prof-dir=profiles --cpu-prof-name=deno.cpuprofile your_script.ts
deno run --cpu-prof --cpu-prof-md --cpu-prof-dir=profiles server.js

bun --cpu-prof --cpu-prof-dir ./profiles --cpu-prof-name bun.cpuprofile script.js
bun --cpu-prof-md script.js
```

Load `.cpuprofile` output in Chrome DevTools or another compatible viewer and confirm the intended workload appears in the sample tree. The Markdown profile options (`--cpu-prof-md`) are summaries for review, not substitutes for the raw CPU profile when detailed stack inspection is needed. Do not assume Node-only heap, GC, or inspector examples in this skill apply unchanged to Deno or Bun.

### Scoped CPU profiling with the built-in inspector

Use `node:inspector` instead of adding `v8-profiler-next`. This captures only the operation between `Profiler.start` and `Profiler.stop`:

```javascript
const fs = require('node:fs/promises');
const inspector = require('node:inspector');

const session = new inspector.Session();
const post = (method, params = {}) => new Promise((resolve, reject) => {
  session.post(method, params, (error, result) => {
    if (error) reject(error);
    else resolve(result);
  });
});

async function captureProfile() {
  session.connect();
  try {
    await post('Profiler.enable');
    await post('Profiler.start');

    await runRepresentativeWorkload();

    const { profile } = await post('Profiler.stop');
    await fs.writeFile('operation.cpuprofile', JSON.stringify(profile));
  } finally {
    session.disconnect();
  }
}

captureProfile().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
```

Do not perform unrelated logging, setup, or teardown inside the measured scope unless it is part of the behavior being investigated.

## Allocation sampling

Capture sampled allocation stacks:

```bash
mkdir -p profiles
node \
  --heap-prof \
  --heap-prof-dir=profiles \
  --heap-prof-name=app.heapprofile \
  your-app.js
```

Load the result in Chrome DevTools under **Memory**. This is allocation sampling: it identifies allocation-heavy stacks, including objects later collected. It does not by itself prove a leak.

Short workloads can produce a structurally valid profile with no samples at the default sampling interval. For a bounded diagnostic run, lower the interval to collect more samples:

```bash
node \
  --heap-prof \
  --heap-prof-interval=1024 \
  --heap-prof-dir=profiles \
  --heap-prof-name=app-1k.heapprofile \
  your-app.js
```

A smaller interval increases overhead and artifact size. Record the interval and never compare profiles captured with different intervals as if their sample counts were equivalent.

## Retained-heap snapshots

Use a heap snapshot when the question is which objects remain reachable and what retains them:

```javascript
const v8 = require('node:v8');

const snapshotPath = v8.writeHeapSnapshot(
  `heap-${process.pid}-${Date.now()}.heapsnapshot`,
);
console.log(`Heap snapshot written to ${snapshotPath}`);
```

`v8.writeHeapSnapshot()` returns only after the file is complete. Load it in Chrome DevTools under **Memory**. For leak analysis, compare snapshots around the same application state after allowing expected temporary objects to be collected; inspect growing retained objects and their retaining paths.

Heap snapshots stop the main thread and may require about twice the current heap, which can terminate a process under memory pressure. They can contain secrets and user data. Do not capture production heaps without authorization, capacity headroom, secure storage, and a retention/deletion plan.

Node also supports signal-triggered snapshots through `--heapsnapshot-signal=<signal>` on supported platforms. There is no general `node --heapsnapshot` flag.

## Garbage-collection tracing

Run a bounded representative workload:

```bash
node --trace-gc your-app.js
```

Interpret each event by collection type, before/after heap size, pause duration, and reason. Repeated scavenges can be normal for allocation-heavy work. Frequent major collections, long pauses, or little memory reclaimed are stronger signals of heap pressure or retention. Do not “fix” GC pressure by increasing `--max-old-space-size` unless the application genuinely needs a larger live heap; a larger heap can defer rather than remove the cause.

For a controlled experiment that explicitly calls `global.gc()`, launch with `--expose-gc` and fail if the flag is missing:

```javascript
if (typeof global.gc !== 'function') {
  throw new Error('Run this diagnostic with node --expose-gc');
}
global.gc();
```

Manual GC changes application behavior. Use it to establish controlled snapshot boundaries, not as a production memory-management strategy.

## Scoped timing and event-loop delay

Measure a named operation with `node:perf_hooks`:

```javascript
const { performance } = require('node:perf_hooks');

performance.mark('operation:start');
await runRepresentativeWorkload();
performance.mark('operation:end');
const measurement = performance.measure(
  'operation',
  'operation:start',
  'operation:end',
);
console.log(`${measurement.name}: ${measurement.duration.toFixed(3)} ms`);
performance.clearMarks();
performance.clearMeasures();
```

`performance.measure()` returns the completed entry, so this form cannot lose a queued `PerformanceObserver` callback by disconnecting too early.

For event-loop delay:

```javascript
const { monitorEventLoopDelay } = require('node:perf_hooks');
const { setImmediate: nextTurn } = require('node:timers/promises');

const delay = monitorEventLoopDelay({ resolution: 20 });
delay.enable();
await nextTurn();

await runRepresentativeWorkload();

await nextTurn();
delay.disable();
console.log({
  meanMs: delay.mean / 1e6,
  p99Ms: delay.percentile(99) / 1e6,
  maxMs: delay.max / 1e6,
});
```

Histogram values are nanoseconds; divide by `1e6` for milliseconds. Let the observation window span event-loop turns on both sides of the work. A very short window can have no samples and report `NaN` for the mean; increase the workload or observation time before interpreting it.

## Webpack and Jest

Avoid version-specific internal paths such as `webpack-cli/bin.js` and `jest-cli/bin/jest.js`. Use the package entry points installed by the project:

```bash
# Webpack production build CPU profile
node \
  --cpu-prof \
  --cpu-prof-dir=profiles \
  --cpu-prof-name=webpack.cpuprofile \
  ./node_modules/webpack/bin/webpack.js \
  --mode production

# Jest CPU profile; serial execution makes attribution and comparison clearer
node \
  --cpu-prof \
  --cpu-prof-dir=profiles \
  --cpu-prof-name=jest.cpuprofile \
  ./node_modules/jest/bin/jest.js \
  --runInBand

# Jest per-test heap reporting
node \
  --expose-gc \
  ./node_modules/jest/bin/jest.js \
  --runInBand \
  --logHeapUsage
```

Keep the project’s existing arguments, config, environment, and test selection. Profile a focused build or test target before a full suite. `--runInBand` changes concurrency, so compare it only with another serial run.

## Reporting and cleanup

Report:

- the exact command and Node version;
- workload input, duration, concurrency, and warm-up state;
- profiler type and settings, including heap sampling interval;
- the hottest or largest call paths with self and total values;
- whether the result concerns allocated, retained, or process memory;
- repeated unprofiled before/after measurements for any claimed optimization.

Delete generated `.cpuprofile`, `.heapprofile`, `.heapsnapshot`, and GC trace artifacts when the investigation ends unless the repository intentionally retains them. Never commit heap snapshots containing application or user data.
