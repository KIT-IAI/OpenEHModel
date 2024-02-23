from typing import List
from pyomo.environ import UnitInterval, Boolean

from components.component import Component, Value


class Generation(Component):
    """
    Local generation of renewable energy. Always needs to bu fully utilized.
    """

    def __init__(
        self,
        name: str,
        positive_powers: dict,
        cost: dict,
        **kwargs,
    ):
        super().__init__(name, ["electricity"], **kwargs)

        powers = [
            (
                f"{type}_max_positive_power",
                lambda model, t: (
                    model.get_attribute(self, f"{type}_power")[t]
                    == positive_powers[type][t]
                ),
            )
            for type in self.types
        ]

        self.constraints = powers

        self.cost_objectives = [
            lambda model: sum(
                [
                    cost[type] * model.get_attribute(self, f"{type}_power")[t]
                    for t in model.t
                    for type in self.types
                ]
            )
        ]
