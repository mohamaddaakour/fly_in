```python
# always any regular class method should take as
# a first parameter keyword self
def parse_zone(self, line_number: int) -> Zone:


# and if we want to call a method inside the class
# we should use self keyword

self.parse_zone(line_number)
```