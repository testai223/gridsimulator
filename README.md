# Grid Simulator

A simple framework to create power grid models, store them in a database and run load-flow calculations using [pandapower](https://pandapower.readthedocs.io/). A small Tkinter GUI allows entering buses and lines and viewing calculation results.

## Features

- Uses SQLite for persistent storage
- Load-flow calculation engine based on pandapower
- Tkinter GUI to add grid elements and run power flow
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
A window opens where buses and lines can be added. Press **Run Load Flow** to perform a calculation and display the bus results.

## Development

The project follows basic PEP8 practices. Tools like `black`, `flake8` and `mypy` can be used for formatting and type checking.

## License

This example project is provided for demonstration purposes.
