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

### cProfile

```
$ python -m cProfile -o profile.out program.py

$ python -m pstats profile.out
profile.out% sort cumulative
profile.out% stats 10
```

### Memray

```
$ memray run program.py
$ memray flamegraph memray-program.py.*.bin
$ open memray-flamegraph-program.py.*.html
```

### psutil

```
$ python run_psutil.py
```
