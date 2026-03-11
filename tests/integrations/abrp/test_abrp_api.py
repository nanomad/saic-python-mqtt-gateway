from __future__ import annotations

import unittest

import httpx

from integrations.abrp.api import AbrpApi, AbrpApiException
from tests.common_mocks import (
    get_mock_charge_management_data_resp,
    get_mock_vehicle_status_resp,
)


class TestAbrpApi(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.api = AbrpApi(
            abrp_api_key="test_key",
            abrp_user_token="test_token",
        )
        self.vehicle_status = get_mock_vehicle_status_resp()
        self.charge_info = get_mock_charge_management_data_resp()

    async def asyncTearDown(self) -> None:
        await self.api.close()

    async def test_raise_for_status_on_server_error(self) -> None:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(500, text="Internal Server Error")
        )
        self.api.client = httpx.AsyncClient(transport=transport)

        with self.assertRaises(AbrpApiException) as ctx:
            await self.api.update_abrp(
                vehicle_status=self.vehicle_status,
                charge_info=self.charge_info,
            )
        self.assertIn("500", str(ctx.exception))

    async def test_raise_for_status_on_client_error(self) -> None:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(403, text="Forbidden")
        )
        self.api.client = httpx.AsyncClient(transport=transport)

        with self.assertRaises(AbrpApiException) as ctx:
            await self.api.update_abrp(
                vehicle_status=self.vehicle_status,
                charge_info=self.charge_info,
            )
        self.assertIn("403", str(ctx.exception))

    async def test_success_on_200(self) -> None:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(200, text='{"status": "ok"}')
        )
        self.api.client = httpx.AsyncClient(transport=transport)

        success, response = await self.api.update_abrp(
            vehicle_status=self.vehicle_status,
            charge_info=self.charge_info,
        )
        self.assertTrue(success)
        self.assertEqual(response, '{"status": "ok"}')

    async def test_skips_when_missing_config(self) -> None:
        api = AbrpApi(abrp_api_key=None, abrp_user_token=None)
        success, response = await api.update_abrp(
            vehicle_status=self.vehicle_status,
            charge_info=self.charge_info,
        )
        self.assertFalse(success)
        await api.close()
