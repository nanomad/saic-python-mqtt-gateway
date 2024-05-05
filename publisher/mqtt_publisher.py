import logging
import os
import ssl
from typing import Optional, List, override

import gmqtt

import mqtt_topics
from configuration import Configuration
from integrations import SaicMqttGatewayIntegration, SaicMqttGatewayIntegrationException
from publisher.core import MqttCommandListener
from publisher.core import Publisher

LOG = logging.getLogger(__name__)
LOG.setLevel(level=os.getenv('LOG_LEVEL', 'INFO').upper())

MQTT_LOG = logging.getLogger(gmqtt.__name__)
MQTT_LOG.setLevel(level=os.getenv('MQTT_LOG_LEVEL', 'INFO').upper())


class MqttClient(Publisher):
    def __init__(self, configuration: Configuration):
        super().__init__(configuration)
        self.configuration = configuration
        self.publisher_id = self.configuration.mqtt_client_id
        self.topic_root = configuration.mqtt_topic
        self.client = None
        self.host = self.configuration.mqtt_host
        self.port = self.configuration.mqtt_port
        self.transport_protocol = self.configuration.mqtt_transport_protocol
        self.command_listener: Optional[MqttCommandListener] = None
        self.integrations: List[SaicMqttGatewayIntegration] = []

        mqtt_client = gmqtt.Client(
            client_id=str(self.publisher_id),
            transport=self.transport_protocol.transport_mechanism,
            logger=MQTT_LOG,
            will_message=gmqtt.Message(
                topic=self.get_topic(mqtt_topics.INTERNAL_LWT, False),
                payload='offline',
                retain=True
            )
        )
        mqtt_client.on_connect = self.__on_connect
        mqtt_client.on_message = self.__on_message
        self.client = mqtt_client

    def get_mqtt_account_prefix(self) -> str:
        return MqttClient.remove_special_mqtt_characters(
            f'{self.configuration.mqtt_topic}/{self.configuration.saic_user}')

    @staticmethod
    def remove_special_mqtt_characters(input_str: str) -> str:
        return input_str.replace('+', '_').replace('#', '_').replace('*', '_') \
            .replace('>', '_').replace('$', '_')

    async def connect(self):
        if self.configuration.mqtt_user is not None:
            if self.configuration.mqtt_password is not None:
                self.client.set_auth_credentials(
                    username=self.configuration.mqtt_user,
                    password=self.configuration.mqtt_password
                )
            else:
                self.client.set_auth_credentials(
                    username=self.configuration.mqtt_user
                )
        if self.transport_protocol.with_tls:
            cert_uri = self.configuration.tls_server_cert_path
            LOG.debug(f'Configuring network encryption and authentication options for MQTT using {cert_uri}')
            ssl_context = ssl.SSLContext()
            ssl_context.load_verify_locations(cafile=cert_uri)
            ssl_context.check_hostname = False
        else:
            ssl_context = None
        await self.client.connect(host=self.host, port=self.port, version=gmqtt.constants.MQTTv311, ssl=ssl_context)

    def __on_connect(self, _client, _flags, rc, _properties) -> None:
        if rc == gmqtt.constants.CONNACK_ACCEPTED:
            LOG.info('Connected to MQTT broker')
            mqtt_account_prefix = self.get_mqtt_account_prefix()
            self.client.subscribe(f'{mqtt_account_prefix}/{mqtt_topics.VEHICLES}/+/+/+/set')
            self.client.subscribe(f'{mqtt_account_prefix}/{mqtt_topics.VEHICLES}/+/+/+/+/set')
            self.client.subscribe(f'{mqtt_account_prefix}/{mqtt_topics.VEHICLES}/+/{mqtt_topics.REFRESH_MODE}/set')
            self.client.subscribe(f'{mqtt_account_prefix}/{mqtt_topics.VEHICLES}/+/{mqtt_topics.REFRESH_PERIOD}/+/set')
            for charging_station in self.configuration.charging_stations_by_vin.values():
                LOG.debug(f'Subscribing to MQTT topic {charging_station.charge_state_topic}')
                self.vin_by_charge_state_topic[charging_station.charge_state_topic] = charging_station.vin
                self.client.subscribe(charging_station.charge_state_topic)
                if charging_station.connected_topic:
                    LOG.debug(f'Subscribing to MQTT topic {charging_station.connected_topic}')
                    self.vin_by_charger_connected_topic[charging_station.connected_topic] = charging_station.vin
                    self.client.subscribe(charging_station.connected_topic)
            self.keepalive()
        else:
            if rc == gmqtt.constants.CONNACK_REFUSED_BAD_USERNAME_PASSWORD:
                LOG.error(f'MQTT connection error: bad username or password. Return code {rc}')
            elif rc == gmqtt.constants.CONNACK_REFUSED_PROTOCOL_VERSION:
                LOG.error(f'MQTT connection error: refused protocol version. Return code {rc}')
            else:
                LOG.error(f'MQTT connection error.Return code {rc}')
            SystemExit(f'Unable to connect to MQTT broker. Return code: {rc}')

    async def __on_message(self, _client, topic, payload, _qos, _properties) -> None:
        try:
            if isinstance(payload, bytes):
                payload = payload.decode('utf-8')
            else:
                payload = str(payload)
            await self.__on_message_real(topic=topic, payload=payload)
        except Exception as e:
            LOG.exception(f'Error while processing MQTT message: {e}')

    async def __on_message_real(self, *, topic: str, payload: str) -> None:
        if await self.__handle_raw_mqtt_message_integrations(topic, payload):
            LOG.debug(f'Received message over topic {topic} with payload {payload}')
        else:
            vin = self.get_vin_from_topic(topic)
            if self.command_listener is not None:
                await self.command_listener.on_mqtt_command_received(vin=vin, topic=topic, payload=payload)
        return

    async def __handle_raw_mqtt_message_integrations(self, topic, payload) -> bool:
        topic = str(topic)
        payload = str(payload)
        success = False
        for integration in self.integrations:
            try:
                integration_refreshed, integration_response = await integration.on_raw_mqtt_message(
                    topic=topic,
                    payload=payload
                )
                if integration_refreshed:
                    LOG.info(f'Handling RAW MQTT message on {topic} in integration {integration.name} succeeded...')
                    success = True
            except SaicMqttGatewayIntegrationException as ae:
                LOG.exception(
                    f'handle_vehicle loop failed during Handling MQTT command {topic} integration {integration.name} processing call',
                    exc_info=ae
                )
        return success

    def publish(self, topic: str, payload) -> None:
        self.client.publish(self.remove_special_mqtt_characters(topic), payload, retain=True)

    def get_topic(self, key: str, no_prefix: bool) -> str:
        if no_prefix:
            topic = key
        else:
            topic = f'{self.topic_root}/{key}'
        return self.remove_special_mqtt_characters(topic)

    @override
    def is_connected(self) -> bool:
        return self.client and self.client.is_connected

    @override
    def publish_json(self, key: str, data: dict, no_prefix: bool = False) -> None:
        payload = self.dict_to_anonymized_json(data)
        self.publish(topic=self.get_topic(key, no_prefix), payload=payload)

    @override
    def publish_str(self, key: str, value: str, no_prefix: bool = False) -> None:
        self.publish(topic=self.get_topic(key, no_prefix), payload=value)

    @override
    def publish_int(self, key: str, value: int, no_prefix: bool = False) -> None:
        self.publish(topic=self.get_topic(key, no_prefix), payload=value)

    @override
    def publish_bool(self, key: str, value: bool | int | None, no_prefix: bool = False) -> None:
        if value is None:
            value = False
        elif isinstance(value, int):
            value = value == 1
        self.publish(topic=self.get_topic(key, no_prefix), payload=value)

    @override
    def publish_float(self, key: str, value: float, no_prefix: bool = False) -> None:
        self.publish(topic=self.get_topic(key, no_prefix), payload=value)

    def get_vin_from_topic(self, topic: str) -> str:
        global_topic_removed = topic[len(self.configuration.mqtt_topic) + 1:]
        elements = global_topic_removed.split('/')
        return elements[2]
