from __future__ import annotations

import json
from typing import override
import unittest
from unittest import mock

from saic_python_mqtt_gateway import mqtt_topics
from saic_python_mqtt_gateway.integrations.home_assistant.discovery import (
    HomeAssistantDiscovery,
)
from saic_python_mqtt_gateway.model import VehicleInfo
from tests.common_mocks import get_mock_vin_info
from tests.mocks import MessageCapturingConsolePublisher

DISCOVERY_PREFIX = "/DISCOVERY_PREFIX"
BASE_MQTT_TOPIC = "/MQTT_TOPIC"
VEHICLE_PREFIX = "VEHICLE_PREFIX"


class HomeAssistantDiscoveryTest(unittest.IsolatedAsyncioTestCase):
    @override
    def setUp(self) -> None:
        configuration = mock.MagicMock(
            mqtt_topic=BASE_MQTT_TOPIC,
            ha_discovery_prefix=DISCOVERY_PREFIX,
            ha_show_unavailable=True,
        )

        vin_info = get_mock_vin_info()
        self.vehicle_info = VehicleInfo(vin_info, None)
        self.publisher = MessageCapturingConsolePublisher(configuration)
        self.sut = HomeAssistantDiscovery(
            self.publisher, VEHICLE_PREFIX, self.vehicle_info, configuration
        )

    def test_should_start_as_unpublished(self) -> None:
        assert self.sut.published is False

        self.sut.publish_ha_discovery_messages(force=False)

        assert self.sut.published is True

    def test_should_use_the_right_discovery_topic(self) -> None:
        self.sut.publish_ha_discovery_messages(force=False)

        topic_map = self.publisher.map

        for topic, value in topic_map.items():
            assert topic.startswith(DISCOVERY_PREFIX)
            if value:
                self.__assert_discovery_topic_value(topic, value)

    def __assert_discovery_topic_value(self, topic: str, value: str) -> None:
        try:
            as_json = json.loads(value)
        except Exception as e:
            self.fail(f"Could not decode topic {topic} value {value} as JSON: {e}")
        if "state_topic" in as_json:
            state_topic = as_json["state_topic"]
            assert isinstance(state_topic, str)
            assert state_topic.startswith(f"{BASE_MQTT_TOPIC}/{VEHICLE_PREFIX}/")
        if "command_topic" in as_json:
            command_topic = as_json["command_topic"]
            assert isinstance(command_topic, str)
            assert command_topic.startswith(f"{BASE_MQTT_TOPIC}/{VEHICLE_PREFIX}/")
            assert command_topic.endswith(mqtt_topics.SET_SUFFIX)
