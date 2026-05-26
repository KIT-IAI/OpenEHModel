# AGENTS.md - Energy Hub MILP/MIQP Optimization

## Project Overview
Pyomo-based optimization system for multi-device energy hub scheduling. Supports both linear (MILP) and quadratic (MIQP) optimization using IPOPT solver.

## Key Commands

### Running Optimization
```bash
python main.py                    # Full workflow: quadratic + linear optimization + statistics
python main.py --quadratic        # Quadratic only (MIQP)
```

### MQTT Integration
```bash
python mqtt_runner.py             # Start MQTT listener for real-time scheduling requests
```

### Single-Day Scheduling
```python
from schedule_generator import connect_and_schedule
connect_and_schedule(
    timeframe=96,
    step_length=900,              # 15 minutes in seconds
    all_results_file="output.json",
    result_schedule_file="schedule.csv",
    quadratic=True,               # MIQP vs MILP
    load_ts="TargetFromResults.pkl",
    days=5
)
```

## Architecture

### Core Modules
- `indexed_model.py` - Pyomo model with IndexedModel class
- `schedule_generator.py` - ScheduleGenerator orchestrates optimization
- `components/` - Device models (Converter, Storage, Grid, Target)
- `Daten/results/` - Plotting and evaluation utilities

### Data Flow
1. Load timeseries from pickle (`TargetFromResults.pkl`)
2. Build IndexedModel with facility parameters (`facility_parameters.json`)
3. Add devices (CHP, PEM, Battery, Methanation, Heat Pump)
4. Solve with IPOPT (quadratic=True → MIQP, quadratic=False → MILP)
5. Extract schedule via `ScheduleGenerator.extract_schedule_from_result()`

### Facility Parameters
Edit `facility_parameters.json` to modify:
- Device capacities and limits
- Conversion efficiencies
- Price constants
- CO2 pricing

## Testing Notes
- No formal test suite (per README: "creating tests for each component" is TODO)
- Run `main.py` to verify end-to-end functionality
- Results saved to `output/` directory

## Dependencies
Key packages in `Requirements.txt`:
- `Pyomo` - Optimization modeling
- `paho-mqtt` - MQTT integration
- `pandas`, `numpy` - Data handling
- `matplotlib`, `seaborn` - Visualization

## Solver
Uses IPOPT. Windows path hardcoded in `schedule_generator.py` line 86:
```python
self.ipopt_executable = "C:\\Users\\cy2814\\Downloads\\Ipopt-3.14.19-win64-msvs2022-md\\bin\\ipopt" or "ipopt"
```
Ensure IPOPT is installed and accessible in PATH.

## Docker
- `Dockerfile` builds Alpine-based container with IPOPT compilation
- `.gitlab-ci.yml` pushes to `iai-artifactory.iai.kit.edu/docker-it4es/energyhub-mqtt`
- Entry point: `mqtt_runner.py`