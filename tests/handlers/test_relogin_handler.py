from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, MagicMock

import pytest

from handlers.relogin import ReloginHandler


class TestReloginHandler(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.mock_api = AsyncMock()
        self.mock_api.login = AsyncMock(return_value=MagicMock(account="test_user"))
        self.mock_scheduler = MagicMock()
        self.mock_scheduler.get_job = MagicMock(return_value=None)
        self.handler = ReloginHandler(
            relogin_relay=15,
            api=self.mock_api,
            scheduler=self.mock_scheduler,
        )

    async def test_login_calls_api_login(self) -> None:
        await self.handler.login()

        self.mock_api.login.assert_awaited_once()

    async def test_login_runs_post_login_callbacks(self) -> None:
        callback = AsyncMock()
        self.handler.add_post_login_callback(callback)

        await self.handler.login()

        callback.assert_awaited_once()

    async def test_login_runs_multiple_callbacks_in_order(self) -> None:
        call_order: list[int] = []
        callback_1 = AsyncMock(side_effect=lambda: call_order.append(1))
        callback_2 = AsyncMock(side_effect=lambda: call_order.append(2))
        self.handler.add_post_login_callback(callback_1)
        self.handler.add_post_login_callback(callback_2)

        await self.handler.login()

        assert call_order == [1, 2]

    async def test_callbacks_not_run_when_login_fails(self) -> None:
        self.mock_api.login.side_effect = RuntimeError("login failed")
        callback = AsyncMock()
        self.handler.add_post_login_callback(callback)

        with pytest.raises(RuntimeError, match="login failed"):
            await self.handler.login()

        callback.assert_not_awaited()

    async def test_failing_callback_does_not_block_others(self) -> None:
        failing_callback = AsyncMock(side_effect=RuntimeError("callback error"))
        ok_callback = AsyncMock()
        self.handler.add_post_login_callback(failing_callback)
        self.handler.add_post_login_callback(ok_callback)

        await self.handler.login()

        failing_callback.assert_awaited_once()
        ok_callback.assert_awaited_once()

    async def test_failing_callback_does_not_fail_login(self) -> None:
        failing_callback = AsyncMock(side_effect=RuntimeError("callback error"))
        self.handler.add_post_login_callback(failing_callback)

        # Should not raise
        await self.handler.login()

        self.mock_api.login.assert_awaited_once()

    async def test_no_callbacks_by_default(self) -> None:
        await self.handler.login()
        # Just verifying login succeeds with no callbacks registered
        self.mock_api.login.assert_awaited_once()

    async def test_callbacks_run_on_every_login(self) -> None:
        callback = AsyncMock()
        self.handler.add_post_login_callback(callback)

        await self.handler.login()
        await self.handler.login()

        assert callback.await_count == 2

    def test_relogin_schedules_job(self) -> None:
        self.handler.relogin()

        self.mock_scheduler.add_job.assert_called_once()
        call_kwargs = self.mock_scheduler.add_job.call_args
        assert call_kwargs.kwargs["func"] == self.handler.login

    def test_relogin_does_not_schedule_duplicate(self) -> None:
        self.mock_scheduler.add_job.return_value = MagicMock()
        self.handler.relogin()
        self.handler.relogin()

        self.mock_scheduler.add_job.assert_called_once()

    def test_relogin_in_progress_initially_false(self) -> None:
        assert self.handler.relogin_in_progress is False

    def test_relogin_in_progress_true_after_schedule(self) -> None:
        self.mock_scheduler.add_job.return_value = MagicMock()
        self.handler.relogin()

        assert self.handler.relogin_in_progress is True

    async def test_relogin_in_progress_false_after_login(self) -> None:
        self.mock_scheduler.add_job.return_value = MagicMock()
        self.handler.relogin()

        await self.handler.login()

        assert self.handler.relogin_in_progress is False

    async def test_relogin_in_progress_false_after_failed_login(self) -> None:
        self.mock_scheduler.add_job.return_value = MagicMock()
        self.mock_api.login.side_effect = RuntimeError("login failed")
        self.handler.relogin()

        with pytest.raises(RuntimeError, match="login failed"):
            await self.handler.login()

        assert self.handler.relogin_in_progress is False

    async def test_failure_callback_runs_on_login_failure(self) -> None:
        self.mock_api.login.side_effect = RuntimeError("login failed")
        callback = AsyncMock()
        self.handler.add_login_failure_callback(callback)

        with pytest.raises(RuntimeError, match="login failed"):
            await self.handler.login()

        callback.assert_awaited_once()

    async def test_failure_callback_not_run_on_success(self) -> None:
        callback = AsyncMock()
        self.handler.add_login_failure_callback(callback)

        await self.handler.login()

        callback.assert_not_awaited()

    async def test_failing_failure_callback_does_not_block_others(self) -> None:
        self.mock_api.login.side_effect = RuntimeError("login failed")
        failing_callback = AsyncMock(side_effect=RuntimeError("callback error"))
        ok_callback = AsyncMock()
        self.handler.add_login_failure_callback(failing_callback)
        self.handler.add_login_failure_callback(ok_callback)

        with pytest.raises(RuntimeError, match="login failed"):
            await self.handler.login()

        failing_callback.assert_awaited_once()
        ok_callback.assert_awaited_once()

    async def test_failure_callback_does_not_prevent_reraise(self) -> None:
        self.mock_api.login.side_effect = RuntimeError("login failed")
        callback = AsyncMock()
        self.handler.add_login_failure_callback(callback)

        with pytest.raises(RuntimeError, match="login failed"):
            await self.handler.login()

        callback.assert_awaited_once()

    async def test_force_login_cancels_pending_relogin(self) -> None:
        mock_job = MagicMock()
        self.mock_scheduler.add_job.return_value = mock_job
        self.mock_scheduler.get_job.return_value = mock_job
        self.handler.relogin()
        assert self.handler.relogin_in_progress is True

        await self.handler.force_login()
        self._assert_force_login_succeeded()
        self.mock_scheduler.remove_job.assert_called()

    async def test_force_login_works_without_pending_relogin(self) -> None:
        await self.handler.force_login()
        self._assert_force_login_succeeded()

    async def test_force_login_raises_on_login_failure(self) -> None:
        self.mock_api.login.side_effect = RuntimeError("login failed")

        with pytest.raises(RuntimeError, match="login failed"):
            await self.handler.force_login()

        assert not self.handler.relogin_in_progress

    def _assert_force_login_succeeded(self) -> None:
        assert not self.handler.relogin_in_progress
        self.mock_api.login.assert_awaited_once()
