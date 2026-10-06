"""Which PYNQ-Z2 cards to run, and where their results are stored.

The oven recipe (temperatures, hold times, and the wait between samples)
stays in run/config.py. Add another card by appending one entry to BOARDS.
Set enabled to False to leave a card in the list without starting it.
"""
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
    """Boards that the oven run should start."""
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
