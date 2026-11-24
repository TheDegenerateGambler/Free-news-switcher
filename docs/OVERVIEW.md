---
Project:        free-news-switcher
Doc:            OVERVIEW.md
Owner:          The Gambler
Classification: Public
Last updated:   2026-11-23
---

# Overview - free-news-switcher

A tiny desktop launcher: a grid of buttons, one per news channel. Click a
button and that channel's official free live stream opens in your browser. No
accounts, no cable - just a browser and internet.

## What it does

- `free-news-switcher.py` - a single-file Tkinter GUI (stdlib) with Pillow for
  icon rendering. It:
  - Builds a button grid from a channel list.
  - Opens the selected channel's URL in the default browser.
  - Shows each channel's logo, fetched as a favicon and cached locally; falls
    back to a generated colored tile with initials if no favicon is available.
  - Matches the OS light/dark theme (incl. a dark Windows title bar).
  - Reads a user-editable channel list from
    `free-news-switcher.channels.json` (created next to the script on first run,
    with built-in defaults if missing/invalid).

## Scripts

| Script | Purpose | Dependencies |
|--------|---------|--------------|
| `free-news-switcher.py` | The GUI launcher. | Python 3 + `tkinter` (stdlib) + `Pillow` (PIL). |

Key functions: `load_channels`, `write_default_config`, `get_icon`,
`_fetch_favicon`, `open_channel`, `build_grid`, `build_ui`, `main`.

## Data & Privacy

This project processes **no personal data** - it does not collect, store, or
transmit anything about the user. For completeness, note that it does:

- **Write local files:** a config file (`free-news-switcher.channels.json`) and
  a favicon cache under `icons/`, both beside the script. These contain only
  channel names/URLs and downloaded logos - no personal data.
- **Make network requests:** it downloads channel favicons from Google's public
  favicon service (`https://www.google.com/s2/favicons`) and opens channel URLs
  in your browser. Only public channel domains are sent; no user identity.

Because no personal data is processed, this project is exempt from
`DATA_INVENTORY.md`, `RETENTION.md`, `PRIVACY.md`, and
`COMPLIANCE_CHECKLIST.md` per the workspace documentation standard.

---
Related: OPERATIONS.md, CHANGELOG.md
