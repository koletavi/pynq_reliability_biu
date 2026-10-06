import sys
from pathlib import Path

import minimalmodbus
import time

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
import boards

# Nova SP540 Communication settings
PORT = 'COM4'
BAUDRATE = 9600
PARITY = 'N'
STOPBITS = 1
TIMEOUT = 1
SLAVE_ID = 1

# Local output directory
LOCAL_OUTPUT_DIR = str(boards.OUTPUT_ROOT)

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

arw = 1000
fuzzy = 1
cmod = 1

p1 = 75 
i1 = 160 
d1 = 130
rp1 = 70
rdv = 0

# process parameters
"""""
softer drive for less steady state error - NOT TESTED
arw = 300
fuzzy = 1
cmod = 1

p1 = 60 
i1 = 200 
d1 = 60
rp1 = 80
rdv = 0


aggresive overshoot supression
arw = 300
fuzzy = 1
cmod = 1

p1 = 55 
i1 = 120 
d1 = 80
rp1 = 100
rdv = 0

best so far- base
arw = 1000
fuzzy = 1
cmod = 1

p1 = 75 
i1 = 160 
d1 = 130
rp1 = 100
rdv = 0
"""

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
def calibrate_pid(instrument):
    try:
        instrument.write_register(
            registeraddress = 501-1, # set ARW
            value = arw, # Write value to register                
            functioncode = 6 # Function code 6 for writing a single register
        )
        time.sleep(0.05)  # Sleep to ensure the write is processed
        instrument.write_register(
            registeraddress = 502-1, # set FUZZY
            value = fuzzy, # Write value to register                
            functioncode = 6 # Function code 6 for writing a single register
        )
        instrument.write_register(
            registeraddress = 503-1, # set CMOD
            value = cmod, # Write value to register                
            functioncode = 6 # Function code 6 for writing a single register
        )
        instrument.write_register(
            registeraddress = 511-1, # set 1.P
            value = p1, # Write value to register                
            functioncode = 6 # Function code 6 for writing a single register
        )
        instrument.write_register(
            registeraddress = 512-1, # set 1.I
            value = i1, # Write value to register                
            functioncode = 6 # Function code 6 for writing a single register
        )
        instrument.write_register(
            registeraddress = 513-1, # set 1.D
            value = d1, # Write value to register                
            functioncode = 6 # Function code 6 for writing a single register
        )
        instrument.write_register(
            registeraddress = 519-1, # set RP1
            value = rp1, # Write value to register                
            functioncode = 6 # Function code 6 for writing a single register
        )
        instrument.write_register(
            registeraddress = 549-1, # set RDV
            value = rdv, # Write value to register                
            functioncode = 6 # Function code 6 for writing a single register
        )
        
        
        print("Completed caribrating PID")
    except Exception as e:
        print(f"Error calibrating PID: {e}")
        raise    

def main():
    try:
        instrument = initialize_instrument()
        calibrate_pid(instrument)    
    except minimalmodbus.NoResponseError as nre:
        print(f"\n\nNo response from the instrument: {nre}")
    except Exception as e:
        print(f"Error calibrating PID: {e}")
        raise

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProgram terminated by user")
    except Exception as e:
        print(f"Program terminated due to error: {str(e)}")