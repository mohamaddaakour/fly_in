"""Command-line entrypoint for the Fly-in project."""

from fly_in.cli import main
import sys


if __name__ == "__main__":
    # exit will terminate the program
    # we can give it a status code (0 or 1)
    # 0 mean exit successfully without errors 1 mean exit with an error
    sys.exit(main())