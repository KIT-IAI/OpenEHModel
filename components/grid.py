from typing import List

from pyomo.environ import Binary, Reals
from components.component import Component, Value

# Utility constant for MILP formulation
M = 10000000000


class Grid(Component):
    """
    External grid, can buy and sell energy.
    max_buying_power <= 0 (negative) and max_selling_power >= 0 (positive)
    max_buying_power < power < max_selling_power

    args:
        name (string): name for internal reference
        energy_cost (list): price in euro/kWh per time step
        max_selling_power: maximum power to be sold by the grid
        max_buying_power: maximum power that can be bought by the grid
        types (list): energy types to be bought and sold, currently only one per Grid
    """

    def __init__(
        self,
        name: str,
        energy_cost: List,
        max_selling_power: int,
        max_buying_power: int,
        types: List = ["electricity"],
        **kwargs,
    ) -> None:
        super().__init__(name, types, **kwargs)

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
                    * -energy_cost[t]
                    * self.step_length
                    / 3600
                ),
            )
        ]

        self.constraints = positive_powers + negative_powers + income
