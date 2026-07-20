- An enum (short for enumeration) is a way to define a fixed set of named constant values.

```python
class ZoneType(str, Enum):
    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"
```

```python
# Convert the enum to a string.
ZoneType.NORMAL.value
```