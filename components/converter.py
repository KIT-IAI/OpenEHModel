from pyomo.environ import UnitInterval, Binary, Reals, Constraint
from components.component import Component, Value


class Converter(Component):
    """
    A generic converter component.
    max_powers and min_powers < 0 for inputs, > 0 for outputs

    Args:
        max_powers (dict): the maximum rated power for each energy type in the shape
            {'type': power}
        min_powers (dict): Contains the minimum rated power for each energy tape, same format as max_powers
        input_types (list): List of all energy types consumed by the converter
        output_types (list): List of all energy types in the output of the converter
        conversion factors (dict): Contains the relationship between the energy types consumed/created.
            All units in energy. For example if an electrolyseur creates 0.6MW of H2 per MW electricity:
            {'electricity': 1, 'H2': 0.6}
        ramp_up (float): the maximum ramp rate when starting the process in relation to the max powers. In [0,1].
        ramp_down (float): the maximum ramp rate when stopping the process.
        CO2_price (float): if methane is burned to price in the CO2-equivalent. In euro/kG
        CH4_to_CO2 (float): the amount of CO2-Mass per Methane mass burned.
        self.step_length (int): Number of seconds per time step (temporal resolution of the model)
    """

    def __init__(
        self,
        max_powers: dict,
        min_powers: dict,
        input_types: list,
        output_types: list,
        conversion_factors: dict,
        ramp_up: float,
        ramp_down: float,
        CO2_price: float = 0,
        CH4_to_CO2: float = 1,
        **kwargs,
    ) -> None:
        super().__init__(types=input_types + output_types, **kwargs)
        self.values.extend(
            [
                Value("setpoint", UnitInterval),
                Value("is_active", Binary),
                Value("income", Reals),
            ]
        )

        self.min_power = min_powers[output_types[0]]
        self.max_power = max_powers[output_types[0]]

        no_outflow = [
            (
                f"{type}_no_outflow",
                lambda model, t: (model.get_attribute(self, f"{type}_power")[t] <= 0),
            )
            for type in input_types
        ]

        no_inflow = [
            (
                f"{type}_no_inflow",
                lambda model, t: (model.get_attribute(self, f"{type}_power")[t] >= 0),
            )
            for type in output_types
        ]

        active_powers = [
            (
                f"{type}_setpoint",
                lambda model, t: (
                    model.get_attribute(self, "setpoint")[t]
                    * model.get_attribute(self, "is_active")[t]
                    * max_power
                    == model.get_attribute(self, f"{type}_power")[t]
                ),
            )
            for type, max_power in max_powers.items()
        ]

        active_setpoint = [
            (
                "active_setpoint",
                lambda model, t: (
                    model.get_attribute(self, "is_active")[t]
                    - model.get_attribute(self, "setpoint")[t]
                    >= 0
                ),
            ),
        ]
        power_equality = [
                (
                    "power_equality",
                    lambda model, t: (
                        -sum(
                            model.get_attribute(self, f"{type}_power")[t]
                            * conversion_factors[type]
                            for type in output_types
                        )
                        == sum(
                            model.get_attribute(self, f"{type}_power")[t]
                            * conversion_factors[type]
                            for type in input_types
                        )
                    ),
                )
        ]
        if False and len(output_types) == 1 and output_types[0] == "h2":  # pem component only
            power_equality = [
                (
                    "power_equality",
                    lambda model, t: (
                        -sum(
                            model.get_attribute(self, f"{type}_power")[t]
                            * conversion_factors[type]
                            for type in output_types
                        )
                        == sum(
                            model.get_attribute(self, f"{type}_power")[t] * model.get_attribute(self, f"{type}_power")[t] * model.get_attribute(self, f"{type}_power")[t] * 0.1
                            * conversion_factors[type]
                            for type in input_types
                        )
                    ),
                )
            ]
        min_powers = [
            (
                "min_power",
                lambda model, t: (
                    model.get_attribute(self, "setpoint")[t]
                    >= (self.min_power / self.max_power)
                    * model.get_attribute(self, "is_active")[t]
                ),
            )
        ]

        ramp_up_constraint = [
            (
                "ramp_up",
                lambda model, t: (
                    (
                        model.get_attribute(self, "setpoint")[t]
                        - model.get_attribute(self, "setpoint")[t - 1]
                        <= self.step_length / ramp_up
                    )
                    if t > 0
                    else Constraint.Feasible
                ),
            )
        ]

        ramp_down_constraint = [
            (
                "ramp_down",
                lambda model, t: (
                    (
                        model.get_attribute(self, "setpoint")[t - 1]
                        - model.get_attribute(self, "setpoint")[t]
                        <= self.step_length / ramp_down
                    )
                    if t > 0
                    else Constraint.Feasible
                ),
            ),
        ]

        if "methane" in output_types:
            self.has_income_objective = True
            income = [
                (
                    "income",
                    lambda model, t: (
                        model.get_attribute(self, "methane_power")[t]
                        * CO2_price
                        * (1 / CH4_to_CO2)
                        * self.step_length
                        / 3600
                        == model.get_attribute(self, "income")[t]
                    ),
                )
            ]
        else:
            self.has_income_objective = False
            income = []

        self.constraints = (
            active_setpoint
            + active_powers
            + no_inflow
            + no_outflow
            + power_equality
            + ramp_up_constraint
            + ramp_down_constraint
            + income
            + min_powers
        )
