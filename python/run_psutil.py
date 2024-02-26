import psutil

from program import main


p = psutil.Process()
print('Initial')
print(p.cpu_times())
print(p.memory_info())
main()
print('After')
print(p.cpu_times())
print(p.memory_info())
