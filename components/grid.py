from typing import List

from pyomo.environ import NonNegativeReals, Binary, Reals
from components.component import Component, Value

M = 10000000000


class Grid(Component):
    """
    External grid, can buy and sell energy.
    max_buying_power <= 0
    max_buying_power < power < max_selling_power
    """

    def __init__(
        self,
        name: str,
        energy_cost: dict,
        max_selling_power: int,
        max_buying_power: int,
        step_length: int = 1,
        types: List = ["electricity"],
    ) -> None:
        super().__init__(name, types)

        self.values.extend([Value("is_buying", Binary), Value("income", Reals)])
        self.has_cost_objective = True

        positive_powers = [
            (
                f"{type}_max_positive_power",
                lambda model, t: (
                    model.get_attribute(self, f"{type}_power")[t] <= max_selling_power
                ),
            )
            for type in types
        ]

        negative_powers = [
            (
                f"{type}_max_negative_power",
                lambda model, t: (
                    model.get_attribute(self, f"{type}_power")[t] >= max_buying_power
                ),
            )
            for type in types
        ]

        income = [
            (
                "income",
                lambda model, t: (
                    model.get_attribute(self, "income")[t]
                    == model.get_attribute(self, f"{types[0]}_power")[t]
                    * -energy_cost[types[0]][t]
                    * step_length / 3600
                ),
            )
        ]

        self.constraints = positive_powers + negative_powers + income
