import json
from types import SimpleNamespace
import pytest
from unittest.mock import patch, MagicMock


def test_mqtt_runner_can_be_imported():
    import mqtt_runner

    assert hasattr(mqtt_runner, "MQTTRunner")


def test_mqtt_runner_init_signature():
    import inspect
    from mqtt_runner import MQTTRunner

    sig = inspect.signature(MQTTRunner.__init__)
    params = list(sig.parameters.keys())
    assert "self" in params
    assert "broker_host" in params
    assert "broker_port" in params
    assert "username" in params
    assert "password" in params
    assert "topic_subscribe" in params
    assert "topic_publish" in params


def test_mqtt_runner_has_required_methods():
    from mqtt_runner import MQTTRunner

    assert hasattr(MQTTRunner, "on_connect")
    assert hasattr(MQTTRunner, "on_message")
    assert hasattr(MQTTRunner, "on_subscribe")
    assert hasattr(MQTTRunner, "on_disconnect")
    assert hasattr(MQTTRunner, "handle_message")
    assert hasattr(MQTTRunner, "publish_results")
    assert hasattr(MQTTRunner, "connect")
    assert hasattr(MQTTRunner, "run")
    assert hasattr(MQTTRunner, "disconnect")


def test_mqtt_runner_publish_results_method_exists():
    from mqtt_runner import MQTTRunner

    assert callable(getattr(MQTTRunner, "publish_results", None))


def test_mqtt_runner_handle_message_method_exists():
    from mqtt_runner import MQTTRunner

    assert callable(getattr(MQTTRunner, "handle_message", None))


def test_mqtt_runner_load_credentials():
    import mqtt_runner
    import os

    creds_file = os.path.join(os.path.dirname(mqtt_runner.__file__), "credentials.json")
    if os.path.exists(creds_file):
        with open(creds_file, "r") as f:
            import json

            data = json.load(f)
            assert "mqtt" in data


def test_mqtt_runner_load_credentials_from_env():
    import os
    import mqtt_runner
    from unittest.mock import patch

    env_vars = {
        "MQTT_BROKER_HOST": "env.host.com",
        "MQTT_BROKER_PORT": "1883",
        "MQTT_USERNAME": "env_user",
        "MQTT_PASSWORD": "env_pass",
        "MQTT_TOPIC_SUBSCRIBE": "/env/sub",
        "MQTT_TOPIC_PUBLISH": "/env/pub",
    }

    with patch.dict(os.environ, env_vars, clear=False):
        with patch("mqtt_runner.open", create=True) as mock_open:
            mock_open.side_effect = FileNotFoundError("No credentials.json")
            import importlib
            import sys

            if "mqtt_runner" in sys.modules:
                del sys.modules["mqtt_runner"]
            with patch("os.path.dirname", return_value="/fake"):
                result = mqtt_runner.load_credentials()
                assert result["broker_host"] == "env.host.com"
                assert result["broker_port"] == 1883
                assert result["username"] == "env_user"
                assert isinstance(result["broker_port"], int)


def test_mqtt_runner_mqtt_results_folder():
    from mqtt_runner import MQTT_RESULTS_FOLDER

    assert isinstance(MQTT_RESULTS_FOLDER, str)


def test_mqtt_runner_log_config():
    import logging
    from mqtt_runner import logger

    assert isinstance(logger, logging.Logger)


def test_mqtt_runner_default_consts():
    from mqtt_runner import MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_KEEPALIVE_INTERVAL

    assert isinstance(MQTT_BROKER_HOST, str)
    assert isinstance(MQTT_BROKER_PORT, int)
    assert isinstance(MQTT_KEEPALIVE_INTERVAL, int)


def test_mqtt_runner_on_connect_callback():
    from mqtt_runner import MQTTRunner
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as td:
        os.makedirs(os.path.join(td, "mqttresults"))

        with patch("mqtt_runner.mqtt.Client") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            runner = MQTTRunner("test.host", 1883, "user", "pass", "sub", "pub")

            mock_client.reset_mock()

            runner.on_connect(mock_client, None, None, 0, None)

            assert mock_client.subscribe.called


def test_mqtt_runner_on_disconnect_callback():
    from mqtt_runner import MQTTRunner
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as td:
        os.makedirs(os.path.join(td, "mqttresults"))

        with patch("mqtt_runner.mqtt.Client") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            runner = MQTTRunner("test.host", 1883, "user", "pass", "sub", "pub")

            runner.on_disconnect(mock_client, None, None, 0, None)


def test_mqtt_runner_on_subscribe_callback():
    from mqtt_runner import MQTTRunner
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as td:
        os.makedirs(os.path.join(td, "mqttresults"))

        with patch("mqtt_runner.mqtt.Client") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            runner = MQTTRunner("test.host", 1883, "user", "pass", "sub", "pub")

            runner.on_subscribe(mock_client, None, 1, [1], None)


def test_mqtt_runner_publish_results():
    from mqtt_runner import MQTTRunner
    import tempfile
    import os
    import json

    with tempfile.TemporaryDirectory() as td:
        os.makedirs(os.path.join(td, "mqttresults"))

        with patch("mqtt_runner.mqtt.Client") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            runner = MQTTRunner("test.host", 1883, "user", "pass", "sub", "pub")

            mock_model = MagicMock()
            mock_model.income_sum.return_value = 100.0

            generator = MagicMock()

            runner.publish_results(mock_model, 100.0, generator, "results")

            assert mock_client.publish.called


def test_mqtt_runner_handle_message_default():
    from mqtt_runner import MQTTRunner
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as td:
        os.makedirs(os.path.join(td, "mqttresults"))

        with patch("mqtt_runner.mqtt.Client") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            with patch("mqtt_runner.ScheduleGenerator") as MockGen:
                mock_model = MagicMock()
                mock_gen_instance = MagicMock()
                mock_gen_instance.optimize_multi_step.return_value = mock_model
                mock_gen_instance.optimize_multi_step.return_value.income_sum.return_value = 100.0
                MockGen.return_value = mock_gen_instance

                runner = MQTTRunner("test.host", 1883, "user", "pass", "sub", "pub")

                mock_message = MagicMock()
                mock_message.payload = b'{"default": true}'
                mock_message.topic = "test"

                runner.handle_message(mock_client, None, mock_message)


def test_mqtt_runner_topics():
    from mqtt_runner import MQTT_TOPIC_TO_SUBSCRIBE, MQTT_TOPIC_TO_PUBLISH

    assert isinstance(MQTT_TOPIC_TO_SUBSCRIBE, str)
    assert isinstance(MQTT_TOPIC_TO_PUBLISH, str)
