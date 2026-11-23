# Beam Designer

Tkinter desktop app for checking a beam's reactions, shear, moment, deflection, bending stress, and available sections.

## Requirements

- Python 3.10+
- Tkinter
- NumPy and Matplotlib (`python3 -m pip install -r requirements.txt`)

## Run

```bash
python3 app.py
```

The app opens with the specification's 20 ft simply supported steel beam example. Calculation tests do not open the window:

```bash
python3 -m unittest discover -s tests -v
```

Beam analysis is implemented in `beam_calculations.py`. It uses inches, kips, and ksi internally for stiffness/deflection, then converts results to the units shown in the UI.
