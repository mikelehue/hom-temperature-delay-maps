# -*- coding: utf-8 -*-
"""
Hong–Ou–Mandel (HOM) delay–temperature map acquisition
------------------------------------------------------

This script:
  • Sweeps crystal temperature with a Thorlabs TC200 (via `instruments` API).
  • Sweeps temporal delay by translating birefringent wedges with a Zaber stage
    (Binary protocol over serial).
  • At each (temperature, delay) point, acquires counts for V, H, C and their
    estimated errors using `meas_dir`.
  • Saves each temperature line as a CSV-like .dat file.

Dependencies (as used in the original code):
  - numpy, pandas
  - zaber.serial (BinarySerial, BinaryCommand)
  - instruments (Thorlabs TC200, via `instruments as ik`)
  - local helpers: meas_dir_1sec (and optionally meas_dir)

Notes:
  - COM ports and paths are hardcoded as in the original script. Adjust if needed.
  - The temperature LUT 'lut_T.xlsx' is loaded but not used here (kept for parity).
  - Output directory defaults to "11th waist".

Reference paper: https://doi.org/10.1016/j.optcom.2021.127461
"""

import os
import time
import numpy as np
import pandas as pd
import instruments as ik
from pathlib import Path
from zaber.serial import BinarySerial, BinaryCommand
from meas_dir import meas_dir
# from meas_dir import meas_dir  # Kept for parity if you need the alternative

# ----------------------------- User-configurable ----------------------------- #
COM_ZABER = "COM8"     # Zaber stage (Binary protocol)
COM_TC200 = "COM11"    # Thorlabs TC200 temperature controller
BAUD_TC200 = 115200

OUTPUT_DIR = Path("11th waist")  # where .dat files will be saved
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Temperature sweep (°C)
T_START = 45.0
T_STOP  = 75.0      # exclusive in np.arange; original code used 45→75 with step 0.2
T_STEP  = 0.2

# Delay scan
# Original constants: N_pas = 25.4 / 0.047625 * 10**3  ≈ 533333 (device counts)
#                     pas_g = 10000 (step, in device counts)
#                     N_grid = round(N_pas / pas_g) + 1
N_PAS_COUNTS = 25.4 / 0.047625 * 1_000   # total travel in controller counts
STEP_COUNTS  = 10_000                    # step per point (controller counts)
N_GRID       = int(round(N_PAS_COUNTS / STEP_COUNTS) + 1)
Y_COUNTS     = np.arange(0, N_PAS_COUNTS, STEP_COUNTS)

# Dwell / waits (seconds)
STAGE_SETTLE_S     = 1.0
TEMP_STABILIZE_S   = 60.0
PRE_LOOP_SLEEP_S   = 5.0
PRE_SCAN_HOME_WAIT = 10.0

# Meas params
# meas_dir(5) -> 5 seconds integration (as per original)
MEAS_SECONDS = 5


# ------------------------------- Helpers ------------------------------------ #
def init_temperature_controller(port: str, baud: int):
    """
    Open and configure the Thorlabs TC200.
    Returns the instrument handle.
    """
    tc = ik.thorlabs.TC200.open_serial(port, baud)
    # PID (from original code)
    tc.p = 120
    tc.i = 60
    tc.d = 30
    tc.enable = True
    return tc


def set_and_wait_temperature(tc, setpoint_c: float, stabilize_s: float = TEMP_STABILIZE_S):
    """
    Set temperature setpoint and wait for a fixed stabilization time.
    If you have a closed-loop criterion (e.g., readback within tolerance),
    replace this fixed wait with that logic.
    """
    tc.temperature_set = setpoint_c
    print(f"[TC200] Setpoint = {setpoint_c:.2f} °C. Stabilizing for {stabilize_s:.0f} s ...")
    time.sleep(stabilize_s)


def zaber_write(serial_port: BinarySerial, device_number: int, command_number: int, data: int | None = None):
    """
    Send a BinaryCommand to a Zaber device.
    - device_number: e.g., 0 (broadcast) or the device ID
    - command_number: Zaber Binary command number (e.g., 1=home; 20=move absolute)
    - data: optional data payload (e.g., target position in counts)
    """
    if data is None:
        cmd = BinaryCommand(device_number, command_number)
    else:
        cmd = BinaryCommand(device_number, command_number, int(data))
    serial_port.write(cmd)


def home_stage(port: BinarySerial):
    """
    Home the Zaber stage (broadcast command 1). Keep original 10 s wait.
    """
    print("[ZABER] Homing...")
    zaber_write(port, 0, 1)
    time.sleep(PRE_SCAN_HOME_WAIT)
    print("[ZABER] Home done.")


def move_stage_abs(port: BinarySerial, counts: int, settle_s: float = STAGE_SETTLE_S):
    """
    Move Zaber stage to an absolute position (in controller counts) and wait briefly.
    Binary command 20 = Move Absolute.
    """
    zaber_write(port, 0, 20, counts)
    time.sleep(settle_s)


def measure_point() -> tuple[float, float, float, float, float, float]:
    """
    Acquire a single measurement at the current (temperature, delay) point.
    Returns (V, H, C, eV, eH, eC).
    """
    V, H, C, eV, eH, eC = meas_dir_1sec(MEAS_SECONDS)
    return V, H, C, eV, eH, eC


# ------------------------------- Main script -------------------------------- #
def main():
    print("=== HOM delay–temperature map acquisition (rewrite) ===")

    # Open Zaber serial (Binary protocol)
    print(f"[ZABER] Opening port {COM_ZABER} ...")
    port_y = BinarySerial(COM_ZABER, timeout=10, inter_char_timeout=0.01)
    time.sleep(PRE_LOOP_SLEEP_S)

    # Load temperature LUT (kept for parity; not used below)
    if Path("lut_T.xlsx").exists():
        print("[INFO] Loading temperature LUT 'lut_T.xlsx' (not used directly).")
        temp_lut = pd.read_excel("lut_T.xlsx")
        _temp_lut_np = pd.DataFrame.to_numpy(temp_lut)
    else:
        print("[WARN] 'lut_T.xlsx' not found. Continuing without LUT.")
        _temp_lut_np = None

    # Init temperature controller
    print(f"[TC200] Opening controller at {COM_TC200} (baud {BAUD_TC200}) ...")
    tc = init_temperature_controller(COM_TC200, BAUD_TC200)

    # Initial temperature
    T_init = T_START
    print(f"[TC200] Setting initial temperature: {T_init:.2f} °C")
    tc.temperature_set = T_init

    # Prepare temperature vector
    T_vec = np.arange(T_START, T_STOP, T_STEP)

    # Prepare arrays for a single line (pre-allocated as in the original code)
    line_V  = np.zeros((N_GRID, 1))
    line_H  = np.zeros((N_GRID, 1))
    line_C  = np.zeros((N_GRID, 1))
    line_eV = np.zeros((N_GRID, 1))
    line_eH = np.zeros((N_GRID, 1))
    line_eC = np.zeros((N_GRID, 1))

    t0_global = time.time()

    try:
        for tset in T_vec:

            t0_line = time.time()

            # Home the stage before each temperature line (as in the original)
            home_stage(port_y)

            # Stabilize temperature
            set_and_wait_temperature(tc, tset, TEMP_STABILIZE_S)

            print("[HOM] Measuring delay line ...")
            jj = 0

            # Reset arrays for this line
            line_V.fill(0)
            line_H.fill(0)
            line_C.fill(0)
            line_eV.fill(0)
            line_eH.fill(0)
            line_eC.fill(0)

            # Delay sweep
            for pos_counts in Y_COUNTS:
                move_stage_abs(port_y, int(pos_counts), STAGE_SETTLE_S)

                # Acquire counts
                V, H, C, eV, eH, eC = measure_point()

                # Store
                line_V[jj, 0]  = V
                line_H[jj, 0]  = H
                line_C[jj, 0]  = C
                line_eV[jj, 0] = eV
                line_eH[jj, 0] = eH
                line_eC[jj, 0] = eC

                # Quick progress info: visibility proxy C/(V+H)
                denom = (V + H) if (V + H) != 0 else np.nan
                vis_proxy = C / denom if denom == denom else np.nan  # guard for NaN
                print(f"[{jj:03d}] C/(V+H) = {vis_proxy:.4f}   C = {C:.0f}")

                jj += 1

            # Save one temperature line
            # Original pattern: "11th waist/<temp>_pump_ha_det_txikienaena_01.dat"
            out_name = f"{round(tset, 1)}_pump_ha_det_txikienaena_01.dat"
            out_path = OUTPUT_DIR / out_name

            # Save in a compact CSV-like format, comma-separated, columns as in original
            data_tuple = (
                line_V[:, 0], line_H[:, 0], line_C[:, 0],
                line_eV[:, 0], line_eH[:, 0], line_eC[:, 0]
            )
            np.savetxt(
                out_path,
                np.vstack(data_tuple).T,   # shape (N, 6)
                delimiter=",",
                header="V,H,C,eV,eH,eC",
                comments=""
            )
            print(f"[SAVE] Wrote: {out_path.resolve()}")

            elapsed_line = time.time() - t0_line
            print(f"[TIMER] Line elapsed: {elapsed_line:.1f} s")

    finally:
        # Close hardware cleanly even if something fails
        try:
            BinarySerial.close(port_y)
            print("[ZABER] Port closed.")
        except Exception as e:
            print(f"[ZABER] Close error (ignored): {e}")

        try:
            # TC200 driver typically closes when object is GC'ed;
            # add any explicit close if your driver supports it.
            print("[TC200] (No explicit close method; ensure serial is released.)")
        except Exception as e:
            print(f"[TC200] Close error (ignored): {e}")

    elapsed_total = time.time() - t0_global
    print(f"[TIMER] Total elapsed: {elapsed_total:.1f} s")


if __name__ == "__main__":
    main()
