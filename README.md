# Free News Switcher

A tiny desktop launcher: a grid of buttons, one per news channel. Click a button
and that channel's official free live stream opens in your browser. No accounts,
no cable — just a browser and internet.

## Features

- Button grid of news channels (CBC, ABC, CBS, NBC, PBS, Bloomberg, Sky, Al
  Jazeera, DW, France 24, Reuters, and more).
- Opens each channel's official free live stream in your default browser.
- Channel logos fetched as favicons and cached locally, with a generated
  colored-tile fallback.
- Matches the OS light/dark theme (including a dark Windows title bar).
- User-editable channel list (`free-news-switcher.channels.json`).

## Requirements

- Python 3 with `tkinter` (bundled with most Python installs)
- `Pillow`:

```
pip install pillow
```

## Run

```
python free-news-switcher.py
```

Click a channel button to open its free live stream. Edit
`free-news-switcher.channels.json` (created on first run) to customise channels.

## Documentation

See [`docs/`](docs/):

| Doc | Purpose |
|-----|---------|
| [OVERVIEW.md](docs/OVERVIEW.md) | What it does, scripts, data & privacy |
| [OPERATIONS.md](docs/OPERATIONS.md) | Install, run, customise, troubleshoot |
| [CHANGELOG.md](docs/CHANGELOG.md) | Release notes |
