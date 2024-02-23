from pyomo.core.base import Var, ConcreteModel, Objective, Constraint, Set, maximize


class IndexedModel(ConcreteModel):

    """
    Creates a Model
    Allows devices to be added, their values, constraints and incomes added to the Model
    Use the methods to set the objective and the overall energy balance after all devices have been added
    Indexed because every value exists for every time step
    """

    def __init__(self, index, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.t = index
        self.income_objective = []
        self.fulfillment_objective = []
        self.devices = []
        self.sources = []
        self.energy_types = []

    def set_index(self, index):
        self.t = Set(initialize=index)

    def get_index(self):
        return self.t

    def set_value(self, name, value):
        var = Var(self.t, within=value.within, initialize=0)
        full_name = name + "_" + value.name
        setattr(self, full_name, var)

    def set_constraint(self, device_name, constraint_name, expr):
        setattr(
            self, device_name + "_" + constraint_name, Constraint(self.t, rule=expr)
        )

    def set_objective_with_weights(
        self,
        income_weight,
        fulfillment_weight,
        step_length,
        max_mean_deviation,
        min_mean_deviation,
        min_income,
        max_income,
    ):
        self.income_sum = sum(sum(objective[t] for t in self.t) for objective in self.income_objective)
        self.income_dof = (self.income_sum - min_income) / (max_income - min_income)

        self.mean_deviation = (
            sum(
                sum((f[t] * step_length / 3600) for t in self.t)
                for f in self.fulfillment_objective
            )
            / 96
        )
        self.fulfillment_dof =  1 - (self.mean_deviation - min_mean_deviation) / (max_mean_deviation - min_mean_deviation)

        expr = self.income_dof * income_weight + self.fulfillment_dof * fulfillment_weight
        self.obj = Objective(rule=expr, sense=maximize)

    def get_attribute(self, device, key):
        return getattr(self, device.name + "_" + key)

    def get_attribute_by_name(self, name, key):
        return getattr(self, name + "_" + key)

    def add_device(self, device):
        energy_types = device.energy_types
        for energy_type in energy_types:
            if energy_type not in self.energy_types:
                self.energy_types.append(energy_type)
        for value in device.values:
            self.set_value(device.name, value)
        for param in device.params:
            self.set_value(device.name, param)
        for constraint in device.constraints:
            self.set_constraint(device.name + "_c", constraint[0], constraint[1])
        self.devices.append(device)
        if device.has_income_objective:
            self.income_objective.append(getattr(self, device.name + "_income"))
        if device.has_fulfillment_objective:
            self.fulfillment_objective.append(
                getattr(self, device.name + "_fulfillment")
            )

    def generate_power_balance(self):
        for energy_type in self.energy_types:
            self.set_constraint(
                energy_type,
                "power_balance",
                lambda model, t: sum(
                    [
                        model.get_attribute(device, f"{energy_type}_power")[t]
                        for device in list(
                            filter(
                                lambda device: energy_type in device.energy_types,
                                self.devices,
                            )
                        )
                    ]
                )
                == 0,
            )
