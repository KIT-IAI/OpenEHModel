from typing import List
from pyomo.environ import NonNegativeReals, Binary, UnitInterval, Constraint
from components.component import Component, Value


class Storage(Component):
    """
    A storage medium for any energy type (battery, gas tank, ..)

    args:
        name (string): for internal reference
        input_types (List): energy type to be used (length needs to be one)
        max_charging_power (float): maximum power input
        max_discharging_power (float): maximum power output
        capacity (float): capacity of the device in kWh
        charging_efficiency (float): Efficiency of storage. Is applied both at charging and discharging
        inital_charge (float) in [0,1]: state of charge at t_0
    """

    def __init__(
        self,
        name: str,
        input_types,
        max_charging_power: float,
        max_discharging_power: float,
        capacity: float,
        charging_efficiency: float,
        initial_charge: float = 0.5,
        **kwargs,
    ) -> None:
        super().__init__(name, types=input_types, **kwargs)

        assert len(input_types) == 1

        self.initial_charge = initial_charge
        self.charging_efficiency = charging_efficiency
        self.capacity = capacity
        self.max_charging_power = max_charging_power
        self.max_discharging_power = max_discharging_power
        self.values.extend(
            [
                Value("state_of_charge", NonNegativeReals, initialize=initial_charge),
                Value("is_charging", Binary),
                Value("setpoint", UnitInterval),
            ]
        )

        self.energy_type = input_types[0]
        self.values.extend(
            [
                Value(f"{self.energy_type}_positive_power", NonNegativeReals),
                Value(f"{self.energy_type}_negative_power", NonNegativeReals),
            ]
        )

        positive_power = f"{self.energy_type}_positive_power"
        negative_power = f"{self.energy_type}_negative_power"
        power = f"{self.energy_type}_power"

        self.constraints = [
            (
                "power_sum",
                lambda model, t: (
                    model.get_attribute(self, positive_power)[t]
                    - model.get_attribute(self, negative_power)[t]
                    == model.get_attribute(self, power)[t]
                ),
            ),
            (
                "positive_charge",
                lambda model, t: (
                    model.get_attribute(self, "is_charging")[t]
                    * model.get_attribute(self, negative_power)[t]
                    == model.get_attribute(self, negative_power)[t]
                ),
            ),
            (
                "negative_charge",
                lambda model, t: (
                    (1 - model.get_attribute(self, "is_charging")[t])
                    * model.get_attribute(self, positive_power)[t]
                    == model.get_attribute(self, positive_power)[t]
                ),
            ),
            (
                "next_state_of_charge",
                lambda model, t: (
                    (model.get_attribute(self, "state_of_charge")[t] == initial_charge)
                    if t == 0
                    else (
                        model.get_attribute(self, "state_of_charge")[t]
                        == model.get_attribute(self, "state_of_charge")[t - 1]
                        + (
                            (
                                (
                                    model.get_attribute(self, negative_power)[t - 1]
                                    * charging_efficiency
                                )
                                - (
                                    model.get_attribute(self, positive_power)[t - 1]
                                    * (1 / charging_efficiency)
                                )
                            )
                            * (self.step_length / 3600)
                        )
                    )
                ),
            ),
            (
                "capacity",
                lambda model, t: (
                    model.get_attribute(self, "state_of_charge")[t] <= capacity
                ),
            ),
            (
                "limit_discharging_power",
                lambda model, t: (
                    model.get_attribute(self, negative_power)[t] <= max_charging_power
                ),
            ),
            (
                "limit_charging_power",
                lambda model, t: (
                    model.get_attribute(self, positive_power)[t]
                    <= max_discharging_power
                ),
            ),
            (
                "setpoint",
                lambda model, t: (
                    model.get_attribute(self, "setpoint")[t]
                    ==
                    model.get_attribute(self, "is_charging")[t] * model.get_attribute(self, negative_power)[t] / max_charging_power
                    + (1 - model.get_attribute(self, "is_charging")[t]) * model.get_attribute(self, positive_power)[t] / max_discharging_power
                ),
            ),]
        
            
