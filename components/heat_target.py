"""
Heat demand target component for the energy optimization system.

This component represents the heat demand that the heat pump and other heat sources
must satisfy. It tracks the fulfillment of heat demand and calculates deviations.
"""

from pyomo.environ import (
    NonNegativeReals,
    Reals,
    Binary,
)
from components.component import Component, Value

N = 100


class HeatTarget(Component):
    """
    Heat demand target for the energy system.
    
    Tracks heat demand that must be satisfied by the heat pump and other heat sources.
    Calculates deviations from the target heat demand and contributes to fulfillment objectives.
    
    Args:
        name (string): Name for internal reference (e.g., "heat_target")
        time_series (list): Heat demand values per timestep in MW
        step_length (int): Duration of each timestep in seconds
    """

    def __init__(
        self,
        name: str,
        time_series: list,
        **kwargs,
    ) -> None:
        super().__init__(
            name,
            types=["heat"],
            **kwargs,
        )
        self.has_fulfillment_objective = True
        self.target = time_series  # list of heat demand per timestep
        
        self.values.extend(
            [
                Value("limit", NonNegativeReals),
                Value("difference", Reals),
                Value("fulfillment", Reals),
                Value("Y", Binary),
            ]
        )

        self.constraints = [
            (
                "calc_difference",
                lambda model, t: (
                    model.get_attribute(self, "difference")[t]
                    == time_series[t]
                    - model.get_attribute(self, "heat_power")[t]
                    if t < len(time_series)
                    else model.get_attribute(self, "difference")[t] == 0.0
                ),
            ),
            (
                "abs_difference_max",
                lambda model, t: (
                    model.get_attribute(self, "difference")[t]
                    + N * model.get_attribute(self, "Y")[t]
                    >= model.get_attribute(self, "limit")[t]
                ),
            ),
            (
                "abs_difference_min",
                lambda model, t: (
                    -model.get_attribute(self, "difference")[t]
                    + N * (1 - model.get_attribute(self, "Y")[t])
                    >= model.get_attribute(self, "limit")[t]
                ),
            ),
            (
                "min_limit",
                lambda model, t: (
                    model.get_attribute(self, "difference")[t]
                    <= model.get_attribute(self, "limit")[t]
                ),
            ),
            (
                "max_limit",
                lambda model, t: (
                    -model.get_attribute(self, "difference")[t]
                    <= model.get_attribute(self, "limit")[t]
                ),
            ),
            (
                "fulfillment_is_limit",
                lambda model, t: (
                    model.get_attribute(self, "limit")[t]
                    == model.get_attribute(self, "fulfillment")[t]
                ),
            ),
        ]
