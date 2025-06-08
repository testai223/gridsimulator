# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

**Run the application:**
```bash
python main.py
```

**Run tests:**
```bash
pytest
```

**Run specific test:**
```bash
pytest tests/test_engine.py
```

**Set up environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**Code quality (mentioned in README):**
```bash
black .          # formatting
flake8 .         # linting
mypy .           # type checking
```

## Architecture Overview

This is a power grid simulation framework with three main architectural layers:

1. **Database Layer** (`database.py`): SQLite-based persistence for grid elements (buses and lines)
2. **Calculation Engine** (`engine.py`): Builds pandapower networks from database and runs load-flow calculations
3. **GUI Layer** (`gui.py`): Tkinter interface for data input and result visualization

**Key Data Flow:**
- User inputs buses/lines via GUI → stored in SQLite database
- GridCalculator reads from database → builds pandapower network → runs power flow
- Results displayed in GUI tables and NetworkX graph visualization

**Core Components:**
- `GridDatabase`: Manages SQLite tables for buses and lines with proper foreign key relationships
- `GridCalculator`: Converts database entries to pandapower network elements and executes calculations
- `GridApp`: Tabbed GUI with separate views for input (buses/lines) and results
- Utility functions in `engine.py`: `element_tables()` for formatted output, `grid_graph()` for NetworkX conversion

**Key Features:**
- **Power Flow Analysis**: Base case and post-contingency power flow studies
- **N-1 Contingency Analysis**: Automatic outage simulation for lines, transformers, and generators
- **Parameter Editing**: Interactive modification of network parameters with immediate analysis
- **Network Visualization**: Graph-based representation with power flow data
- **Multiple Test Systems**: 2-bus tutorial, IEEE 9-bus, and IEEE 39-bus New England systems

**Dependencies:**
- pandapower: Power system analysis engine
- NetworkX: Graph operations and visualization
- matplotlib: Grid graph plotting
- tkinter: GUI framework