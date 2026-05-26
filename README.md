# Energy Hub MILP/MIQP Optimization

Pyomo-based optimization system for multi-device energy hub scheduling. Supports both linear (MILP) and quadratic (MIQP) optimization using IPOPT solver.

## Features

- Multi-device energy hub optimization (CHP, PEM, Battery, Methanation, Heat Pump)
- MILP and MIQP solving via IPOPT
- MQTT integration for real-time scheduling
- Comprehensive test suite with 80%+ code coverage
- All configuration centralized in project_config.json

## Requirements

- Python 3.8+
- IPOPT solver (install separately, e.g., via conda: `conda install -c conda-forge ipopt`)

## Installation

### Using uv (recommended)

```bash
# Clone the repository
cd energy-hub-milp

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .

# Install development dependencies (for testing)
uv pip install -e ".[dev]"
```

### Dependencies

All dependencies are listed in `pyproject.toml`:
- `pyomo` - Optimization modeling
- `numpy` - Numerical computing
- `pandas` - Data handling
- `matplotlib`, `seaborn` - Visualization
- `paho-mqtt` - MQTT integration
- `requests` - HTTP requests

Dev dependencies:
- `pytest` - Testing framework
- `pytest-cov` - Coverage reporting

## Configuration

All configuration is managed through `project_config.json`. Key configuration sections:

### Paths
- `paths.data_dir` - Data directory (default: "Daten")
- `paths.output_dir` - Output directory (default: "output")
- `paths.logs_dir` - Logs directory (default: "logs")

### Solver
- `solver.ipopt_executable` - IPOPT executable path

### MQTT

MQTT credentials are stored in `credentials.json`. Update this file with your broker details before running the MQTT runner.

## Running Tests

```bash
# Run all tests with coverage
pytest tests/ --cov=. --cov-report=term-missing

# Run tests quietly
pytest tests/ -q

# Run specific test file
pytest tests/test_schedule_generator.py -v
```

## Running the Optimization

### Full workflow (quadratic + linear + statistics)
```bash
python main.py
```

### Quadratic optimization only (MIQP)
```bash
python main.py --quadratic
```

### Single-day scheduling
```python
from schedule_generator import connect_and_schedule
connect_and_schedule(
    timeframe=96,
    step_length=900,  # 15 minutes in seconds
    all_results_file="output.json",
    result_schedule_file="schedule.csv",
    quadratic=True,
    load_ts="TargetFromResults.pkl",
    days=5
)
```

### MQTT Runner
```bash
python mqtt_runner.py
```

## Project Structure

```
milp/
├── config.py                 # Configuration loader
├── project_config.json       # Project configuration
├── main.py                   # Main optimization script
├── schedule_generator.py     # Optimization orchestration
├── mqtt_runner.py           # MQTT integration
├── indexed_model.py         # Pyomo model
├── components/              # Device models
│   ├── converter.py
│   ├── storage.py
│   ├── grid.py
│   ├── target.py
│   └── heat_target.py
├── tests/                   # Test suite
│   ├── test_indexed_model.py
│   ├── test_schedule_generator.py
│   ├── test_mqtt_runner.py
│   ├── test_components.py
│   └── test_utils.py
├── Daten/                   # Data and results
│   └── results/
└── .gitlab-ci.yml          # CI/CD pipeline
```

## Testing in GitLab CI

The `.gitlab-ci.yml` includes a test stage that runs automatically with coverage enforcement:

```yaml
test:
  stage: test
  script:
    - pytest tests/ --cov=. --cov-report=term-missing --cov-report=html --cov-fail-under=80
```

Tests run automatically on every push to the repository. The pipeline enforces minimum 80% code coverage.

## License

MIT