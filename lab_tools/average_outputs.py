import matplotlib.pyplot as plt
import os
import sys
import csv
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
import boards


def plot_avg_bar_graph(csv_path, gate_type):
    """Reads the given CSV file and plots a bar graph of the average values in the last row.

    Uses a context manager to ensure the CSV file is closed even on exceptions.
    Closes the matplotlib figure after showing to free resources.
    """
    with open(csv_path, newline='') as f:
        reader = list(csv.reader(f))
    # file is closed here because of the with-block

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
            # Header is "<minutes>min_<index>" or "<YYYY_MM_DD>_<minutes>min_<index>".
            left, right = h.split('min_', 1)
            minutes = float(left.rsplit('_', 1)[-1])
            date_prefix = left[:left.rfind('_')] if '_' in left else ""
            if date_prefix:
                labels.append(f"{date_prefix}_{minutes:.2f}min_{right}")
            else:
                labels.append(f"{minutes:.2f}min_{right}")
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
    plt.close()  # free figure resources


# output_data_11_80C_2026_10_08_1_2_3_time_0.csv
# Older files without a date still match: output_data_11_80C_1_2_3_time_0.csv
pattern = re.compile(
    r"output_data_(\w+?)_(\d+C)_(?:(\d{4})_(\d{2})_(\d{2})_)?(\d+)_(\d+)_(\d+)_time_(\d+)\.csv$"
)


def measurement_parts(fname):
    """Return the name fields, or None when the file is not a measurement CSV."""
    match = pattern.match(fname)
    if not match:
        return None
    if match.group(3):
        day = f"{match.group(3)}_{match.group(4)}_{match.group(5)}"
    else:
        day = ""
    return {
        "gate": match.group(1),
        "temp": match.group(2),
        "date": day,
        "hours": int(match.group(6)),
        "minutes": int(match.group(7)),
        "seconds": int(match.group(8)),
        "index": int(match.group(9)),
    }


def parse_time(fname):
    """Sort by date, then elapsed time, then the file counter."""
    parts = measurement_parts(fname)
    if parts:
        elapsed = parts["hours"] * 3600 + parts["minutes"] * 60 + parts["seconds"]
        return (parts["date"], elapsed, parts["index"])
    return ("", 0, 0)

def group_files_by_temp(directory):
    # Group all files by temperature only
    groups = defaultdict(list)
    for fname in os.listdir(directory):
        parts = measurement_parts(fname)
        if parts:
            groups[parts["temp"]].append(fname)
    
    # Sort files within each group by time
    for temp in groups:
        groups[temp].sort(key=parse_time)
    return groups

def read_csv_ignore_zeros(filepath):
    with open(filepath, newline='') as f:
        reader = csv.reader(f)
        return [[float(cell) if cell not in ('0', '0.0', '') else None for cell in row] for row in reader]


def write_avg_csv_for_temp(temp, files, directory, avg_output_dir):
    # Group files by gate type
    gate_groups = defaultdict(list)
    for f in files:
        parts = measurement_parts(f)
        if parts:
            gate_groups[parts["gate"]].append(f)
    
    # Process each gate type separately
    for gate_type, gate_files in gate_groups.items():
        # Prepare header with time information in minutes and sort by time first
        header_info = []
        for f in gate_files:
            parts = measurement_parts(f)
            if parts:
                total_minutes = parts["hours"] * 60 + parts["minutes"] + (parts["seconds"] / 60)
                header_info.append((parts["date"], total_minutes, parts["index"], f))

        header_info.sort(key=lambda item: (item[0], item[1], item[2]))

        header = []
        for day, total_minutes, index, _fname in header_info:
            label = f"{total_minutes:.2f}min_{index}"
            if day:
                label = f"{day}_{label}"
            header.append(label)
        gate_files = [item[3] for item in header_info]

        # Now read CSV data in the sorted order so that data matches header/file order
        data = [read_csv_ignore_zeros(os.path.join(directory, f)) for f in gate_files]
        num_rows = max((len(d) for d in data), default=0)
    
        # Write output
        os.makedirs(avg_output_dir, exist_ok=True)
        avg_file = os.path.join(avg_output_dir, f"avg_output_data_{temp}_{gate_type}.csv")
        boards.clear_readonly(avg_file)

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

        boards.mark_readonly(avg_file)
        # Plot the bar graph for this gate type
        plot_avg_bar_graph(avg_file, gate_type)


def create_daily_summary_log(log_dir):
    """Fold this board's run logs into one daily file and remove the originals."""
    os.makedirs(log_dir, exist_ok=True)
    now = datetime.now()
    summary_name = f"pynq_log_{now.day:02d}_{now.month:02d}_{str(now.year)[-2:]}.log"
    summary_path = os.path.join(log_dir, summary_name)

    # collect existing logs excluding today's summary if present
    files = [f for f in os.listdir(log_dir) if f.lower().endswith('.log') and f != summary_name]
    if not files:
        return summary_path

    files.sort()
    with open(summary_path, 'w', encoding='utf-8') as outf:
        for fname in files:
            path = os.path.join(log_dir, fname)
            try:
                with open(path, 'r', encoding='utf-8') as inf:
                    outf.write(f"--- Start of {fname} ---\n")
                    outf.write(inf.read())
                    outf.write(f"\n--- End of {fname} ---\n\n")
            except Exception:
                continue

    # delete originals
    for fname in files:
        try:
            os.remove(os.path.join(log_dir, fname))
        except Exception:
            pass

    return summary_path


def main():
    boards_root = boards.BOARDS_ROOT
    if not boards_root.is_dir():
        print(f"No board results at {boards_root}")
        return

    found = False
    for board_dir in sorted(path for path in boards_root.iterdir() if path.is_dir()):
        data_dir = board_dir / "pynq_run_data"
        log_dir = board_dir / "logs"
        if not data_dir.is_dir():
            print(f"Skipping {board_dir.name}: no pynq_run_data")
            continue
        found = True
        print(f"Averaging {board_dir.name}")
        groups = group_files_by_temp(str(data_dir))
        if not groups:
            print(f"No measurement CSVs in {data_dir}")
        avg_dir = str(board_dir / "averages")
        for temp, files in groups.items():
            write_avg_csv_for_temp(temp, files, str(data_dir), avg_dir)
        try:
            if log_dir.is_dir():
                create_daily_summary_log(str(log_dir))
        except Exception:
            pass

    if not found:
        print(f"No pynq_run_data directories under {boards_root}")


if __name__ == "__main__":
    main()
