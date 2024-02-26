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
