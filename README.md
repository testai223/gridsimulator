# Grid Simulator

A simple framework to create power grid models, store them in a database and run load-flow calculations using [pandapower](https://pandapower.readthedocs.io/). A small Tkinter GUI allows entering buses and lines and viewing calculation results.

## Features

- Uses SQLite for persistent storage
- Load-flow calculation engine based on pandapower
- Tkinter GUI to add grid elements and run power flow
- Convert calculated networks to NetworkX graphs
- Visualize the grid graph from the GUI with bus voltages and line flows
- Minimal, single-file entry point (`main.py`)

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

## Development

The project follows basic PEP8 practices. Tools like `black`, `flake8` and `mypy` can be used for formatting and type checking. Automated tests can be run with `pytest`.

## License

This example project is provided for demonstration purposes.
