import argparse
import json
import os
import re
import shlex
import sys
import time
from datetime import date
from pathlib import Path

import paramiko

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
import boards
import preflight

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
    """Generate a unique output file path with an incrementing number.

    The date sits between the temperature and the elapsed-time label:
    output_data_11_80C_2026_10_08_1_2_3_time_0.csv
    """
    base_name = os.path.splitext(base_output_path)[0]
    day = date.today().strftime("%Y_%m_%d")
    log(f"Base output path: {base_name}")
    counter = 0
    while True:
        new_path = f"{base_name}_{temp}C_{day}_{time_str}_{counter}{suffix}"
        if not os.path.exists(new_path):
            return new_path
        counter += 1


def patch_source_text(text, params):
    """Replace the three assignments. Return None when this cell has none of them."""
    patterns = {
        name: re.compile(rf"^(\s*){name}\s*=\s*[^#\n]*", re.M)
        for name in ("ctr_run_time", "ro_sel", "sample_size")
    }
    counts = {name: len(patterns[name].findall(text)) for name in patterns}
    if all(count == 0 for count in counts.values()):
        return None
    if any(count != 1 for count in counts.values()):
        found = ", ".join(f"{name} x{count}" for name, count in counts.items())
        raise ValueError(f"expected one assignment each, found {found}")
    for name, pattern in patterns.items():
        text = pattern.sub(rf"\g<1>{name} = {int(params[name])} ", text, count=1)
    return text


def patch_notebook(notebook, params):
    """Write ctr_run_time, ro_sel, and sample_size into the notebook that will run."""
    patched = 0
    for cell in notebook.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        source = cell.get("source", "")
        as_list = isinstance(source, list)
        text = "".join(source) if as_list else source
        updated = patch_source_text(text, params)
        if updated is None:
            continue
        cell["source"] = updated.splitlines(keepends=True) if as_list else updated
        patched += 1
    if patched == 0:
        raise ValueError("no cell contains ctr_run_time, ro_sel, and sample_size")
    return notebook


def push_notebook_params(ssh, notebook_path, params, password):
    """Read the notebook on the board, set the three values, and save it back.

    nbconvert then executes that same file. The local copies are not used.
    The notebook directory on the card is owned by root, so the copy uses sudo
    with the same password that opened SSH.
    """
    sftp = ssh.open_sftp()
    tmp_path = f"/tmp/{os.path.basename(notebook_path)}.config.tmp"
    try:
        with sftp.file(notebook_path, "r") as remote:
            raw = remote.read()
        notebook = json.loads(raw.decode("utf-8"))
        patch_notebook(notebook, params)
        payload = json.dumps(notebook, ensure_ascii=False, indent=1)
        if not payload.endswith("\n"):
            payload += "\n"
        with sftp.file(tmp_path, "w") as remote:
            remote.write(payload.encode("utf-8"))
    finally:
        sftp.close()

    quoted_tmp = shlex.quote(tmp_path)
    quoted_dest = shlex.quote(notebook_path)
    inner = f"cp {quoted_tmp} {quoted_dest} && chmod 644 {quoted_dest}"
    command = f"sudo -S -p '' bash -c {shlex.quote(inner)} && rm -f {quoted_tmp}"
    stdin, stdout, stderr = ssh.exec_command(command)
    stdin.write(password + "\n")
    stdin.flush()
    errors = stderr.read().decode(errors="replace")
    exit_status = stdout.channel.recv_exit_status()
    if exit_status != 0:
        ssh.exec_command(f"rm -f {quoted_tmp}")
        detail = "\n".join(
            line for line in errors.splitlines()
            if line.strip() and "password" not in line.lower()
        )
        raise RuntimeError(f"could not update {notebook_path}: {detail or 'exit ' + str(exit_status)}")


def notebook_failed(exit_status, output, errors):
    """True when nbconvert exits non-zero or the notebook output contains Traceback.

    A good nbconvert run still writes words such as "failed" and "Error" to
    stderr. Those words are not a failed notebook.
    """
    if exit_status != 0:
        return True
    if output and "Traceback" in output:
        return True
    if errors and "Traceback" in errors:
        return True
    return False


def execute_notebook_and_copy(notebook_name, output_csv_name, ip, username, password, remote_notebook_dir, data_dir, temp, time_str, board_id, params):
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

        log(
            f"{notebook_name}: ctr_run_time={params['ctr_run_time']}, "
            f"ro_sel={params['ro_sel']}, sample_size={params['sample_size']}"
        )
        push_notebook_params(ssh, notebook_path, params, password)

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
        boards.mark_readonly(local_output_path)
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


def format_round_line(board_id, result_path, return_code=None):
    """One summary line. A failed notebook is never reported as a full success."""
    total = len(boards.NOTEBOOKS)
    path = Path(result_path) if result_path is not None else None
    if path is None or not path.is_file():
        return f"{board_id}: 0/{total} csv (no result)"
    data = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip()
    ok = data.get("ok", "0")
    reported_total = data.get("total", str(total))
    failed = data.get("failed", "")
    if failed:
        return f"{board_id}: {ok}/{reported_total} csv ({failed} failed)"
    if return_code not in (None, 0):
        return f"{board_id}: {ok}/{reported_total} csv (notebook failed)"
    return f"{board_id}: {ok}/{reported_total} csv"


def write_round_result(result_path, ok_count, total, failed_name):
    """Record how many notebooks on this board copied a CSV."""
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

    config_path = os.path.join(os.path.dirname(__file__), "config.py")
    try:
        notebook_params = preflight.load_notebook_params(config_path, announce=False)
    except SystemExit as exc:
        print(exc)
        sys.exit(1)

    if args.dry_run:
        print(f"Board: {board['id']}")
        print(f"IP: {ip}")
        print(f"Output directory: {output_dir}")
        print("Notebooks: " + ", ".join(name for name, _csv in boards.NOTEBOOKS))
        for name, _csv in boards.NOTEBOOKS:
            values = notebook_params[name]
            print(
                f"{name}: ctr_run_time={values['ctr_run_time']}, "
                f"ro_sel={values['ro_sel']}, sample_size={values['sample_size']}"
            )
        print("Dry run only. No SSH connection was opened.")
        return

    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)
    result_path = Path(args.result_file) if args.result_file else Path(output_dir) / "round_result.txt"
    log_path = get_unique_log_path(log_dir)
    log_file = open(log_path, "w", encoding="utf-8")
    log(f"board_id={board['id']}")
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
                notebook_params[notebook],
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
