# Spotify Soloist for Home Assistant

A minimal Home Assistant custom integration for controlling a local
[Spotify Soloist](https://github.com/spotify/soloist) instance.

## Current scope

- Playback state and track metadata
- Playback progress interpolation
- Play, pause, next, previous, and volume commands
- Seek support
- Shuffle control and state
- Repeat control and state
- Automatic WebSocket reconnects

Queue browsing, queue metadata, add-to-queue support, and runtime-file discovery
are not included yet.

## Installation

### HACS custom repository

Until this repository is included in HACS's default catalogue:

1. Open **HACS** in Home Assistant.
2. Open **Integrations**.
3. Open the three-dot menu and select **Custom repositories**.
4. Add `https://github.com/mo-foss/hassio-soloist` with category **Integration**.
5. Install **Spotify Soloist**.
6. Restart Home Assistant.

### Manual installation

Copy the `custom_components/soloist` directory into the `custom_components`
directory under your Home Assistant configuration directory, then restart Home
Assistant.

The final path must be:

After restarting, add **Spotify Soloist** through **Settings > Devices &
services**.

## Soloist setup

Start Soloist with its local WebSocket API enabled, for example:

```text
soloist --device-name "Kitchen speaker" --api-key "$SOLOIST_API_KEY" --ws 0.0.0.0:9090
```

Then add **Spotify Soloist** through **Settings > Devices & services** and
enter the host and port of the Soloist WebSocket API.

The Home Assistant host must be able to reach the configured Soloist address.
For example, `127.0.0.1` inside a Home Assistant container refers to the
container itself, not necessarily the host running Soloist.

## Configuration

The integration asks for:

- **Host**: the hostname or IP address where Soloist's WebSocket API is
  reachable
- **WebSocket port**: the port configured with Soloist's `--ws` option
- **Name**: the Home Assistant device name

Soloist must be logged in to Spotify. The media player is available for
playback and control only while Soloist is the active Spotify Connect device.

## Troubleshooting

If setup fails or the entity is unavailable:

- Confirm Soloist was started with `--ws`.
- Confirm the host and port are reachable from Home Assistant.
- Confirm Soloist is logged in and selected as the active Spotify Connect
  device.
- Check the Home Assistant logs for messages containing `soloist`.

The WebSocket API has no built-in authentication, authorization, TLS, or
network exposure policy. Bind it only to a trusted interface or protect it with
an appropriate network boundary.

## Disclaimer

This is an independent, unofficial community project. It is not affiliated
with, endorsed by, sponsored by, or otherwise associated with Spotify AB or
Home Assistant.

Spotify, Spotify Soloist, and related names, logos, and marks are trademarks
of their respective owners. This project does not claim ownership of those
trademarks.

Use this integration and Spotify Soloist at your own risk. The author and
contributors provide no warranty and accept no responsibility for damage,
data loss, service interruption, account issues, or other consequences arising
from its use. Users are responsible for complying with applicable laws, terms
of service, and licensing requirements.
