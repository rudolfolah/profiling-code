# gprof (GNU Profiler)

**When to use:** a simple CPU flat profile and estimated call graph for a native executable when rebuilding with compiler instrumentation is acceptable. It is useful for batch programs and a quick first pass, not for low-perturbation production measurements, precise wall-clock latency, or modern asynchronous/thread-heavy workloads.

**Build and capture:**

```bash
# Compile and link every relevant object with -pg (not only the final link).
cc -O2 -g -pg -o app main.c other.c
./app < fixed-input > /dev/null
# The process normally writes gmon.out on normal exit in its working directory.
gprof -b ./app gmon.out > gprof.txt
# Optional focused reports:
gprof -p ./app gmon.out       # flat profile
gprof -q ./app gmon.out      # call-graph profile
```

For a multi-file build, apply `-pg` consistently to compilation and linking, and place each run's `gmon.out` in a separate directory. A crash, `_exit`, or forced termination may prevent the profile from being written. If the executable forks, consult the platform's gprof documentation for how child output is handled rather than assuming one complete file.

**Read the output:** the flat profile reports sampled time and the number of calls attributed to functions; the call-graph section reports callers, callees, and propagated time. Timer samples estimate time, while call counts/edges come from `mcount`-style instrumentation. “Self” time is work in that function; propagated/children time includes descendants. A high call count with little self time may still matter through allocation, locking, or cache effects. Missing symbols or aggressive inlining can collapse work into a parent or show `??`; verify the binary and debug information before acting.

**Costs and limitations:** `-pg` changes every instrumented call and can materially alter short functions, recursion, synchronization, and cache layout. Timer resolution is platform-dependent; percentages are statistical. gprof's call graph is a poor fit for threads, signals, JIT code, and event-loop latency, and support depends on the GNU binutils build. It is primarily a Unix-like native tool; it is not a native Windows workflow. Prefer perf or Instruments for low-overhead sampling and Tracy or targeted tracing for event timing.

Official documentation: [GNU gprof](https://sourceware.org/binutils/docs/gprof/).
