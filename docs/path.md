```python
# we create a path object
map_path: Path = Path(args.map_file)

# to check if this path exists (not None)
# will check does maps/example.map exist from the current working directory
if map_path.exists():

# this will check if this is a file
if map_path.is_file():
```

```python
# this will read the content of this file using the read_text method and then split each line and put
# it as an elemnt in this list using the splitlines method
lines: list[str] = path.read_text(encoding="utf-8").splitlines()
```