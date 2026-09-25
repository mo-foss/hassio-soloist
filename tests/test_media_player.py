"""Tests for the Spotify Soloist media player."""

from homeassistant.components.media_player import MediaPlayerState
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
            "item": {
                "decorations": {
                    "identity": {"name": "Test track"},
                    "playback": {"duration_ms": 120000},
                }
            },
        }
    )
    player = SoloistMediaPlayer(coordinator, entry)

    assert player.state == MediaPlayerState.PLAYING
    assert player.media_title == "Test track"
    assert player.volume_level == 0.25
