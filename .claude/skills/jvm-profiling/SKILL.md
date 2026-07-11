# JVM Profiling with VisualVM and Java Flight Recorder

Use this skill when a Java application's CPU time, latency, allocation rate, garbage collection, heap growth, or thread contention needs evidence rather than guesses. It is deliberately independent of a build system: replace the example application command and output paths with the command used to launch the service.

## Choose the tool

- **VisualVM** is an interactive GUI for a quick look at one JVM: live heap and GC charts, thread states, sampled CPU/memory views, and heap dumps. Use it for exploratory diagnosis and for navigating an object graph.
- **Java Flight Recorder (JFR)** is the low-overhead event recorder built into modern JDKs. Use it for a bounded production investigation, startup or intermittent latency, GC/safepoint behavior, allocation rates, locks, and correlated JVM/OS events.
- **JDK Mission Control (JMC)** is the GUI for opening and analyzing `.jfr` recordings. It is especially useful when the problem happened in the past or on another host.
- A useful default sequence is: establish a baseline, collect a short JFR recording, then use VisualVM or a heap dump only when the evidence points to a live heap/object-graph question. Do not treat a profiler's percentage as a diagnosis by itself.

Official repository resources:

- [VisualVM](https://visualvm.github.io/) — the repository's VisualVM link.
- [Java Flight Recorder and JDK Mission Control](https://www.oracle.com/java/technologies/jdk-mission-control.html) — the repository's JFR/JMC link.
- The `jcmd` syntax and options are versioned with the JDK; use the documentation for the JDK actually running the target JVM (for example, the [JDK 25 `jcmd` reference](https://docs.oracle.com/en/java/javase/25/docs/specs/man/jcmd.html)).

## Before collecting data

1. Record the JDK vendor/version, JVM flags, host/container limits, PID, deployment version, and the workload window. Keep these with every profile.
2. Define one question and a short capture interval (for example, “why do requests pause for 90 seconds?”), and capture a comparable healthy interval if possible.
3. Use a JDK tool from the same release family as the target (`jcmd -l`, `java -version`). Local attach normally requires the same OS user or an explicitly permitted service account. Containers, PID namespaces, and hardened JVMs can hide or deny attach.
4. Create a private output directory with enough space and predictable ownership. Use absolute paths for recordings and dumps; avoid writing diagnostic files into an application's working directory or a world-readable temporary directory.

## VisualVM workflows

### Attach to an existing JVM

1. Start VisualVM and allow the **Local** applications list to populate. If the process is not listed, confirm the PID from the service supervisor/container and check user, namespace, and attach permissions.
2. Open the target JVM and first use its monitor/overview to establish heap usage, GC activity, thread count, and process CPU. Save a screenshot or note the baseline before changing anything.
3. Use **Sampler** first for a low-intrusion view. Start CPU sampling during the problematic workload and stop it after a fixed interval; save the snapshot. Repeat for a healthy interval with the same request mix.
4. Use the **Profiler** only when sampling does not identify the code path. Instrumentation can change timings and class behavior; limit the included packages/classes and capture briefly.
5. For a memory question, take a heap dump only at a planned point (and, for leak work, take two or more dumps after the same workload has run). Save the dump securely, then inspect classes, instance counts, shallow size, retained size, and reference paths. A heap dump is a point-in-time object graph, not an allocation history.
6. Inspect the thread view for state transitions and blocked/waiting threads. Capture a thread dump when a stall is occurring, and correlate it with the CPU and GC timeline rather than reading one thread in isolation.

### Start a JVM, then observe it

VisualVM does not need to be the process launcher. Start the application with its normal command, record the resulting PID, and attach using the workflow above. This is the safest way to preserve the normal startup path. If the application must be observed from the first instruction, launch it under the same account with its normal class path/options, then connect as soon as the PID appears; use JFR's startup option below when a deterministic startup recording is needed.

### Read VisualVM results

- A CPU sampler reports where samples landed, not exact invocation counts. **Self** time points to work in the method itself; **total/callee** time points to a subtree. Compare the same workload and look for a repeatable hot path, not a single top row.
- A large heap chart is not automatically a leak: the JVM may simply have reserved heap or be between collections. Look at post-GC occupancy and its trend. In a dump, shallow size is the object itself; retained size is what would become unreachable if that object were removed. Follow dominators and retaining references across repeated dumps.
- High allocation or object counts can cause GC pressure even when the live heap is small. A stable live set with high allocation churn is a different problem from a live set that grows after each equivalent workload.
- A thread marked waiting or sleeping may be healthy. Repeated `BLOCKED`/monitor contention, long waits on one lock, runnable threads with little CPU, or a cycle of lock ownership are stronger signals. Check whether the blocked thread is on the request-critical path.

## JFR and JMC workflows

JFR recordings are read in JMC. Keep the recording's JDK/JMC versions compatible, copy the `.jfr` file out of the host through an access-controlled channel, and open it in JMC's automated analysis plus event pages. `default.jfc` is intended for low-overhead, potentially continuous recordings; `profile.jfc` enables more detail and is better for a short investigation with more overhead.

### Attach to an already-running JVM with `jcmd`

Find the process and check whether a recording already exists:

```bash
jcmd -l
jcmd <PID> VM.command_line
jcmd <PID> JFR.check
```

Start a bounded recording using the JDK's low-overhead configuration:

Use a concrete, unique filename for each capture. JFR's `filename` option does **not** expand the `%p` and `%t` placeholders supported by unified JVM logging; passing those placeholders can make JVM startup fail. Generate the timestamp/PID in the shell, service manager, or deployment configuration before invoking `java` or `jcmd`. The filenames below are examples of already-expanded capture IDs.

```bash
jcmd <PID> JFR.start name=latency settings=default duration=90s filename=/secure/profiles/latency-20260710T120000Z-12345.jfr
jcmd <PID> JFR.check name=latency
```

`duration` lets the JVM close the recording and write the file without a second stop command. When the incident is event-driven and the end time is unknown, omit `duration`, then dump or stop it explicitly:

```bash
jcmd <PID> JFR.start name=incident settings=default
# Wait for the known failure or latency spike.
jcmd <PID> JFR.dump name=incident filename=/secure/profiles/incident-20260710T120000Z-12345.jfr
# Use JFR.stop instead when you want to finish the recording and release it.
jcmd <PID> JFR.stop name=incident
```

`JFR.dump` writes a snapshot while the recording continues; `JFR.stop` ends it. Do not use an unbounded recording without a disk/retention plan. For a short, higher-detail capture, use `settings=profile` and a small duration only after checking that the extra overhead is acceptable:

```bash
jcmd <PID> JFR.start name=short-profile settings=profile duration=30s filename=/secure/profiles/profile-20260710T120000Z-12345.jfr
```

If attach fails, do not repeatedly retry against a live production process. Check PID namespace and permissions, use the target JDK's `jcmd`, and consult the service/container's diagnostic policy. A restart may be required for startup-only flags or for a JVM that disallows attach.

### Start with a recording from JVM startup

Add a startup option to the normal Java launch command when startup, class loading, or an early failure matters:

```bash
java -XX:StartFlightRecording=name=startup,settings=default,duration=2m,filename=/secure/profiles/startup-20260710T120000Z.jfr <the-usual-java-options-and-application-command>
```

For a continuously available, bounded rolling window, configure retention and dump on exit. Check the path and disk budget before enabling it:

```bash
java -XX:StartFlightRecording=name=rolling,settings=default,maxage=1h,maxsize=512m,dumponexit=true,filename=/secure/profiles/rolling-20260710T120000Z.jfr <the-usual-java-options-and-application-command>
```

A startup option is part of process configuration: deploy it deliberately, verify the file is created, and remove it after the investigation if it is not an intentional baseline. Do not assume that a startup recording captures data from before the JVM was launched; it starts during JVM initialization.

### Interpret a recording in JMC

Start with the time range containing the symptom and correlate these views:

- **CPU/execution:** execution samples show where threads were observed running; compare Java method stacks with process/host CPU. A method with high wall-clock presence may be waiting or blocked, while a high-CPU stack is a stronger candidate for compute cost. Look for repeated application frames, not only framework dispatch.
- **Threads and locks:** inspect thread states, Java monitor blocked events, parks, waits, and thread dumps around the incident. Many blocked threads behind one owner indicate contention; many runnable threads with low host CPU can indicate scheduling or I/O rather than a CPU algorithm.
- **Garbage collection:** correlate young/old collection pauses, pause duration, heap occupancy before/after GC, allocation rate, promotion, and safepoints. Frequent short collections suggest allocation pressure; a rising post-GC live set suggests retention or an undersized workload window. A long pause can be GC, a safepoint operation, or an external stall—use the event type and thread stacks to distinguish them.
- **Memory/allocation:** JFR allocation events (including TLAB and outside-TLAB allocations where enabled) identify allocation sites and rates. They do not replace a full heap graph. Use VisualVM or a heap dump when the question is “what is retaining these objects?” rather than “where are they being allocated?”
- **Latency:** use event timestamps and duration, not just averages. A tail-latency spike should be aligned with thread blocking, GC/safepoint pauses, I/O, CPU saturation, or a deployment/configuration change.

## Overhead and production safety

- JFR's `default` configuration is designed for low overhead, but it is not free; stack depth, high-rate events, custom events, and `profile` settings increase CPU, memory, and disk use. Keep captures short, set `maxage`/`maxsize` for rolling use, and monitor the output filesystem.
- VisualVM sampling is generally less intrusive than instrumentation, but sampling still consumes CPU and can miss short-lived work. Instrumented CPU profiling can add substantial overhead and perturb lock scheduling, JIT compilation, and latency; never use its timings as production truth without a controlled comparison.
- Heap dumps and class histograms can pause the JVM, require significant disk, and expose object contents. Treat dumps as sensitive data: restrict permissions, encrypt in transit/storage, avoid collecting during the busiest interval unless the pause is acceptable, and delete them according to the incident-retention policy.
- JFR recordings contain stack traces, thread names, class/method names, and any values emitted by application/custom events. Restrict access and redact before sharing. Do not enable remote JMX or expose a profiler port without authentication, authorization, network controls, and TLS.
- Never run `jcmd` as an unreviewed “fix.” Profiling explains behavior; it does not repair a deadlock, leak, or overload. Record the exact command, start/stop time, PID, JDK, settings, workload, and observed impact so another engineer can reproduce the analysis.
- Stop when the question is answered, restore the normal launch configuration, verify that temporary recordings/dumps are no longer accumulating, and compare against a baseline or controlled reproduction before changing application code.
