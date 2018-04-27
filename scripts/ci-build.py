#! python3
"""
ci-vulnscan script which is executed with the bundle compiler
"""
# pylint: disable=C0103
from compile import build_main

if __name__ == "__main__":
    # execute only if run as a script
    build_main()
