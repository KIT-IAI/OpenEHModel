from typing import List
from pyomo.environ import (
    NonNegativeReals,
    Reals,
    Binary,
)
from components.component import Component, Value

N = 1000

class Target(Component):
    """
    Target of the energy Grid. Contains the sum of generation and Demand.
    """

    def __init__(
        self,
        name: str,
        time_series: list,
        electricity_prices: list,
        step_length: int = 1,
        **kwargs,
    ) -> None:
        super().__init__(
            name,
            **kwargs,
        )
        self.has_fulfillment_objective = True
        self.target = time_series
        self.values.extend(
            [
                Value("limit", NonNegativeReals),
                Value("difference", Reals),
                Value("fulfillment", Reals),
                Value("income", Reals),
                Value("Y", Binary),
            ]
        )

        self.constraints = [
            (
                "calc_difference",
                lambda model, t: (
                    model.get_attribute(self, "difference")[t]
                    == time_series[t]
                    - model.get_attribute(self, "electricity_power")[t]
                ),
            ),
            (
                "abs_difference_max",
                lambda model, t: (
                     model.get_attribute(self, "difference")[t] + N * model.get_attribute(self, "Y")[t] >= model.get_attribute(self, "limit")[t]
                ),
            ),
            (
                "abs_difference_min",
                lambda model, t: (
                    -model.get_attribute(self, "difference")[t] + N * (1 - model.get_attribute(self, "Y")[t]) >= model.get_attribute(self, "limit")[t]
                ),
            ),
            (
                "min_limit",
                lambda model, t: (
                    model.get_attribute(self, "difference")[t] <= model.get_attribute(self, "limit")[t]
                ),
            ),
            (
                "max_limit",
                lambda model, t: (
                    -model.get_attribute(self, "difference")[t] <= model.get_attribute(self, "limit")[t]
                ),
            ),
            (
                "fulfillment_is_limit",
                lambda model, t: (
                    model.get_attribute(self, "limit")[t]
                    == model.get_attribute(self, "fulfillment")[t]
                ),
            )
        ]
        self.has_income_objective = True
        income = [
            (
                "income",
                lambda model, t: (
                    model.get_attribute(self, "income")[t]
                    == electricity_prices[t]
                    * -model.get_attribute(self, "electricity_power")[t]
                    * step_length / 3600
                ),
            )
        ]
        self.constraints.extend(income)
