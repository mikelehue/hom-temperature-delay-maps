# -*- coding: utf-8 -*-
"""
GUI counter readout via AutoIt for HOM acquisition.

Reads three numeric fields (V, H, C) from a Windows app using AutoIt's
control APIs, multiple times, then returns their means and standard deviations.

Returns:
    (V_mean, H_mean, C_mean, V_std, H_std, C_std)  -- floats

Requirements:
    pip install -U pyautoit  (o el paquete 'autoit' que estés usando)

Original control classes kept as defaults for backward compatibility.
"""

from __future__ import annotations
from typing import Tuple, Mapping
import time
import numpy as np

try:
    import autoit  # pyautoit / autoit
except Exception as exc:
    raise ImportError(
        "AutoIt Python bindings are required (e.g. 'pip install pyautoit')."
    ) from exc


def _read_int_field(window_spec: str, control_id: str) -> int:
    """
    Read a control's text and convert to int. Raises ValueError if parsing fails.
    """
    txt = autoit.control_get_text(window_spec, control_id)
    # Some GUIs add spaces/commas; strip and keep digits/sign
    txt = str(txt).strip().replace(",", "")
    return int(txt)


def meas_dir(
    times: int,
    *,
    window_spec: str = "[Class:WindowsForms10.Window.8.app.0.33c0d9d]",
    controls: Mapping[str, str] = None,
    sleep_between_reads: float = 0.2,
) -> Tuple[float, float, float, float, float, float]:
    """
    Sample V/H/C counters from a Windows GUI multiple times and compute stats.

    Args:
        times: Number of samples to collect.
        window_spec: AutoIt window specification string.
        controls: Mapping with keys 'V', 'H', 'C' -> control id strings.
                  Defaults match the original script.
        sleep_between_reads: Pause between reads (seconds).

    Returns:
        (V_mean, H_mean, C_mean, V_std, H_std, C_std)

    Raises:
        ValueError: if a control’s text cannot be parsed into an integer.
        RuntimeError: if window or controls are not found (as reported by AutoIt).
    """
    if times <= 0:
        raise ValueError("times must be a positive integer")

    if controls is None:
        # Defaults from the legacy code
        controls = {
            "V": "WindowsForms10.EDIT.app.0.33c0d9d82",
            "H": "WindowsForms10.EDIT.app.0.33c0d9d83",
            "C": "WindowsForms10.EDIT.app.0.33c0d9d24",
        }

    # Quick sanity: ensure window exists (best-effort; some AutoIt builds return 1/0)
    try:
        if autoit.win_exists(window_spec) == 0:
            raise RuntimeError(f"Target window not found: {window_spec}")
    except Exception:
        # If the binding does not support win_exists properly, continue and let reads fail clearly
        pass

    V_samples = np.zeros(times, dtype=float)
    H_samples = np.zeros(times, dtype=float)
    C_samples = np.zeros(times, dtype=float)

    for i in range(times):
        try:
            V_samples[i] = _read_int_field(window_spec, controls["V"])
            H_samples[i] = _read_int_field(window_spec, controls["H"])
            C_samples[i] = _read_int_field(window_spec, controls["C"])
        except KeyError as e:
            raise RuntimeError(f"Missing control mapping for key: {e}") from e
        time.sleep(sleep_between_reads)

    # Means and standard deviations (population=False -> sample std ddof=0, same as np.std default)
    V_mean, H_mean, C_mean = float(np.mean(V_samples)), float(np.mean(H_samples)), float(np.mean(C_samples))
    V_std,  H_std,  C_std  = float(np.std(V_samples)),  float(np.std(H_samples)),  float(np.std(C_samples))

    return V_mean, H_mean, C_mean, V_std, H_std, C_std


if __name__ == "__main__":
    # Quick manual test (will fail if the target window/controls aren't present)
    print(meas_dir(
        5,
        window_spec="[Class:WindowsForms10.Window.8.app.0.33c0d9d]",
        controls={
            "V": "WindowsForms10.EDIT.app.0.33c0d9d82",
            "H": "WindowsForms10.EDIT.app.0.33c0d9d83",
            "C": "WindowsForms10.EDIT.app.0.33c0d9d24",
        },
        sleep_between_reads=0.2,
    ))
