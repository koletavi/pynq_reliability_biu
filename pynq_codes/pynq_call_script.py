import subprocess
import time
import os

PYNQ_RUN_SCRIPT = r"C:\pynq\pynq_codes\pynq_run_script.py"  # Path to the script that runs on the PYNQ-Z2

TEMP = 50
TIME = "0_0_0_time"
# Execute the PYNQ-Z2 notebook externally using a subprocess
def execute_notebook_externally(previous_process=None , temp=TEMP , time_str=TIME):
    try:
        if previous_process is not None:
            # Check if the previcleous process is still running
            pynq_state = previous_process.poll()
            if pynq_state is None:
                print("PYNQ-Z2 script is already running. No new process started.")
                return previous_process
            else:
                print("No process currently running")
            
        pynq_process = subprocess.Popen(["python", PYNQ_RUN_SCRIPT , str(temp), time_str], shell=False)
        return pynq_process  # Start a new process to run the PYNQ-Z2 script
    except Exception as e:
        print(f"Error executing PYNQ-Z2 script: {e}")
        return None

if __name__ == "__main__":
    # Execute the PYNQ-Z2 notebook externally
    start_time = time.time()  # Initialize time to avoid delay in the first execution
    process = execute_notebook_externally()
    
    if process:
        print("\nPYNQ-Z2 script executed successfully.")
        next_process = execute_notebook_externally(process)
    else:
        print("\nFailed to execute PYNQ-Z2 script.")
    
    # Monitor the process with a while loop
    if process:
        process.wait() 
        current_time = time.time() - start_time

        print("\nPYNQ-Z2 script completed. in {:.2f} seconds.".format(current_time))
    else:
        print("No PYNQ-Z2 script to wait for.")