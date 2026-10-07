"""Retired entry point. The oven run is run/oven_run.py.

Running this file does not open the oven port and does not program a
temperature profile. The lab account starts the oven with oven_board_01.bat.
"""


def main():
    raise SystemExit(
        "The oven is started by oven_board_01.bat. This file does not start the oven."
    )


if __name__ == "__main__":
    main()
