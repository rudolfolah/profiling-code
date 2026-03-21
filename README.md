# profiling-code

Collection of examples and links that uses different profiling tools to show memory usage and timings.

Shows how to use the profiler and what the output looks like. Includes only tools that are maintained.

[awesome-profiling](https://github.com/msaroufim/awesome-profiling): Great list of profiling tools, though includes some tools for Python that are no longer maintained.

# ⚙️ Tools and Techniques for Profiling Code
- [Game Development: C#, Unity, Godot](./gamedev/README.md)
- [Node.js: JavaScript, TypeScript](./javascript/README.md)
- [Python](./python/README.md): examples using cProfile, guppy3, psutil, memray, pyinstrument, tracemalloc, yappi, filprofiler, DTrace
  - [Python 3.12 support for the Linux perf profiler](https://docs.python.org/3/howto/perf_profiling.html)
  - [pyperformance - Python Performance Benchmarking Suite](https://github.com/python/pyperformance)
- [gprof: GNU Profiler](https://sourceware.org/binutils/docs/gprof/)
- [Tracy Profiler](https://github.com/wolfpld/tracy): supports C, C++, Lua, Python with 3rd party bindings for Rust, Zig, C#
- [valgrind](https://valgrind.org/info/tools.html)
  - [memcheck](https://valgrind.org/docs/manual/mc-manual.html): memory error detection
  - [cachegrind](https://valgrind.org/docs/manual/cg-manual.html): CPU cache profiling
  - [callgrind](https://valgrind.org/docs/manual/cl-manual.html) is cachegrind with a call graph and branch prediction profiler
  - [massif](https://valgrind.org/docs/manual/ms-manual.html) for heap profiling
- [Apple Instruments](https://help.apple.com/instruments/mac/current/)
- [VisualVM](https://visualvm.github.io/): Java profiling tool
- [Java Flight Recorder and JDK Mission Control](https://www.oracle.com/java/technologies/jdk-mission-control.html): Java profiling tool

## 🧰 GPU Profiling Tools
- [NVIDIA Visual Profiler](https://developer.nvidia.com/nvidia-visual-profiler)
- [NVIDIA Nsight Systems](https://developer.nvidia.com/nsight-systems)
- [NVIDIA Nsight Compute](https://developer.nvidia.com/nsight-compute)
- [Android GPU Inspector (AGI)](https://developer.android.com/agi)
- [Metal debugger](https://developer.apple.com/documentation/xcode/metal-debugger)
- [AMD uProf](https://www.amd.com/en/developer/uprof.html)
- [Intel VTune Profiler](https://www.intel.com/content/www/us/en/developer/tools/oneapi/vtune-profiler.html)

# 📚 Learning Resources
## 📖 Books
* ["BPF Performance Tools", Brendan Gregg](https://www.brendangregg.com/bpf-performance-tools-book.html)
* ["Systems Performance: Enterprise and the Cloud, 2nd Edition", Brendan Gregg](https://www.brendangregg.com/systems-performance-2nd-edition-book.html)

## 📰 Articles
* ["All my favorite tracing tools: eBPF, QEMU, Perfetto, new ones I built and more", Tristan Hume](https://thume.ca/2023/12/02/tracing-methods/)
* ["Flame Graphs: The future of performance analysis", Brendan Gregg](https://queue.acm.org/detail.cfm?id=2927301)
* ["Flame Graphs", Brendan Gregg](https://www.brendangregg.com/flamegraphs.html)
* ["Sampling v. tracing", Dan Luu](https://danluu.com/perf-tracing/)
* [Memory and CPU profiling, "The Hacker's Guide to Scaling Python", Julien Danjou](https://www.educative.io/courses/hackers-guide-scaling-python/memory-and-cpu-profiling)
* [ebpf-apps](https://github.com/feiskyer/ebpf-apps): sample apps for eBPF for C, C++, Python, Go, and Rust.

## 📺 Videos
- [Python profiling and performance tuning in production](https://www.youtube.com/watch?v=B9Kv3Fije1I)
- [Memray: The endgame Python memory profiler](https://www.youtube.com/watch?v=wn_2e33KaYQ)
- [GopherCon 2021: Go Profiling and Observability from Scratch](https://www.youtube.com/watch?v=7hg4T2Qqowk)
- [eBPF](https://ebpf.io/)
  - [A Beginner's Guide to eBPF Programming with Go](https://www.youtube.com/watch?v=uBqRv8bDroc)
  - [eBPF: Fueling New Flame Graphs & more](https://www.youtube.com/watch?v=HKQR7wVapgk)
  - [Kernel Analysis Using eBPF](https://www.youtube.com/watch?v=AZTtTgni7LQ)
