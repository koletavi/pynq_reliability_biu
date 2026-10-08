# PYNQ reliability run (university branch)

One oven heats the boards. The lab account measures `board_01` and leaves that window open. Group B later uses the same PC and measures `board_02` only, while that oven run is still going. Group B does not start a second oven program. Both groups share the current oven temperature. Their result folders do not overlap.

Students do only the steps in "What you do". Everything else is for the TA.

## What you do

Edit only `run/config.py`. If the TA did not give you different temperatures or times, leave it as it is.

### Group A

1. Double-click `check_oven.bat`.
2. Wait until the window says `OK`. If it says `FAIL`, stop. Read the sentence above `FAIL` and call the TA. Do not start the oven.
3. Double-click `oven_board_01.bat` and leave that window open for the whole run.

`check_oven.bat` does not start the oven. `oven_board_01.bat` programs the oven and measures `board_01` only.

### Group B

1. Double-click `check_board_02.bat`.
2. Wait until the window says `OK`. If it says `FAIL`, stop. Read the sentence above `FAIL` and call the TA.
3. Double-click `board_02_only.bat` and leave that window open.
* notice - Do not run `oven_board_01.bat`. The oven is already running.
`check_board_02.bat` does not open the oven port. `board_02_only.bat` measures `board_02` only. It does not start an oven program.

Stop a job with Ctrl+C in its own window. That stops only that window. The other group's window keeps running.

After each measurement round the window prints one summary line, for example:

```text
board_01: 3/3 csv
```

A notebook that fails is not counted as a success. The line then names the notebook, for example `board_01: 2/3 csv (rofc_51 failed)`.

## What you are allowed to change

Edit **only** `run/config.py`. The program reads that file when it starts and stops immediately if a value is not allowed. The message names the exact problem.

| Setting | Meaning | Rules |
| --- | --- | --- |
| `temperature_list` | Oven setpoints, in °C, in the order they will be used | Integers from 80 to 110, each one higher than the one before |
| `temperature_enable` | `1` means "do this setpoint", `0` means "skip it" | Same length as `temperature_list`. All the `1`s must come first, then only `0`s. Example: `[1, 1, 0, 0]` runs the first two temperatures |
| `time_list` | `[rise minutes, hold minutes]` | Exactly two numbers, each at least 10. The first is how long the oven may take to reach the setpoint. The second is how long it stays there |
| `pynq_wait_threshold` | Seconds to wait after one measurement round before the next one can start | At least 120. `60*10` means 10 minutes |
| `oven_port` | Serial port of the oven controller. Optional | Leave it unset. The default is `COM4`. Change it only if the TA tells you the port name |

The checked-in file runs only the first setpoint (80°C), with a 10 minute rise, a 60 minute hold, and 10 minutes between measurement rounds.

## What the runs do

The lab account's window prints `Oven port: COMx`, programs the oven, and starts the temperature profile. It records the oven temperature about once a second. A setpoint counts as stable only after the measured temperature has stayed within 5°C of the setpoint for 2 minutes. Those two limits are fixed. They are not in `run/config.py`. When the temperature is stable, that window measures `board_01` at `169.254.168.99`. It does not start `board_02`.

Group B's window does not wait for oven stability and does not write the temperature program. It measures `board_02` at `169.254.168.100`, waits `pynq_wait_threshold` seconds, and measures again until Ctrl+C.

Each measurement runs three notebooks that are already on that board, one after another:

1. `rofc_11.ipynb`
2. `rofc_21.ipynb`
3. `rofc_51.ipynb`

The copies in `run/notebooks/` are not used. If one notebook fails, that board does not run the notebooks after it in that round. The next round can still start. The other window keeps running.

## Where the results go

Results are written under `data/` in this folder. Git does not track that folder.

```text
data/boards/board_01/                  lab account CSVs and logs
data/boards/board_02/groupB/           group B CSVs and logs
data/temperature_data/                 one shared oven log
```

`board_02_only.bat` uses the group name `groupB`, so that folder is `data/boards/board_02/groupB/`. The two result folders do not overlap.

Do not run `lab_tools/average_outputs.py`. That script is for the TA. It deletes the raw CSVs after it averages them.

## For the TA

Students should not need these. `lab_tools/` is calibration, checks, and offline processing.

| Script | Use |
| --- | --- |
| `lab_tools/average_outputs.py` | Average each board's top-level `pynq_run_data` CSVs into `data/boards/<board>/averages/`. After that it deletes the raw CSVs it averaged and folds that board's logs into one daily log. Do not run it until those raw files have been copied somewhere safe. It does not look inside `data/boards/board_02/<group>/` |
| `lab_tools/animate_example_prev.py` | Live plot of `data/temperature_data/live_temperature_data.csv` while the oven run is going |
| `lab_tools/plot_temp_vs_time.py` | Plot the saved oven log after a run |
| `lab_tools/pynq_call_script.py` | Start the three notebooks on one board only. This does not run the oven |
| `lab_tools/notebook_setup.py` | Run `rofc_setup.ipynb` on the boards, one board after another |
| `lab_tools/calibrate_pid.py` | Oven PID calibration |
| `lab_tools/oven_csv_single_read_list.py` | Dump oven registers. Uses its own serial port |
| `lab_tools/oven_initial_read_array.py` | Dump oven registers into a matrix. Uses its own serial port |

Register dumps are written to `data/oven_reads/`.

The four student bats change to the folder that contains the bat, then prefer `.venv\Scripts\python.exe`, then `py -3`, then `python`. They print `OK` or `FAIL`. A failure leaves the window open.

| Bat | Command |
| --- | --- |
| `check_oven.bat` | `python run/oven_run.py --check --boards board_01` |
| `oven_board_01.bat` | `python run/oven_run.py --boards board_01` |
| `check_board_02.bat` | `python run/preflight.py --board board_02` |
| `board_02_only.bat` | `python run/board_only.py --board board_02 --group groupB` |

`python run/oven_run.py --dry-run --boards board_01` only loads `run/config.py` and prints `board_01`. It does not open the oven port and does not contact the boards.

`run/oven_run.py` is the only script that opens the oven port and writes the temperature program. On start it writes `data/boards/board_01/OVEN_OWNED` and removes that file on exit, including Ctrl+C. If that file is already present, a second start prints one sentence and does not program the oven. `run/process_main.py` does not start the oven.

`board_02_only.bat` writes `data/boards/board_02/BOARD_BUSY` while it runs and removes that file on exit, including Ctrl+C. It refuses to start when `data/boards/board_02/OVEN_OWNED` or `data/boards/board_02/BOARD_BUSY` is present. The oven run does not start a board that has `BOARD_BUSY`.

If a window was closed without Ctrl+C and no matching window is still open, delete the stale `OVEN_OWNED` or `BOARD_BUSY` file before starting again. Do not delete it while a window is running.

The board list, SSH account, and notebook names are in `boards.py`. `board_01` is `169.254.168.99`. `board_02` is `169.254.168.100`. `board_03` at `169.254.168.101` is not listed. The SSH account is `xilinx` / `xilinx`. Every measured board must already have `rofc_11.ipynb`, `rofc_21.ipynb`, and `rofc_51.ipynb` in `/home/xilinx/jupyter_notebooks/rofc/`.

On the lab PC, results can be sent to the old data folder by setting `OUTPUT_ROOT` in `boards.py` to `Path(r"C:\pynq\pynq_data")`. The per-board folders are still created under that path.

Install the main-run packages with `pip install -r requirements.txt` if a check says an import is missing. The file lists `minimalmodbus`, `paramiko`, `pandas`, and `matplotlib` with minimum versions only, so a newer package that is already installed is left as it is.

Do not change `hardware_versions/` or the FPGA tcl for a student run.
