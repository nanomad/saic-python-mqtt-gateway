from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import logging
from typing import TYPE_CHECKING, override

from saic_ismart_client_ng.api.message import MessageEntity

import mqtt_topics
from status_publisher import VehicleDataPublisher

if TYPE_CHECKING:
    from publisher.core import Publisher
    from vehicle_info import VehicleInfo

LOG = logging.getLogger(__name__)


@dataclass(kw_only=True, frozen=True)
class MessagePublisherProcessingResult:
    processed: bool


class MessagePublisher(
    VehicleDataPublisher[MessageEntity, MessagePublisherProcessingResult]
):
    def __init__(
        self, vin: VehicleInfo, publisher: Publisher, mqtt_vehicle_prefix: str
    ) -> None:
        super().__init__(vin, publisher, mqtt_vehicle_prefix)
        self.__last_car_vehicle_message = datetime.min.replace(tzinfo=UTC)

    @override
    def publish(self, message: MessageEntity) -> MessagePublisherProcessingResult:
        if (
            self.__last_car_vehicle_message == datetime.min.replace(tzinfo=UTC)
            or message.message_time > self.__last_car_vehicle_message
        ):
            self.__last_car_vehicle_message = message.message_time
            self._publish(
                topic=mqtt_topics.INFO_LAST_MESSAGE_TIME,
                value=self.__last_car_vehicle_message,
            )

            if isinstance(message.messageId, str):
                self._publish(
                    topic=mqtt_topics.INFO_LAST_MESSAGE_ID,
                    value=message.messageId,
                )
            else:
                self._transform_and_publish(
                    topic=mqtt_topics.INFO_LAST_MESSAGE_ID,
                    value=message.messageId,
                    transform=str,
                )

            self._publish(
                topic=mqtt_topics.INFO_LAST_MESSAGE_TYPE,
                value=message.messageType,
            )

            self._publish(
                topic=mqtt_topics.INFO_LAST_MESSAGE_TITLE,
                value=message.title,
            )

            self._publish(
                topic=mqtt_topics.INFO_LAST_MESSAGE_SENDER,
                value=message.sender,
            )

            self._publish(
                topic=mqtt_topics.INFO_LAST_MESSAGE_CONTENT,
                value=message.content,
            )

            self._publish(
                topic=mqtt_topics.INFO_LAST_MESSAGE_STATUS,
                value=message.read_status,
            )

            self._publish(
                topic=mqtt_topics.INFO_LAST_MESSAGE_VIN,
                value=message.vin,
            )

            self.__publish_message_event(message)

            return MessagePublisherProcessingResult(processed=True)
        return MessagePublisherProcessingResult(processed=False)

    def __publish_message_event(self, message: MessageEntity) -> None:
        try:
            self._publish(
                topic=mqtt_topics.EVENTS_VEHICLE_MESSAGE,
                value={
                    "event_type": "vehicle_message",
                    "title": message.title or "",
                    "content": message.content or "",
                    "message_type": message.messageType or "",
                    "sender": message.sender or "",
                    "vin": message.vin or "",
                },
            )
        except Exception:
            LOG.warning(
                "Failed to publish vehicle message event",
                exc_info=True,
            )
