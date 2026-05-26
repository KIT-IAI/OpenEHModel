from components.converter import Converter


class CHP(Converter):
    """
    A combined heat and power plant.
    Generates electricity and heat from methane.
    Generates income by selling heat, reduced by CO2 certificates.

    args:
        heat_price (float): €/kWh of heat energy created.
        thermic_efficiency (float): in [0,1]; efficiency of methane burned
        CO2_price (float): cost of emitting CO2 in euro/kG
        CH4_to_CO2 (float): amount of CO2 (kg) emitted per unit of Methane burned (energy equivalent)
    """

    def __init__(
        self, heat_price, thermic_efficiency, CO2_price, CH4_to_CO2, **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.has_income_objective = True
        self.thermic_efficiency = thermic_efficiency
        income = [
            (
                "income",
                lambda model, t: (
                    -model.get_attribute(self, "methane_power")[t]
                    * self.thermic_efficiency
                    * heat_price[t]
                    * self.step_length
                    / 3600
                    + model.get_attribute(self, "methane_power")[t]
                    * self.step_length
                    / 3600
                    * CO2_price
                    * CH4_to_CO2
                    == model.get_attribute(self, "income")[t]
                ),
            )
        ]
        self.constraints.extend(income)
