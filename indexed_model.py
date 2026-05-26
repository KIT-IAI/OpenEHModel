from pyomo.core.base import Var, ConcreteModel, Objective, Constraint, Set, maximize, minimize
from typing import List, Callable, Any


class IndexedModel(ConcreteModel):
    """
    Time-indexed optimization model for multi-device energy systems.
    
    Extends Pyomo's ConcreteModel to manage:
    - Time-indexed variables for all components (one variable per timestep)
    - Multi-energy type power balances (electricity, heat, methane, hydrogen, etc.)
    - Device constraints and objectives across timeframe
    - Weighted combination of income and fulfillment objectives
    
    Workflow:
        1. Create: model = IndexedModel(index=range(96))
        2. Add devices: model.add_device(component) for each component
        3. Set objective: model.set_objective_with_weights(...)
        4. Generate balance: model.generate_power_balance()
        5. Solve: solver.solve(model)
    """

    def __init__(self, index, *args, **kwargs):
        """
        Initialize indexed model with time index.
        
        Args:
            index: Time index (e.g., range(96) for 96 timesteps)
            *args, **kwargs: Passed to parent ConcreteModel
        """
        super().__init__(*args, **kwargs)
        self.t = index
        self.income_objective: List[Any] = []
        self.fulfillment_objective: List[Any] = []
        self.devices: List[Any] = []
        self.sources: List[Any] = []
        self.energy_types: List[str] = []
        # Objective computation attributes (initialized in set_objective_with_weights)
        self.income_sum: float = 0.0
        self.income_dof: float = 0.0
        self.mean_deviation: float = 0.0
        self.fulfillment_dof: float = 0.0

    def set_index(self, index):
        """Set or override the time index."""
        self.t = Set(initialize=index)

    def get_index(self):
        """Retrieve the current time index."""
        return self.t

    def _build_variable_name(self, device_name: str, value_name: str) -> str:
        """Build standardized variable name: {device_name}_{value_name}."""
        return f"{device_name}_{value_name}"

    def add_indexed_variable(self, name: str, value: Any):
        """
        Create a time-indexed variable for a device value.
        
        Args:
            name: Device name (e.g., 'chp', 'battery')
            value: Value object with .within and .name attributes
        """
        var = Var(self.t, within=value.within, initialize=0)
        full_name = self._build_variable_name(name, value.name)
        setattr(self, full_name, var)

    def add_constraint(self, device_name: str, constraint_name: str, expr: Callable):
        """
        Register a time-indexed constraint.
        
        Args:
            device_name: Device identifier
            constraint_name: Constraint identifier
            expr: Lambda function (model, t) -> boolean expression
        """
        constraint_attr = f"{device_name}_{constraint_name}"
        setattr(self, constraint_attr, Constraint(self.t, rule=expr))

    def _calculate_income_sum(self) -> float:
        """Sum all income objectives across all timesteps and devices."""
        return sum(
            sum(objective[t] for t in self.t) 
            for objective in self.income_objective
        )

    def _calculate_income_dof(self, income_sum: float, min_income: float, max_income: float) -> float:
        """
        Calculate income degree of freedom [0,1].
        
        Normalized as: (income - min) / (max - min)
        """
        return (income_sum - min_income) / (max_income - min_income)

    def _calculate_mean_deviation_quadratic(self) -> float:
        """
        Calculate quadratic mean deviation for all fulfillment objectives.
        
        Formula: sum((f[t]^2 / 10)) / len(f) summed over all fulfillment objectives
        """
        return sum(
            sum((f[t] * f[t] / 10) for t in range(len(f))) / len(f)
            for f in self.fulfillment_objective
        )

    def _calculate_mean_deviation_linear(self, step_length: float) -> float:
        """
        Calculate linear mean deviation normalized by time.
        
        Formula: sum(f[t] * step_length_hours) / 96 summed over all fulfillment objectives
        """
        return sum(
            sum((f[t] * step_length / 3600) for t in self.t)
            for f in self.fulfillment_objective
        ) / 96

    def _calculate_fulfillment_dof_linear(
        self, mean_deviation: float, min_mean_deviation: float, max_mean_deviation: float
    ) -> float:
        """
        Calculate fulfillment degree of freedom [0,1] for linear objective.
        
        Normalized as: 1 - (mean_deviation - min) / (max - min)
        Higher fulfillment (lower deviation) yields higher DOF.
        """
        return 1 - (mean_deviation - min_mean_deviation) / (max_mean_deviation - min_mean_deviation)

    def set_objective_with_weights(
        self,
        income_weight: float,
        fulfillment_weight: float,
        step_length: float,
        max_mean_deviation: float,
        min_mean_deviation: float,
        min_income: float,
        max_income: float,
        quadratic: bool = False,
    ):
        """
        Set weighted optimization objective combining income and fulfillment.
        
        Args:
            income_weight: Weight for income component [0,1]
            fulfillment_weight: Weight for fulfillment component [0,1]
            step_length: Timestep duration in seconds (e.g., 900 for 15 min)
            max_mean_deviation: Reference max deviation for normalization
            min_mean_deviation: Reference min deviation for normalization
            min_income: Reference min income for normalization
            max_income: Reference max income for normalization
            quadratic: If True, use quadratic fulfillment and minimize; else linear and maximize
        
        Objective Sense:
            - Quadratic (MIQP): minimize mean_squared_deviation
            - Linear (MILP): maximize weighted combination
        """
        # Calculate income component
        self.income_sum = self._calculate_income_sum()
        self.income_dof = self._calculate_income_dof(self.income_sum, min_income, max_income)

        if quadratic:
            self._set_quadratic_objective(income_weight, fulfillment_weight)
        else:
            self._set_linear_objective(
                income_weight,
                fulfillment_weight,
                step_length,
                min_mean_deviation,
                max_mean_deviation,
            )

    def _set_quadratic_objective(self, income_weight: float, fulfillment_weight: float):
        """Set quadratic (MIQP) objective: minimize mean squared deviation."""
        self.mean_deviation = self._calculate_mean_deviation_quadratic()
        self.fulfillment_dof = self.mean_deviation
        expr = self.income_dof * income_weight + self.fulfillment_dof * fulfillment_weight
        # Delete old objective if it exists
        if hasattr(self, 'obj'):
            del self.obj
        self.obj = Objective(rule=expr, sense=minimize)

    def _set_linear_objective(
        self,
        income_weight: float,
        fulfillment_weight: float,
        step_length: float,
        min_mean_deviation: float,
        max_mean_deviation: float,
    ):
        """Set linear (MILP) objective: maximize weighted income and fulfillment."""
        self.mean_deviation = self._calculate_mean_deviation_linear(step_length)
        self.fulfillment_dof = self._calculate_fulfillment_dof_linear(
            self.mean_deviation, min_mean_deviation, max_mean_deviation
        )
        expr = self.income_dof * income_weight + self.fulfillment_dof * fulfillment_weight
        # Delete old objective if it exists
        if hasattr(self, 'obj'):
            del self.obj
        self.obj = Objective(rule=expr, sense=maximize)

    def get_attribute(self, device: Any, key: str) -> Any:
        """Get a device attribute variable by device object and key name."""
        return getattr(self, self._build_variable_name(device.name, key))

    def get_attribute_by_name(self, name: str, key: str) -> Any:
        """Get a device attribute variable by device name (string) and key name."""
        return getattr(self, self._build_variable_name(name, key))

    def _register_energy_types(self, device: Any):
        """Add device's energy types to model's energy_types list if not present."""
        for energy_type in device.energy_types:
            if energy_type not in self.energy_types:
                self.energy_types.append(energy_type)

    def _register_device_variables(self, device: Any):
        """Register all values and parameters as time-indexed variables."""
        for value in device.values:
            self.add_indexed_variable(device.name, value)
        for param in device.params:
            self.add_indexed_variable(device.name, param)

    def _register_device_constraints(self, device: Any):
        """Register all device constraints with model."""
        for constraint in device.constraints:
            constraint_name, constraint_expr = constraint
            self.add_constraint(f"{device.name}_c", constraint_name, constraint_expr)

    def _register_device_objectives(self, device: Any):
        """Register device income and fulfillment objectives if applicable."""
        if device.has_income_objective:
            income_var = getattr(self, self._build_variable_name(device.name, "income"))
            self.income_objective.append(income_var)
        if device.has_fulfillment_objective:
            fulfillment_var = getattr(self, self._build_variable_name(device.name, "fulfillment"))
            self.fulfillment_objective.append(fulfillment_var)

    def add_device(self, device: Any):
        """
        Add a device component to the model.
        
        Registers device's:
        - Energy types (electricity, heat, methane, h2, etc.)
        - Time-indexed variables (values and parameters)
        - Constraints (functional relationships between variables)
        - Objectives (income and fulfillment contributions)
        
        Args:
            device: Component object with energy_types, values, params, constraints, etc.
        """
        self._register_energy_types(device)
        self._register_device_variables(device)
        self._register_device_constraints(device)
        self._register_device_objectives(device)
        self.devices.append(device)

    def _get_devices_for_energy_type(self, energy_type: str) -> List[Any]:
        """Filter devices that handle a specific energy type."""
        return [
            device 
            for device in self.devices 
            if energy_type in device.energy_types
        ]

    def _build_power_balance_constraint(self, energy_type: str) -> Callable:
        """
        Create power balance constraint for an energy type.
        
        Constraint: sum of all {energy_type}_power across relevant devices == 0
        (Energy conservation: generation + discharge + purchase == load + charge + sale)
        
        Args:
            energy_type: Energy type identifier (e.g., 'electricity', 'heat')
            
        Returns:
            Lambda function (model, t) -> boolean expression
        """
        devices = self._get_devices_for_energy_type(energy_type)
        
        def constraint_rule(model, t):
            power_sum = sum(
                model.get_attribute(device, f"{energy_type}_power")[t]
                for device in devices
            )
            return power_sum == 0
        
        return constraint_rule

    def generate_power_balance(self):
        """
        Generate energy balance constraints for all energy types in system.
        
        For each energy type (electricity, heat, methane, h2):
        - Sum all device power outputs/inputs for that energy type
        - Enforce sum == 0 (energy conservation)
        
        Must be called after all devices have been added via add_device().
        """
        for energy_type in self.energy_types:
            constraint_rule = self._build_power_balance_constraint(energy_type)
            self.add_constraint(
                energy_type,
                "power_balance",
                constraint_rule,
            )
