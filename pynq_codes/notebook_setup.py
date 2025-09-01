import paramiko
import time
import os
import sys
from pathlib import Path

# Configuration
PYNQ_IP = "169.254.226.99"
USERNAME = "xilinx"
PASSWORD = "xilinx"  # Replace with your actual password or use SSH key
SETUP_NOTE = "rofc_setup.ipynb"
REMOTE_NOTEBOOK_DIR = "/home/xilinx/jupyter_notebooks/rofc/"
LOCAL_OUTPUT_DIR = r"C:\pynq\pynq_data"

def execute_setup_notebook(notebook_name):
    """Execute a Jupyter notebook on PYNQ-Z2 via SSH and copy the updated CSV file with a unique name."""
    ssh = None
    scp = None
    try:
        # Initialize SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(PYNQ_IP, username=USERNAME, password=PASSWORD)

        notebook_path = REMOTE_NOTEBOOK_DIR + notebook_name 

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
    global log_file
    os.makedirs(LOCAL_OUTPUT_DIR, exist_ok=True)
    try:
        notebook = SETUP_NOTE
        print(f"\n--- Running {notebook} ---")
        success = execute_setup_notebook(notebook)
        if not success:
            print(f"Failed to execute {notebook} or copy its output. Stopping sequence.")
        
        else:
            print("\nAll notebooks executed and output files copied successfully.")
    except Exception as e:
        print(f"got exception: {e}")

if __name__ == "__main__":
    main()