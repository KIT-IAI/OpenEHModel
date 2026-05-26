from typing import List
from pyomo.environ import Set, Reals


class Value:
    """
    Wrapper for pyomo Value (Var) class.
    Used internally to enable more complex conditions.
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
        step_length: int = 1,
        **kwargs,
    ) -> None:
        self.name = name
        self.step_length = step_length
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
