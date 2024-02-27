import yappi

from program import main

yappi.set_clock_type("cpu")
yappi.start()
main()
yappi.get_func_stats().print_all()
yappi.get_thread_stats().print_all()
print(f"Memory usage {yappi.get_mem_usage()}")
yappi.get_thread_stats().print_all()
