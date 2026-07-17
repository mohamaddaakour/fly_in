```python
import sys

# to exit the program with the specific status code
# status code 1 means exit because an error
# status code 0 means exit without error
sys.exit(main())
```

```python
# to create a set
_ZONE_KEYS: set[str] = set(["zone", "color", "max_drones"])
```

```python
@dataclass(frozen=True)
class Connection:
    zone_a: str
    zone_b: str
    max_link_capacity: int

    # @property creates a read-only computed attribute
    # so we can call the function without using the ()
    # example: connection.name
    @property
    def name(self) -> str:
        return f"{self.zone_a}-{self.zone_b}"
```

```python
# we create a new exception type
class ParseError(Exception):
    """Raised when a Fly-in map file contains invalid syntax."""

# we can use it later like that
raise ParseError(f"Could not read map file: {error}")
```

```python
# this is a built in method to check if this string starts with
# nb_drones:
if not line.startswith("nb_drones:")
```

```python
# removeprefix() removes a string only if it appear
# at the beginning (prefix) of another string
line.removeprefix("nb_drones:".strip())
```

```python
# ternary operator
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