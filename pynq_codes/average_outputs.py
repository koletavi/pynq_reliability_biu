import matplotlib.pyplot as plt

def plot_avg_bar_graph(csv_path, gate_type):
    """Reads the given CSV file and plots a bar graph of the average values in the last row."""
    with open(csv_path, newline='') as f:
        reader = list(csv.reader(f))
        if not reader or len(reader) < 2:
            print("CSV file is empty or too short.")
            return
        headers = reader[0]
        avg_row = reader[-1]
        # Convert to float, skip empty or non-numeric and the 'Time' column
        values = []
        labels = []
        for h, v in zip(headers[1:], avg_row[1:]):  # Skip first column (Time)
            try:
                val = float(v)
                values.append(val)
                # Extract just the time and index from the header
                time_index = h.split('min_')  # Split at 'min_'
                labels.append(f"{float(time_index[0]):.2f}min_{time_index[1]}")
            except (ValueError, TypeError):
                continue
        plt.figure(figsize=(10, 6))
        plt.bar(labels, values)
        plt.xlabel('Time (minutes)')
        plt.ylabel('Average Value')
        plt.title(f'Average Values for {gate_type.upper()} Gates')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.show()
import os
import csv
import re
from collections import defaultdict

# Base directory for all data
LOCAL_OUTPUT_DIR = r"C:\pynq\pynq_data"
# Directory containing the input CSV files from PYNQ runs
LOCAL_PYNQ_DATA_DIR = os.path.join(LOCAL_OUTPUT_DIR, "pynq_run_data")
# Directory for averaged output files
AVG_OUTPUT_DIR = os.path.join(LOCAL_OUTPUT_DIR, "averages")


# Regex to match files like output_data_not_0C_1_2_3_time_4.csv
pattern = re.compile(r"output_data_(\w+?)_(\d+C)_(\d+)_(\d+)_(\d+)_time_(\d+)\.csv$")

def parse_time(fname):
    """Extract and convert time components to seconds for sorting"""
    match = pattern.match(fname)
    if match:
        hours = int(match.group(3))
        minutes = int(match.group(4))
        seconds = int(match.group(5))
        index = int(match.group(6))  # Use index for secondary sorting
        return (hours * 3600 + minutes * 60 + seconds, index)
    return (0, 0)

def group_files_by_temp(directory):
    # Group all files by temperature only
    groups = defaultdict(list)
    for fname in os.listdir(directory):
        match = pattern.match(fname)
        if match:
            temp = match.group(2)
            groups[temp].append(fname)
    
    # Sort files within each group by time
    for temp in groups:
        groups[temp].sort(key=parse_time)
    return groups

def read_csv_ignore_zeros(filepath):
    with open(filepath, newline='') as f:
        reader = csv.reader(f)
        return [[float(cell) if cell not in ('0', '0.0', '') else None for cell in row] for row in reader]


def write_avg_csv_for_temp(temp, files, directory):
    # Group files by gate type
    gate_groups = defaultdict(list)
    for f in files:
        match = pattern.match(f)
        if match:
            gate_type = match.group(1)
            gate_groups[gate_type].append(f)
    
    # Process each gate type separately
    for gate_type, gate_files in gate_groups.items():
        # Process files for the given temperature and gate type
        data = [read_csv_ignore_zeros(os.path.join(directory, f)) for f in gate_files]
        num_rows = max(len(d) for d in data)
        
        # Prepare header with time information in minutes
        header_info = []
        for f in gate_files:
            match = pattern.match(f)
            if match:
                hours = int(match.group(3))
                mins = int(match.group(4))
                secs = int(match.group(5))
                index = match.group(6)
                total_minutes = (hours * 60) + mins + (secs / 60)
                header_info.append((total_minutes, index, f))
        
        # Sort by time
        header_info.sort(key=lambda x: x[0])
        
        # Create sorted headers and reorganize files list to match
        header = [f"{h[0]:.2f}min_{h[1]}" for h in header_info]
        gate_files = [h[2] for h in header_info]
    
        # Write output
        os.makedirs(AVG_OUTPUT_DIR, exist_ok=True)
        avg_file = os.path.join(AVG_OUTPUT_DIR, f"avg_output_data_{temp}_{gate_type}.csv")
        
        with open(avg_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Time'] + header)  # Add 'Time' as first column header
            
            # Write data rows
            for row_idx in range(num_rows):
                row = [str(row_idx)]  # First column is the row index
                for d in data:
                    if row_idx < len(d):
                        if len(d[row_idx]) == 1:
                            val = d[row_idx][0]
                            row.append(val if val is not None else '')
                        else:
                            vals = [str(v) for v in d[row_idx] if v is not None]
                            row.append(','.join(vals) if vals else '')
                    else:
                        row.append('')
                writer.writerow(row)
                
            # Write average row
            avg_row = ['Average']  # Label for the average row
            for d in data:
                vals = []
                for row in d:
                    for v in row:
                        if v not in (None, 0.0):
                            vals.append(v)
                avg = sum(vals)/len(vals) if vals else ''
                avg_row.append(avg)
            writer.writerow(avg_row)
            
        # Plot the bar graph for this gate type
        plot_avg_bar_graph(avg_file, gate_type)


def main():
    groups = group_files_by_temp(LOCAL_PYNQ_DATA_DIR)
    for temp, files in groups.items():
        write_avg_csv_for_temp(temp, files, LOCAL_PYNQ_DATA_DIR)

if __name__ == "__main__":
    main()
