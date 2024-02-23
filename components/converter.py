from pyomo.environ import UnitInterval, Binary, Reals, Constraint
from components.component import Component, Value


class Converter(Component):
    """
    A generic converter component.
    max_powers and min_powers < 0 for inputs, > 0 for outputs
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
        thermic_efficiency: float = 1,
        heat_price: list = None,
        is_chp: bool = False,
        pr_CO2: float = 0,
        CH4_CO2_conversion: float = 0,
        step_length: int = 1,
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

        self.thermic_efficiency = thermic_efficiency
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
                    model.get_attribute(self, "setpoint")[t]
                    - model.get_attribute(self, "setpoint")[t - 1]
                    <= step_length / ramp_up
                )
                if t > 0
                else Constraint.Feasible,
            )
        ]

        ramp_down_constraint = [
            (
                "ramp_down",
                lambda model, t: (
                    model.get_attribute(self, "setpoint")[t - 1]
                    - model.get_attribute(self, "setpoint")[t]
                    <= ramp_down
                )
                if t > 0
                else Constraint.Feasible,
            ),
        ]

        if is_chp:
            self.has_income_objective = True
            income = [
                (
                    "income",
                    lambda model, t: (
                        -model.get_attribute(self, "methane_power")[t]
                        * self.thermic_efficiency
                        * heat_price[t]
                        * step_length / 3600
                        + model.get_attribute(self, "methane_power")[t]
                        * step_length / 3600
                        * pr_CO2
                        * CH4_CO2_conversion
                        == model.get_attribute(self, "income")[t]
                    ),
                )
            ]
        elif "methane" in output_types:
            self.has_income_objective = True
            income = [
                (
                    "income",
                    lambda model, t: (
                        model.get_attribute(self, "methane_power")[t]
                        * pr_CO2
                        * CH4_CO2_conversion
                        * step_length / 3600
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
            + income
            + min_powers
        )
