# Development Guide

## Project Structure

```
geo_toolbox/
├── src/geo_toolbox/              # Source code (src-layout)
│   ├── __init__.py              # Package initialization
│   ├── core/                     # GEE data extraction
│   │   ├── __init__.py
│   │   └── eedata.py
│   ├── processing/               # Time series processing
│   │   ├── __init__.py
│   │   └── processors.py
│   ├── visualization/            # Plotting utilities
│   │   ├── __init__.py
│   │   └── visualizer.py
│   └── utils/                    # Helper functions
│       └── __init__.py
├── tests/                        # Unit tests
├── examples/                     # Example notebooks and data
│   ├── notebooks/
│   │   └── experiment.ipynb
│   └── data/
├── docs/                         # Documentation
├── pyproject.toml               # Project configuration (PEP 621)
└── README.md
```

## Setup Development Environment

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/geo-toolbox.git
cd geo-toolbox
```

### 2. Create a virtual environment

```bash
# Using venv
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Or using conda
conda create -n geo-toolbox python=3.10
conda activate geo-toolbox
```

### 3. Install in development mode

```bash
# Install with dev and notebook dependencies
pip install -e ".[dev,notebooks]"

# Or just core dependencies
pip install -e .
```

## Code Style and Quality

### Format code with Black

```bash
black src tests
```

### Check code style with Flake8

```bash
flake8 src tests
```

### Sort imports with isort

```bash
isort src tests
```

### Type checking with mypy

```bash
mypy src
```

### Run all linters

```bash
black src tests && isort src tests && flake8 src tests
```

## Running Tests

### Run all tests

```bash
pytest tests/ -v
```

### Run specific test file

```bash
pytest tests/test_processors.py -v
```

### Generate coverage report

```bash
pytest tests/ --cov=src/geo_toolbox --cov-report=html
```

## Building the Package

### Build distribution

```bash
pip install build
python -m build
```

This creates:
- `dist/geo_toolbox-0.1.0.tar.gz` (source distribution)
- `dist/geo_toolbox-0.1.0-py3-none-any.whl` (wheel)

### Upload to PyPI

```bash
pip install twine
twine upload dist/*
```

## Contributing Guidelines

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** and write tests

3. **Run linters and tests**
   ```bash
   black src tests && isort src tests && pytest tests/
   ```

4. **Commit with clear messages**
   ```bash
   git commit -m "Add feature: description"
   ```

5. **Push and create a Pull Request**

## Important Notes

- Always use the **src-layout** pattern: code goes in `src/geo_toolbox/`
- Dependencies are managed in `pyproject.toml` (no setup.py needed)
- Tests should be in `tests/` directory with `test_*.py` naming
- Documentation goes in `docs/` directory
- Example notebooks go in `examples/notebooks/`
- Data files should not be committed to git (add to `.gitignore`)

## Troubleshooting

### Import errors after changes

If you get import errors, reinstall the package:
```bash
pip install -e .
```

### Jupyter notebook can't find the package

Make sure the kernel is using the correct Python environment:
```bash
python -m ipykernel install --user --name geo-toolbox
```

Then select the `geo-toolbox` kernel in the notebook.
