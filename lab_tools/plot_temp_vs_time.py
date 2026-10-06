import sys
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
import boards

# Path to the CSV file written by run/process_main.py
temperature_file = boards.TEMPERATURE_DIR / "temperature_data.csv"

print("\n\nMeasurement sequence complete or terminated.")
temp_data_file = pd.read_csv(temperature_file)
x = temp_data_file['time']
y = temp_data_file['Temperature']

# Create the plot
plt.figure(figsize=(10, 6))
plt.plot(x, y, label='Temperature (°C)', color='blue', marker='o', linestyle='-')
plt.xlabel('time (min)')
plt.ylabel('Temperature (°C)')
plt.title('Temperature vs time')
plt.grid(True)
plt.legend()

# Show the plot
plt.show()
