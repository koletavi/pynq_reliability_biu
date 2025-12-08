import paramiko
import time
import os
import sys
from pathlib import Path

# Check if a temperature and time arguments are provided, otherwise use default
if len(sys.argv) > 1:
    # If a temperature and time argument are provided, use them
    TEMP = sys.argv[1]
    TIME = sys.argv[2]
else:
    # If no argument is provided, use a default value
    TEMP = "0"
    TIME = "0_0_0_time"
# Configuration
PYNQ_IP = "169.254.168.99"
USERNAME = "xilinx"
PASSWORD = "xilinx"  # Replace with your actual password or use SSH key
NOTEBOOKS = [
    ("rofc_11.ipynb", "output_data_11.csv"),
    ("rofc_21.ipynb", "output_data_21.csv"),
    ("rofc_51.ipynb", "output_data_51.csv"),
]
REMOTE_NOTEBOOK_DIR = "/home/xilinx/jupyter_notebooks/rofc/"
LOCAL_OUTPUT_DIR = r"C:\pynq\pynq_data"
LOG_DIR = os.path.join(LOCAL_OUTPUT_DIR, "logs")
LOCAL_PYNQ_DATA_DIR = os.path.join(LOCAL_OUTPUT_DIR, "pynq_run_data")
POLL_TIMEOUT = 5*60  # Maximum seconds to wait for output file
POLL_INTERVAL = 1  # Seconds between file existence checks

def get_unique_log_path():
    base_name = os.path.join(LOG_DIR, "pynq_run_")
    counter = 0
    while True:
        log_path = f"{base_name}{counter}.log"
        if not os.path.exists(log_path):
            return log_path
        counter += 1

log_file = None

def log(msg):
    if log_file:
        log_file.write(str(msg) + "\n")
        log_file.flush()

def get_unique_output_path(base_output_path, suffix):
    """Generate a unique output file path with an incrementing number."""
    base_name = os.path.splitext(base_output_path)[0]
    log(f"Base output path: {base_name}")
    counter = 0
    while True:
        new_path = f"{base_name}_{TEMP}C_{TIME}_{counter}{suffix}"
        if not os.path.exists(new_path):
            return new_path
        counter += 1

def execute_notebook_and_copy(notebook_name, output_csv_name):
    """Execute a Jupyter notebook on PYNQ-Z2 via SSH and copy the updated CSV file with a unique name."""
    ssh = None
    scp = None
    try:
        # Initialize SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(PYNQ_IP, username=USERNAME, password=PASSWORD)

        notebook_path = REMOTE_NOTEBOOK_DIR + notebook_name 
        output_file = REMOTE_NOTEBOOK_DIR + output_csv_name
        local_output_base = os.path.join(LOCAL_PYNQ_DATA_DIR, output_csv_name)
        local_output_path = get_unique_output_path(local_output_base, ".csv")

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
        # Check for errors during execution
        errors = stderr.read().decode()
        output = stdout.read().decode()
        if "Traceback" in errors or "Error" in errors or "failed" in errors.lower():
            log(f"Errors during notebook execution: {errors}")
            return False
        else:
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
            log(f"Timeout: Output file {output_file} not found or not updated after {POLL_TIMEOUT} seconds.")
            return False

        # Ensure output file is readable
        chmod_command = f"sudo chmod 644 {output_file}"
        ssh.exec_command(chmod_command)
        time.sleep(0.1)

        # Copy the output file using SCP with unique name
        log(f"Copying output file to {local_output_path}...")
        scp = ssh.open_sftp()
        os.makedirs(LOCAL_PYNQ_DATA_DIR, exist_ok=True)
        scp.get(output_file, local_output_path)
        log(f"Output file copied to {local_output_path}")

        return True

    except Exception as e:
        log(f"An error occurred: {str(e)}")
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
    global log_file
    os.makedirs(LOCAL_PYNQ_DATA_DIR, exist_ok=True)
    log_path = get_unique_log_path()
    log_file = open(log_path, "w", encoding="utf-8")
    try:
        for notebook, output_csv in NOTEBOOKS:
            log(f"\n--- Running {notebook} ---")
            success = execute_notebook_and_copy(notebook, output_csv)
            if not success:
                log(f"Failed to execute {notebook} or copy its output. Stopping sequence.")
                break
        else:
            log("\nAll notebooks executed and output files copied successfully.")
    finally:
        if log_file:
            log_file.close()

if __name__ == "__main__":
    main()