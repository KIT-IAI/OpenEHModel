# MILP/MIQP Energy Hub Optimization Model

This document summarizes the mathematical formulation of the energy hub optimization model implemented in Pyomo.

## Model Overview

The model optimizes a multi-device energy system over a discrete time horizon (typically 96 timesteps = 24 hours with 15-minute resolution). It supports two objective types:
- **MIQP (Quadratic)**: Minimizes mean squared deviation from target
- **MILP (Linear)**: Maximizes weighted combination of income and fulfillment

---

## 1. Sets and Indices

- **T**: Time index set, |T| = number of timesteps (typically 96)
- **E**: Energy types {electricity, heat, methane, h2}
- **D**: Device set

---

## 2. Decision Variables

### 2.1 Common Variables (All Devices)
| Variable | Domain | Description |
|----------|--------|-------------|
| `{device}_{energy_type}_power[t]` | ℝ | Power at timestep t for device and energy type |
| `{device}_setpoint[t]` | [0,1] | Normalized operating point (0-100%) |
| `{device}_is_active[t]` | {0,1} | Binary indicator if device is operating |
| `{device}_income[t]` | ℝ | Income/cost at timestep t |

### 2.2 Converter-Specific Variables
- `{device}_setpoint[t]` ∈ [0,1] - Operating setpoint
- `{device}_is_active[t]` ∈ {0,1} - Active status

### 2.3 Storage-Specific Variables
| Variable | Domain | Description |
|----------|--------|-------------|
| `state_of_charge[t]` | ℝ₊ | Energy stored (kWh) |
| `is_charging[t]` | {0,1} | Charging indicator |
| `{energy_type}_positive_power[t]` | ℝ₊ | Charging power |
| `{energy_type}_negative_power[t]` | ℝ₊ | Discharging power |

### 2.4 Target-Specific Variables
| Variable | Domain | Description |
|----------|--------|-------------|
| `difference[t]` | ℝ | Deviation from target |
| `limit[t]` | ℝ₊ | Absolute value of deviation |
| `fulfillment[t]` | ℝ₊ | Target fulfillment measure |
| `Y[t]` | {0,1} | Binary for linearization |

---

## 3. Objective Functions

### 3.1 Quadratic (MIQP) - Minimization
```
minimize:  w_income × DOF_income + w_fulfillment × DOF_fulfillment

where:
    DOF_income = (income_sum - min_income) / (max_income - min_income)
    DOF_fulfillment = Σ(Σ(f[t]² / 10) / |T|)  for all fulfillment objectives
    income_sum = Σ_t Σ_d income_d[t]
```

### 3.2 Linear (MILP) - Maximization
```
maximize:  w_income × DOF_income + w_fulfillment × DOF_fulfillment

where:
    mean_deviation = Σ(Σ(f[t] × step_length / 3600) / 96)
    DOF_fulfillment = 1 - (mean_deviation - min_deviation) / (max_deviation - min_deviation)
```

---

## 4. Component Constraints

### 4.1 Converter (e.g., CHP, Electrolyzer, Heat Pump)

#### Power Conversion Equality
```
-Σ(output_type × conversion_factor) = Σ(input_type × conversion_factor)
```

#### Setpoint-Based Power
```
setpoint[t] × is_active[t] × max_power == power[t]
```

#### No Inflow/Outflow
```
input_type_power[t] ≤ 0     (cannot produce input)
output_type_power[t] ≥ 0   (cannot consume output)
```

#### Active Status
```
is_active[t] - setpoint[t] ≥ 0
```

#### Minimum Power
```
setpoint[t] ≥ (min_power / max_power) × is_active[t]
```

#### Ramp Rate Limits
```
setpoint[t] - setpoint[t-1] ≤ step_length / ramp_up
setpoint[t-1] - setpoint[t] ≤ step_length / ramp_down
```

#### Income (for methane converters)
```
income[t] = methane_power[t] × CO2_price × (1/CH4_to_CO2) × step_length / 3600
```

---

### 4.2 Storage (Battery, Gas Tank)

#### Power Balance
```
positive_power[t] - negative_power[t] == power[t]
```

#### Charging/Discharging Logic
```
is_charging[t] × negative_power[t] == negative_power[t]
(1 - is_charging[t]) × positive_power[t] == positive_power[t]
```

#### State of Charge Evolution
```
soc[0] = initial_charge
soc[t] = soc[t-1] + (negative_power[t-1] × η - positive_power[t-1] × (1/η)) × (step_length / 3600)
```

#### Capacity Limits
```
soc[t] ≤ capacity
negative_power[t] ≤ max_charging_power
positive_power[t] ≤ max_discharging_power
```

#### Setpoint Calculation
```
setpoint[t] = is_charging[t] × negative_power[t] / max_charging_power 
             + (1 - is_charging[t]) × positive_power[t] / max_discharging_power
```

---

### 4.3 Grid (External Energy Provider)

#### Power Limits
```
power[t] ≤ max_selling_power
power[t] ≥ max_buying_power
```

#### Income Calculation
```
income[t] = power[t] × (-energy_cost[t]) × step_length / 3600
```

---

### 4.4 Target (Demand/Load)

#### Difference from Target
```
difference[t] = target[t] - electricity_power[t]
```

#### Linearized Absolute Value (Big-M method)
```
difference[t] + N × Y[t] ≥ limit[t]
-difference[t] + N × (1 - Y[t]) ≥ limit[t]
difference[t] ≤ limit[t]
-difference[t] ≤ limit[t]
```

#### Fulfillment
```
fulfillment[t] = limit[t]
```

#### Income
```
income[t] = electricity_power[t] × (-electricity_price[t]) × step_length / 3600
```

---

## 5. Energy Balance Constraints

For each energy type e ∈ E:
```
Σ_d power_{d,e}[t] = 0    ∀t ∈ T
```

This ensures energy conservation: generation + discharge + import = load + charge + export

---

## 6. Model Parameters

| Parameter | Description | Typical Value |
|-----------|-------------|----------------|
| `timeframe` | Number of timesteps | 96 |
| `step_length` | Seconds per timestep | 900 (15 min) |
| `income_weight` | Weight for income objective | 0.01 |
| `fulfillment_weight` | Weight for fulfillment | 0.99 |
| `min_income` | Min income for normalization | 0 |
| `max_income` | Max income for normalization | 1,000,000 |
| `min_mean_deviation` | Min deviation for normalization | 0 |
| `max_mean_deviation` | Max deviation for normalization | 1.0 |

---

## 7. Component Types Summary

| Component | Energy Types | Key Variables | Constraints |
|-----------|-------------|---------------|-------------|
| **Converter** | input → output | setpoint, is_active | power equality, ramp rates, min power |
| **Storage** | single type | soc, is_charging | SOC evolution, capacity, power limits |
| **Grid** | electricity | is_buying | power bounds, income |
| **Target** | electricity | difference, limit, fulfillment | target matching, income |

---

## 8. Solution Extraction

After solving, schedules are extracted:
```
schedule[device] = [value[t] for t in T]
```

For batteries, sign convention flips based on charging status:
```
schedule[t] = -setpoint if is_charging else setpoint
```

---