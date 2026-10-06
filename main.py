import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from house.ui.app_landscape import run


def main():
    run()


if __name__ == "__main__":
    main()
