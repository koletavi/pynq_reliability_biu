"""Which PYNQ-Z2 cards to run, and where their results are stored.

The oven recipe (temperatures, hold times, and the wait between samples)
stays in run/config.py. Add another card by appending one entry to BOARDS.
Set enabled to False to leave a card in the list without starting it.

The oven run measures only the boards named on its command line. A named
board is started even when enabled is False. An enabled board that is not
named is not started.
"""
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent

# Results land inside the repo by default. On the lab PC, point this at the
# shared data folder instead, for example Path(r"C:\pynq\pynq_data").
OUTPUT_ROOT = REPO_ROOT / "data"
TEMPERATURE_DIR = OUTPUT_ROOT / "temperature_data"
BOARDS_ROOT = OUTPUT_ROOT / "boards"
OVEN_READ_DIR = OUTPUT_ROOT / "oven_reads"

USERNAME = "xilinx"
PASSWORD = "xilinx"

REMOTE_NOTEBOOK_DIR = "/home/xilinx/jupyter_notebooks/rofc/"
NOTEBOOKS = [
    ("rofc_11.ipynb", "output_data_11.csv"),
    ("rofc_21.ipynb", "output_data_21.csv"),
    ("rofc_51.ipynb", "output_data_51.csv"),
]

BOARDS = [
    {"id": "board_01", "ip": "169.254.168.99", "enabled": True},
    {"id": "board_02", "ip": "169.254.168.100", "enabled": True},
]


def enabled_boards():
    """Boards with enabled set to True. TA tools use this list.

    The oven run measures only the boards named with --boards.
    """
    return [board for board in BOARDS if board.get("enabled", True)]


def board_by_id(board_id):
    """Return one board dict, or raise KeyError if the id is not listed."""
    for board in BOARDS:
        if board["id"] == board_id:
            return board
    known = ", ".join(board["id"] for board in BOARDS) or "(none)"
    raise KeyError(f"Unknown board {board_id!r}. Known boards: {known}")


def board_output_dir(board_id):
    """Root directory for one board's CSVs and logs."""
    return BOARDS_ROOT / board_id


def group_output_dir(board_id, group):
    """Result directory for one group measuring this board.

    Group B writes here so its CSVs never land in the oven run's folders.
    """
    return board_output_dir(board_id) / group


def oven_owned_path(board_id):
    """Marker written while the oven run is measuring this board."""
    return board_output_dir(board_id) / "OVEN_OWNED"


def board_busy_path(board_id):
    """Marker written while a board-only job is measuring this board."""
    return board_output_dir(board_id) / "BOARD_BUSY"


def find_oven_owned():
    """Return an OVEN_OWNED marker if an oven run is already active."""
    if not BOARDS_ROOT.is_dir():
        return None
    for child in sorted(BOARDS_ROOT.iterdir()):
        marker = child / "OVEN_OWNED"
        if child.is_dir() and marker.is_file():
            return marker
    return None


def write_marker(path):
    """Create a lock marker exclusively. Return False if it already exists."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        handle = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    with os.fdopen(handle, "w", encoding="utf-8") as marker:
        marker.write(f"pid={os.getpid()}\n")
    return True


def remove_marker(path):
    """Remove a lock marker. Missing files are fine."""
    try:
        path.unlink()
    except OSError:
        pass
