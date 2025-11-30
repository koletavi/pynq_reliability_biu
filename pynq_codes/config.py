# Configuration overrides for process_main.py
# Edit the values below to change the oven process behavior.

# temperature_list: list of setpoint temperatures in degrees Celsius.
# Example: [90, 100, 105, 110]

# Note: values should be numbers (int). Keep as a Python list.
temperature_list = [90, 100, 105, 110]

# temperature_enable: list of 0/1 flags indicating if the corresponding
# temperature in `temperature_list` is enabled (1) or disabled (0).
# Example: [1, 0, 0, 0]

# Note: if one value is enabled (1) all previous values should be enabled (1) as well.
temperature_enable = [1, 0, 0, 0]

# time_list: list of times in minutes. First value is rise time, second is hold time.
# Example: [10, 60*35]  # rise time 10 minutes, hold time 35 hours (if intended)

# Use integers or expressions (they will be evaluated by Python).
time_list = [10, 60*35]

# pynq_wait_threshold: minimum time to wait between triggering the PYNQ-Z2 in seconds.
# Example: 60*30  # 30 minutes
pynq_wait_threshold = 60*30

