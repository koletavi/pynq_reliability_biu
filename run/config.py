# Edit only this file. The oven run and the board-only run read it at start.
# Invalid values stop the program before the oven is touched.

# temperature_list: list of setpoint temperatures in degrees Celsius.
# Example: [80, 90, 100, 110]

# Note: values should be numbers (int). Keep as a Python list.
temperature_list = [80, 90, 100, 110]

# temperature_enable: list of 0/1 flags indicating if the corresponding
# temperature in `temperature_list` is enabled (1) or disabled (0).
# Example: [1, 0, 0, 0]

# Note: if one value is enabled (1) all previous values should be enabled (1) as well.
temperature_enable = [1, 0, 0, 0]

# time_list: list of times in minutes. First value is rise time, second is hold time.
# Example: [10, 60*35]  # rise time 10 minutes, hold time 35 hours (if intended)

# Use integers or expressions (they will be evaluated by Python).
time_list = [10, 60*1]

# pynq_wait_threshold: minimum time to wait between triggering the PYNQ-Z2 in seconds.
# Example: 60*30  # 30 minutes
pynq_wait_threshold = 60*10

# oven_port: serial port of the Nova controller. Optional.
# Leave this unset unless the TA tells you to change it. The default is COM4.
# oven_port = "COM4"

# notebook_params: values written into the notebooks on the PYNQ card before each run.
# The copies in run/notebooks/ are not executed.
# ctr_run_time: run length in 100 MHz cycles.
# ro_sel: ring oscillator. 1=not, 3=nor, 5 or 7=nand.
# sample_size: number of samples. It has to match the bitstream on that card.
notebook_params = {
    "rofc_11.ipynb": {"ctr_run_time": 300_000_000, "ro_sel": 1, "sample_size": 100},
    "rofc_21.ipynb": {"ctr_run_time": 300_000_000, "ro_sel": 3, "sample_size": 100},
    "rofc_51.ipynb": {"ctr_run_time": 300_000_000, "ro_sel": 5, "sample_size": 100},
}

