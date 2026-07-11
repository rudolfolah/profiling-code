# Browser JavaScript Performance Profiling with Chrome DevTools

Use this skill when the subject is JavaScript running in a browser page: page-load cost, interaction latency, rendering jank, long tasks, layout/paint work, or objects retained by a page. The primary reference is the [Chrome DevTools Performance features reference](https://developer.chrome.com/docs/devtools/performance/reference).

This is **browser-page profiling**, not Node.js process profiling. The existing JavaScript/Node.js skill covers `node --cpu-prof`, `node --heap-prof`, `--trace-gc`, V8 heap APIs, and server-side tools. Do not use those Node flags as a substitute for recording a page: they profile a Node process and its isolate. A Node `.cpuprofile` or `.heapprofile` can be opened in DevTools, but it is not a browser Performance trace and does not include the page's renderer, network, layout, paint, or user interaction. Use the Performance and Memory panels below for a browser page.

## Choose the panel for the question

| Question | First workflow | Main evidence |
| --- | --- | --- |
| Why is an interaction or animation janky? | Performance panel, runtime recording | Main-thread tasks, frames, interactions, scripting, style/layout, paint, and user-timing markers |
| Why is initial load slow? | Performance panel, **Record and reload** | Network request timing, parse/compile, script execution, rendering milestones, and screenshots |
| Which objects remain alive after teardown? | Memory panel, heap snapshots | Snapshot comparison, retained size, dominators, and retainer paths to GC roots |
| What allocates repeatedly during a scenario? | Memory panel, **Allocation instrumentation on timeline** | Allocation intervals, allocation stacks, and objects that survive later collections |
| Is the issue caused by a slow service or transport? | Performance panel plus Network track/conditions | Request queueing, connection, response, and page work; corroborate with server and field data |

## Establish a repeatable capture

1. **State the hypothesis and observable.** Record whether the target is load time, interaction latency, frame drops, CPU self-time, retained heap, allocation rate, or a particular user-timing measure. Define the exact URL, viewport, device emulation, input sequence, data set, and success criterion.
2. **Use the right build.** Profile the same production-like bundle, feature flags, and source-map revision that users receive. Development builds add assertions, logging, unminified code, and different scheduling behavior. Keep the browser/OS/Chrome version, viewport, zoom, display scale, and extension set constant.
3. **Control state.** Decide whether the test is cold-cache or warm-cache and use that state consistently. Use a test account and deterministic fixtures where possible. Close unrelated tabs and background work, but do not silently change the workload between runs.
4. **Prepare capture settings.** Open **Performance** and inspect **Capture settings**. Choose CPU and Network throttling deliberately; write the exact presets down. Enable screenshots only when visual correlation is needed. Keep JavaScript samples enabled when function-level attribution matters; disable them only to reduce trace size when broad browser/renderer activity is sufficient.
5. **Warm up, then capture only the scenario.** Let one run settle if the page has startup compilation or cache effects. Clear the old recording, start at a known state, perform the same actions, stop promptly, and repeat several times. A long trace containing unrelated idle time is harder to interpret and consumes more memory.
6. **Compare like with like.** Keep an unprofiled run and profiled runs under the same conditions. Profiling, screenshots, throttling, DevTools itself, and forced garbage collection can change scheduling and memory behavior. Treat a single trace as a lead, not a regression result.

For a load investigation, use **Record and reload** so the navigation is included in the trace. For a runtime investigation, use **Record**, then perform only the interaction under test. Save a trace only after confirming that its selected interval and settings represent the intended scenario.

### Agent-executable capture with the Browser tool

The DevTools panel instructions above are useful for a person, but an agent cannot open DevTools inside the Browser tool's page tab. Do not stop after telling the user to record a trace manually. When the page can be driven by the Browser tool, use a Chrome DevTools Protocol (CDP) session from Puppeteer's `page.createCDPSession()` and capture the scenario directly.

1. Open the target with the Browser tool and reach the deterministic starting state.
2. In one `browser.run` call, create a CDP session, start `Tracing`, perform the interaction, stop tracing, wait for `Tracing.tracingComplete`, and drain its `IO` stream.
3. Keep the trace in memory unless the user explicitly needs an artifact. Saved traces can contain sensitive data.
4. Report the browser version, URL/build, viewport, cache state, throttling, exact action, and whether `dataLossOccurred` was false.

Use this tested `browser.run` body as the starting point. Replace only the marked scenario and the analysis needed for the hypothesis:

```js
const client = await page.createCDPSession();
let tracingStarted = false;

try {
  const browserVersion = await client.send('Browser.getVersion');

  await client.send('Tracing.start', {
    transferMode: 'ReturnAsStream',
    streamFormat: 'json',
    traceConfig: {
      recordMode: 'recordAsMuchAsPossible',
      enableSampling: true,
      includedCategories: [
        'devtools.timeline',
        'v8.execute',
        'blink.user_timing',
        'disabled-by-default-devtools.timeline',
      ],
    },
  });
  tracingStarted = true;

  // Scenario: replace this selector/action and keep the capture bounded.
  await page.evaluate(() => document.querySelector('#work').click());
  await new Promise(resolve => setTimeout(resolve, 100));

  // Subscribe before Tracing.end so the completion event cannot be missed.
  const completed = new Promise(resolve => {
    client.once('Tracing.tracingComplete', resolve);
  });
  await client.send('Tracing.end');
  tracingStarted = false;

  const completion = await completed;
  if (completion.dataLossOccurred) {
    throw new Error('Trace buffer lost data; repeat with a shorter scenario');
  }
  if (!completion.stream) {
    throw new Error('Tracing completed without a result stream');
  }

  let traceJson = '';
  for (;;) {
    const chunk = await client.send('IO.read', {
      handle: completion.stream,
    });
    traceJson += chunk.data;
    if (chunk.eof) break;
  }
  await client.send('IO.close', {handle: completion.stream});

  const {traceEvents} = JSON.parse(traceJson);
  const completeEvents = traceEvents.filter(
    event => event.ph === 'X' && event.dur,
  );
  const totalMs = name =>
    completeEvents
      .filter(event => event.name === name)
      .reduce((sum, event) => sum + event.dur / 1000, 0);

  const evidence = {
    browser: browserVersion.product,
    traceEventCount: traceEvents.length,
    eventDispatchMs: totalMs('EventDispatch'),
    layoutMs: totalMs('Layout'),
    styleMs: totalMs('UpdateLayoutTree'),
    gcMs: totalMs('MinorGC') + totalMs('MajorGC'),
  };
  display(evidence);
  return evidence;
} finally {
  // A failed action must not leave browser-global tracing active.
  if (tracingStarted) {
    try {
      await client.send('Tracing.end');
    } catch {}
  }
  await client.detach();
}
```

The totals above are a smoke-test summary, not a complete diagnosis. Trace events are nested, so never add `EventDispatch`, JavaScript, style, and layout totals into one “total CPU” number. For a real investigation, restrict analysis to the operation's User Timing interval, identify the renderer main thread, rank complete events by duration/self-time, and inspect the event arguments and stacks that support the hypothesis. Use `performance.getEntriesByName()` only to corroborate a marker duration; it cannot replace the trace because it has no layout, paint, network, task, or call-stack attribution.

For **load profiling**, start tracing before `tab.goto(...)` or `page.goto(...)` in the same `browser.run` call, then wait for the agreed readiness condition before ending the trace. For **runtime profiling**, navigate and warm up first, then start tracing immediately before the action. Set cache and CPU/network emulation through CDP before capture when required, and repeat with identical settings.

If `Tracing.start` reports that tracing is already active, an earlier run failed without cleanup. Close and kill the Browser tool tab/process, reopen it, and repeat with the `try`/`finally` pattern above. If `tab.click()` times out on an otherwise present element during a synthetic fixture, use the normal observed element handle or `page.evaluate()` only when programmatic dispatch is an acceptable representation of the scenario; trusted pointer/input timing requires the real click path.

### Throttling and environment notes

- CPU throttling is relative to the machine running Chrome. A `4x slowdown` is not a real replica of a particular phone's CPU architecture, thermal state, scheduler, or GPU. Calibrate a custom preset when appropriate, and report the preset with the result.
- Network throttling approximates latency, throughput, and request behavior; it does not reproduce a carrier radio, packet loss, server queue, CDN, DNS, or all service-worker/cache behavior. Record cache state and explain whether the server was local, staging, or remote.
- Use throttling to expose bottlenecks and compare alternatives, not to claim a universal user experience. Validate important conclusions with field data such as real-user Web Vitals, CrUX, or application telemetry.
- Keep browser device emulation, viewport, DPR, orientation, and input method fixed. A desktop renderer under emulation is still not the same hardware as a mobile device.

## Add user-timing markers

Use the browser User Timing API to label the business operation in the trace. Marks and measures appear in the **Timings** track and let the operation be correlated with Main-thread work, screenshots, and network activity.

```js
performance.mark('search-start');
await runSearch();
performance.mark('search-end');
performance.measure('search', 'search-start', 'search-end');
```

For an event-driven flow, put the end mark in the callback or promise continuation that represents completion, not immediately after scheduling work. Use stable names plus an operation id when several instances overlap. Clear obsolete entries in a long-lived test page when appropriate (`performance.clearMarks()` / `performance.clearMeasures()`), and avoid logging sensitive input in marker names. A measure is elapsed page time; it does not by itself say how much time was CPU, network, rendering, or waiting. Inspect the corresponding trace interval.

## Performance panel: recording and analysis

### Record the smallest useful trace

1. Open DevTools on the target page and select **Performance**.
2. Set Capture settings, CPU/Network conditions, and the screenshot/JavaScript-sample options before starting.
3. Choose **Record and reload** for load work, or **Record** for a runtime interaction.
4. Reproduce the scenario once it reaches the agreed starting state, then stop immediately.
5. In the overview, drag-select the interesting interval. Use the **Main**, **Network**, **Frames**, **Timings**, and interaction tracks to connect cause and symptom. Do not infer a page problem from an unselected unrelated part of the recording.
6. Select an event to inspect its Summary, source location, initiator, and related details. Use the Call tree or Bottom-up views to rank inclusive work and self-time, then verify the largest entries in the trace itself.

Screenshots are useful for answering “which frame was late?” and connecting a layout/paint event to a visual change. They add capture overhead and size, so leave them off for CPU-only investigations unless the visual evidence is necessary.

### Read the overview and flame chart

The timeline is horizontal: width is elapsed time, and nested bars are work occurring within a parent event. A wide parent can contain several children; do not add parent and child durations as if they were independent. **Self-time** is work attributed to the selected function/event itself; **inclusive time** includes descendants. Sort or inspect both when deciding whether to optimize a leaf function or the caller that caused many descendants.

Start with the overview's CPU activity and frame cadence, then zoom to the slow interaction or frame. On the Main track, look for:

- **Long tasks and blocked frames.** A task over roughly 50 ms is a long task and can delay input, rendering, and other work. At 60 Hz a frame has about 16.7 ms, and at 120 Hz about 8.3 ms, before accounting for browser and compositor work. These are useful budgets, not guarantees that every task must fit exactly. Identify the task's top-level cause and its self-time rather than blaming the widest nested bar.
- **JavaScript and event handlers.** Repeated handlers, large synchronous loops, parsing/compilation, JSON work, and promise/microtask chains can monopolize the main thread. Correlate function names with the input event and User Timing mark; do not assume a function is slow merely because it appears often in a sampling view.
- **Style and layout.** Recalculate Style and Layout events indicate rendering work. Repeated DOM writes followed by layout reads can force synchronous layout (“layout thrashing”); inspect the stack and invalidated elements. A large layout may be legitimate for a large DOM, so compare the affected subtree and frequency, not only one duration.
- **Paint, raster, and compositing.** Paint and layer/compositor work can explain a visually late frame even when JavaScript is short. Use screenshots and the event details to distinguish expensive visual updates from main-thread scripting. The trace is not a complete GPU profiler; use a GPU-specific tool when GPU execution is the unresolved question.
- **Garbage collection.** GC events are pauses and evidence of allocation/collection activity, not automatically a leak. Frequent collections during an interaction suggest allocation churn or pressure; a large pause suggests collection cost. Compare heap after the operation has had time to settle. A baseline that rises after repeated equivalent cycles, especially after collection, is stronger leak evidence than one large temporary peak.
- **Network and scheduling.** A request's queueing, connection, wait, download, and subsequent parse/execute/render work are different costs. Follow the request to its initiator and then to the Main-thread work it unlocks. A slow request may be expected under the selected condition rather than a JavaScript defect.

The flame chart is a time-attribution view, not a proof of causality. Use event initiators, stack traces, screenshots, marks, and repeated captures to establish the order of cause and effect. Sampling may omit very short calls; a trace with JavaScript samples disabled cannot answer function-level CPU questions.

### Useful comparisons

- Compare the same selected interval before and after a change, under identical settings, input, cache state, and warm-up.
- Compare a cold-cache load and a warm-cache load separately; do not average them into one unexplained number.
- Compare unthrottled and throttled recordings to learn whether the bottleneck is CPU-sensitive or network-sensitive, but keep the two claims separate.
- For a suspected interaction regression, use the interaction/INP details and the trace's event-to-paint sequence, not only total page-load time.

## Memory panel: heap snapshots and allocation timelines

Open **Memory** and choose the capture type that matches the question. Memory captures can pause the page and require substantial memory, so use a bounded test page or test account and avoid taking them casually in production.

### Heap snapshots

Use **Heap snapshot** for point-in-time ownership and retention:

1. Take a baseline snapshot after the page reaches a known idle state.
2. Perform one bounded create/use/destroy cycle, or repeat the suspected operation a fixed number of times.
3. Return to the intended idle state and take a second snapshot. A third snapshot after another equivalent cycle is often more informative.
4. If the question is “what remains live?”, use DevTools' garbage-collection control between captures where available and record that intervention. Forced GC changes the workload; do not use it as evidence of normal user timing.
5. Use the comparison view to inspect new or growing constructors, then follow **retainers** toward GC roots. Sort by shallow size to find large objects and by retained size to find objects keeping subgraphs alive.

A shallow size is the object's own storage; retained size estimates what would become collectible if the object were released. A retained path through a global, event listener, timer, closure, cache, or framework registry is a lead to the ownership bug. Detached DOM nodes are suspicious only when they persist unexpectedly across equivalent teardown cycles. Caches and pools can be intentional; confirm the lifecycle and an expected upper bound before calling growth a leak.

A heap snapshot describes the JavaScript heap and related browser-visible objects at a point in time. It does not account for all native allocations, GPU memory, browser-process memory, network buffers, or another tab. Use process/OS telemetry and the appropriate native tool for those questions.

### Allocation instrumentation on timeline

Use **Allocation instrumentation on timeline** when the important question is *when* allocations occur and which call stacks produce them:

1. Start the allocation recording at a known idle point.
2. Perform the same interaction or repeated cycle.
3. Stop recording promptly and select the interval containing the spike.
4. Inspect allocation stacks and the objects that survive later collections. Correlate a surviving group with a heap snapshot if ownership is unclear.

A rising allocation rate can be harmless if objects are short-lived and collected efficiently. Conversely, a modest rate can leak if each cycle retains a reference. Distinguish temporary allocated bytes, live bytes, and retained bytes; they answer different questions. Allocation instrumentation has more overhead than a normal page run, so use it to explain a hypothesis and verify with a lighter repeat.

## Source maps and readable attribution

Enable JavaScript and CSS source maps in DevTools **Settings > Preferences > Sources** when the deployed assets have matching maps. Confirm that the map corresponds to the exact deployed bundle and release; a stale map can point at the wrong source line or hide the real chunk. With maps available, inspect original modules and source lines in the trace and heap allocation stacks. Without maps, minified bundle names and generated offsets are still evidence, but attribution must be checked against the build output.

Source maps can expose original source, paths, comments, and internal names to anyone who can fetch them. Keep private maps behind the approved access policy, use a sanitized staging deployment for shared investigation, and do not attach a map to a profile or issue tracker without checking its contents. Maps do not make a profile deterministic: inlining, code splitting, async boundaries, and sampling still affect what is visible.

## Artifacts, privacy, and production safety

Treat saved Performance traces, heap snapshots, and allocation profiles as sensitive diagnostics. Depending on the page and capture settings they may contain:

- URLs, query strings, origins, script paths, request/initiator metadata, and user-timing names;
- source locations and source-map content or identifiers;
- DOM text, object property strings, form data, cached application state, tokens, or other values reachable from the heap;
- console arguments, framework state, and names of users or records used in the scenario.

Before saving or sharing, use synthetic data and a test account, remove or redact sensitive inputs where possible, restrict artifact permissions, and follow retention/deletion policy. Do not commit traces or heap snapshots to the repository. Avoid uploading them to an unapproved third-party viewer. If the artifact cannot be safely sanitized, keep it in the authorized local evidence store and share only derived timings or a screenshot with sensitive text removed.

Do not profile a production session containing real user data merely because it is convenient. Prefer a representative staging build and a reproducible fixture. If production capture is explicitly approved, minimize scope and duration, disable unnecessary screenshots, protect the artifact, and document who may access it. Memory snapshots and forced GC can pause a tab and change behavior; they are particularly unsuitable for an unplanned live user session.

## Limits of lab captures

A DevTools trace is a controlled observation of one renderer, browser version, machine, workload, and set of emulated conditions. It is not a population-wide measurement. DevTools overhead, CPU/network emulation, warm caches, extensions, power/thermal state, browser scheduling, service workers, cross-origin frames, and server variance can all change the result. A lab trace is excellent for locating a causal chain and validating a fix under stated conditions; it cannot by itself establish field INP/LCP/CLS, battery impact, crash rates, or behavior on every device. Pair the trace with repeatable local measurements and real-user telemetry before making a production-wide claim.

## Completion checklist

- [ ] The question, URL/build, data fixture, viewport/device settings, cache state, Chrome version, and throttling presets are recorded.
- [ ] The capture type matches the question: runtime, load/reload, heap snapshot, or allocation timeline.
- [ ] The trace is bounded to the scenario and repeated under identical conditions.
- [ ] Main-thread self-time, long tasks, layout/paint work, GC, network dependencies, and user-timing marks were interpreted together.
- [ ] Memory conclusions are based on post-cycle retention and retainer paths, not a single heap peak.
- [ ] Source-map revision and access policy were checked before sharing attribution.
- [ ] Saved artifacts contain no unapproved secrets or personal data and are outside version control.
- [ ] The conclusion states the lab limitations and, where user impact matters, is checked against field data.
