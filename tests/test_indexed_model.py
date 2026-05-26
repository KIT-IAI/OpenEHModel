import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyomo.environ import Reals, minimize, maximize, Objective
from pyomo.core.base import Constraint

from indexed_model import IndexedModel


class _ValueStub:
    def __init__(self, name: str, within=None):
        self.name = name
        # Pyomo expects a domain type for 'within'. Use Reals by default.
        self.within = within if within is not None else Reals


class _DeviceStub:
    def __init__(
        self,
        name: str,
        energy_types: list,
        has_income_objective: bool = True,
        has_fulfillment_objective: bool = True,
    ):
        self.name = name
        self.energy_types = energy_types
        self.has_income_objective = has_income_objective
        self.has_fulfillment_objective = has_fulfillment_objective
        self.values = []  # time-indexed variables (ValueStub instances)
        self.params = []
        self.constraints = []  # not used heavily in tests


def _make_device(name: str, energy_types: list) -> _DeviceStub:
    d = _DeviceStub(name=name, energy_types=energy_types)
    values = [_ValueStub("income")]
    for et in energy_types:
        values.append(_ValueStub(f"{et}_power"))
    values.append(_ValueStub("fulfillment"))
    d.values = values
    return d


@pytest.fixture
def single_electricity_device():
    return _make_device("charger1", ["electricity"])


@pytest.fixture
def two_devices_mixed_energy():
    d1 = _make_device("charger1", ["electricity"])
    d2 = _make_device("heater1", ["heat"])
    return d1, d2


def test_model_initialization_with_time_index():
    idx = range(4)
    m = IndexedModel(index=idx)
    # t should reflect the provided index; here we check length for sanity
    assert len(m.get_index()) == 4


def test_setting_quadratic_objective(single_electricity_device):
    m = IndexedModel(index=range(2))
    m.add_device(single_electricity_device)
    m.set_objective_with_weights(
        income_weight=0.5,
        fulfillment_weight=0.5,
        step_length=900,
        max_mean_deviation=10,
        min_mean_deviation=0,
        min_income=0,
        max_income=100,
        quadratic=True,
    )
    assert isinstance(m.obj, Objective)  # Objective object exists
    assert m.obj.sense == minimize


def test_setting_linear_objective(single_electricity_device):
    m = IndexedModel(index=range(2))
    m.add_device(single_electricity_device)
    m.set_objective_with_weights(
        income_weight=0.6,
        fulfillment_weight=0.4,
        step_length=900,
        max_mean_deviation=10,
        min_mean_deviation=0,
        min_income=0,
        max_income=100,
        quadratic=False,
    )
    assert isinstance(m.obj, Objective)  # still an Objective object
    assert m.obj.sense == maximize


def test_adding_devices_and_energy_types_registered(two_devices_mixed_energy):
    m = IndexedModel(index=range(3))
    d1, d2 = two_devices_mixed_energy
    m.add_device(d1)
    m.add_device(d2)
    # Energy types should include both electricity and heat after addition
    assert "electricity" in m.energy_types
    assert "heat" in m.energy_types


def test_generate_power_balance_constraint_generation(two_devices_mixed_energy):
    m = IndexedModel(index=range(2))
    d1, d2 = two_devices_mixed_energy
    m.add_device(d1)
    m.add_device(d2)
    m.generate_power_balance()
    # Expect a power balance constraint for each energy type present
    assert hasattr(m, "electricity_power_balance")
    assert hasattr(m, "heat_power_balance")
    assert isinstance(getattr(m, "electricity_power_balance"), Constraint)
    assert isinstance(getattr(m, "heat_power_balance"), Constraint)


def test_get_attribute_by_name_and_get_attribute(single_electricity_device):
    m = IndexedModel(index=range(2))
    m.add_device(single_electricity_device)
    # Build attributes by expected names
    income_attr = m.get_attribute(single_electricity_device, "income")
    direct_income_attr = getattr(m, f"{single_electricity_device.name}_income")
    assert income_attr is direct_income_attr

    electricity_power_attr = m.get_attribute(
        single_electricity_device, "electricity_power"
    )
    direct_power_attr = getattr(
        m, f"{single_electricity_device.name}_electricity_power"
    )
    assert electricity_power_attr is direct_power_attr

    # Also test get_attribute_by_name helper
    income_by_name = m.get_attribute_by_name(single_electricity_device.name, "income")
    assert income_by_name is direct_income_attr
