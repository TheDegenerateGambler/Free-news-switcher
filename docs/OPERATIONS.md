---
Project:        free-news-switcher
Doc:            OPERATIONS.md
Owner:          The Gambler
Classification: Public
Last updated:   2026-11-23
---

# Operations - free-news-switcher

## Requirements

- Python 3 with `tkinter` (bundled with most Python installs).
- `Pillow` for icon rendering:

```
pip install pillow
```

## Run

```
python free-news-switcher.py
```

Then click a channel button to open its free live stream in your default
browser. If a channel is not live at that moment, try another.

## Customising channels

Edit `free-news-switcher.channels.json` (created next to the script on first
run). It is a JSON list of `{"name": ..., "url": ...}` objects. If the file is
missing or invalid, the built-in default channels are used.

## Files it creates

| Path | Contents |
|------|----------|
| `free-news-switcher.channels.json` | Your channel list (name + URL). |
| `icons/` | Cached channel favicons (PNG). |

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `ModuleNotFoundError: PIL` | `pip install pillow`. |
| `tkinter` not found | Install the Tk bindings for your Python (OS package). |
| A button shows a colored initials tile | The favicon could not be fetched; the generated placeholder is expected. |
| Stream does not play | That channel is not live right now; free streams come and go - try another. |

---
Related: OVERVIEW.md, CHANGELOG.md
