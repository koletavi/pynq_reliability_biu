# PYNQ reliability run (university branch)

This repository runs a temperature sweep on one oven and, at each stable temperature, measures two PYNQ-Z2 boards. Students use the main run below. The other scripts are for the TA.

## What you run

From the repository folder:

```text
python run/process_main.py
```

That is the full experiment. Leave it running. Stop it with Ctrl+C. When it finishes, it shows a plot of oven temperature versus time.

Before a real lab day you can check the setup without connecting to the oven or the boards:

```text
python run/process_main.py --dry-run
```

A dry run only checks `run/config.py`, prints the two boards, and creates the empty result folders.

## What you are allowed to change

Edit **only** `run/config.py`. The program reads that file when it starts and stops immediately if a value is not allowed. The message names the exact problem.

| Setting | Meaning | Rules |
| --- | --- | --- |
| `temperature_list` | Oven setpoints, in °C, in the order they will be used | Integers from 80 to 110, each one higher than the one before |
| `temperature_enable` | `1` means "do this setpoint", `0` means "skip it" | Same length as `temperature_list`. All the `1`s must come first, then only `0`s. Example: `[1, 1, 0, 0]` runs the first two temperatures |
| `time_list` | `[rise minutes, hold minutes]` | Exactly two numbers, each at least 10. The first is how long the oven may take to reach the setpoint. The second is how long it stays there |
| `pynq_wait_threshold` | Seconds to wait after one measurement round before the next one can start | At least 120. `60*10` means 10 minutes |

The checked-in file runs only the first setpoint (80°C), with a 10 minute rise, a 60 minute hold, and 10 minutes between measurement rounds.

Do not edit `run/process_main.py` to change the test. Values written there are defaults. `run/config.py` replaces them.

## What the main run does

There is one oven and two boards. The boards do not heat anything. They measure while the oven holds a temperature.

1. The program programs the oven and starts the temperature profile.
2. It records the oven temperature about once a second.
3. A setpoint counts as stable only after the measured temperature has stayed within 5°C of the setpoint for 2 minutes. Those two limits are fixed. They are not in `run/config.py`.
4. When the temperature is stable, both boards start together:
   - `board_01` at `169.254.168.99`
   - `board_02` at `169.254.168.100`
5. Each board then runs three notebooks, one after another, on that board only:
   1. `rofc_11.ipynb`
   2. `rofc_21.ipynb`
   3. `rofc_51.ipynb`
6. Those notebooks already live on each board, in `/home/xilinx/jupyter_notebooks/rofc/`. The run does not use the notebooks stored in this repository.
7. If one notebook fails, that board stops and does not run the notebooks after it. The other board continues.
8. After a round starts, the program waits `pynq_wait_threshold` seconds before it is allowed to start another round. A board that is still measuring is not started again.

The screen keeps four status lines: oven reading, how long the temperature has been stable, what each board is doing, and the wait until the next round.

## Where the results go

Results are written under `data/` in this repository. Git does not track that folder.

```text
data/
  temperature_data/
    temperature_data.csv          oven temperature for the whole run
    live_temperature_data.csv     same log, kept short for a live plot
  boards/
    board_01/
      pynq_run_data/              CSVs copied back from 169.254.168.99
      logs/                       text log for that board
    board_02/
      pynq_run_data/              CSVs copied back from 169.254.168.100
      logs/
```

Each measurement file is named like `output_data_11_80C_0_2_5_time_0.csv`. The number after `output_data_` is the test (`11`, `21`, or `51`). The number before `C` is the temperature label. The three numbers before `_time_` are how long the oven had been stable, as hours, minutes, and seconds. The last number counts repeated copies so a new file does not overwrite an old one.

`board_01` and `board_02` never write into each other's folders. The oven log is shared because there is only one oven.

## What not to touch

- `boards.py` lists the boards, their IP addresses, and the three notebooks. Adding or disabling a board is a TA change.
- `run/notebooks/` contains older notebook copies (`rofc_not`, `rofc_nor`, `rofc_nand`). The main run does not execute them.
- `hardware_versions/` is the FPGA project. It is not used when you start `run/process_main.py`.
- `tests/` is an old sample of oven register values.

The oven serial port is `COM4` inside `run/process_main.py`. Change that only if the TA says the oven is on a different port.

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

To add a third board later, append one entry to `BOARDS` in `boards.py`. Set `"enabled": False` to leave a board in the list without starting it. Both cards must already have `rofc_11.ipynb`, `rofc_21.ipynb`, and `rofc_51.ipynb` in `/home/xilinx/jupyter_notebooks/rofc/`.

On the lab PC, results can be sent to the old data folder by setting `OUTPUT_ROOT` in `boards.py` to `Path(r"C:\pynq\pynq_data")`. The per-board folders are still created under that path.

Python packages used by the main run are `minimalmodbus`, `paramiko`, `pandas`, and `matplotlib`.
