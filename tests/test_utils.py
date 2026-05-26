import pickle
import json
import math
import pytest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from load_import import load_obj
from main import load_ea_results, save_ea_results, calculate_statistics


@pytest.fixture
def pickle_data_path(tmp_path):
    path = tmp_path / "sample.pkl"
    data = {"a": 1, "b": [1, 2, 3]}
    with open(path, "wb") as f:
        pickle.dump(data, f)
    return path, data


@pytest.fixture
def ea_results_folder(tmp_path):
    folder = tmp_path / "ea_results"
    folder.mkdir()
    data = {
        "BHKW": {"P_el": [1000000] * 96},
        "Electrolyseur": {"P_el": [500000] * 96},
        "Battery": {"P": [100000] * 96},
        "Lastreihe": {"P_el": [800000] * 96},
    }
    with open(folder / "result_1.json", "w") as f:
        json.dump(data, f)
    with open(folder / "result_2.json", "w") as f:
        json.dump(data, f)
    return folder


@pytest.fixture
def empty_pickle_path(tmp_path):
    path = tmp_path / "empty.pkl"
    path.write_bytes(b"")
    return path


def test_load_obj_valid(pickle_data_path):
    path, expected = pickle_data_path
    assert load_obj(str(path)) == expected


def test_load_obj_missing_file():
    with pytest.raises(FileNotFoundError):
        load_obj("nonexistent.pkl")


def test_load_obj_empty_file(empty_pickle_path):
    with pytest.raises((EOFError, pickle.UnpicklingError)):
        load_obj(str(empty_pickle_path))


def test_load_ea_results_valid(ea_results_folder):
    results = load_ea_results(str(ea_results_folder))
    assert isinstance(results, list)
    assert len(results) == 2


def test_load_ea_results_missing_file():
    with pytest.raises(FileNotFoundError):
        load_ea_results("missing_folder")


def test_load_ea_results_empty_or_invalid(tmp_path):
    empty_folder = tmp_path / "empty"
    empty_folder.mkdir()
    results = load_ea_results(str(empty_folder))
    assert results == []


def test_save_ea_results_valid(tmp_path):
    path = tmp_path / "saved_results.json"
    data = [([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]), ([4.0, 5.0, 6.0], [4.0, 5.0, 6.0])]
    save_ea_results(data, str(path))
    with open(path, "r") as f:
        loaded = json.load(f)
    assert len(loaded) == 2
    assert loaded[0][0] == [1.0, 2.0, 3.0]
    assert loaded[0][1] == [1.0, 2.0, 3.0]


def test_save_ea_results_invalid_data_type(tmp_path):
    path = tmp_path / "bad.json"
    bad_data = {"set": {1, 2, 3}}
    with pytest.raises(TypeError):
        save_ea_results(bad_data, str(path))


def test_calculate_statistics_valid(tmp_path):
    results_file = tmp_path / "results.json"
    results = [[[1.0, 2.0, 3.0], [1.0, 2.0, 3.0]], [[1.5, 2.5, 3.5], [1.0, 2.0, 4.0]]]
    with open(results_file, "w") as f:
        json.dump(results, f)
    stats_file = tmp_path / "stats.txt"
    calculate_statistics(str(results_file), str(stats_file))
    assert stats_file.exists()
    content = stats_file.read_text()
    assert "Mean RMSE:" in content


def test_calculate_statistics_length_mismatch(tmp_path):
    results_file = tmp_path / "results.json"
    results = [[[1.0, 2.0], [1.0, 2.0, 3.0]]]
    with open(results_file, "w") as f:
        json.dump(results, f)
    stats_file = tmp_path / "stats.txt"
    calculate_statistics(str(results_file), str(stats_file))
    content = stats_file.read_text()
    assert "Statistics for 0 days" in content


def test_config_load():
    from config import load_config, get_config

    config = load_config()
    assert isinstance(config, dict)
    assert "paths" in config
    assert "solver" in config


def test_config_get_path():
    from config import get_path

    path = get_path("data_dir")
    assert path == "Daten"


def test_config_get_solver():
    from config import get_solver

    solver = get_solver()
    assert isinstance(solver, dict)
    assert "ipopt_executable" in solver


def test_config_get_optimization():
    from config import get_optimization

    opt = get_optimization()
    assert isinstance(opt, dict)
    assert "timesteps_per_day" in opt


def test_config_get_weights():
    from config import get_weights

    weights = get_weights()
    assert isinstance(weights, dict)


def test_config_get_constraints():
    from config import get_constraints

    constraints = get_constraints()
    assert isinstance(constraints, dict)


def test_config_get_output():
    from config import get_output

    output = get_output()
    assert isinstance(output, dict)


def test_config_get_data_dir():
    from config import get_data_dir

    assert get_data_dir() == "Daten"


def test_config_get_output_dir():
    from config import get_output_dir

    assert get_output_dir() == "output"


def test_config_get_logs_dir():
    from config import get_logs_dir

    assert get_logs_dir() == "logs"


def test_config_get_ipopt_executable():
    from config import get_ipopt_executable

    assert get_ipopt_executable() == "ipopt"


def test_main_optimization_config():
    from main import OptimizationConfig

    config = OptimizationConfig(n_days=3)
    assert config.n_days == 3
    assert hasattr(config, "all_results_file_quad")
    assert hasattr(config, "ea_folder_path")


def test_main_optimization_config_default():
    from main import OptimizationConfig

    config = OptimizationConfig()
    assert config.n_days == 5


def test_main_load_ea_results_returns_list():
    from main import load_ea_results
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as td:
        folder = os.path.join(td, "res")
        os.makedirs(folder)
        data = {
            "BHKW": {"P_el": [100] * 96},
            "Electrolyseur": {"P_el": [50] * 96},
            "Battery": {"P": [10] * 96},
            "Lastreihe": {"P_el": [80] * 96},
        }
        import json

        with open(os.path.join(folder, "test.json"), "w") as f:
            json.dump(data, f)
        results = load_ea_results(folder)
        assert isinstance(results, list)


def test_generate_loadts_read_ea_results():
    from generate_loadts import read_ea_results
    import tempfile
    import os
    import pandas as pd

    with tempfile.TemporaryDirectory() as td:
        folder = os.path.join(td, "res")
        os.makedirs(folder)
        data = {"Lastreihe": {"P_el": [100] * 96}}
        import json

        with open(os.path.join(folder, "test.json"), "w") as f:
            json.dump(data, f)
        df = read_ea_results(folder)
        assert isinstance(df, pd.DataFrame)
        assert "time" in df.columns
        assert "Lastreihe" in df.columns


def test_utils_result_schedule_handler():
    from utils.result_schedule_handler import ResultScheduleHandler

    handler = ResultScheduleHandler(schedule_filename="test.csv")
    assert hasattr(handler, "write_day")
    assert hasattr(handler, "read_file")
    assert hasattr(handler, "get_day")


def test_utils_mqtt_handler():
    import utils.mqtt_handler as mh

    assert mh is not None


def test_main_optimization_config_timeseries_path():
    from main import OptimizationConfig

    config = OptimizationConfig(n_days=1)
    expected_file = config.timeseries_filename
    assert expected_file.endswith(".pkl")


def test_main_load_ea_results_with_multiple_files():
    from main import load_ea_results
    import tempfile
    import os
    import json

    with tempfile.TemporaryDirectory() as td:
        res_folder = os.path.join(td, "res")
        os.makedirs(res_folder)
        for i in range(3):
            data = {
                "BHKW": {"P_el": [100 + i] * 96},
                "Electrolyseur": {"P_el": [50 + i] * 96},
                "Battery": {"P": [10 + i] * 96},
                "Lastreihe": {"P_el": [80 + i] * 96},
            }
            with open(os.path.join(res_folder, f"result_{i}.json"), "w") as f:
                json.dump(data, f)

        results = load_ea_results(res_folder)
        assert isinstance(results, list)
        assert len(results) == 3


def test_schedule_generator_extract_schedule_from_result():
    from schedule_generator import ScheduleGenerator

    class FakeAttr:
        def extract_values(self):
            return {0: 1.0, 1: 2.0, 2: 3.0}

    class FakeModel:
        def get_attribute_by_name(self, facility, attr):
            return FakeAttr()

    model = FakeModel()
    schedule = ScheduleGenerator.extract_schedule_from_result(model)
    assert isinstance(schedule, dict)


def test_schedule_generator_solve_model_with_mock():
    from schedule_generator import ScheduleGenerator
    from unittest.mock import patch, MagicMock

    sg = ScheduleGenerator(timeframe=2, step_length=900)

    mock_model = MagicMock()
    mock_model.income_sum.return_value = 100.0
    mock_model.income_dof.return_value = 0.5
    mock_model.fulfillment_dof.return_value = 0.8
    mock_model.mean_deviation.return_value = 0.1

    with patch("schedule_generator.IndexedModel") as MockModel:
        mock_instance = MagicMock()
        MockModel.return_value = mock_instance
        mock_instance.set_objective_with_weights.return_value = None
        mock_instance.generate_power_balance.return_value = None
        mock_instance.income_sum.return_value = 100.0
        mock_instance.income_dof.return_value = 0.5
        mock_instance.fulfillment_dof.return_value = 0.8
        mock_instance.mean_deviation.return_value = 0.1

        with patch("schedule_generator.SolverFactory") as MockSolver:
            mock_solver = MagicMock()
            MockSolver.return_value = mock_solver
            mock_solver.solve.return_value = MagicMock()

            result = sg.solve_model(
                mock_model,
                income_weight=0.5,
                fulfillment_weight=0.5,
                max_mean_deviation=10,
                min_mean_deviation=0,
                min_income=0,
                max_income=1000,
                quadratic=True,
            )


def test_schedule_generator_optimize_multi_step():
    from schedule_generator import ScheduleGenerator
    from unittest.mock import patch, MagicMock

    with patch("schedule_generator.ScheduleGenerator.solve_model") as mock_solve:
        mock_solve.return_value = MagicMock()

        sg = ScheduleGenerator(timeframe=2, step_length=900)
        result = sg.optimize_multi_step(load_timeseries=None, quadratic=True)

        assert mock_solve.called


def test_main_save_ea_results_loads_json():
    from main import save_ea_results
    import json
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "results.json")
        data = [[1.0, 2.0], [3.0, 4.0]]
        save_ea_results(data, path)
        with open(path) as f:
            loaded = json.load(f)
        assert loaded == data


def test_main_calculate_statistics_with_valid_data():
    from main import calculate_statistics
    import json
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as td:
        results_file = os.path.join(td, "results.json")
        stats_file = os.path.join(td, "stats.txt")

        results = [[[1.0, 2.0], [1.0, 2.0]], [[3.0, 4.0], [3.0, 4.0]]]
        with open(results_file, "w") as f:
            json.dump(results, f)

        calculate_statistics(results_file, stats_file)

        assert os.path.exists(stats_file)
        with open(stats_file) as f:
            content = f.read()
        assert "Mean RMSE:" in content
