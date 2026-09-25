"""Media player platform for Spotify Soloist."""

from __future__ import annotations

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SoloistCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Soloist media player."""
    coordinator: SoloistCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SoloistMediaPlayer(coordinator, entry)])


class SoloistMediaPlayer(CoordinatorEntity[SoloistCoordinator], MediaPlayerEntity):
    """Represent one Spotify Soloist player."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_media_content_type = MediaType.MUSIC
    _attr_supported_features = (
        MediaPlayerEntityFeature.PLAY
        | MediaPlayerEntityFeature.PAUSE
        | MediaPlayerEntityFeature.NEXT_TRACK
        | MediaPlayerEntityFeature.PREVIOUS_TRACK
        | MediaPlayerEntityFeature.VOLUME_SET
    )

    def __init__(self, coordinator: SoloistCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = entry.unique_id
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.unique_id)},
            "name": entry.data[CONF_NAME],
            "manufacturer": "Spotify",
            "model": "Soloist",
        }

    @property
    def available(self) -> bool:
        return (
            self.coordinator.connected
            and self.coordinator.logged_in
            and self.coordinator.active
        )

    @property
    def state(self) -> MediaPlayerState:
        if not self.coordinator.active:
            return MediaPlayerState.IDLE
        status = (self.coordinator.data or {}).get("status")
        return {
            "playing": MediaPlayerState.PLAYING,
            "paused": MediaPlayerState.PAUSED,
            "buffering": MediaPlayerState.BUFFERING,
            "idle": MediaPlayerState.IDLE,
        }.get(status, MediaPlayerState.IDLE)

    @property
    def media_title(self) -> str | None:
        return self._item.get("decorations", {}).get("identity", {}).get("name")

    @property
    def media_artist(self) -> str | None:
        creators = self._item.get("creators", [])
        names = [
            creator.get("entity", {})
            .get("decorations", {})
            .get("identity", {})
            .get("name")
            for creator in creators
        ]
        names = [name for name in names if name]
        return ", ".join(names) or None

    @property
    def media_album_name(self) -> str | None:
        parent = self._item.get("parent", {}).get("entity", {})
        return parent.get("decorations", {}).get("identity", {}).get("name")

    @property
    def media_image_url(self) -> str | None:
        covers = (
            self._item.get("decorations", {})
            .get("visual_identity", {})
            .get("cover", [])
        )
        covers_by_size = {
            cover.get("size"): cover.get("url")
            for cover in covers
            if cover.get("url")
        }
        return next(
            (
                covers_by_size[size]
                for size in ("xlarge", "large", "default", "small")
                if covers_by_size.get(size)
            ),
            None,
        )

    @property
    def media_duration(self) -> float | None:
        duration = (
            self._item.get("decorations", {})
            .get("playback", {})
            .get("duration_ms")
        )
        return duration / 1000 if duration is not None else None

    @property
    def media_position(self) -> float | None:
        position = self.coordinator.current_position_ms()
        if position is None:
            return None
        duration = self.media_duration
        if duration is not None:
            position = min(position, int(duration * 1000))
        return position / 1000

    @property
    def media_position_updated_at(self):
        """Return the local time of the last position anchor."""
        anchor = self.coordinator.position_anchor
        return anchor.updated_at if anchor is not None else None

    @property
    def volume_level(self) -> float | None:
        volume = (self.coordinator.data or {}).get("volume")
        return volume / 100 if volume is not None else None

    @property
    def _item(self) -> dict:
        return (self.coordinator.data or {}).get("item") or {}

    async def async_media_play(self) -> None:
        await self.coordinator.async_command("play")

    async def async_media_pause(self) -> None:
        await self.coordinator.async_command("pause")

    async def async_media_next_track(self) -> None:
        await self.coordinator.async_command("skip_next")

    async def async_media_previous_track(self) -> None:
        await self.coordinator.async_command("skip_prev")

    async def async_set_volume_level(self, volume: float) -> None:
        await self.coordinator.async_command("set_volume", volume=round(volume * 100))
