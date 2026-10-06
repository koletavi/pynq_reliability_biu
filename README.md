# PYNQ reliability run (university branch)

One oven heats the boards. Two PYNQ-Z2 boards measure at each stable temperature. Students do only the steps in "What you do". Everything else is for the TA.

## What you do

1. Edit only `run/config.py` if the TA gave you different temperatures or times. If you were not told to change it, leave it as it is.
2. Double-click `check_lab.bat`, or from this folder run:

```text
check_lab.bat
```

3. Wait until the window says `OK`. If it says `FAIL`, stop. Do not start the run. Read the sentence above `FAIL` and call the TA.
4. Double-click `run_lab.bat`, or run:

```text
run_lab.bat
```

5. Leave that window open. Stop the run with Ctrl+C. At the end it shows a plot of oven temperature versus time.

`check_lab.bat` only checks the PC, the oven port, and the boards. It does not heat the oven and it does not measure. `run_lab.bat` runs that same check again and then starts the experiment. If the check fails, the oven is not started.

After each measurement round the run prints one line, for example:

```text
board_01: 3/3 csv, board_02: 2/3 csv (rofc_51 failed)
```

That means board 1 copied three files and board 2 copied two. A failure on one board does not stop the other board.

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

Do not edit `boards.py`, `run/process_main.py`, or the files in `lab_tools/`.

## What the run does

There is one oven and two boards. The boards do not heat anything. They measure while the oven holds a temperature.

1. The program prints `Oven port: COMx`, programs the oven, and starts the temperature profile.
2. It records the oven temperature about once a second.
3. A setpoint counts as stable only after the measured temperature has stayed within 5°C of the setpoint for 2 minutes. Those two limits are fixed. They are not in `run/config.py`.
4. When the temperature is stable, both boards start together:
   - `board_01` at `169.254.168.99`
   - `board_02` at `169.254.168.100`
5. Each board then runs three notebooks that are already on that board, one after another:
   1. `rofc_11.ipynb`
   2. `rofc_21.ipynb`
   3. `rofc_51.ipynb`

   The copies in `run/notebooks/` are not used.
6. If one notebook fails, that board stops and does not run the notebooks after it. The other board continues.
7. A board that is still measuring is not started again.
8. After a round starts, the program waits `pynq_wait_threshold` seconds before it is allowed to start another round.

## Where the results go

Results are written under `data/` in this folder. Git does not track that folder.

```text
data/boards/board_01/pynq_run_data/    CSVs from 169.254.168.99
data/boards/board_01/logs/
data/boards/board_02/pynq_run_data/    CSVs from 169.254.168.100
data/boards/board_02/logs/
data/temperature_data/                 one shared oven log
```

Each measurement file is named like `output_data_11_80C_0_2_5_time_0.csv`. The number after `output_data_` is the test (`11`, `21`, or `51`). `board_01` and `board_02` never write into each other's folders.

Do not run `lab_tools/average_outputs.py`. That script is for the TA. It deletes the raw CSVs after it averages them.

## For the TA

Students should not need these. `lab_tools/` is calibration, checks, and offline processing.

| Script | Use |
| --- | --- |
| `lab_tools/average_outputs.py` | Average each board's CSVs into `data/boards/<board>/averages/`. After that it deletes the raw CSVs it averaged and folds that board's logs into one daily log. Do not run it until the raw files have been copied somewhere safe |
| `lab_tools/animate_example_prev.py` | Live plot of `data/temperature_data/live_temperature_data.csv` while the main run is going |
| `lab_tools/plot_temp_vs_time.py` | Plot the saved oven log after a run |
| `lab_tools/pynq_call_script.py` | Start the three notebooks on one board only. This does not run the oven. Default board is `board_01` |
| `lab_tools/notebook_setup.py` | Run `rofc_setup.ipynb` on the boards, one board after another |
| `lab_tools/calibrate_pid.py` | Oven PID calibration |
| `lab_tools/oven_csv_single_read_list.py` | Dump oven registers. Uses its own serial port |
| `lab_tools/oven_initial_read_array.py` | Dump oven registers into a matrix. Uses its own serial port |

Register dumps are written to `data/oven_reads/`.

`check_lab.bat` runs `python run/process_main.py --check`. `run_lab.bat` runs `python run/process_main.py`. Both use `.venv\Scripts\python.exe` when that file exists. Otherwise they use `py -3` when that Python can import the lab packages, and otherwise `python`. `python run/process_main.py --dry-run` only loads `run/config.py` and prints the board plan. It does not open the oven port and does not contact the boards.

The board list, SSH account, notebook names, and result folder are in `boards.py`. To add a third board, append an entry there. `board_03` at `169.254.168.101` is not enabled unless you add it. Set `"enabled": False` to leave a board in the list without starting it. Every enabled card must already have `rofc_11.ipynb`, `rofc_21.ipynb`, and `rofc_51.ipynb` in `/home/xilinx/jupyter_notebooks/rofc/`.

On the lab PC, results can be sent to the old data folder by setting `OUTPUT_ROOT` in `boards.py` to `Path(r"C:\pynq\pynq_data")`. The per-board folders are still created under that path.

Install the main-run packages with `pip install -r requirements.txt` if `check_lab.bat` says an import is missing. The file lists minimum versions only, so a newer package that is already installed is left as it is.
