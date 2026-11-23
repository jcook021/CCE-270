# Beam Designer

A Tkinter desktop app for analyzing beam reactions, shear, moment, deflection, and section checks. It also saves designs and exports CSV results and PDF calculation sheets.

## Install

Requires Python 3.10+, Tkinter, NumPy, and Matplotlib. Install the Python packages in a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On macOS with Homebrew Python, install the matching Tk package if needed (for Python 3.15: `brew install python-tk@3.15`).

## Run

```bash
python app.py
```
