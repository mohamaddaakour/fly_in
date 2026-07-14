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