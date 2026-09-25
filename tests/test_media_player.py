"""Tests for the Spotify Soloist media player."""

from unittest.mock import AsyncMock

from homeassistant.components.media_player import (
    MediaPlayerEntityFeature,
    MediaPlayerState,
    RepeatMode,
)
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.soloist.const import DOMAIN
from custom_components.soloist.coordinator import SoloistCoordinator
from custom_components.soloist.media_player import SoloistMediaPlayer


async def test_media_player_maps_soloist_state(hass: HomeAssistant) -> None:
    """Media-player properties map the Soloist snapshot."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="127.0.0.1:9090",
        data={"host": "127.0.0.1", "port": 9090, "name": "Test Soloist"},
    )
    coordinator = SoloistCoordinator(hass, entry)
    coordinator.async_set_updated_data(
        {
            "status": "playing",
            "volume": 25,
            "logged_in": True,
            "is_active": True,
            "options": {"shuffle": True, "repeat": "track"},
            "item": {
                "decorations": {
                    "identity": {"name": "Test track"},
                    "playback": {"duration_ms": 120000},
                    "visual_identity": {
                        "cover": [
                            {"size": "small", "url": "https://example/small"},
                            {"size": "xlarge", "url": "https://example/xlarge"},
                        ]
                    },
                }
            },
        }
    )
    websocket = AsyncMock()
    websocket.closed = False
    coordinator.websocket = websocket
    player = SoloistMediaPlayer(coordinator, entry)

    assert player.available
    assert player.state == MediaPlayerState.PLAYING
    assert player.media_title == "Test track"
    assert player.media_image_url == "https://example/xlarge"
    assert player.volume_level == 0.25
    assert player.shuffle is True
    assert player.repeat == RepeatMode.ONE
    assert player.supported_features & MediaPlayerEntityFeature.SEEK
    assert player.supported_features & MediaPlayerEntityFeature.SHUFFLE_SET
    assert player.supported_features & MediaPlayerEntityFeature.REPEAT_SET

    coordinator.async_set_updated_data({**coordinator.data, "is_active": False})

    assert not player.available
    assert player.state == MediaPlayerState.IDLE

    coordinator.async_set_updated_data({**coordinator.data, "is_active": True})

    assert player.available
    assert player.state == MediaPlayerState.PLAYING


async def test_media_player_sends_seek_shuffle_and_repeat_commands(
    hass: HomeAssistant,
) -> None:
    """Playback feature methods send Soloist commands."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="127.0.0.1:9090",
        data={"host": "127.0.0.1", "port": 9090, "name": "Test Soloist"},
    )
    coordinator = SoloistCoordinator(hass, entry)
    coordinator.async_set_updated_data({"logged_in": True, "is_active": True})
    websocket = AsyncMock()
    websocket.closed = False
    coordinator.websocket = websocket
    player = SoloistMediaPlayer(coordinator, entry)

    await player.async_media_seek(12.345)
    await player.async_set_shuffle(True)
    await player.async_set_repeat(RepeatMode.ONE)

    assert [call.args[0] for call in websocket.send_json.await_args_list] == [
        {"type": "command", "command": "seek", "position_ms": 12345},
        {"type": "command", "command": "set_shuffle", "enabled": True},
        {
            "type": "command",
            "command": "set_repeat_context",
            "enabled": False,
        },
        {
            "type": "command",
            "command": "set_repeat_track",
            "enabled": True,
        },
    ]
