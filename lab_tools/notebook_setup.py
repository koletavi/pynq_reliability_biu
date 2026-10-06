import argparse
import os
import sys
from pathlib import Path

import paramiko

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
import boards

SETUP_NOTE = "rofc_setup.ipynb"

def execute_setup_notebook(notebook_name, board):
    """Execute the setup notebook on one PYNQ-Z2 via SSH."""
    ssh = None
    scp = None
    try:
        # Initialize SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        username = board.get("username", boards.USERNAME)
        password = board.get("password", boards.PASSWORD)
        remote_notebook_dir = board.get("remote_notebook_dir", boards.REMOTE_NOTEBOOK_DIR)
        ssh.connect(board["ip"], username=username, password=password)

        notebook_path = remote_notebook_dir + notebook_name 

        # Command to activate virtual environment and execute notebook
        command = (
            "source /usr/local/share/pynq-venv/bin/activate && "
            f"sudo /usr/local/share/pynq-venv/bin/jupyter nbconvert --to notebook --execute "
            f"{notebook_path} --output executed_setup.ipynb"
        )
        
        stdin, stdout, stderr = ssh.exec_command(command)
        # Check for errors during execution
        errors = stderr.read().decode()
        output = stdout.read().decode()
        if "Traceback" in errors or "Error" in errors or "failed" in errors.lower():
            print(f"Errors during notebook execution: {errors}")
            return False
        else:
            print(f"Notebook execution output: {output}")
            print(f"Notebook execution status (stderr): {errors}")

        return True

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return False
    finally:
        if scp is not None:
            try:
                scp.close()
            except Exception:
                pass
        if ssh is not None:
            try:
                ssh.close()
            except Exception:
                pass

def main():
    parser = argparse.ArgumentParser(description="Run the remote setup notebook on one or every enabled PYNQ-Z2.")
    parser.add_argument("--board", default=None, help="Board id. Defaults to every enabled board, one after another.")
    args = parser.parse_args()
    if args.board:
        selected = [boards.board_by_id(args.board)]
    else:
        selected = boards.enabled_boards()
    if not selected:
        print("No enabled boards in boards.py")
        return

    os.makedirs(boards.OUTPUT_ROOT, exist_ok=True)
    try:
        for board in selected:
            print(f"\n--- {board['id']} ({board['ip']}) running {SETUP_NOTE} ---")
            success = execute_setup_notebook(SETUP_NOTE, board)
            if not success:
                print(f"Failed to execute {SETUP_NOTE} on {board['id']}. Stopping sequence.")
                break
        else:
            print("\nSetup notebook finished on every selected board.")
    except Exception as e:
        print(f"got exception: {e}")

if __name__ == "__main__":
    main()