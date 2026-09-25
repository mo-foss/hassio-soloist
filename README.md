# Spotify Soloist for Home Assistant

A minimal Home Assistant custom integration for controlling a local
[Spotify Soloist](https://github.com/spotify/soloist) instance.

## Current scope

- Playback state and track metadata
- Playback progress interpolation
- Play, pause, next, previous, and volume commands
- Automatic WebSocket reconnects

Queue browsing, shuffle, repeat, and runtime-file discovery are not included yet.

## Soloist setup

Start Soloist with its local WebSocket API enabled, for example:

```text
soloist --device-name "Kitchen speaker" --api-key "$SOLOIST_API_KEY" --ws 0.0.0.0:9090
```

Then install this integration into Home Assistant's `custom_components` directory
and add **Spotify Soloist** through **Settings > Devices & services**.

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
