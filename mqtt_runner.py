import random
from schedule_generator import ScheduleGenerator
import json
from datetime import datetime, timedelta
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_path, get_optimization

import paho.mqtt.client as mqtt
import ssl
import time

log_dir = get_path("logs_dir")
log_filename = "mqtt_runner.log"
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(log_dir, log_filename),
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_credentials():
    """Load MQTT credentials from credentials.json or environment variables."""
    env_config = {
        "broker_host": os.getenv("MQTT_BROKER_HOST"),
        "broker_port": os.getenv("MQTT_BROKER_PORT", "1883"),
        "keepalive_interval": os.getenv("MQTT_KEEPALIVE_INTERVAL", "60"),
        "username": os.getenv("MQTT_USERNAME"),
        "password": os.getenv("MQTT_PASSWORD"),
        "topic_subscribe": os.getenv("MQTT_TOPIC_SUBSCRIBE", "/default_sub"),
        "topic_publish": os.getenv("MQTT_TOPIC_PUBLISH", "/default_pub"),
    }

    if all(env_config.get(k) for k in ["broker_host", "username", "password"]):
        env_config["broker_port"] = int(env_config["broker_port"])
        env_config["keepalive_interval"] = int(env_config["keepalive_interval"])
        return env_config

    config_file = os.path.join(os.path.dirname(__file__), "credentials.json")
    try:
        with open(config_file, "r") as f:
            config = json.load(f)
        return config["mqtt"]
    except FileNotFoundError:
        logger.error(
            f"credentials.json not found at {config_file} and no environment variables set"
        )
        raise
    except KeyError:
        logger.error("Invalid credentials.json format - missing 'mqtt' section")
        raise


mqtt_config = load_credentials()
MQTT_BROKER_HOST = mqtt_config["broker_host"]
MQTT_BROKER_PORT = mqtt_config["broker_port"]
MQTT_KEEPALIVE_INTERVAL = mqtt_config["keepalive_interval"]
USERNAME = mqtt_config["username"]
PASSWORD = mqtt_config["password"]
MQTT_TOPIC_TO_SUBSCRIBE = mqtt_config["topic_subscribe"]
MQTT_TOPIC_TO_PUBLISH = mqtt_config["topic_publish"]

MQTT_RESULTS_FOLDER = get_path("mqtt_results_folder")


class MQTTRunner:
    """
    Encapsulates MQTT client connection and message handling for real-time energy optimization.

    Manages connection to MQTT broker, subscribes to load forecasts, and publishes
    optimization results from the ScheduleGenerator.
    """

    def __init__(
        self,
        broker_host,
        broker_port,
        username,
        password,
        topic_subscribe,
        topic_publish,
        keepalive_interval=60,
    ):
        """
        Initialize MQTT client with connection parameters.

        Args:
            broker_host: MQTT broker hostname
            broker_port: MQTT broker port
            username: MQTT authentication username
            password: MQTT authentication password
            topic_subscribe: Topic to subscribe to for incoming load forecasts
            topic_publish: Topic to publish optimization results to
            keepalive_interval: Keep-alive interval in seconds
        """
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.username = username
        self.password = password
        self.topic_subscribe = topic_subscribe
        self.topic_publish = topic_publish
        self.keepalive_interval = keepalive_interval

        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=username)
        self._configure_client()
        self._ensure_output_folder()

    def _configure_client(self):
        """Configure MQTT client with credentials, TLS, and callbacks."""
        self.client.username_pw_set(self.username, self.password)
        self.client.tls_set(
            ca_certs=None,
            certfile=None,
            keyfile=None,
            cert_reqs=ssl.CERT_NONE,
            tls_version=ssl.PROTOCOL_TLSv1_2,
            ciphers=None,
        )

        # Assign callback methods
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_subscribe = self.on_subscribe
        self.client.on_disconnect = self.on_disconnect

        # Add specific message callback for subscribed topic
        self.client.message_callback_add(self.topic_subscribe, self.handle_message)

    def on_connect(self, client, userdata, flags, rc, properties=None):
        """
        Callback for when the client receives a CONNACK response from the server.
        (rc is the connection result)
        """
        if rc == 0:
            logger.info("Successfully connected to MQTT Broker: %s", self.broker_host)
            # Subscribe to the specific topic upon successful connection
            # Using QoS 1 for at-least-once delivery
            client.subscribe(self.topic_subscribe, qos=1)
            logger.info("Subscribed to topic: '%s'", self.topic_subscribe)
        else:
            logger.error(
                "Failed to connect, return code: %s\nCheck broker address, port, and network.",
                rc,
            )

    def on_message(self, client, userdata, message):
        """
        Callback for when a PUBLISH message is received from the server.
        This is a general message handler.
        """
        logger.debug(
            "Generic on_message: Received message on topic '%s' with payload '%s'",
            message.topic,
            message.payload.decode(),
        )

    def on_subscribe(self, client, userdata, mid, granted_qos, properties=None):
        """
        Callback for when the broker responds to a subscription request.
        """
        logger.debug("Subscribed with MID %s, Granted QoS: %s", mid, granted_qos)

    def on_disconnect(self, client, userdata, flags, rc, properties=None):
        """
        Callback for when the client disconnects from the broker.
        """
        if rc != 0:
            logger.warning(
                "Unexpected disconnection from MQTT Broker. Return code: %s", rc
            )
        else:
            logger.info("Successfully disconnected from MQTT Broker.")

    def handle_message(self, client, userdata, message):
        """
        Callback for processing incoming MQTT messages with load constraint data.

        Handles three types of requests:
        1. Default operation plan (no constraints)
        2. Power constraints (with load forecasts)
        3. Results messages (acknowledgments)

        Args:
            client: MQTT client instance
            userdata: User-provided data
            message: Received MQTT message
        """
        payload_str = message.payload.decode("utf-8")
        logger.info("--- Message Received ---")
        logger.info("Topic: %s", message.topic)
        logger.debug("Payload: %s", payload_str)
        logger.debug("QoS: %s", message.qos)
        logger.debug("Retain Flag: %s", message.retain)

        if len(payload_str) > 5:
            payload_dict = {}
            try:
                payload_dict = json.loads(payload_str)
            except json.JSONDecodeError:
                payload_dict = {"message": payload_str}

            try:
                # payload "accepted operation plan" and "declined operation plan" not yet implemented
                if "default" in payload_str:
                    logger.info("Processing default operation plan request")
                    # Create unconstrained optimization (no load constraints)
                    generator = ScheduleGenerator(timeframe=96, step_length=15 * 60)
                    no_restraints_model = generator.optimize_multi_step(
                        load_timeseries=None, quadratic=True
                    )
                    self.publish_results(
                        no_restraints_model,
                        round(no_restraints_model.income_sum(), 3),
                        generator,
                        mqtt_type="unconstrained",
                    )

                elif "type" not in payload_dict:
                    logger.info("Processing power request with constraints")
                    # Type check and validate payload structure
                    if not isinstance(payload_dict, list):
                        logger.error(
                            "Invalid payload type: expected list, got type %s payload %s",
                            type(payload_dict).__name__,
                            payload_dict,
                        )
                        return

                    if len(payload_dict) == 0:
                        logger.error("Empty power constraints list received")
                        return

                    # Validate each constraint item
                    parsed_power = []
                    for idx, item in enumerate(payload_dict):
                        if not isinstance(item, dict):
                            logger.error(
                                "Invalid constraint item at index %d: expected dict, got type %s payload %s",
                                idx,
                                type(item).__name__,
                                item,
                            )
                            return

                        if "unix_timestep" not in item or "power_EH" not in item:
                            logger.error(
                                "Missing required keys in constraint item at index %d. Expected 'unix_timestep' and 'power_EH'",
                                idx,
                            )
                            return

                        try:
                            timestep = int(item["unix_timestep"])
                            power = float(item["power_EH"])
                            parsed_power.append((timestep, power))
                        except (ValueError, TypeError) as e:
                            logger.error(
                                "Type conversion error at index %d: %s", idx, e
                            )
                            return

                    # Convert to (index, power) format for 96 timesteps
                    parsed_power = [
                        (i, parsed_power[i][1])
                        for i in range(min(len(parsed_power), 96))
                    ]

                    # Run constrained optimization
                    generator = ScheduleGenerator(timeframe=96, step_length=15 * 60)
                    model = generator.optimize_multi_step(
                        load_timeseries=[p[1] for p in parsed_power], quadratic=True
                    )

                    # Run unconstrained optimization for comparison
                    no_restraints_generator = ScheduleGenerator(
                        timeframe=96, step_length=15 * 60
                    )
                    no_restraints_model = no_restraints_generator.optimize_multi_step(
                        load_timeseries=None, quadratic=True
                    )

                    # Publish results with cost difference
                    cost_difference = round(
                        model.income_sum() - no_restraints_model.income_sum(), 3
                    )
                    self.publish_results(
                        model, cost_difference, generator, mqtt_type="results"
                    )
                    logger.info(
                        "Optimization completed. Cost difference: €%s", cost_difference
                    )

                else:
                    logger.info("Results message received and processed")

            except Exception as e:
                logger.error("Error processing message payload: %s", e, exc_info=True)

    def publish_results(self, model, constraint_costs, generator, mqtt_type="results"):
        """
        Publishes the results of the optimization model to the MQTT broker.

        Args:
            model: Solved Pyomo model
            constraint_costs: Cost difference or constraint penalty
            generator: ScheduleGenerator instance used for optimization
            mqtt_type: Type of results being published (default "results")
        """
        milp_schedule = generator.extract_schedule_from_result(model)
        timeframe = len(milp_schedule["chp"])
        combined_schedule = [0 for _ in range(timeframe)]
        for key in milp_schedule:
            # add arrays into combined schedule and round to three decimals
            combined_schedule = [
                round(sum(x), 3) for x in zip(combined_schedule, milp_schedule[key])
            ]
        milp_result = model.get_attribute_by_name(
            "target", "electricity_power"
        ).extract_values()

        publish_dict = {
            "type": mqtt_type,
            "power": [
                min(-1 * round(x * random.uniform(0.9, 1.0), 3), 2.0)
                for x in milp_result.values()
            ],
            "costs": 1.0 * constraint_costs,
        }
        self.client.publish(self.topic_publish, json.dumps(publish_dict))
        logger.info("Published results: %s", publish_dict)
        # save json to file with timestamp
        timestamp = int(time.time())
        with open(
            os.path.join(MQTT_RESULTS_FOLDER, f"published_results_{timestamp}.json"),
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(publish_dict, f)

    def _ensure_output_folder(self) -> None:
        """Create output folder if it does not exist."""
        os.makedirs(MQTT_RESULTS_FOLDER, exist_ok=True)

    def connect(self):
        """
        Establish connection to the MQTT broker.

        Raises:
            ConnectionRefusedError: If connection is refused
            Exception: For other connection errors
        """
        logger.info(
            "Attempting to connect to MQTT broker: %s:%s...",
            self.broker_host,
            self.broker_port,
        )
        try:
            self.client.connect(
                self.broker_host, self.broker_port, self.keepalive_interval
            )
        except ConnectionRefusedError:
            logger.error(
                "Connection refused. Is the broker running at %s:%s?",
                self.broker_host,
                self.broker_port,
            )
            raise
        except Exception as e:
            logger.error("Could not connect to MQTT broker: %s", e)
            raise

    def run(self):
        """
        Start the MQTT client event loop.

        This is a blocking call that handles network traffic, dispatches callbacks,
        and handles reconnections automatically. Press Ctrl+C to exit.
        """
        try:
            logger.info(
                "Starting MQTT client loop... Press Ctrl+C to disconnect and exit."
            )
            error_code = self.client.loop_forever(timeout=2)
            if error_code != 0:
                logger.warning("Loop exited with error code: %s", error_code)
        except KeyboardInterrupt:
            logger.info(
                "Keyboard interrupt received. Disconnecting from MQTT broker..."
            )
        finally:
            self.disconnect()

    def disconnect(self):
        """Cleanly disconnect from the MQTT broker and stop the event loop."""
        self.client.disconnect()
        self.client.loop_stop()
        logger.info("Client disconnected and loop stopped.")


# --- Main Entry Point ---
if __name__ == "__main__":
    runner = MQTTRunner(
        broker_host=MQTT_BROKER_HOST,
        broker_port=MQTT_BROKER_PORT,
        username=USERNAME,
        password=PASSWORD,
        topic_subscribe=MQTT_TOPIC_TO_SUBSCRIBE,
        topic_publish=MQTT_TOPIC_TO_PUBLISH,
        keepalive_interval=MQTT_KEEPALIVE_INTERVAL,
    )

    try:
        runner.connect()
        runner.run()
    except Exception as e:
        logger.error("Fatal error: %s", e, exc_info=True)
        exit(1)
