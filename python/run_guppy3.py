from guppy import hpy

from program import main


print('Initial')
h = hpy()
print(h.heap())
main()
print('After')
print(h.heap())
