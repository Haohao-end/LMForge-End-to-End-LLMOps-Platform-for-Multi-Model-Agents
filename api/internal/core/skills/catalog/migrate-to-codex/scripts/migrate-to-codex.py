from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parent))

from cli import *  # noqa: F403,E402
from cli import main  # noqa: E402


if __name__ == "__main__":
    main()
