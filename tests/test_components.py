import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyomo.environ import Reals, UnitInterval, Binary, NonNegativeReals

from components.component import Component, Value
from components.converter import Converter
from components.storage import Storage
from components.grid import Grid
from components.target import Target
from components.heat_target import HeatTarget


def test_value_class_basic():
    v = Value("test_value", Reals, initialize=0.0)
    assert v.name == "test_value"
    assert v.initialize == 0.0
    assert v.within is Reals


def test_component_basic_initialization():
    comp = Component("compA", types=["electricity", "gas"], step_length=3)
    assert comp.name == "compA"
    assert comp.step_length == 3
    assert comp.energy_types == ["electricity", "gas"]
    # Two power variables should be created for the two energy types
    power_names = {v.name for v in comp.values}
    assert "electricity_power" in power_names
    assert "gas_power" in power_names
    assert comp.params == []
    assert comp.constraints == []
    assert comp.cost_objectives == []
    assert comp.fulfillment_objectives == []


def test_converter_initialization_basic():
    max_powers = {"H2": 2.0}
    min_powers = {"H2": 0.0}
    input_types = ["electricity"]
    output_types = ["H2"]
    conv = Converter(
        name="conv1",
        max_powers=max_powers,
        min_powers=min_powers,
        input_types=input_types,
        output_types=output_types,
        conversion_factors={"electricity": 1.0, "H2": 0.6},
        ramp_up=0.5,
        ramp_down=0.5,
        step_length=60,
    )

    # Base Component initialization checks
    assert conv.name == "conv1"
    assert conv.energy_types == input_types + output_types
    assert conv.min_power == 0.0
    assert conv.max_power == 2.0
    # Should always contain setpoint, is_active, and income values
    value_names = {v.name for v in conv.values}
    assert "setpoint" in value_names
    assert "is_active" in value_names
    assert "income" in value_names


def test_storage_initialization_basic():
    s = Storage(
        name="storage1",
        input_types=["electricity"],
        max_charging_power=3.0,
        max_discharging_power=5.0,
        capacity=10.0,
        charging_efficiency=0.95,
        initial_charge=0.4,
        step_length=60,
    )
    assert s.name == "storage1"
    assert s.energy_type == "electricity"
    assert s.initial_charge == 0.4
    assert s.capacity == 10.0
    assert s.max_charging_power == 3.0
    assert s.max_discharging_power == 5.0
    # state_of_charge initialization
    sc_names = {v.name for v in s.values}
    assert "state_of_charge" in sc_names
    # Ensure the initialize value is carried through
    for v in s.values:
        if v.name == "state_of_charge":
            assert v.initialize == 0.4
            break
    assert "is_charging" in sc_names
    assert "setpoint" in sc_names


def test_grid_initialization_basic():
    g = Grid(
        name="grid1",
        energy_cost=[0.2],
        max_selling_power=5,
        max_buying_power=-3,
        types=["electricity"],
        step_length=60,
    )
    assert g.name == "grid1"
    assert g.energy_types == ["electricity"]
    assert g.has_cost_objective is True
    # should contain is_buying and income values
    names = {v.name for v in g.values}
    assert "is_buying" in names
    assert "income" in names


def test_target_initialization_basic():
    time_series = {0: 50.0, 1: 60.0}
    prices = [0.25, 0.24]
    t = Target(
        name="target1",
        time_series=time_series,
        electricity_prices=prices,
        step_length=60,
    )
    assert t.name == "target1"
    assert t.energy_types == ["electricity"]
    assert t.target == time_series
    # values present
    names = {v.name for v in t.values}
    for n in ["limit", "difference", "fulfillment", "income", "Y"]:
        assert n in names
    assert t.has_income_objective is True


def test_heat_target_initialization_basic():
    ht = HeatTarget(name="heat1", time_series=[10, 20, 30], step_length=60)
    assert ht.name == "heat1"
    assert ht.energy_types == ["heat"]
    assert ht.target == [10, 20, 30]
    names = {v.name for v in ht.values}
    for n in ["limit", "difference", "fulfillment", "Y"]:
        assert n in names
    assert ht.has_fulfillment_objective is True
