from components.component import Component


class Generation(Component):
    """
    Local generation of renewable energy. Always needs to bu fully utilized.
    args:
        name (string): name of the device for internal reference
        positive_powers (dict): amount of power created per type and time step. Shape
           {'type':[power_t0, power_t1,...], }
        cost (dict): Cost of energy production per type in euro/kWh
            {'type': cost,}
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
