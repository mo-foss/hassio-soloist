"""WebSocket coordinator for Spotify Soloist."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import RECONNECT_MAX_DELAY, RECONNECT_MIN_DELAY, WS_TIMEOUT

_LOGGER = logging.getLogger(__name__)


@dataclass
class PositionAnchor:
    """A server playback position captured at local monotonic time."""

    position_ms: int
    speed: float
    monotonic: float
    updated_at: datetime


class SoloistCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinate pushed Soloist state and commands."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass, _LOGGER, name="Spotify Soloist", always_update=True)
        self.entry = entry
        self.host = entry.data["host"]
        self.port = entry.data["port"]
        self.websocket: aiohttp.ClientWebSocketResponse | None = None
        self._session: aiohttp.ClientSession | None = None
        self._listen_task: asyncio.Task[None] | None = None
        self._reconnect_task: asyncio.Task[None] | None = None
        self._stop_requested = False
        self._reconnect_delay = RECONNECT_MIN_DELAY
        self.position_anchor: PositionAnchor | None = None

    @property
    def connected(self) -> bool:
        """Return whether the WebSocket is connected."""
        return self.websocket is not None and not self.websocket.closed

    @property
    def logged_in(self) -> bool:
        """Return whether Soloist reports an authenticated session."""
        return bool(self.data and self.data.get("logged_in"))

    async def _async_update_data(self) -> dict[str, Any]:
        if self._session is None:
            self._session = aiohttp.ClientSession()
        self._stop_requested = False
        await self._connect()
        if self.data is None:
            raise ConnectionError("Soloist did not provide state")
        return self.data

    async def _connect(self) -> None:
        if self.connected:
            return
        self._state_event = asyncio.Event()
        if self._session is None:
            self._session = aiohttp.ClientSession()
        websocket = await self._session.ws_connect(
            f"ws://{self.host}:{self.port}", timeout=WS_TIMEOUT
        )
        self.websocket = websocket
        self._reconnect_delay = RECONNECT_MIN_DELAY
        self._listen_task = asyncio.create_task(self._listen())

        # Soloist sends auth_state on connect. Request the full state once
        # authentication is confirmed by the event handler.
        await self._wait_for_connection_state()

    async def _wait_for_connection_state(self) -> None:
        """Wait briefly for the initial Soloist state."""
        try:
            await asyncio.wait_for(self._state_available.wait(), WS_TIMEOUT)
        except TimeoutError as err:
            raise ConnectionError("Soloist did not send auth_state") from err

    @property
    def _state_available(self) -> asyncio.Event:
        if not hasattr(self, "_state_event"):
            self._state_event = asyncio.Event()
        return self._state_event

    async def _listen(self) -> None:
        assert self.websocket is not None
        try:
            async for message in self.websocket:
                if message.type == aiohttp.WSMsgType.TEXT:
                    await self._handle_message(json.loads(message.data))
                elif message.type in (
                    aiohttp.WSMsgType.CLOSE,
                    aiohttp.WSMsgType.CLOSED,
                    aiohttp.WSMsgType.ERROR,
                ):
                    break
        except (aiohttp.ClientError, asyncio.CancelledError, json.JSONDecodeError):
            if not self._stop_requested:
                _LOGGER.debug("Soloist WebSocket listener stopped", exc_info=True)
        finally:
            self.websocket = None
            if not self._stop_requested:
                self._schedule_reconnect()

    async def _handle_message(self, message: dict[str, Any]) -> None:
        event_type = message.get("type")
        if event_type == "auth_state":
            data = {**(self.data or {}), **message}
            self._state_available.set()
            if message.get("logged_in") and self.connected:
                await self._send_command("get_state")
        elif event_type == "playback_state":
            data = {**(self.data or {}), **message}
            self._set_position_anchor(message.get("position"))
        elif event_type == "track_changed":
            data = {**(self.data or {}), "item": message.get("item")}
        elif event_type == "playback_changed":
            data = {**(self.data or {}), "status": message.get("status")}
        elif event_type == "volume_changed":
            data = {**(self.data or {}), "volume": message.get("volume")}
        elif event_type == "device_changed":
            data = {**(self.data or {}), **message}
        elif event_type == "context_changed":
            data = {**(self.data or {}), "context": message.get("context")}
        elif event_type == "options_changed":
            data = {**(self.data or {}), "options": message.get("options")}
        elif event_type == "position_sync":
            data = {**(self.data or {}), "position": message.get("position")}
            self._set_position_anchor(message.get("position"))
        elif event_type == "error":
            _LOGGER.warning("Soloist rejected command: %s", message.get("message"))
            data = self.data or {}
        else:
            data = self.data or {}

        if data:
            self.async_set_updated_data(data)

    def _set_position_anchor(self, position: dict[str, Any] | None) -> None:
        if position is None:
            self.position_anchor = None
            return
        self.position_anchor = PositionAnchor(
            position_ms=int(position.get("position_ms", 0)),
            speed=float(position.get("speed", 0)),
            monotonic=time.monotonic(),
            updated_at=dt_util.utcnow(),
        )

    def current_position_ms(self) -> int | None:
        """Return an interpolated playback position."""
        if self.position_anchor is None:
            return None
        elapsed_ms = (time.monotonic() - self.position_anchor.monotonic) * 1000
        return max(
            0,
            int(
                self.position_anchor.position_ms
                + elapsed_ms * self.position_anchor.speed
            ),
        )

    async def async_command(self, command: str, **fields: Any) -> None:
        """Send a control command to Soloist."""
        if not self.connected:
            return
        await self._send_command(command, **fields)

    async def _send_command(self, command: str, **fields: Any) -> None:
        if self.websocket is None or self.websocket.closed:
            return
        await self.websocket.send_json(
            {"type": "command", "command": command, **fields}
        )

    def _schedule_reconnect(self) -> None:
        if self._reconnect_task is None or self._reconnect_task.done():
            self._reconnect_task = asyncio.create_task(self._reconnect())

    async def _reconnect(self) -> None:
        await asyncio.sleep(self._reconnect_delay)
        self._reconnect_delay = min(self._reconnect_delay * 2, RECONNECT_MAX_DELAY)
        try:
            await self._connect()
        except (aiohttp.ClientError, asyncio.TimeoutError, ConnectionError, OSError):
            if not self._stop_requested:
                self._schedule_reconnect()

    async def async_shutdown(self) -> None:
        """Stop the WebSocket and owned tasks."""
        self._stop_requested = True
        for task in (self._listen_task, self._reconnect_task):
            if task is not None:
                task.cancel()
        if self.websocket is not None:
            await self.websocket.close()
        if self._session is not None:
            await self._session.close()
