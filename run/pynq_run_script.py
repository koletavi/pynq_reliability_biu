import argparse
import os
import sys
import time
from pathlib import Path

import paramiko

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
import boards

POLL_TIMEOUT = 5 * 60  # Maximum seconds to wait for output file
POLL_INTERVAL = 1  # Seconds between file existence checks

log_file = None


def log(msg):
    if log_file:
        log_file.write(str(msg) + "\n")
        log_file.flush()


def get_unique_log_path(log_dir):
    base_name = os.path.join(log_dir, "pynq_run_")
    counter = 0
    while True:
        log_path = f"{base_name}{counter}.log"
        if not os.path.exists(log_path):
            return log_path
        counter += 1


def get_unique_output_path(base_output_path, suffix, temp, time_str):
    """Generate a unique output file path with an incrementing number."""
    base_name = os.path.splitext(base_output_path)[0]
    log(f"Base output path: {base_name}")
    counter = 0
    while True:
        new_path = f"{base_name}_{temp}C_{time_str}_{counter}{suffix}"
        if not os.path.exists(new_path):
            return new_path
        counter += 1


def notebook_failed(exit_status, output, errors):
    """True when nbconvert failed or the notebook raised."""
    if exit_status != 0:
        return True
    return "Traceback" in output or "Traceback" in errors


def execute_notebook_and_copy(notebook_name, output_csv_name, ip, username, password, remote_notebook_dir, data_dir, temp, time_str, board_id):
    """Execute a Jupyter notebook on one PYNQ-Z2 via SSH and copy the updated CSV file with a unique name."""
    ssh = None
    scp = None
    try:
        # Initialize SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, username=username, password=password)

        notebook_path = remote_notebook_dir + notebook_name
        output_file = remote_notebook_dir + output_csv_name
        local_output_base = os.path.join(data_dir, output_csv_name)
        local_output_path = get_unique_output_path(local_output_base, ".csv", temp, time_str)

        # Get initial modification time of the output file (if it exists)
        check_file_command = f"stat -c %Y {output_file} || echo '0'"
        stdin, stdout, stderr = ssh.exec_command(check_file_command)
        initial_mtime = int(stdout.read().decode().strip() or 0)

        # Command to activate virtual environment and execute notebook
        command = (
            "source /usr/local/share/pynq-venv/bin/activate && "
            f"sudo /usr/local/share/pynq-venv/bin/jupyter nbconvert --to notebook --execute "
            f"{notebook_path} --output executed_notebook.ipynb"
        )
        log(f"Executing {notebook_name}...")
        stdin, stdout, stderr = ssh.exec_command(command)
        errors = stderr.read().decode(errors="replace")
        output = stdout.read().decode(errors="replace")
        exit_status = stdout.channel.recv_exit_status()
        if notebook_failed(exit_status, output, errors):
            log(f"{board_id}: {notebook_name} failed (exit {exit_status})")
            log(f"Notebook execution output: {output}")
            log(f"Notebook execution status (stderr): {errors}")
            return False
        log(f"Notebook execution output: {output}")
        log(f"Notebook execution status (stderr): {errors}")

        # Poll for output file existence or update
        log(f"Waiting for output file {output_file} to be created or updated...")
        start_time = time.time()
        while time.time() - start_time < POLL_TIMEOUT:
            check_file_command = f"stat -c %Y {output_file} || echo '0'"
            stdin, stdout, stderr = ssh.exec_command(check_file_command)
            current_mtime = int(stdout.read().decode().strip() or 0)
            if current_mtime > initial_mtime:
                log(f"Output file {output_file} detected or updated.")
                break
            time.sleep(POLL_INTERVAL)
        else:
            log(f"{board_id}: {notebook_name} failed. Timeout: output file {output_file} not found or not updated after {POLL_TIMEOUT} seconds.")
            return False

        # Ensure output file is readable
        chmod_command = f"sudo chmod 644 {output_file}"
        ssh.exec_command(chmod_command)
        time.sleep(0.1)

        # Copy the output file using SCP with unique name
        log(f"Copying output file to {local_output_path}...")
        scp = ssh.open_sftp()
        os.makedirs(data_dir, exist_ok=True)
        scp.get(output_file, local_output_path)
        log(f"Output file copied to {local_output_path}")

        return True

    except Exception as e:
        log(f"{board_id}: {notebook_name} failed. An error occurred: {str(e)}")
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


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run the RO frequency notebooks on one PYNQ-Z2 and copy the CSVs back."
    )
    parser.add_argument("--board", required=True, help="Board id from boards.py, for example board_01")
    parser.add_argument("--ip", default=None, help="Override the board IP from boards.py")
    parser.add_argument("--temp", default="0", help="Temperature label stored in the CSV name")
    parser.add_argument("--time", default="0_0_0_time", dest="time_str", help="Stability-time label stored in the CSV name")
    parser.add_argument("--output-dir", default=None, help="Directory for this board's logs and CSVs")
    parser.add_argument("--result-file", default=None, help="File that receives this round's csv count")
    parser.add_argument("--dry-run", action="store_true", help="Print the board IP and output directory without opening SSH")
    return parser.parse_args()


def write_round_result(result_path, ok_count, total, failed_name):
    """Tell process_main how many notebooks on this board copied a CSV."""
    path = Path(result_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    failed = failed_name or ""
    path.write_text(f"ok={ok_count}\ntotal={total}\nfailed={failed}\n", encoding="utf-8")


def main():
    global log_file
    args = parse_args()
    try:
        board = boards.board_by_id(args.board)
    except KeyError as exc:
        print(exc)
        sys.exit(2)

    ip = args.ip or board["ip"]
    username = board.get("username", boards.USERNAME)
    password = board.get("password", boards.PASSWORD)
    remote_notebook_dir = board.get("remote_notebook_dir", boards.REMOTE_NOTEBOOK_DIR)
    output_dir = Path(args.output_dir) if args.output_dir else boards.board_output_dir(board["id"])
    data_dir = os.path.join(output_dir, "pynq_run_data")
    log_dir = os.path.join(output_dir, "logs")

    if args.dry_run:
        print(f"Board: {board['id']}")
        print(f"IP: {ip}")
        print(f"Output directory: {output_dir}")
        print("Notebooks: " + ", ".join(name for name, _csv in boards.NOTEBOOKS))
        print("Dry run only. No SSH connection was opened.")
        return

    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)
    result_path = Path(args.result_file) if args.result_file else Path(output_dir) / "round_result.txt"
    log_path = get_unique_log_path(log_dir)
    log_file = open(log_path, "w", encoding="utf-8")
    ok_count = 0
    failed_name = ""
    total = len(boards.NOTEBOOKS)
    try:
        for notebook, output_csv in boards.NOTEBOOKS:
            log(f"\n--- Running {notebook} on {board['id']} ({ip}) ---")
            success = execute_notebook_and_copy(
                notebook,
                output_csv,
                ip,
                username,
                password,
                remote_notebook_dir,
                data_dir,
                args.temp,
                args.time_str,
                board["id"],
            )
            if not success:
                failed_name = os.path.splitext(notebook)[0]
                log(f"{board['id']}: {notebook} failed. Stopping this board. Other boards are not affected.")
                break
            ok_count += 1
        else:
            log("\nAll notebooks executed and output files copied successfully.")
    finally:
        write_round_result(result_path, ok_count, total, failed_name)
        if log_file:
            log_file.close()
    if failed_name:
        sys.exit(1)


if __name__ == "__main__":
    main()
