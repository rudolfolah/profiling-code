#!/usr/bin/env bash
source .venv/bin/activate

function run {
  echo 'Running' $1
  time python $1 > /dev/null
}

run program.py
run run_guppy3.py
run run_psutil.py
echo 'Running memray'
time memray run program.py > /dev/null
echo 'Running pyinstrument'
time pyinstrument program.py > /dev/null
echo 'Running cProfile'
time python -m cProfile -o profile.out program.py > /dev/null
run run_tracemalloc.py
run run_yappi.py
