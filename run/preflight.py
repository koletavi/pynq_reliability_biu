"""Checks the lab PC before a run. Does not program the oven.

The oven preflight may open the oven port and then close it. It does not
write a temperature program. The board preflight never opens the port.
"""

import argparse
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
import boards

REQUIRED_IMPORTS = ("minimalmodbus", "paramiko", "pandas", "matplotlib")
CALL_TA = "Leave the script. Call the TA."
NOTEBOOK_PARAM_NAMES = ("ctr_run_time", "ro_sel", "sample_size")
RO_SEL_VALUES = (1, 3, 5, 7)
MAX_CTR_RUN_TIME = 2**32 - 1
DEFAULT_NOTEBOOK_PARAMS = {
    "rofc_11.ipynb": {"ctr_run_time": 100_000_000, "ro_sel": 1, "sample_size": 100},
    "rofc_21.ipynb": {"ctr_run_time": 300_000_000, "ro_sel": 3, "sample_size": 100},
    "rofc_51.ipynb": {"ctr_run_time": 300, "ro_sel": 5, "sample_size": 100},
}


def _required_notebook_names():
    return [name for name, _csv in boards.NOTEBOOKS]


def _positive_int(value, name):
    if isinstance(value, bool) or not isinstance(value, int):
        raise SystemExit(f"Configuration error: `{name}` must be an integer.")
    if value < 1:
        raise SystemExit(f"Configuration error: `{name}` must be at least 1.")
    return value


def _copy_notebook_params(source):
    copied = {}
    for name, values in source.items():
        copied[name] = {key: values[key] for key in NOTEBOOK_PARAM_NAMES}
    return copied


def _validate_notebook_params(raw):
    """Return one validated value set for every notebook the run calls."""
    expected = _required_notebook_names()
    if not isinstance(raw, dict):
        raise SystemExit("Configuration error: `notebook_params` must be a dict of notebook names.")
    missing = [name for name in expected if name not in raw]
    if missing:
        raise SystemExit(
            "Configuration error: `notebook_params` is missing " + ", ".join(missing) + "."
        )
    unknown = [name for name in raw if name not in expected]
    if unknown:
        raise SystemExit(
            "Configuration error: `notebook_params` has unknown notebook "
            + ", ".join(unknown)
            + "."
        )
    validated = {}
    for name in expected:
        entry = raw[name]
        if not isinstance(entry, dict):
            raise SystemExit(f"Configuration error: `notebook_params['{name}']` must be a dict.")
        extra = [key for key in entry if key not in NOTEBOOK_PARAM_NAMES]
        if extra:
            raise SystemExit(
                f"Configuration error: `notebook_params['{name}']` has unknown setting {extra[0]}."
            )
        absent = [key for key in NOTEBOOK_PARAM_NAMES if key not in entry]
        if absent:
            raise SystemExit(
                f"Configuration error: `notebook_params['{name}']` is missing {absent[0]}."
            )
        ctr_run_time = _positive_int(entry["ctr_run_time"], f"notebook_params['{name}']['ctr_run_time']")
        if ctr_run_time > MAX_CTR_RUN_TIME:
            raise SystemExit(
                f"Configuration error: `notebook_params['{name}']['ctr_run_time']` must be at most {MAX_CTR_RUN_TIME}."
            )
        ro_sel = _positive_int(entry["ro_sel"], f"notebook_params['{name}']['ro_sel']")
        if ro_sel not in RO_SEL_VALUES:
            raise SystemExit(
                f"Configuration error: `notebook_params['{name}']['ro_sel']` must be 1, 3, 5, or 7."
            )
        sample_size = _positive_int(entry["sample_size"], f"notebook_params['{name}']['sample_size']")
        validated[name] = {
            "ctr_run_time": ctr_run_time,
            "ro_sel": ro_sel,
            "sample_size": sample_size,
        }
    return validated


def notebook_params_from_module(user_config, announce=True):
    """Read notebook_params from an already loaded config module."""
    if not hasattr(user_config, "notebook_params"):
        params = _copy_notebook_params(DEFAULT_NOTEBOOK_PARAMS)
        if announce:
            print("No `notebook_params` in config.py — using the built-in notebook values.")
    else:
        params = _validate_notebook_params(user_config.notebook_params)
    if announce:
        for name in _required_notebook_names():
            values = params[name]
            print(
                f"Using `{name}`: ctr_run_time={values['ctr_run_time']}, "
                f"ro_sel={values['ro_sel']}, sample_size={values['sample_size']}"
            )
    return params


def load_notebook_params(config_path, announce=True):
    """Load run/config.py and return the notebook values that will be written to the boards."""
    if not os.path.exists(config_path):
        return notebook_params_from_module(object(), announce=announce)
    spec = importlib.util.spec_from_file_location("user_notebook_config", config_path)
    user_config = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    try:
        spec.loader.exec_module(user_config)
    except SystemExit:
        raise
    except Exception as exc:
        raise SystemExit(f"Error loading config.py: {exc}")
    return notebook_params_from_module(user_config, announce=announce)


def load_recipe(config_path, temperature_list, temperature_enable, time_list, pynq_wait_threshold, oven_port="COM4"):
    """Apply run/config.py using the existing validators.

    Returns temperature_list, temperature_enable, time_list, pynq_wait_threshold, oven_port.
    A missing file keeps the defaults. The first invalid value raises SystemExit.
    """
    if not os.path.exists(config_path):
        print("No `config.py` found — using built-in defaults.")
        return temperature_list, temperature_enable, time_list, pynq_wait_threshold, oven_port

    try:
        spec = importlib.util.spec_from_file_location("user_config", config_path)
        user_config = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(user_config)
        print(f"Loaded configuration from {config_path}")

        def _is_list_of_numbers_strict(v, name):
            if not isinstance(v, list) or not all(isinstance(x, (int, float)) for x in v):
                raise SystemExit(f"Configuration error: `{name}` must be a list of numbers.")
            return True

        def _is_list_of_ints_0_1_strict(v, name):
            if not isinstance(v, list):
                raise SystemExit(f"Configuration error: `{name}` must be a list of 0/1 values.")
            for x in v:
                if int(x) not in (0, 1):
                    raise SystemExit(f"Configuration error: `{name}` contains non-binary value {x}.")
            return True

        if hasattr(user_config, "temperature_list"):
            _is_list_of_numbers_strict(user_config.temperature_list, "temperature_list")
            candidate = [int(x) for x in user_config.temperature_list]
            for x in candidate:
                if x < 80 or x > 110:
                    raise SystemExit(f"Configuration error: temperature_list value {x} out of allowed range [80, 110].")
            for a, b in zip(candidate, candidate[1:]):
                if not (b > a):
                    raise SystemExit(f"Configuration error: temperature_list must be strictly increasing (found {a} then {b}).")
            temperature_list = candidate
            print(f"Using `temperature_list` from config: {temperature_list}")

        if hasattr(user_config, "temperature_enable"):
            _is_list_of_ints_0_1_strict(user_config.temperature_enable, "temperature_enable")
            candidate = [int(x) for x in user_config.temperature_enable]
            if len(candidate) != len(temperature_list):
                raise SystemExit("Configuration error: `temperature_enable` length must match `temperature_list` length.")
            seen_zero = False
            for i, val in enumerate(candidate):
                if seen_zero and val == 1:
                    raise SystemExit(f"Configuration error: `temperature_enable` must be ones followed by zeros (prefix rule violated at index {i}).")
                if val == 0:
                    seen_zero = True
            temperature_enable = candidate
            print(f"Using `temperature_enable` from config: {temperature_enable}")

        if hasattr(user_config, "time_list"):
            _is_list_of_numbers_strict(user_config.time_list, "time_list")
            candidate = [int(x) for x in user_config.time_list]
            if len(candidate) != 2:
                raise SystemExit("Configuration error: `time_list` must contain exactly two values (rise and hold).")
            if candidate[0] < 10 or candidate[1] < 10:
                raise SystemExit("Configuration error: Both values in `time_list` must be at least 10 minutes.")
            time_list = candidate
            print(f"Using `time_list` from config: {time_list}")

        if hasattr(user_config, "pynq_wait_threshold"):
            if not isinstance(user_config.pynq_wait_threshold, (int, float)):
                raise SystemExit("Configuration error: `pynq_wait_threshold` must be a number (seconds).")
            candidate = int(user_config.pynq_wait_threshold)
            if candidate < 60 * 2:
                raise SystemExit(f"Configuration error: `pynq_wait_threshold` must be at least {60 * 2} seconds.")
            pynq_wait_threshold = candidate
            print(f"Using `pynq_wait_threshold` from config: {pynq_wait_threshold} seconds")

        if hasattr(user_config, "oven_port"):
            port = user_config.oven_port
            if not isinstance(port, str) or not port.strip():
                raise SystemExit("Configuration error: `oven_port` must be a port name such as COM4.")
            oven_port = port.strip()

        notebook_params_from_module(user_config, announce=True)
        return temperature_list, temperature_enable, time_list, pynq_wait_threshold, oven_port
    except SystemExit:
        raise
    except Exception as exc:
        raise SystemExit(f"Error loading config.py: {exc}")


def import_problems():
    problems = []
    for name in REQUIRED_IMPORTS:
        try:
            __import__(name)
        except Exception:
            problems.append(f"Python cannot import {name}. {CALL_TA}")
    return problems


def oven_port_problem(oven_port):
    """Return a sentence if the port cannot be opened. Do not write to the oven."""
    try:
        import minimalmodbus
        instrument = minimalmodbus.Instrument(oven_port, 1)
        instrument.serial.timeout = 1
        instrument.serial.close()
    except Exception:
        return f"Oven port {oven_port} cannot be opened. {CALL_TA}"
    return None


def _ping_ok(ip):
    try:
        completed = subprocess.run(
            ["ping", "-n", "1", "-w", "1000", ip],
            capture_output=True,
            text=True,
            timeout=8,
        )
    except Exception:
        return False
    return completed.returncode == 0


def _remote_file_exists(ssh, path):
    _stdin, stdout, _stderr = ssh.exec_command(f"test -f {path} && echo yes || echo no")
    answer = stdout.read().decode(errors="replace").strip()
    return answer == "yes"


def board_problems(board_list):
    """Ping, SSH, and notebook checks for the boards in this list only."""
    problems = []
    try:
        import paramiko
    except Exception:
        paramiko = None

    for board in board_list:
        ip = board["ip"]
        label = f"{board['id']} at {ip}"
        if not _ping_ok(ip):
            problems.append(f"{label} did not answer a ping. {CALL_TA}")
            continue
        if paramiko is None:
            continue

        ssh = None
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            username = board.get("username", boards.USERNAME)
            password = board.get("password", boards.PASSWORD)
            ssh.connect(
                ip,
                username=username,
                password=password,
                timeout=5,
                banner_timeout=5,
                auth_timeout=5,
            )
        except Exception:
            problems.append(f"{label} did not accept SSH. {CALL_TA}")
            if ssh is not None:
                try:
                    ssh.close()
                except Exception:
                    pass
            continue

        try:
            remote_dir = board.get("remote_notebook_dir", boards.REMOTE_NOTEBOOK_DIR)
            for notebook, _csv in boards.NOTEBOOKS:
                remote_path = remote_dir + notebook
                try:
                    found = _remote_file_exists(ssh, remote_path)
                except Exception:
                    found = False
                if not found:
                    problems.append(f"{board['id']} is missing {remote_path}. {CALL_TA}")
        finally:
            try:
                ssh.close()
            except Exception:
                pass
    return problems


def lock_problems(board_list, marker_names):
    """One sentence for each lock marker that is present."""
    problems = []
    for board in board_list:
        for name in marker_names:
            path = boards.board_output_dir(board["id"]) / name
            if path.is_file():
                problems.append(f"{board['id']} is held by {name}.")
    return problems


def output_root_problem():
    root = boards.OUTPUT_ROOT
    probe = root / ".write_test"
    try:
        root.mkdir(parents=True, exist_ok=True)
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except Exception:
        return f"The results folder cannot be written ({root}). {CALL_TA}"
    return None


def _finish(problems, announce=True):
    if problems:
        for problem in problems:
            print(problem)
        return 1
    if announce:
        print("OK")
    return 0


def run_oven_checks(oven_port, board_list, announce=True):
    """Check imports, the oven port, and these boards.

    The caller loads run/config.py before this. Opens the oven port and closes
    it again. Does not write a temperature program.
    """
    problems = []
    problems.extend(import_problems())
    if not any(item.startswith("Python cannot import minimalmodbus") for item in problems):
        port_problem = oven_port_problem(oven_port)
        if port_problem:
            problems.append(port_problem)
    problems.extend(board_problems(board_list))
    root_problem = output_root_problem()
    if root_problem:
        problems.append(root_problem)
    problems.extend(lock_problems(board_list, ("BOARD_BUSY",)))
    return _finish(problems, announce=announce)


def run_board_checks(board_list):
    """Check one board-only job. Does not open the oven port."""
    problems = []
    problems.extend(import_problems())
    problems.extend(board_problems(board_list))
    root_problem = output_root_problem()
    if root_problem:
        problems.append(root_problem)
    problems.extend(lock_problems(board_list, ("OVEN_OWNED", "BOARD_BUSY")))
    return _finish(problems)


def main(argv=None):
    """Board preflight used by check_board_02.bat. Does not open the oven port."""
    parser = argparse.ArgumentParser(
        description="Check one PYNQ-Z2 before a board-only run. Does not open the oven port."
    )
    parser.add_argument("--board", required=True, help="Board id, for example board_02")
    args = parser.parse_args(argv)
    try:
        board = boards.board_by_id(args.board)
    except KeyError as exc:
        print(exc)
        return 1
    return run_board_checks([board])


if __name__ == "__main__":
    sys.exit(main())
