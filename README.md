# System Monitor

Current release: **0.1.1**. A local Linux desktop application.

## Installation

Download the repository source ZIP from GitHub, extract it, and open a terminal in that folder. On Ubuntu/Zorin install Python prerequisites:

```bash
sudo apt install python3-venv python3-tk python3-pil python3-psutil
python3 install.py
```

The installer installs app files and a desktop/application-menu launcher. Existing user data is preserved. Local WebUI creates its isolated Qt runtime when needed.

## Update notifications

The app checks exactly once at launch in a background thread, using a five-second timeout and GitHub's public Contents API for the root `VERSION` file. There are no credentials in the request. Equal, older, malformed, and unavailable versions are silent. A newer version adds a muted bottom-right **Update available · vX.Y.Z ↗** link to this installation page. There are no automatic downloads or installations.

`APP_VERSION`, `VERSION`, and the installer describe the same release. Update checks use the Contents API rather than the raw endpoint to avoid stale raw-file responses. Results pass through a queue to the GUI thread; normal status updates cannot replace the link.

## Tests

```bash
python3 -m unittest test_update_check
```

## Sensors

CPU and RAM use psutil. NVIDIA GPU information uses `nvidia-smi` when available. No administrator privileges are required.
