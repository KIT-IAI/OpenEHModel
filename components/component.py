from typing import List
from pyomo.environ import Set, Reals


class Value:
    """
    Wrapper for pyomo Value (Var) class.
    """

    def __init__(self, name: str, within: Set, initialize: float = 0) -> None:
        self.name = name
        self.within = within
        self.initialize = initialize


class Component:
    """
    Base class for all components of the system.
    """

    def __init__(
        self,
        name: str,
        types: List = ["electricity"],
        **kwargs,
    ) -> None:
        self.name = name
        self.values = []
        self.values.extend([Value(f"{type}_power", Reals) for type in types])
        self.params = []
        self.constraints = []
        self.cost_objectives = []
        self.fulfillment_objectives = []
        self.energy_types = types
        self.has_cost_objective = False
        self.has_fulfillment_objective = False
        self.has_income_objective = False
