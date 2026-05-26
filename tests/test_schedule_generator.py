import pytest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schedule_generator import ScheduleGenerator, facility_names, name_to_id


@pytest.fixture
def sg():
    return ScheduleGenerator(timeframe=10, step_length=900)


def test_init_sets_parameters(sg):
    assert sg.timeframe == 10
    assert sg.step_length == 900


def test_get_gas_price_returns_list(sg):
    prices = sg.get_gas_price()
    assert isinstance(prices, list)
    assert len(prices) > 0
    for p in prices:
        assert isinstance(p, (int, float))


def test_get_electricity_price_returns_list(sg):
    prices = sg.get_electricity_price()
    assert isinstance(prices, list)
    for p in prices:
        assert isinstance(p, (int, float))


def test_get_heat_demand_returns_list(sg):
    demands = sg.get_heat_demand()
    assert isinstance(demands, list)
    assert len(demands) == sg.timeframe


def test_facility_names_constant():
    assert isinstance(facility_names, list)
    assert "chp" in facility_names
    assert "pem" in facility_names
    assert "bat" in facility_names


def test_name_to_id_constant():
    assert isinstance(name_to_id, dict)
    assert "chp" in name_to_id
    assert name_to_id["chp"] == "1"


def test_schedule_generator_has_build_model(sg):
    assert hasattr(sg, "build_model")
    assert callable(sg.build_model)


def test_schedule_generator_has_solve_model(sg):
    assert hasattr(sg, "solve_model")
    assert callable(sg.solve_model)


def test_schedule_generator_has_extract_schedule(sg):
    assert hasattr(sg, "extract_schedule_from_result")


def test_load_facility_parameters():
    from schedule_generator import load_facility_parameters

    params = load_facility_parameters()
    assert isinstance(params, dict)
    assert "constants" in params


def test_schedule_generator_get_gas_price():
    sg = ScheduleGenerator(timeframe=10, step_length=900)
    prices = sg.get_gas_price()
    assert isinstance(prices, list)


def test_schedule_generator_get_electricity_price():
    sg = ScheduleGenerator(timeframe=10, step_length=900)
    prices = sg.get_electricity_price(start_time=0)
    assert isinstance(prices, list)


def test_schedule_generator_get_heat_demand():
    sg = ScheduleGenerator(timeframe=10, step_length=900)
    heat = sg.get_heat_demand()
    assert isinstance(heat, list)
    assert len(heat) == 10


def test_schedule_generator_model_creation():
    from indexed_model import IndexedModel

    sg = ScheduleGenerator(timeframe=10, step_length=900)
    model = sg.build_model(load_timeseries=None)
    assert model is not None


def test_schedule_generator_facility_params():
    sg = ScheduleGenerator(timeframe=10, step_length=900)
    assert hasattr(sg, "facility_params")
    assert isinstance(sg.facility_params, dict)


def test_schedule_generator_connect_and_schedule():
    from schedule_generator import connect_and_schedule

    assert callable(connect_and_schedule)


def test_schedule_generator_solve_model():
    from schedule_generator import solve_model

    assert callable(solve_model)


def test_schedule_generator_single_step():
    from schedule_generator import single_step_optimization

    assert callable(single_step_optimization)


def test_schedule_generator_multi_step():
    from schedule_generator import multi_step_optimization

    assert callable(multi_step_optimization)


def test_schedule_generator_schedule_day():
    from schedule_generator import schedule_day

    assert callable(schedule_day)


def test_schedule_generator_facility_params_access():
    sg = ScheduleGenerator(timeframe=5, step_length=900)
    assert "Gasstation" in sg.facility_params
    assert "bat" in sg.facility_params


def test_schedule_generator_create_fake_activity_matrix():
    from schedule_generator import create_fake_activity_matrix

    schedule = {
        "chp": [1, 2, 3],
        "pem": [4, 5, 6],
        "bat": [7, 8, 9],
        "meth": [10, 11, 12],
        "Gasstorage": [13, 14, 15],
    }
    matrix = create_fake_activity_matrix(schedule)
    assert isinstance(matrix, list)
    assert len(matrix) > 0
