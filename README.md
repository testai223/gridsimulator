# Grid Simulator

A simple framework to create power grid models, store them in a database and run load-flow calculations using [pandapower](https://pandapower.readthedocs.io/). A small Tkinter GUI allows entering buses and lines and viewing calculation results.

## Features

- Uses SQLite for persistent storage
- Load-flow calculation engine based on pandapower
- Tkinter GUI to add grid elements and run power flow
- Convert calculated networks to NetworkX graphs
- Visualize the grid graph from the GUI with bus voltages and line flows
- Minimal, single-file entry point (`main.py`)
- Browser-based web GUI (`web_app.py`, see below)

## Installation

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the application with:
```bash
python main.py
```
A window opens where buses and lines can be added. Press **Run Load Flow** to
perform a calculation. Bus voltages and line power flows are displayed in a
table on the *Results* tab. The GUI also includes **Run Example Grid** which runs
a minimal two-bus example network.

## Web GUI

Besides the Tkinter desktop GUI there is a browser-based GUI (Flask backend +
single-page vanilla-JS frontend, no build step, no CDN). It reuses the existing
simulation code (`examples.py`, `database.py`, `engine.py`, `contingency.py`,
`state_estimation_module.py`) and exposes:

- **Grid selection** – built-in examples (2-bus, IEEE 9-bus, IEEE 39-bus, IEEE 39-bus
  MATPOWER) and all grids stored in `grid.db` (read-only)
- **Network diagram** – SVG graph of buses, lines and transformers, coloured by
  bus voltage and line loading after a load flow (hover for details)
- **Load flow** – bus voltages/angles, line and transformer flows, generators,
  KPIs (losses, violations); optional what-if outages of lines/trafos/generators
- **N-1 contingency analysis** – result table with severity colouring and the
  detailed voltage/overload violation list
- **State estimation** – WLS estimation (voltage-only or comprehensive), estimated
  vs. true state, measurement list, and measurement outage scenarios

Run it with:
```bash
pip install -r requirements.txt
python web_app.py                 # then open http://127.0.0.1:5000
python web_app.py --host 0.0.0.0 --port 8080 --db path/to/grid.db
```
The database path can also be set with the `GRID_DB` environment variable.
The JSON API (`/api/grids`, `/api/grid`, `/api/loadflow`, `/api/contingency`,
`/api/state-estimation`, `/api/measurement-outage`) is covered by
`tests/test_web_app.py`. The server is the Flask development server and is meant
for local use.

## Development

The project follows basic PEP8 practices. Tools like `black`, `flake8` and `mypy` can be used for formatting and type checking. Automated tests can be run with `pytest`.

## License

This example project is provided for demonstration purposes.
