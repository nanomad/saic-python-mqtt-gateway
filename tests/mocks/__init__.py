from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, override

from saic_python_mqtt_gateway.publisher.log_publisher import ConsolePublisher

if TYPE_CHECKING:
    from saic_python_mqtt_gateway.configuration import Configuration

LOG = logging.getLogger(__name__)


class MessageCapturingConsolePublisher(ConsolePublisher):
    def __init__(self, configuration: Configuration) -> None:
        super().__init__(configuration)
        self.map: dict[str, Any] = {}

    @override
    def internal_publish(self, key: str, value: Any) -> None:
        self.map[key] = value
        LOG.debug(f"{key}: {value}")
