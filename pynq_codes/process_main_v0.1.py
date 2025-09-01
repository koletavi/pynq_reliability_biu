# this script should run the oven control system side and call the other script that handles the pynq side and live graphs

import minimalmodbus
import time
import subprocess
import os
import pandas as pd
import matplotlib.pyplot as plt

# Nova SP540 Communication settings
PORT = 'COM4'
BAUDRATE = 9600
PARITY = 'N'
STOPBITS = 1
TIMEOUT = 1
SLAVE_ID = 1

# Local output directory
LOCAL_OUTPUT_DIR = r"C:\pynq\pynq_data"

# List of registers to read (from d_reg_minimal_file.xlsx)
REGISTERS = [
    (1, "NPV"), (2, "NSP"), (3, "TSP"), (6, "MVOUT"), (9, "PIDNO"), (10, "NOWSTS"),
    (14, "ALSTS"), (17, "SIGNAL.STS"), (19, "ERROR"), (25, "PTNO"),
    (26, "SEG.NO"), (27, "END.SEG.NO"), (28, "RUN.TIME"), (29, "SET.TIME"),
    (31, "LINK.CODE"), (32, "RPT"), (33, "RST"), (34, "REN"), (36, "WAIT.TIME"),
    (111, "F.KEY,RST/P1/P2"), (112, "HOLD,OFF/ON"), (113, "STEP,OFF/ON"),
    (121, "AT"), (122, "AT-G"), (133, "PE-TM"), (135, "US1"), (136, "US2"),
    (137, "LOCK"), (138, "DI.SL"), (139, "DSP.H"), (140, "DSP.L"),
    (205, "HOLD SP"), (206, "HOLD TIME"), (301, "1.IST"), (302, "1.ISB"),
    (303, "1.ISH"), (304, "1.ISL"), (305, "1.ISD"), (306, "2.IST"),
    (307, "2.ISB"), (308, "2.ISH"), (309, "2.ISL"), (310, "2.ISD"),
    (311, "DO1"), (312, "DO2"), (313, "DO3"), (314, "DO4"), (401, "ALT1"),
    (402, "ALT2"), (403, "ALT3"), (406, "AL-1"), (407, "AL-2"), (408, "AL-3"),
    (411, "A1DB"), (412, "A2DB"), (413, "A3DB"), (416, "A1DY"), (417, "A2DY"),
    (418, "A3DY"), (421, "AL1.H"), (422, "AL2.H"), (423, "AL3.H"),
    (426, "AL1.L"), (427, "AL2.L"), (428, "AL3.L"), (501, "ARW"), (502, "FUZZY"),
    (503, "C.MOD"), (511, "1.P"), (512, "1.I"), (513, "1.D"), (514, "1.MR"),
    (519, "RP1"), (521, "2.P"), (522, "2.I"), (523, "2.D"), (524, "2.MR"),
    (529, "RP2"), (531, "3.P"), (532, "3.I"), (533, "3.D"), (534, "3.MR"),
    (539, "RHY"), (541, "4.P"), (542, "4.I"), (543, "4.D"), (544, "4.MR"),
    (549, "RDV"), (601, "IN-T"), (602, "INT-U"), (603, "IN.RH"), (604, "IN.RL"),
    (605, "IN.DP"), (606, "IN.SH"), (607, "IN.SL"), (608, "IN.FL"), (609, "BSL"),
    (610, "RSL"), (611, "BSP1"), (612, "BSP2"), (613, "BSP3"), (614, "D.FL14"),
    (615, "BS0"), (616, "BS1"), (617, "BS2"), (618, "BS3"), (619, "BS4"),
    (621, "OUT1"), (622, "OUT2"), (623, "OUT3"), (625, "SUB1"), (626, "SUB2"),
    (631, "HEAT2"), (633, "HEAT3"), (637, "O.ACT"), (638, "CT"), (641, "OH"),
    (642, "OL"), (646, "PO"), (651, "RET"), (652, "RETH"), (653, "RETL"),
    (661, "COM.P"), (662, "BAUD"), (663, "PRTY"), (664, "SBIT"), (665, "DLEN"),
    (666, "ADDR"), (667, "RP.TM"), (1001, "TMU"), (1002, "STC"), (1003, "WZ"),
    (1004, "WTM"), (1101, "1.LC"), (1102, "1.SSP"), (1104, "1.SP1"), (1105, "1.TM1"),
    (1106, "1.TS1"), (1107, "1.SP2"), (1108, "1.TM2"), (1109, "1.TS2"),
    (1110, "1.SP3"), (1111, "1.TM3"), (1112, "1.TS3"), (1113, "1.SP4"),
    (1114, "1.TM4"), (1115, "1.TS4"), (1116, "1.SP5"), (1117, "1.TM5"),
    (1118, "1.TS5"), (1119, "1.SP6"), (1120, "1.TM6"), (1121, "1.TS6"),
    (1122, "1.SP7"), (1123, "1.TM7"), (1124, "1.TS7"), (1125, "1.SP8"),
    (1126, "1.TM8"), (1127, "1.TS8"), (1128, "1.SP9"), (1129, "1.TM9"),
    (1130, "1.TS9"), (1131, "1.SPA"), (1132, "1.TMA"), (1133, "1.TSA"),
    (1134, "1.SPB"), (1135, "1.TMB"), (1136, "1.TSB"), (1137, "1.SPC"),
    (1138, "1.TMC"), (1139, "1.TSC"), (1140, "1.SPD"), (1141, "1.TMD"),
    (1142, "1.TSD"), (1143, "1.SPE"), (1144, "1.TME"), (1145, "1.TSE"),
    (1146, "1.SPF"), (1147, "1.TMF"), (1148, "1.TSF"), (1151, "1.RPT"),
    (1152, "1.RST"), (1153, "1.REN"), (1201, "2.LC"), (1202, "2.SSP"),
    (1204, "2.SP1"), (1205, "2.TM1"), (1206, "2.TS1"), (1207, "2.SP2"),
    (1208, "2.TM2"), (1209, "2.TS2"), (1210, "2.SP3"), (1211, "2.TM3"),
    (1212, "2.TS3"), (1213, "2.SP4"), (1214, "2.TM4"), (1215, "2.TS4"),
    (1216, "2.SP5"), (1217, "2.TM5"), (1218, "2.TS5"), (1219, "2.SP6"),
    (1220, "2.TM6"), (1221, "2.TS6"), (1222, "2.SP7"), (1223, "2.TM7"),
    (1224, "2.TS7"), (1225, "2.SP8"), (1226, "2.TM8"), (1227, "2.TS8"),
    (1228, "2.SP9"), (1229, "2.TM9"), (1230, "2.TS9"), (1231, "2.SPA"),
    (1232, "2.TMA"), (1233, "2.TSA"), (1234, "2.SPB"), (1235, "2.TMB"),
    (1236, "2.TSB"), (1237, "2.SPC"), (1238, "2.TMC"), (1239, "2.TSC"),
    (1240, "2.SPD"), (1241, "2.TMD"), (1242, "2.TSD"), (1243, "2.SPE"),
    (1244, "2.TME"), (1245, "2.TSE"), (1246, "2.SPF"), (1247, "2.TMF"),
    (1248, "2.TSF"), (1251, "2.RPT"), (1252, "2.RST"), (1253, "2.REN")
]

#FIXME: Change these values as needed

# process parameters
lc = 0 # LC: Loop Control - 0=RPT 1=HOLD 2=P1 3=P2
ssp = 25 # SSP: starting setpoint in degrees Celsius
temperature_list = [ 30 , 35 , 40 , 45 ]
temperature_enable = [ 1 , 0 , 0 , 0 ] # Enable or disable each temperature in the list 1 = enabled, 0 = disabled
time_list = [ 60 , 30 ] # rise time and hold time in minutes

measurements_per_temperature = 2  # Number of measurements per temperature

# stability parameters
stability_standard_deviation = 1  # Standard deviation threshold for stability
stability_threshold = 3*60  # Number of consecutive stable readings before considering the process stable about 3 each second

PYNQ_RUN_SCRIPT = r"C:\pynq\python_codes\complete_modular_script\pynq_run_script.py"  # Path to the script that runs on the PYNQ-Z2

#--------------------------------#
##### Oven Control Functions #####
#--------------------------------#

# Initialize the Modbus instrument with the specified communication settings. - 0 seconds wait
def initialize_instrument():
    try:
        instrument = minimalmodbus.Instrument(PORT, SLAVE_ID)
        instrument.serial.baudrate = BAUDRATE
        instrument.serial.parity = PARITY
        instrument.serial.stopbits = STOPBITS
        instrument.serial.timeout = TIMEOUT
        instrument.mode = minimalmodbus.MODE_RTU
        print("Modbus instrument initialized successfully.")
        return instrument
    except Exception as e:
        print(f"Failed to initialize Modbus instrument: {e}")
        raise

# Program segment 1: Write the first segment of the program to the instrument. - 0.9 seconds wait
def program_segment_1(instrument):
    try:
        pivot_register = 1101  # Starting register for segment 1
        input_list = [ 
            lc*10, ssp*10 , # LC and SSP
            temperature_list[0]*10 , time_list[0]*temperature_enable[0] ,  # rise time 1: SP1 TM1
            temperature_list[0]*10 , time_list[1]*temperature_enable[0] ,  # hold time 1: SP2 TM2
            temperature_list[1]*10 , time_list[0]*temperature_enable[1] ,  # rise time 2: SP3 TM3
            temperature_list[1]*10 , time_list[1]*temperature_enable[1] ,  # hold time 2: SP4 TM4
            temperature_list[2]*10 , time_list[0]*temperature_enable[2] ,  # rise time 3: SP5 TM5
            temperature_list[2]*10 , time_list[1]*temperature_enable[2] ,  # hold time 3: SP6 TM6
            temperature_list[3]*10 , time_list[0]*temperature_enable[3] ,  # rise time 4: SP7 TM7
            temperature_list[3]*10 , time_list[1]*temperature_enable[3]    # hold time 4: SP8 TM8
        ]
        for i in range(len(input_list)):
            instrument.write_register(
                registeraddress = pivot_register-1, # Register address starts from 0
                value = input_list[i], # Write value to register
                functioncode = 6 # Function code 6 for writing a single register
            )
            print(f"{i} wrote:\t{pivot_register}:\t{input_list[i]}")
            time.sleep(0.05)  # Sleep to ensure the write is processed
            if (pivot_register-1099)%3 == 0:
                pivot_register += 2 
            else:
                pivot_register += 1
        print("Completed programming segment 1.")
    except Exception as e:
        print(f"Error programming segment 1: {e}")
        raise    

# Activate the P1 key to start the program. 3.05 seconds wait
def p1_key_activate(instrument):
    try:
        register_address = 111  # Register address for P1 key activation
        instrument.write_register(
            registeraddress = register_address - 1,  # Register address starts from 0
            value = 2,  # Activate P1 key
            functioncode = 6  # Function code 6 for writing a single register
        )
        time.sleep(3)  # Sleep to ensure the write is processed
        instrument.write_register(
            registeraddress = register_address - 1,  # Register address starts from 0
            value = 0,  # Deactivate P1 key
            functioncode = 6  # Function code 6 for writing a single register
        )
        time.sleep(0.05)  # Sleep to ensure the write is processed
        print("\n\n### proccess 1 started successfully. ###\n\n")
    except ValueError as ve:
        print(f"Value error activating P1 key: {ve}")
        raise    
    except Exception as e:
        print(f"Error activating P1 key: {e}")
        raise

# Sample the controller by reading the NPV, NSP, and PTNO registers. - 0.15 seconds wait
def sample_controller(instrument, start_time=0, expected_run_time=0, filename=None, live_filename=None):
    try:
        npv = instrument.read_register(0)/10  # Read NPV register
        time.sleep(0.05)  # Sleep to ensure the read is processed
        nsp = instrument.read_register(1)/10  # Read NSP register
        time.sleep(0.05)  # Sleep to ensure the read is processed
        ptno = instrument.read_register(24)  # Read PTNO register
        time.sleep(0.05)  # Sleep to ensure the read is processed

        fin_hours = expected_run_time // 3600  # Calculate expected hours
        fin_minutes = (expected_run_time % 3600) // 60  # Calculate expected minutes
        fin_seconds = expected_run_time % 60  # Calculate expected seconds

        elapsed_time = time.time() - start_time  # Calculate elapsed time
        hours, rem = divmod(elapsed_time, 3600)  # Convert to hours
        minutes, seconds = divmod(rem, 60)  # Convert remaining seconds to minutes
        print(f"\r\033[2KTIME: {int(hours):02d}:{int(minutes):02d}:{seconds:04.2f}/{int(fin_hours):02d}:{int(fin_minutes):02d}:{fin_seconds:04.2f} - NPV: {npv}, NSP: {nsp}", end="", flush=True)
        
        append_to_csv(filename, "time", "Temperature", elapsed_time, npv, False)  # Append time and NPV to CSV file
        append_to_csv(live_filename, "time", "Temperature", elapsed_time, npv, True)  # Append time and NPV to live CSV file
        stable = abs(npv - nsp) < stability_standard_deviation  # Check if the process is stable
        
        return [ptno, stable, npv]  # Return the process number and stability status
    except minimalmodbus.NoResponseError as nre:
        print(f"\r\033[2KNo response from the instrument: {nre}")
        return [0, False, 0]
    except Exception as e:
        print(f"\r\033[2KError reading registers: {e}")
        return [0, False, 0]  # Return 0 for PTNO and False for stability in case of error

#--------------------------------#
##### CSV handling Functions #####
#--------------------------------#

# create_csv: Create a new CSV file with an index column and a value column. - 0 seconds wait 
def create_csv(filename, time_column, value_column):
    """Create a new CSV file with an index column and a value column."""
    df = pd.DataFrame(columns=[time_column, value_column])
    df.to_csv(filename, index=False)

# append_to_csv: Append a value to the CSV value column with an auto-incrementing index - 0 seconds wait
def append_to_csv(filename, time_column, value_column, time_value, value, live=False):
    """Append a value to the CSV value column with an auto-incrementing index"""
    # Check if file exists, create if it doesn't
    if not os.path.exists(filename):
        create_csv(filename, time_column, value_column)
    
    # Read current CSV
    df = pd.read_csv(filename)
    
    # Create new row
    new_row = pd.DataFrame({time_column: [time_value], value_column: [value]})
    
    # If DataFrame is empty, use new_row directly
    if df.empty:
        df = new_row
    else:
        # Append new row with concat for non-empty DataFrame
        df = pd.concat([df, new_row], ignore_index=True)
    
    if live and len(df) > 10000:
        df = df.tail(10000)  # Keep only the last 10000 rows for live data
    
    # Save updated CSV
    df.to_csv(filename, index=False)

#-------------------------------------#
##### PYNQ-Z2 Execution Functions #####
#-------------------------------------#

# Execute the PYNQ-Z2 notebook externally using a subprocess. - 0 seconds wait
def execute_notebook_externally(previous_process=None, temp=lc):
    try:
        if previous_process is not None:
            # Check if the previous process is still running
            pynq_state = previous_process.poll()
            if pynq_state is None:
                return previous_process
        pynq_process = subprocess.Popen(["python3", PYNQ_RUN_SCRIPT, str(temp)], shell=False)
        return pynq_process  # Start a new process to run the PYNQ-Z2 script
    except Exception as e:
        print(f"\nError executing PYNQ-Z2 script: {e}")
        return None

def main():
    try:
        print("=== Starting Temperature Control and Data Collection ===\n")

        #----------------------------------------#
        #------- Initialization and Setup -------#
        #----------------------------------------#
        print("=== Initialization and Setup ===\n")

        # Ensure the local output directory exists
        temperature_file = os.path.join(LOCAL_OUTPUT_DIR, "temperature_data.csv")
        live_temperature_file = os.path.join(LOCAL_OUTPUT_DIR, "live_temperature_data.csv")
        # Create csv files
        create_csv(temperature_file, "time", "Temperature")  # Create initial CSV
        create_csv(live_temperature_file, "time", "Temperature")  # Create live temperature CSV

        # per-run time parameters
        expected_run_time = sum(time_list)*sum(temperature_enable)  # Calculate expected run time in seconds
        start_time = time.time()  # Record the start time of the process
        
        # Initialize the Modbus instrument
        instrument = initialize_instrument()
        
        # Program segment 1
        program_segment_1(instrument)

        #-----------------------------------------#
        #---- Process Control and Monitoring -----#
        #-----------------------------------------#
        print("\n=== Process Control and Monitoring ===\n")

        # Activate process using P1 key
        p1_key_activate(instrument)

        completed_temperatures = set()  # List to keep track of completed temperatures
        stability_counter = 0  # Initialize stability counter
        pynq_process = None  # Initialize PYNQ-Z2 process variable
        measurement_number = 0  # Initialize measurement number
        status_line1 = ""  # Line for stability messages
        status_line2 = ""  # Line for PYNQ-Z2 status

        while True:
            # Sample the controller (prints to first display line)
            [ptno, stable, npv] = sample_controller(instrument, start_time, expected_run_time, temperature_file, live_temperature_file)
            current_temperature = round(npv)  # npv is the current temperature in degrees Celsius
            
            # Move to status line 1 (second display line)
            print("\033[1E\033[2K", end="", flush=True)  # Move down 1 line, clear it
            print(status_line1, end="", flush=True)  # Print stability status
            
            # Move to status line 2 (third display line)
            print("\033[1E\033[2K", end="", flush=True)  # Move down 1 line, clear it
            print(status_line2, end="", flush=True)  # Print PYNQ-Z2 status
            
            # Return cursor to first display line
            print("\033[2F", end="", flush=True)  # Move up 2 lines to sample data line

            if ptno == 0:
                break  # Exit loop if PTNO is 0 (indicating process completion)
            
            if stable:
                stability_counter += 1
            else:
                stability_counter = 0
                status_line1 = ""  # Clear stability message when not stable

            # Check if the current temperature is stable and in the temperature list
            if (current_temperature not in completed_temperatures and
                current_temperature in temperature_list and 
                stability_counter >= stability_threshold):
                
                elapsed_time = time.time() - start_time
                hours, rem = divmod(elapsed_time, 3600)
                minutes, seconds = divmod(rem, 60)
                status_line1 = f"Process is stable at {int(hours):02d}:{int(minutes):02d}:{seconds:04.2f}, sampling pynq z2"
                
                pynq_process = execute_notebook_externally(pynq_process, current_temperature)
                if pynq_process is not None and pynq_process.poll() is None:
                    status_line2 = "PYNQ-Z2 script is running."
                else:
                    measurement_number += 1
                    status_line2 = f"PYNQ-Z2 script has completed {measurement_number} times at {current_temperature}°C."
                
                if measurement_number >= measurements_per_temperature:
                    completed_temperatures.add(current_temperature)
                    measurement_number = 0
                    status_line1 = ""  # Clear stability message after completion
                    status_line2 = ""  # Clear PYNQ-Z2 status after completion

    except minimalmodbus.NoResponseError as nre:
        print(f"\n\nNo response from the instrument: {nre}")
        return
    except Exception as e:
        print(f"\n\nError during initialization: {e}")
        return
    finally:
        print("\n\nMeasurement sequence complete or terminated.")
        temp_data_file = pd.read_csv(temperature_file)
        x = temp_data_file['time']
        y = temp_data_file['Temperature']

        # Create the plot
        plt.figure(figsize=(10, 6))
        plt.plot(x, y, label='Temperature (°C)', color='blue', marker='o', linestyle='-')
        plt.xlabel('time')
        plt.ylabel('Temperature (°C)')
        plt.title('Temperature vs time')
        plt.grid(True)
        plt.legend()

        # Show the plot
        plt.show()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProgram terminated by user")
    except Exception as e:
        print(f"Program terminated due to error: {str(e)}")
