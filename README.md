# hom-temperature-delay-maps

Automated **Hong–Ou–Mandel (HOM)** interferometry experiment for mapping photon interference visibility as a function of **crystal temperature** and **temporal delay** between twin photons. Implements full hardware control and data acquisition using Python APIs for **Zaber** motor stages and a **Thorlabs TC200** temperature controller. And autoIT for obtaining data from Coincidence Counting Unit.

---

## 🧠 Overview

This repository contains the acquisition software used in the paper:

**“Temperature and spatial effects in type-II spontaneous parametric down-conversion,”**  
*Optics Communications 490 (2021) 127461.*  
[https://doi.org/10.1016/j.optcom.2021.127461](https://doi.org/10.1016/j.optcom.2021.127461)

The experiment scans:
- **Temperature (45–75 °C)** of a nonlinear ppKTP crystal using a Thorlabs TC200 controller.  
- **Temporal delay** between orthogonally polarized photons by translating **calcite wedges** mounted on Zaber motor stages.

At each temperature step, the delay axis is scanned in discrete steps, and coincidence counts are recorded to reconstruct Hong–Ou–Mandel interference maps.

---

## ⚙️ Features

- **Zaber API integration** – precise delay control via serial binary protocol.  
- **Thorlabs TC200 API control** – temperature stabilization using PID loop.  
- **Automated acquisition** – nested temperature/delay loops with timestamped data saving.  
- **GUI readout automation** – counts (Signal [V], Idler[H], Coincidences[C]) acquired automatically using AutoIt from the detector interface (implemented in a FPGA board based on [https://doi.org/10.1364/AO.54.004727](https://doi.org/10.1364/AO.54.004727)).  
- **Structured data output** – one `.dat` file per temperature with counts and standard deviations.

---

## 📁 Repository structure

```
hom-temperature-delay-maps/
├── hom_scan.py       # Main experimental script (temperature + delay sweep)
├── meas_dir.py       # GUI counter readout via AutoIt (V, H, C + standard deviation)
├── lut_T.xlsx        # (optional) temperature calibration lookup table
└── README.md
```

---

## 🧩 Requirements

- Python 3.8 or later  
- Dependencies:
  - numpy  
  - pandas  
  - autoit  
  - zaber.serial  
  - instruments (for Thorlabs TC200 control)

Install all dependencies using pip:

```bash
pip install numpy pandas autoit zaber.serial instruments
```

---

## ▶️ Usage

The script will:
- Initialize both controllers.  
- Sweep through the specified temperature range.  
- For each temperature, perform a full delay scan and record photon counts.  
- Save one `.dat` file per temperature step in the output directory (`11th waist/`).

---

## 📊 Output format

Each `.dat` file contains six comma-separated columns:

| Column | Description |
|---------|-------------|
| `V` | Vertical polarization (signal) channel counts |
| `H` | Horizontal polarization (idler) channel counts |
| `C` | Coincidence counts |
| `eV` | Standard deviation of `V` |
| `eH` | Standard deviation of `H` |
| `eC` | Standard deviation of `C` |

---

## 🧪 Example results

The resulting data reconstructs Hong–Ou–Mandel dip maps as a function of both **temperature** and **delay**, allowing the study of spectral and temporal correlations in SPDC photon pairs.

---  
- Update COM port assignments and control class names in `meas_dir.py` if your setup differs.  
- The acquisition logic can be reused for other **temperature–delay** interferometry or optical metrology experiments.
