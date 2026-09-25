"""Tests for the Spotify Soloist coordinator."""

from unittest.mock import AsyncMock

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.soloist.const import DOMAIN
from custom_components.soloist.coordinator import SoloistCoordinator


def make_entry() -> MockConfigEntry:
    """Create a test config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id="127.0.0.1:9090",
        data={"host": "127.0.0.1", "port": 9090, "name": "Test Soloist"},
    )


async def test_playback_state_and_position(hass: HomeAssistant) -> None:
    """Playback snapshots populate state and interpolated position."""
    coordinator = SoloistCoordinator(hass, make_entry())

    await coordinator._handle_message(
        {
            "type": "playback_state",
            "status": "playing",
            "volume": 65,
            "item": {
                "uri": "spotify:track:test",
                "decorations": {
                    "identity": {"name": "Test track"},
                    "playback": {"duration_ms": 180000},
                },
            },
            "position": {
                "position_ms": 45000,
                "timestamp_ms": 1,
                "speed": 1.0,
            },
        }
    )

    assert coordinator.data["status"] == "playing"
    assert coordinator.data["volume"] == 65
    assert coordinator.current_position_ms() >= 45000


async def test_granular_events_merge_state(hass: HomeAssistant) -> None:
    """Granular Soloist events update the existing snapshot."""
    coordinator = SoloistCoordinator(hass, make_entry())
    await coordinator._handle_message(
        {"type": "playback_state", "status": "paused", "volume": 10}
    )
    await coordinator._handle_message(
        {"type": "volume_changed", "volume": 42}
    )
    await coordinator._handle_message(
        {"type": "playback_changed", "status": "playing"}
    )

    assert coordinator.data["status"] == "playing"
    assert coordinator.data["volume"] == 42


async def test_commands_use_soloist_envelope(hass: HomeAssistant) -> None:
    """Control commands use Soloist's documented JSON envelope."""
    coordinator = SoloistCoordinator(hass, make_entry())
    coordinator.async_set_updated_data({"logged_in": True, "is_active": True})
    websocket = AsyncMock()
    websocket.closed = False
    coordinator.websocket = websocket

    await coordinator.async_command("set_volume", volume=50)

    websocket.send_json.assert_awaited_once_with(
        {"type": "command", "command": "set_volume", "volume": 50}
    )


async def test_inactive_device_blocks_commands(hass: HomeAssistant) -> None:
    """Commands are blocked after playback moves to another device."""
    coordinator = SoloistCoordinator(hass, make_entry())
    coordinator.async_set_updated_data({"logged_in": True, "is_active": True})
    websocket = AsyncMock()
    websocket.closed = False
    coordinator.websocket = websocket

    await coordinator._handle_message(
        {"type": "device_changed", "is_active": False}
    )
    await coordinator.async_command("pause")

    assert not coordinator.active
    websocket.send_json.assert_not_awaited()
