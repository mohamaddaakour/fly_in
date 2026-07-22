```python
import sys

# This is the entry point.
if __name__ == "__main__":
    # exit keyword will terminate the program
    # we can give it a status code (0 or 1)
    # 0 mean exit successfully without errors 1 mean exit with an error
    sys.exit(main())
```

```python
# Create a new exception type.
class ParseError(Exception):
    """Raised when a Fly-in map file contains invalid syntax."""

# We can use it later like that.
raise ParseError(f"Could not read map file: {error}")
```

```python
# this is a built in method to check if this string starts with
# nb_drones:
if line.startswith("nb_drones:")
```

```python
# removeprefix() removes a string only if it appear
# at the beginning (prefix) of another string
line.removeprefix("nb_drones:".strip())
```

```python
# Ternary operator.
0 if zone.zone_type == ZoneType.PRIORITY else 1
```

```python
string: str = "hello"

# count is a built in method to count how many characters
# we have in the string
print(string.count("l")) # 2
```

```python
string: str = "hello"

# index is a built in method to give us the index
# of a specific character (first occurence)
print(string.index("l")) # 2
```

```python
# when we put values inside of { } instead of keys and values
# we create a set not a dictionary
arr = {1, 2, 3}

print(type(arr)) # <class 'set'>
```