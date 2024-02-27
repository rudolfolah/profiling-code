import tracemalloc

from program import main

tracemalloc.start()

snapshot1 = tracemalloc.take_snapshot()
main()
snapshot2 = tracemalloc.take_snapshot()
top_stats = snapshot2.compare_to(snapshot1, "lineno")
print("[ Top 10 differences ]")
for stat in top_stats[:10]:
    print(stat)
