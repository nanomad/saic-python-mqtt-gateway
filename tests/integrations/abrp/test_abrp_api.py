from __future__ import annotations

import unittest

import httpx

from integrations.abrp.api import AbrpApi, AbrpApiException
from tests.common_mocks import (
    get_mock_charge_management_data_resp,
    get_mock_vehicle_status_resp,
)

MOCK_API_KEY = "test_api_key"
MOCK_USER_TOKEN = "test_user_token"


class TestAbrpApi(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.api = AbrpApi(
            abrp_api_key=MOCK_API_KEY,
            abrp_user_token=MOCK_USER_TOKEN,
        )
        self.vehicle_status = get_mock_vehicle_status_resp()
        self.charge_info = get_mock_charge_management_data_resp()

    async def asyncTearDown(self) -> None:
        await self.api.close()

    async def _set_mock_transport(self, status_code: int, text: str) -> None:
        await self.api.client.aclose()
        transport = httpx.MockTransport(
            lambda request: httpx.Response(status_code, text=text)
        )
        self.api.client = httpx.AsyncClient(transport=transport)

    async def test_raise_for_status_on_server_error(self) -> None:
        await self._set_mock_transport(500, "Internal Server Error")

        with self.assertRaises(AbrpApiException) as ctx:
            await self.api.update_abrp(
                vehicle_status=self.vehicle_status,
                charge_info=self.charge_info,
            )
        self.assertIn("500", str(ctx.exception))

    async def test_raise_for_status_on_client_error(self) -> None:
        await self._set_mock_transport(403, "Forbidden")

        with self.assertRaises(AbrpApiException) as ctx:
            await self.api.update_abrp(
                vehicle_status=self.vehicle_status,
                charge_info=self.charge_info,
            )
        self.assertIn("403", str(ctx.exception))

    async def test_success_on_200(self) -> None:
        await self._set_mock_transport(200, '{"status": "ok"}')

        success, response = await self.api.update_abrp(
            vehicle_status=self.vehicle_status,
            charge_info=self.charge_info,
        )
        self.assertTrue(success)
        self.assertEqual(response, '{"status": "ok"}')

    async def test_skips_when_missing_config(self) -> None:
        api = AbrpApi(abrp_api_key=None, abrp_user_token=None)
        success, _response = await api.update_abrp(
            vehicle_status=self.vehicle_status,
            charge_info=self.charge_info,
        )
        self.assertFalse(success)
        await api.close()
