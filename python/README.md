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

```bash
python -m cProfile -o profile.out main.py
```
