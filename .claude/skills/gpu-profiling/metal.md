# Metal GPU profiling

## Metal debugger

**Use when:** the target is an Apple Metal workload and the question is command order, render/compute pass dependencies, resources, attachments, pipeline state, shader behavior, GPU timeline, or Apple GPU counters. The Metal debugger is part of Xcode and supports GPU frame capture/replay; it is the graphics API capture workflow for Metal.

**Xcode GUI capture:**

1. In the Run scheme, open **Edit Scheme > Run > Options** and set **GPU Frame Capture** to **Metal** (or **Automatically** when appropriate).
2. Run the app, click the **Metal Capture** button in the debug bar, select a frame/command queue/device/custom capture scope and count, and click **Capture**.
3. Inspect the replayed GPU trace: command buffers, encoders/passes, dependencies, attachments, resources, pipeline state, shader source, timeline, and counters. Export with **File > Export** when a `.gputrace` artifact is needed.

To capture a bounded workload from code, use `MTLCaptureManager` and `MTLCaptureDescriptor` around the desired command buffers. The capture destination can be a GPU trace (`.gputrace`) when supported. On macOS 14 and later, `MTL_CAPTURE_ENABLED=1` enables programmatic capture support; it has a small but measurable CPU effect, so keep it out of release builds.

**CLI trace inspection:** current Xcode versions provide the interactive `gpudebug` command for GPU traces:

```bash
gpudebug -t /path/to/Scene.gputrace
# At the gpudebug prompt, navigate and inspect a node:
# go commands/cb1/re0
# info pipeline
# fetch color0
```

The exact trace node paths depend on the capture; use `man gpudebug` and the tool's `list`/`go` commands rather than hard-coding paths. CLI replay is useful for scripted inspection and resource extraction, while Xcode is better for visual exploration and shader debugging.

**Interpretation:**

- Use the timeline to find long encoders, gaps, and pass dependencies; then inspect the command that owns the cost.
- Use counter statistics and per-line shader profiling only for the captured pass/command and the exact Apple GPU; counters are not portable across Apple GPU generations or to non-Apple GPUs.
- A frame capture can reveal incorrect attachments or state even when the performance symptom is elsewhere. Pair the capture with uninstrumented frame-time data.

**Overhead and limits:** frame capture and replay can add CPU work, memory, disk, synchronization, and shader instrumentation effects. The debugger may replay on a different device than the one that produced the trace unless configured otherwise. Capture only a small reproducible scope, record device/OS/Xcode versions, and do not use a capture-enabled build as the performance baseline.
