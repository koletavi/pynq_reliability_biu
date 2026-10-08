import sys
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
import boards

plt.style.use('fivethirtyeight')

LIVE_TEMPERATURE_FILE = boards.TEMPERATURE_DIR / "live_temperature_data.csv"

def animate(i):
    try:
        # Read the CSV file
        data = pd.read_csv(LIVE_TEMPERATURE_FILE)
        # Extract x and y data
        x = data['time']
        y = data['Temperature']
        
        # Clear the current axes
        plt.cla()
        # Plot the data
        plt.plot(x, y, label='Temperature', color='orange', marker='o', linestyle='-')
        plt.title('Temperature Over Time - LIVE')
        plt.xlabel('time (min)')
        plt.ylabel('Temperature Value (C)')
        plt.legend(loc='upper left')
        plt.tight_layout()
    except FileNotFoundError:
        print("live_temperature_data.csv not found. Start oven_board_01.bat and leave it running.")
    except pd.errors.EmptyDataError:
        print("CSV file is empty or corrupted.")
    except KeyError as e:
        print(f"Missing expected column in CSV: {e}")
    except Exception as e:
        print(f"Error reading data: {str(e)}")

def main():
    try:
        # Create the animation with 500ms interval (0.5 seconds)
        ani = FuncAnimation(plt.gcf(), animate, interval=500)
        # Show the plot
        plt.tight_layout()
        plt.show()
    except KeyboardInterrupt:
        print("\nAnimation interrupted by user.")
        plt.close('all')
        sys.exit(0)
    except Exception as e:
        print(f"Unexpected error: {e}")
        plt.close('all')
        sys.exit(1)

if __name__ == "__main__":
    main()