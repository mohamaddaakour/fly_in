```python
# using @dataclass a constructor for this class will automatically be created
# frozen=True means after you create the object, you cannot change its fields
@dataclass(frozen=True)
class Zone:
    name: str
    x: int
    y: int
    zone_type: ZoneType
    color: str
    max_drones: int
    is_start: bool = False
    is_end: bool = False
```

```python
@dataclass
class Drone:
    # here int is immutable so when we use @dataclass
    # we can give it an initial value
    transit_turns_remaining: int = 0

    # but list is mutable so when we use @dataclass we can't
    # give it an initial value so instead we use this field
    # that will create an empty list by default
    assigned_path: list[str] = field(default_factory=list)
```