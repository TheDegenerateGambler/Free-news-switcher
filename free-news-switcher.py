#!/usr/bin/env python3
"""
Free News Switcher — press a button, the stream changes.
Runs on Windows / Mac / Linux with Python's built-in tkinter only.
No installs, no accounts, no cable. Just internet + a browser.

How to run on your Windows computer:
  1. Save this file, e.g. to your Desktop.
  2. Double-click it, or in a terminal run:  python free-news-switcher.py
  3. Press a channel button. It opens that channel's official free live stream in your browser.

Customizing channels:
  Edit "free-news-switcher.channels.json" (created next to this script on first run).
  It is a JSON list of {"name": ..., "url": ...} objects. If the file is missing
  or invalid, the built-in default channels are used instead.

If a channel's live page is not streaming at that moment, try another button —
free live streams come and go, and some (like CBC News Network's 24-hour feed)
are paid inside CBC Gem, which is why the buttons below use the free streams.
"""

from __future__ import annotations

import ctypes
import io
import json
import logging
import math
import sys
import tkinter as tk
import urllib.request
import webbrowser
from pathlib import Path
from typing import NamedTuple
from urllib.parse import urlparse

from PIL import Image, ImageDraw, ImageFont, ImageTk

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("free-news-switcher")

CONFIG_PATH = Path(__file__).resolve().with_name("free-news-switcher.channels.json")
ICON_DIR = CONFIG_PATH.with_name("icons")

ALLOWED_SCHEMES = ("http://", "https://")

ICON_SIZE = 48
GRID_COLS = 6
CELL_WIDTH = 116
FAVICON_URL = "https://www.google.com/s2/favicons?domain={domain}&sz=64"

# Channels whose URL is a generic YouTube page map to their real brand site so
# each one shows a distinct, recognizable logo instead of the YouTube icon.
BRAND_DOMAINS: dict[str, str] = {
    "CBC News (YouTube Live)": "cbc.ca",
    "ABC News Live": "abcnews.go.com",
    "CBS News 24/7": "cbsnews.com",
    "NBC News NOW": "nbcnews.com",
    "PBS NewsHour": "pbs.org",
    "Bloomberg Television": "bloomberg.com",
    "LiveNOW from FOX": "fox.com",
    "Sky News (UK)": "news.sky.com",
    "Al Jazeera English": "aljazeera.com",
    "DW News (Germany)": "dw.com",
    "France 24 English": "france24.com",
    "Reuters": "reuters.com",
}

# Accent colors for generated placeholder tiles (cycled by channel index).
_PLACEHOLDER_COLORS = ("#3b82f6", "#ef4444", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899")


# Color palettes. Keys must stay identical between the two themes.
DARK_THEME: dict[str, str] = {
    "bg": "#1e1e1e",
    "fg": "#e0e0e0",
    "sub_fg": "#b0b0b0",
    "btn_bg": "#2d2d2d",
    "btn_fg": "#e0e0e0",
    "btn_active_bg": "#3a3a3a",
    "btn_active_fg": "#ffffff",
    "status_fg": "#4ec9b0",
    "note_fg": "#8a8a8a",
}

LIGHT_THEME: dict[str, str] = {
    "bg": "#f0f0f0",
    "fg": "#000000",
    "sub_fg": "#333333",
    "btn_bg": "#e1e1e1",
    "btn_fg": "#000000",
    "btn_active_bg": "#d0d0d0",
    "btn_active_fg": "#000000",
    "status_fg": "#2a7745",
    "note_fg": "gray",
}


def is_dark_mode() -> bool:
    """Return True if Windows is set to dark app mode.

    Reads HKCU\\...\\Themes\\Personalize\\AppsUseLightTheme (0 = dark, 1 = light).
    On non-Windows platforms, a missing key, or any error, returns False (light)
    so the app stays cross-platform and never crashes on theme detection.
    """
    if sys.platform != "win32":
        return False
    try:
        import winreg

        key_path = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return value == 0
    except (OSError, ImportError, ValueError) as exc:
        logger.debug("Could not read Windows theme (%s). Assuming light.", exc)
        return False


def apply_dark_titlebar(root: tk.Tk) -> None:
    """Make the native Windows title bar dark to match the dark body.

    Uses the DWM immersive dark-mode attribute (Windows 10 1809+/11). Any
    failure (old Windows, non-Windows, missing dwmapi) is a silent no-op.
    """
    if sys.platform != "win32":
        return
    try:
        root.update_idletasks()  # ensure the native window exists
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
        value = ctypes.c_int(1)
        # 20 = DWMWA_USE_IMMERSIVE_DARK_MODE on current builds; 19 on 1809..19040.
        for attribute in (20, 19):
            result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, attribute, ctypes.byref(value), ctypes.sizeof(value)
            )
            if result == 0:
                break
    except (OSError, AttributeError) as exc:
        logger.debug("Could not set dark title bar (%s).", exc)


class Channel(NamedTuple):
    """A single named stream the user can open."""

    name: str
    url: str


def _domain_for(channel: "Channel") -> str:
    """Return the best logo domain for a channel.

    Uses the brand mapping first (so YouTube-hosted channels get a distinct
    logo), otherwise falls back to the domain parsed from the channel URL.
    """
    if channel.name in BRAND_DOMAINS:
        return BRAND_DOMAINS[channel.name]
    netloc = urlparse(channel.url).netloc.lower()
    return netloc[4:] if netloc.startswith("www.") else netloc


def _placeholder_image(channel: "Channel", index: int) -> Image.Image:
    """Draw a simple colored tile with the channel's initials as a fallback."""
    color = _PLACEHOLDER_COLORS[index % len(_PLACEHOLDER_COLORS)]
    img = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), color)
    draw = ImageDraw.Draw(img)
    words = [w for w in channel.name.replace("(", " ").split() if w[:1].isalnum()]
    initials = "".join(w[0] for w in words[:2]).upper() or "?"
    try:
        font = ImageFont.truetype("arial.ttf", 22)
    except OSError:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), initials, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(
        ((ICON_SIZE - tw) / 2 - bbox[0], (ICON_SIZE - th) / 2 - bbox[1]),
        initials,
        fill="white",
        font=font,
    )
    return img


def _fetch_favicon(domain: str, dest: Path) -> bool:
    """Download a domain's favicon PNG to dest. Returns True on success."""
    url = FAVICON_URL.format(domain=domain)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
        Image.open(io.BytesIO(data)).verify()  # validate it is a real image
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return True
    except (OSError, ValueError) as exc:
        logger.debug("Could not fetch favicon for %s (%s).", domain, exc)
        return False


def get_icon(channel: "Channel", index: int) -> ImageTk.PhotoImage:
    """Return a Tk image for a channel, caching favicons under ICON_DIR.

    Falls back to a generated initials tile if the favicon cannot be fetched
    or loaded, so the grid always renders something.
    """
    domain = _domain_for(channel)
    cache_path = ICON_DIR / f"{domain}.png"

    if not cache_path.exists():
        _fetch_favicon(domain, cache_path)

    try:
        img = Image.open(cache_path).convert("RGBA")
    except (OSError, ValueError):
        img = _placeholder_image(channel, index)

    img = img.resize((ICON_SIZE, ICON_SIZE), Image.LANCZOS)
    return ImageTk.PhotoImage(img)


DEFAULT_CHANNELS: list[Channel] = [
    Channel("CBC News (YouTube Live)", "https://www.youtube.com/@CBCNews/streams"),
    Channel("CBC Gem (free, Canada)", "https://gem.cbc.ca/live"),
    Channel("CTV News (Canada)", "https://www.ctvnews.ca/"),
    Channel("Global News (Canada)", "https://globalnews.ca/live/"),
    Channel("CP24 (free, Canada)", "https://www.cp24.com/live/"),
    Channel("CityNews (Canada)", "https://toronto.citynews.ca/live/"),
    Channel("ABC News Live", "https://www.youtube.com/@ABCNews/streams"),
    Channel("CBS News 24/7", "https://www.youtube.com/@CBSNews/streams"),
    Channel("NBC News NOW", "https://www.youtube.com/@NBCNews/streams"),
    Channel("PBS NewsHour", "https://www.youtube.com/@PBSNewsHour/streams"),
    Channel("Bloomberg Television", "https://www.youtube.com/@markets/streams"),
    Channel("LiveNOW from FOX", "https://www.youtube.com/@livenowfox/streams"),
    Channel("Sky News (UK)", "https://www.youtube.com/@SkyNews/streams"),
    Channel("Al Jazeera English", "https://www.youtube.com/@aljazeeraenglish/streams"),
    Channel("DW News (Germany)", "https://www.youtube.com/@DWNews/streams"),
    Channel("France 24 English", "https://www.youtube.com/@FRANCE24English/live"),
    Channel("Reuters", "https://www.youtube.com/@Reuters/streams"),
    Channel("Pluto TV (free live TV)", "https://pluto.tv/en/live-tv"),
    Channel("The Roku Channel (Live)", "https://therokuchannel.roku.com/live"),
    Channel("Plex Live TV (free)", "https://watch.plex.tv/live-tv"),
    Channel("Samsung TV Plus", "https://www.samsungtvplus.com/"),
    Channel("Netflix", "https://www.netflix.com/browse"),
    Channel("Crave", "https://www.crave.ca/en"),
    Channel("Tubi (free channels)", "https://tubitv.com/"),
    Channel("Ecuador", "https://www.youtube.com/watch?v=HQbC88WvPIM"),
]


def _is_valid_url(url: object) -> bool:
    """Return True if the URL is a non-empty http(s) link."""
    return isinstance(url, str) and url.strip().lower().startswith(ALLOWED_SCHEMES)



def _parse_channels(raw: object) -> list[Channel]:
    """Validate parsed JSON into a list of Channel entries, skipping bad ones."""
    if not isinstance(raw, list):
        raise ValueError("channels config must be a JSON list")

    channels: list[Channel] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            logger.warning("Skipping channel #%d: not an object.", index)
            continue
        name = item.get("name")
        url = item.get("url")
        if not isinstance(name, str) or not name.strip():
            logger.warning("Skipping channel #%d: missing/invalid 'name'.", index)
            continue
        if not _is_valid_url(url):
            logger.warning("Skipping channel '%s': missing/invalid 'url'.", name)
            continue
        channels.append(Channel(name.strip(), url.strip()))
    return channels


def write_default_config(path: Path = CONFIG_PATH) -> bool:
    """Write the built-in channels to the config file. Returns True on success."""
    try:
        payload = [{"name": c.name, "url": c.url} for c in DEFAULT_CHANNELS]
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        logger.info("Wrote default channel config to %s", path)
        return True
    except OSError as exc:
        logger.warning("Could not write default config (%s). Using built-ins.", exc)
        return False


def load_channels(path: Path = CONFIG_PATH) -> list[Channel]:
    """Load channels from the config file, falling back to the defaults.

    If the file is missing, create it from the defaults. If it is present but
    invalid, log a warning and use the built-in defaults.
    """
    if not path.exists():
        write_default_config(path)
        return list(DEFAULT_CHANNELS)

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        channels = _parse_channels(raw)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("Could not read %s (%s). Using built-in channels.", path, exc)
        return list(DEFAULT_CHANNELS)

    if not channels:
        logger.warning("No valid channels in %s. Using built-in channels.", path)
        return list(DEFAULT_CHANNELS)
    return channels


def open_channel(url: str) -> bool:
    """Open a URL in a new browser tab. Returns True if the browser accepted it."""
    if not _is_valid_url(url):
        logger.error("Refusing to open invalid URL: %r", url)
        return False
    try:
        return webbrowser.open_new_tab(url)
    except webbrowser.Error as exc:
        logger.error("No usable web browser found: %s", exc)
        return False


def build_grid(
    parent: tk.Widget,
    channels: list[Channel],
    theme: dict[str, str],
    on_click,
    image_refs: list,
) -> None:
    """Build a left-to-right wrapping grid of icon + name cells."""
    for index, channel in enumerate(channels):
        row, col = divmod(index, GRID_COLS)

        cell = tk.Frame(parent, bg=theme["bg"], width=CELL_WIDTH)
        cell.grid(row=row, column=col, padx=4, pady=6, sticky="n")
        cell.grid_propagate(False)
        cell.configure(height=ICON_SIZE + 34)

        photo = get_icon(channel, index)
        image_refs.append(photo)  # keep a reference so Tk does not GC it

        icon = tk.Label(cell, image=photo, bg=theme["bg"], cursor="hand2")
        icon.pack(pady=(4, 2))
        name = tk.Label(
            cell,
            text=channel.name,
            font=("Segoe UI", 8),
            bg=theme["bg"],
            fg=theme["fg"],
            wraplength=CELL_WIDTH - 12,
            justify="center",
            cursor="hand2",
        )
        name.pack()

        widgets = (cell, icon, name)

        def _enter(_event, w=widgets):
            for wid in w:
                wid.configure(bg=theme["btn_active_bg"])

        def _leave(_event, w=widgets):
            for wid in w:
                wid.configure(bg=theme["bg"])

        for wid in widgets:
            wid.bind("<Button-1>", lambda _e, c=channel: on_click(c))
            wid.bind("<Enter>", _enter)
            wid.bind("<Leave>", _leave)


def build_ui(root: tk.Tk, channels: list[Channel]) -> None:
    """Build the window contents."""
    root.title("Free News Switcher")

    dark = is_dark_mode()
    theme = DARK_THEME if dark else LIGHT_THEME
    root.configure(bg=theme["bg"])
    root._icon_refs = []  # type: ignore[attr-defined]  # keep images alive

    # Size the window to the icon grid: GRID_COLS wide, wrapping into rows.
    rows = math.ceil(len(channels) / GRID_COLS)
    width = GRID_COLS * (CELL_WIDTH + 8) + 24
    chrome = 170  # title + subtitle + status + note + padding
    height = chrome + rows * (ICON_SIZE + 40)
    root.geometry(f"{width}x{height}")
    root.minsize(width, min(height, 560))
    root.resizable(False, True)

    title = tk.Label(
        root,
        text="Free News Switcher",
        font=("Segoe UI", 18, "bold"),
        bg=theme["bg"],
        fg=theme["fg"],
    )
    title.pack(pady=(14, 2))
    sub = tk.Label(
        root,
        text="Click a channel — the stream opens in your browser.",
        bg=theme["bg"],
        fg=theme["sub_fg"],
    )
    sub.pack(pady=(0, 10))

    status = tk.StringVar(value="")

    def on_click(channel: Channel) -> None:
        if open_channel(channel.url):
            status.set(f"Opened: {channel.name}")
        else:
            status.set(f"Could not open: {channel.name} (no browser?)")

    grid = tk.Frame(root, bg=theme["bg"])
    grid.pack(pady=4)
    build_grid(grid, channels, theme, on_click, root._icon_refs)  # type: ignore[attr-defined]

    status_label = tk.Label(
        root,
        textvariable=status,
        bg=theme["bg"],
        fg=theme["status_fg"],
    )
    status_label.pack(pady=(8, 2))

    note = tk.Label(
        root,
        text=(
            "All channels above are free, legal streams.\n"
            "Full live CNN / Fox News / MSNBC are paid —\n"
            "they are not included on purpose."
        ),
        bg=theme["bg"],
        fg=theme["note_fg"],
    )
    note.pack(pady=(4, 10))

    if dark:
        apply_dark_titlebar(root)



def main() -> None:
    channels = load_channels()
    root = tk.Tk()
    build_ui(root, channels)
    root.mainloop()


if __name__ == "__main__":
    main()
