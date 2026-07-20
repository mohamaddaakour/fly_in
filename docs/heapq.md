```python
# heapq implements a priority queue (min-heap)

# the element with the min priority will be at the beginning
from heapq import heappop, heappush

queue = []

heappush(queue, (5, "A"))
heappush(queue, (2, "B"))
heappush(queue, (8, "C"))

print(queue) # [(2, 'B'), (5, 'A'), (8, 'C')]

print(heappop(queue)) # (2, 'B')
```