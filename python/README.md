# Python Profiling

## Setup

```bash
pyenv install $(cat .python-version)
pyenv local
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

Run the following to show the timings of the different profiling methods:

```
$ ./timing.sh
```

Here are the results of the timing from one run:

| Method       | Real Time | User Time | System Time |
|--------------|-----------|-----------|-------------|
| No profiling | 0m0.344s  | 0m0.157s  | 0m0.017s    |
| guppy3       | 0m0.525s  | 0m0.343s  | 0m0.018s    |
| psutil       | 0m0.349s  | 0m0.149s  | 0m0.016s    |
| memray       | 0m0.686s  | 0m0.360s  | 0m0.065s    |
| pyinstrument | 0m0.496s  | 0m0.310s  | 0m0.024s    |

### [cProfile](https://docs.python.org/3/library/profile.html#module-cProfile)

```
$ python -m cProfile -o profile.out program.py

$ python -m pstats profile.out
profile.out% sort cumulative
profile.out% stats 10
```

### [Memray](https://bloomberg.github.io/memray/overview.html)

```
$ memray run program.py
$ memray flamegraph memray-program.py.*.bin
$ open memray-flamegraph-program.py.*.html
```

### [psutil](https://psutil.readthedocs.io/en/latest/)

```
$ python run_psutil.py
```


### [guppy3](https://github.com/zhuyifei1999/guppy3)

```
$ python run_guppy3.py
```
