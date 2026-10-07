"""Measure one PYNQ-Z2 until Ctrl+C. Does not program the oven.

This file does not import the oven program, open a serial port, or write
a temperature profile. Group B runs it through board_02_only.bat:

    python run/board_only.py --board board_02 --group groupB
"""

import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
import boards
import preflight

PYNQ_RUN_SCRIPT = Path(__file__).resolve().parent / "pynq_run_script.py"
GROUP_NAME = re.compile(r"[A-Za-z0-9_-]+")
USAGE = "Usage: python run/board_only.py --board board_02 --group groupB"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Measure one PYNQ-Z2 until Ctrl+C. Does not start the oven.",
        usage=USAGE,
    )
    parser.add_argument("--board", default=None, help="Board id, for example board_02")
    parser.add_argument("--group", default=None, help="Result folder name, for example groupB")
    return parser.parse_args(argv)


def shared_temperature_label():
    """Last oven temperature from the shared log, rounded like the oven run.

    Reading the log does not open the oven port. A missing log uses 0.
    """
    path = boards.TEMPERATURE_DIR / "live_temperature_data.csv"
    for _ in range(3):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            time.sleep(0.2)
            continue
        last = ""
        for line in text.splitlines():
            if line and not line.lower().startswith("time"):
                last = line
        if not last or "," not in last:
            return "0"
        raw = last.rsplit(",", 1)[-1].strip()
        try:
            value = float(raw)
        except ValueError:
            return "0"
        return str(int(round(value / 10.0) * 10))
    return "0"


def elapsed_label(start_time):
    elapsed = int(time.time() - start_time)
    hours, rem = divmod(elapsed, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{hours}_{minutes}_{seconds}_time"


def holder_sentence(board_id):
    """One sentence naming the lock that already holds this board."""
    holders = []
    if boards.oven_owned_path(board_id).is_file():
        holders.append("OVEN_OWNED")
    if boards.board_busy_path(board_id).is_file():
        holders.append("BOARD_BUSY")
    if not holders:
        return None
    return f"{board_id} is held by {' and '.join(holders)}."


def load_wait():
    """Read pynq_wait_threshold through the existing config validators."""
    config_path = os.path.join(os.path.dirname(__file__), "config.py")
    _temps, _enable, _times, wait, _port = preflight.load_recipe(
        config_path,
        [80, 90, 100, 110],
        [1, 0, 0, 0],
        [10, 60],
        60 * 10,
    )
    return wait


def run_round(board, output_dir, temp, time_str):
    """Run the three notebooks once and return the summary line."""
    output_dir.mkdir(parents=True, exist_ok=True)
    result_path = output_dir / f"round_result_{time.time_ns()}.txt"
    command = [
        sys.executable,
        str(PYNQ_RUN_SCRIPT),
        "--board", board["id"],
        "--ip", board["ip"],
        "--temp", str(temp),
        "--time", time_str,
        "--output-dir", str(output_dir),
        "--result-file", str(result_path),
    ]
    process = subprocess.Popen(command, shell=False)
    try:
        return_code = process.wait()
    except KeyboardInterrupt:
        if process.poll() is None:
            process.terminate()
        raise
    from pynq_run_script import format_round_line
    line = format_round_line(board["id"], result_path, return_code)
    try:
        result_path.unlink()
    except OSError:
        pass
    return line


def main(argv=None):
    args = parse_args(argv)
    if not args.board or not args.group:
        print(USAGE)
        return 2
    if not GROUP_NAME.fullmatch(args.group):
        print(USAGE)
        return 2
    try:
        board = boards.board_by_id(args.board)
    except KeyError as exc:
        print(exc)
        return 1
    held = holder_sentence(board["id"])
    if held:
        print(held)
        return 1
    try:
        wait_seconds = load_wait()
    except SystemExit as exc:
        if str(exc):
            print(exc)
        return 1

    busy_path = boards.board_busy_path(board["id"])
    if not boards.write_marker(busy_path):
        print(f"{board['id']} is held by BOARD_BUSY.")
        return 1

    output_dir = boards.group_output_dir(board["id"], args.group)
    started = time.time()
    try:
        while True:
            temp = shared_temperature_label()
            time_str = elapsed_label(started)
            print(run_round(board, output_dir, temp, time_str))
            print(f"Waiting {wait_seconds} seconds before the next round.")
            time.sleep(wait_seconds)
    finally:
        boards.remove_marker(busy_path)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nStopped.")
