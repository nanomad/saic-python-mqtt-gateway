from typing import Optional

from mqtt_topics import INTERNAL
from publisher.core import Publisher
from saic_api_listener import MqttGatewayListenerApiListener

INTERNAL_ABRP_TOPIC = INTERNAL + '/abrp'


class MqttGatewayAbrpListener(MqttGatewayListenerApiListener):
    def __init__(self, publisher: Publisher):
        super().__init__(publisher, INTERNAL_ABRP_TOPIC)

    async def on_request(self, path: str, body: Optional[str] = None, headers: Optional[dict] = None):
        await self.publish_request(path, body, headers)

    async def on_response(self, path: str, body: Optional[str] = None, headers: Optional[dict] = None):
        await self.publish_response(path, body, headers)
