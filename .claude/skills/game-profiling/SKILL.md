---
name: game-profiling
description: Profile Unity and Godot frame hitches, low frame rates, allocations, retained memory, rendering cost, and project-wide performance risks with reproducible captures.
---

# Game Development Performance Profiling Skill

Use this skill when investigating frame hitches, low frame rate, memory growth, allocation spikes, rendering cost, or project-wide performance risks in Unity or Godot. Treat a profiler capture as evidence: preserve the workload and environment, separate measured facts from hypotheses, and recommend one change at a time so that a before/after capture can verify the result.

## Start with a reproducible question

Before opening a tool, ask for (or record):

- engine and package versions, target platform/device, graphics API, build configuration, and commit/build identifier;
- target frame rate and frame budget (`1000 / target FPS` ms: 16.67 ms at 60 FPS, 33.33 ms at 30 FPS);
- exact scene, player input, camera, quality settings, resolution, VSync/frame cap, and a short step-by-step reproduction;
- whether the symptom is a sustained low rate, an intermittent hitch, a memory/GC increase, or a visual/rendering issue.

Prefer a Development/Profiling player on the target hardware over the Editor. Keep the same quality, resolution, refresh rate, renderer, scripting backend, and asset data as the reported scenario. Warm up loading and shaders, then record a short steady-state window and repeat the scenario several times. Clarify whether a reported hitch duration is the total frame time, time over budget, or an added stall. For sustained workloads, compare like-for-like frame-time distributions. For event-triggered hitches, define a fixed event window and report the trigger frame or maximum frame per trial, the individual values, median, and sample count; report a tail percentile only when enough repeated events make it meaningful.

## Choose the tool

| Question | First tool | What it can establish | Important boundary |
| --- | --- | --- | --- |
| Which thread, system, script, physics step, or wait makes a frame slow? | [Unity Profiler](https://docs.unity3d.com/6000.1/Documentation/Manual/Profiler.html) | Runtime CPU/GPU frame timeline, hierarchy, markers, worker threads, and allocation samples | A marker's cost and a tool's instrumentation overhead are not the same as production cost; Editor data is not a device measurement |
| Where does memory go, what remains reachable, or what grows after repeated loads? | [Memory Profiler](https://docs.unity3d.com/Packages/com.unity.memoryprofiler@latest) | Point-in-time Unity memory snapshots and comparisons across managed/native and other supported categories | A snapshot is not a per-frame allocation trace; capture can pause or materially perturb the player, and support/details vary by platform/package version |
| Which draw calls and rendering events build a frame, and why are batches/pass count high? | [Frame Debugger](https://docs.unity3d.com/6000.1/Documentation/Manual/FrameDebugger.html) | Ordered rendering events, state changes, draw-call/batching decisions, and the visible result at an event | It explains *what* was submitted, not reliable GPU milliseconds, bandwidth, or shader occupancy; use a platform GPU tool when those are the question |
| Which project settings, assets, or serialized/static patterns are risky before runtime? | [Project Auditor](https://docs.unity3d.com/Packages/com.unity.project-auditor@1.0/manual/index.html) | Static rules, findings, severities, and project-wide configuration/asset/API checks | It cannot prove a runtime hotspot, actual device frame time, or that every finding matters to this game |
| Is a Godot script, process/physics step, frame metric, or renderer counter abnormal? | [Godot Profiler](https://docs.godotengine.org/en/stable/tutorials/scripting/debug/the_profiler.html) | Script function timings plus the Debugger Profiler and available frame/process/physics/rendering/memory monitors | Monitor names and availability vary by Godot version/renderer; script profiling does not account for all engine or GPU work |

## Unity Profiler: CPU/frame timing and allocations

Use the Unity Profiler first for a runtime symptom.

1. Attach to or launch the same player/device and select the relevant modules (CPU Usage, GPU Usage where supported, Rendering, Memory, and related modules). Record the scenario after warm-up; do not profile an idle menu and generalize to gameplay.
2. In the CPU Usage timeline, find the long frame(s), then compare Main Thread, Render Thread, Jobs/worker threads, and waits. Switch between Timeline and Hierarchy: use Timeline to understand overlap/order and Hierarchy to aggregate self time and total time by marker. Follow a marker to its caller and the work it invokes rather than optimizing a broad parent label.
3. Compare the frame time with the target budget. A busy main thread over budget is a CPU bottleneck; a render/GPU path over budget points toward rendering or GPU work. `WaitForTargetFPS`, `Present`, or a similar wait may be a frame cap or back-pressure, not a slow game system. CPU and GPU can overlap, so do not add their times as if they were serial without evidence.
4. Look for repeated `GC.Alloc` in the exact workload and correlate it with managed-GC pauses. Distinguish a transient allocation from retained memory: the Profiler allocation sample says when managed allocation occurs, while Memory Profiler snapshots show what remains reachable. Confirm a suspected fix by running the same scenario and checking both allocation rate and hitch distribution.
5. Use markers, custom profiling samples, and a narrow time range to make a hypothesis testable. Deep Profile can expose call detail for a small reproduction, but it changes timings and can create substantial overhead; turn it off for the baseline and final validation.

The Profiler may show Editor overhead, synchronization waits, profiler transport cost, or a different graphics path from a player. On-device captures and a non-profiled confirmation build are required before treating a small regression as real.

## Unity Memory Profiler: snapshots and allocation investigations

Use the [Memory Profiler](https://docs.unity3d.com/Packages/com.unity.memoryprofiler@latest) when memory grows, a load/unload cycle leaks, an out-of-memory failure is suspected, or asset duplication is expensive.

1. Establish a repeatable lifecycle: capture after a clean boot, after the first load, after the target scene/action, and after the same unload/reload cycle. Keep the player state and cache/warm-up policy consistent. Name captures with build, device, scene, and lifecycle step.
2. Capture a baseline and a suspect snapshot, then compare them. Inspect managed objects, native Unity objects, textures/meshes/asset data, and other categories exposed by the package. For a candidate object, follow references and ownership to determine whether it is retained intentionally, held by a static/event/cache reference, duplicated by bundles, or simply still in a legitimate cache.
3. Pair snapshots with Unity Profiler `GC.Alloc` and Memory module evidence. A larger snapshot does not automatically mean a leak, and a low managed heap does not rule out native or graphics memory pressure. Verify that a repeated cycle returns to a stable range rather than relying on one before/after difference.
4. After changing load/unload, pooling, asset import, or references, repeat the same lifecycle and compare snapshots again. Keep the largest captures outside source control unless the project explicitly manages them; they can contain sensitive scene names, paths, and large binary data.

Snapshot capture can pause the player, consume substantial memory/storage, and alter timing. Do not use a snapshot's pause duration as the game's hitch time. Check package/platform support and compare captures made under the same Unity and Memory Profiler versions.

## Unity Frame Debugger: rendering passes and draw-call decisions

Use the [Frame Debugger](https://docs.unity3d.com/6000.1/Documentation/Manual/FrameDebugger.html) after runtime evidence points at rendering, excessive draw calls, overdraw, state changes, or an unexpected pass.

1. Reproduce one deterministic view (camera, resolution, quality, lights, and frame index). Pause on the relevant frame and open the Frame Debugger event list. Step through the ordered events from clears and shadow/depth work through opaque/transparent objects, post-processing, UI, and final presentation as applicable.
2. For a suspicious event, inspect the source renderer/material/shader, pass, render target, keywords, state changes, and batching/instancing decision. Identify why a batch split occurs (for example, material/state/mesh/light/shadow differences) instead of assuming that reducing object count alone will help.
3. Record the event/draw/pass pattern and the visual change at the event. Test a targeted change (material sharing, batching/instancing eligibility, culling, resolution, shader/pass selection, or an unnecessary effect), then capture the same view again. A smaller event list is useful evidence, but verify frame time on the target GPU.
4. Use a GPU timing/counter tool appropriate to the platform when the question is GPU milliseconds, bandwidth, shader occupancy, tiler behavior, or thermal throttling. The Frame Debugger is a submission/event inspection tool, not a substitute for hardware GPU timing.

Pausing, attaching, and displaying events can change resource lifetime and timing. Editor rendering, Game view scaling, and debug visualization can differ from a player. Keep the camera and frame selection fixed; never compare unrelated frames just because they contain the same object.

## Unity Project Auditor: project/static analysis

Use [Project Auditor](https://docs.unity3d.com/Packages/com.unity.project-auditor@1.0/manual/index.html) for a project-wide preflight, regression check, or when runtime profiling suggests a broad configuration/asset issue.

1. Run the Auditor against the same project revision and package configuration used for the build. Start with all relevant analyzers/categories, then filter by severity, platform, category, and location to make the report actionable.
2. Triage each finding: understand the rule and affected asset/setting/API, verify that it applies to the target platform and shipping configuration, and record a minimal remediation. High severity is a prioritization signal, not proof of an observed frame cost.
3. Fix one class of issue at a time, rerun the audit, and keep the report with the commit/build metadata. If a finding is expected, document the reason and ensure it does not hide a newly introduced finding. Validate performance-related fixes with a Unity Profiler or device test; validate memory/rendering fixes with the corresponding runtime tool.

Auditor is static analysis: it can find risky import settings, serialized data, project configuration, and API/usage patterns without running gameplay, but it cannot see runtime frequency, actual frame overlap, dynamic content, or hardware-specific GPU behavior. Rules and package output can change with Unity/package versions.

## Godot Profiler: script timing and frame monitors

Use the [Godot Profiler](https://docs.godotengine.org/en/stable/tutorials/scripting/debug/the_profiler.html) for a Godot runtime symptom.

1. Run the target scene or build with the same renderer, resolution, VSync/frame cap, quality, and device as the report. In the Debugger, record a short, repeatable scenario with the Profiler, then stop recording before inspecting it. Use the function list/call tree to compare self time (work in that function) with total time (including called functions), and separate script process work from physics/process work where the version exposes it.
2. Check the Profiler's frame monitors during the same window. Correlate frame time/FPS with available `Process`, `Physics Process`, rendering counters such as draw calls, objects, and primitives, pipeline-compilation counters where available, and memory/video-memory counters. Preserve the exact labels because monitor sets differ by Godot release and renderer. Record each monitor's observed update cadence: values sampled every frame may repeat a slower-updating value and are not independent samples, so do not derive frame-time percentiles from duplicated monitor readings. Use Profiler frame samples or direct frame timestamps for per-frame distributions. Rendering counters show that submitted work changed; they are not GPU timings, bandwidth, occupancy, or proof of a GPU bottleneck.
3. For a rendering symptom, make a controlled A/B capture in one warmed build: keep the camera, scene, resolution/render scale, quality, VSync/frame cap, renderer/API, and effect state deterministic, then compare fixed windows with only the suspect effect disabled versus enabled. If script/process evidence does not explain the frame-time change, record the target OS, GPU, renderer, and graphics API before selecting a compatible platform GPU tool. Preserve the existing renderer/API rather than switching APIs for capture.
4. Use that GPU tool to collect supported GPU timestamps or hardware counters when the question is GPU milliseconds, fill/fragment cost, bandwidth, or occupancy. A frame debugger's pass/event list and draw count remain submission evidence, not GPU-cost evidence. Repeat intermittent hitches; do not conclude from first-use shader or pipeline compilation, and do not micro-optimize scripts merely because total frame time is high.
5. Confirm a suspected change with the game's own frame metrics in a non-profiled run. The Godot script Profiler alone cannot identify every render pass or account for all engine and GPU work.

Profiler recording and remote inspection add overhead and can perturb short frames. The Editor and a running export may differ. Treat `await`/idle, draw, physics, and synchronization time according to the version's labels, and preserve the exact Godot version, renderer, monitor names, and capture settings with the result.

## Capture hygiene and reproducibility

- Prefer a player/export on target hardware. If only the Editor is available, label it explicitly and do not present it as device evidence.
- Keep VSync, frame caps, refresh rate, resolution, dynamic resolution, quality, power mode, thermal state, and background apps consistent. Record when a cap is intentionally enabled.
- Warm up shaders, caches, scene streaming, and asset loading. Exclude startup/loading frames when investigating steady-state gameplay, but capture them separately for load-time problems.
- Record a short named interval around the symptom, repeat at least three times when practical, and retain the raw capture/snapshot plus metadata (engine/package versions, commit, build type, device/OS, renderer/API, scene, action, and settings).
- Give automated captures both a deterministic frame/event limit and a wall-clock timeout. Fail loudly and label the capture incomplete if either limit is exceeded; never let a benchmark or unattended player run indefinitely.
- Disable unrelated Editor windows, gizmos, logging, breakpoints, and visual debug overlays. Avoid Deep Profile or extra monitors for the baseline; use them only in a targeted diagnostic capture.
- Never infer a leak from one larger snapshot, a GPU bottleneck from draw-call count alone, or a CPU bottleneck from a single frame. Compare like-for-like captures and validate the proposed fix in a non-profiled run.
- Keep captures reproducible and safe to share: scrub sensitive paths/project names where required, avoid committing large binary snapshots by default, and do not alter production settings solely to make a profiler capture look better.

## Practical triage for Claude

1. Ask whether the report is CPU/frame timing, allocation/memory, rendering submission/passes, static project risk, or Godot frame-monitor behavior; select the narrowest first tool.
2. Request the target build/device and a capture around the exact reproduction. If no capture exists, give the user a deterministic capture recipe rather than guessing from code or object counts.
3. Translate observations into a bounded hypothesis: e.g. “Main Thread exceeds 16.67 ms during the spawn step,” “managed allocations recur every frame,” “a transparent effect adds repeated passes,” “native texture memory remains after reload,” or “the Auditor flags platform-inappropriate import settings.”
4. Recommend one change, then repeat the same capture and report the measured delta, regressions, and remaining budget. Keep static findings separate from runtime proof and keep Frame Debugger event counts separate from GPU timing.

## Repository links

- [Unity Profiler](https://docs.unity3d.com/6000.1/Documentation/Manual/Profiler.html)
- [Memory Profiler](https://docs.unity3d.com/Packages/com.unity.memoryprofiler@latest)
- [Frame Debugger](https://docs.unity3d.com/6000.1/Documentation/Manual/FrameDebugger.html)
- [Project Auditor](https://docs.unity3d.com/Packages/com.unity.project-auditor@1.0/manual/index.html)
- [Getting started with Unity Project Auditor video](https://www.youtube.com/watch?v=8QQG0J624LY)
- [Ultimate Guide to Profiling Unity Games](https://unity.com/resources/ultimate-guide-to-profiling-unity-games)
- [Unity Profiler Walkthrough & Tutorial](https://www.youtube.com/watch?v=xjsqv8nj0cw)
- [Memory Profiler Walkthrough & Tutorial](https://www.youtube.com/watch?v=Uuzd39AjFWQ)
- [Godot Profiler](https://docs.godotengine.org/en/stable/tutorials/scripting/debug/the_profiler.html)
- [Locate Performance Issues Using Godot's Profiler](https://www.youtube.com/watch?v=eafdNo1kMA8)
