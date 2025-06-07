# Hello World Python Template

A simple Python project template that follows best practices and PEP8 guidelines.

## Features

- ✅ Type hints for better code clarity
- ✅ Comprehensive docstrings
- ✅ PEP8 compliant code style
- ✅ Proper project structure
- ✅ Main entry point pattern
- ✅ Ready for testing and linting

## Project Structure

```
.
├── main.py           # Main application file
├── requirements.txt  # Project dependencies
├── README.md        # Project documentation
├── .gitignore       # Git ignore file
└── setup.cfg        # Configuration for linting tools
```

## Installation

1. Clone this repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the application:
```bash
python main.py
```

## Development

### Code Style

This project follows PEP8 guidelines. To check code style:

```bash
# Install development dependencies
pip install black flake8 mypy isort

# Format code
black main.py
isort main.py

# Check code style
flake8 main.py

# Type checking
mypy main.py
```

### Testing

```bash
# Install pytest
pip install pytest

# Run tests (when you add them)
pytest
```

## License

This is a template project - feel free to use it as a starting point for your own projects.