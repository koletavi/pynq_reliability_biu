import pandas as pd
import matplotlib.pyplot as plt

# Path to the CSV file
temperature_file = r"C:\pynq\pynq_data\8_6_25_temp_vs_time.csv"

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
