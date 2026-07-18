# py-spy: external sampling and flame graphs

`py-spy` appears in `python/requirements.txt` as version `0.3.14`, but the repository README and `timing.sh` do not provide a py-spy run. The following are CLI examples for the installed dependency; they do not replace the repository's exact commands above.

Launch and record the target in one command:

```bash
py-spy record -o profile.svg -- python program.py
```

This writes an interactive SVG flame graph. The `--` separates py-spy's options from the target command. To watch a live summary instead:

```bash
py-spy top -- python program.py
```

To inspect a process that is already running, first obtain the PID from a process you own and then use:

```bash
py-spy top --pid <PID>
py-spy dump --pid <PID>
py-spy record -o profile.svg --pid <PID>
```

`top` is useful for a long-lived process; `dump` is useful for a one-time stack snapshot, such as diagnosing a hang. `program.py` is short and performs one request, so a launched `record` run is generally more useful than trying to attach after it has already exited.

A flame graph's horizontal width is proportional to sampled time, not to exact invocation count. Read from the bottom (the process/thread root) upward: broad branches are the stacks that occupied the most samples; narrow branches may still be important if they are latency-sensitive or under-sampled. A missing short function is expected with sampling. The default view attempts to omit idle threads, so a missing network wait should not be interpreted as proof that no wall time was spent waiting. Use pyinstrument or yappi with `wall` when blocked time is the question.

For a process that creates Python child processes, ask py-spy to follow them when supported by the installed version:

```bash
py-spy record --subprocesses -o profile.svg -- python program.py
py-spy top --subprocesses -- python program.py
```

Without `--subprocesses`, a parent profile does not automatically explain work done in a child interpreter. `cProfile`, pyinstrument, and yappi similarly require profiling code in each child or a separately launched profiler; do not assume that an in-process profile covers multiprocessing workers.

## Permission and safety caveats

py-spy reads another interpreter's memory from outside the target process, which is why it has low in-process overhead but also why OS security rules matter. On macOS, attaching commonly requires root; on Linux, attaching to an unrelated PID can require root or ptrace permission. If a PID attach fails with an access/permission error, first prefer the launched form (`py-spy ... -- python program.py`) for a process you own. If the OS still requires elevation, rerun only the specific command with `sudo` and use an explicit path so the intended installed binary is selected, for example:

```bash
sudo "$(command -v py-spy)" record -o profile.svg -- python program.py
```

Do not attach to an unrelated process or use `sudo` to bypass a policy without authorization. A root-run target may have different environment, proxy, file permissions, and output ownership, so record that fact with the profile. `--locals` (where supported) can expose application data; avoid it for this target unless the data is safe to disclose.
