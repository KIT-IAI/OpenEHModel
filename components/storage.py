from typing import List
from pyomo.environ import NonNegativeReals, Binary, Reals, UnitInterval, Constraint
from components.component import Component, Value


class Storage(Component):
    """ """

    def __init__(
        self,
        name: str,
        input_types,
        max_charging_power: float,
        max_discharging_power: float,
        capacity: float,
        charging_efficiency: float,
        initial_charge: float = 0,
        step_length: int = 3600,
    ) -> None:
        super().__init__(name, types=input_types)

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
                            * (step_length / 3600)
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
                "cant_overcharge",
                lambda model, t: (
                    (
                        model.get_attribute(self, negative_power)[t]
                        * charging_efficiency
                        * (3600 / step_length)
                        <= capacity - initial_charge
                    )
                    if t == 0
                    else (
                        model.get_attribute(self, negative_power)[t]
                        * charging_efficiency
                        * (3600 / step_length)
                        <= (capacity - model.get_attribute(self, "state_of_charge")[t])
                    )
                ),
            ),
            (
                "output_only_charge",
                lambda model, t: (
                    (
                        model.get_attribute(self, positive_power)[t]
                        * (1 / charging_efficiency)
                        * (3600 / step_length)
                        <= initial_charge
                    )
                    if t == 0
                    else (
                        model.get_attribute(self, positive_power)[t]
                        * (1 / charging_efficiency)
                        * (3600 / step_length)
                        <= model.get_attribute(self, "state_of_charge")[t]
                    )
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
                "upper_positive_setpoint",
                lambda model, t: (
                    model.get_attribute(self, positive_power)[t]
                    == (1 - model.get_attribute(self, "is_charging")[t])
                    * max_discharging_power
                    * model.get_attribute(self, "setpoint")[t]
                ),
            ),
            (
                "negative_setpoint",
                lambda model, t: (
                    model.get_attribute(self, negative_power)[t]
                    == model.get_attribute(self, "is_charging")[t]
                    * max_charging_power
                    * model.get_attribute(self, "setpoint")[t]
                ),
            ),
        ]
        """
        self.constraints.append[
            (
                "step_zero",
                lambda model, t: (
                    (model.get_attribute(self, power)[t] == 0)
                    if (t == 0 or t == 95)
                    else Constraint.Feasible
                ),
            )
        ]
        """


class Battery(Storage):
    def __init__(
        self,
        **kwargs,
    ) -> None:
        energy_type_input = ["electricity"]
        energy_type_output = ["electricity"]
        super().__init__(
            **kwargs,
            input_types=energy_type_input,
            output_types=energy_type_output,
        )

        self.params = []
