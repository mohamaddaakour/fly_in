```python
# this function is used to parse arguments from the terminal
def build_parser() -> ArgumentParser:
    # we create the object argument parser
    parser: ArgumentParser = ArgumentParser(
        prog="fly-in",
        description="Route drones through connected zones.",
    )

    # here we will get an argument for the map_file
    # nargs-"?' means this positional argument may appear zero or one time
    # if the user didn't give any argument in the terminal by default it will
    # take the content inside maps/example.map file
    parser.add_argument(
        "map_file",
        nargs="?",
        default="maps/example.map",
        help="Path to a Fly-in map file.",
    )

    return parser
```

```python
# here we apply the parsing
args: Namespace = parser.parse_args()
```

```python
# here we create a path object for the path of map_file
# argument that we take it from the terminal argument
map_path: Path = Path(args.map_file)
```