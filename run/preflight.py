"""Checks the lab PC can see the oven and both boards. Does not start the oven."""

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


def board_problems():
    problems = []
    try:
        import paramiko
    except Exception:
        paramiko = None

    for board in boards.enabled_boards():
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


def run_checks(oven_port):
    """Run every hardware check. Return 0 when all pass, 1 otherwise.

    Does not program the oven and does not start a temperature run.
    """
    problems = []
    problems.extend(import_problems())
    if not any(item.startswith("Python cannot import minimalmodbus") for item in problems):
        port_problem = oven_port_problem(oven_port)
        if port_problem:
            problems.append(port_problem)
    problems.extend(board_problems())
    root_problem = output_root_problem()
    if root_problem:
        problems.append(root_problem)

    if problems:
        for problem in problems:
            print(problem)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    config_path = os.path.join(os.path.dirname(__file__), "config.py")
    try:
        _temps, _enable, _times, _wait, port = load_recipe(
            config_path,
            [80, 90, 100, 110],
            [1, 0, 0, 0],
            [10, 60 * 35],
            60 * 30,
            "COM4",
        )
    except SystemExit as exc:
        if str(exc):
            print(exc)
        sys.exit(1)
    sys.exit(run_checks(port))
