import argparse
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
import boards

PYNQ_RUN_SCRIPT = REPO_ROOT / "run" / "pynq_run_script.py"


def board_command(board, temp, time_str):
    return [
        sys.executable,
        str(PYNQ_RUN_SCRIPT),
        "--board", board["id"],
        "--ip", board["ip"],
        "--temp", str(temp),
        "--time", time_str,
        "--output-dir", str(boards.board_output_dir(board["id"])),
    ]


def execute_notebook_externally(board, previous_process=None, temp="50", time_str="0_0_0_time"):
    """Start the measurement on one board, unless that launch is already running."""
    try:
        if previous_process is not None:
            pynq_state = previous_process.poll()
            if pynq_state is None:
                print("PYNQ-Z2 script is already running. No new process started.")
                return previous_process
            else:
                print("No process currently running")

        return subprocess.Popen(board_command(board, temp, time_str), shell=False)
    except Exception as e:
        print(f"Error executing PYNQ-Z2 script: {e}")
        return None


def selected_board(board_id):
    if board_id:
        return boards.board_by_id(board_id)
    enabled = boards.enabled_boards()
    if not enabled:
        return None
    return enabled[0]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manually start the measurement on one PYNQ-Z2.")
    parser.add_argument("--board", default=None, help="Board id. Defaults to the first enabled board.")
    parser.add_argument("--temp", default="50")
    parser.add_argument("--time", default="0_0_0_time", dest="time_str")
    args = parser.parse_args()

    board = selected_board(args.board)
    if board is None:
        print("No enabled boards in boards.py")
        sys.exit(1)
    print(f"Manual run for {board['id']} at {board['ip']}")

    start_time = time.time()
    process = execute_notebook_externally(board, temp=args.temp, time_str=args.time_str)

    if process:
        print("\nPYNQ-Z2 script executed successfully.")
        execute_notebook_externally(board, process, temp=args.temp, time_str=args.time_str)
    else:
        print("\nFailed to execute PYNQ-Z2 script.")

    if process:
        process.wait()
        current_time = time.time() - start_time
        print("\nPYNQ-Z2 script completed. in {:.2f} seconds.".format(current_time))
    else:
        print("No PYNQ-Z2 script to wait for.")
