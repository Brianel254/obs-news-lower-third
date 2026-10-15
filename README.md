# OBS News Lower Third

A 1920 × 1080 browser source for OBS with a live clock, animated headline changes, rotating supporting lines, shared ticker, logo, and a separate control page.

## Start

Requires Python 3.10 or newer. On Windows, run `start-news-overlay.bat`. Alternatively run:

```powershell
python news-overlay-server.py --port 8080
```

Keep the server running during the broadcast. Open the control page at `http://127.0.0.1:8080/news-controls.html`. It shows both OBS links under the preview: **OBS Browser Source URL** and **OBS Custom Browser Dock URL**. Copy the links from that page so they use the port your server is actually running on.

1. **Overlay:** Add the **OBS Browser Source URL** as a Browser Source in your scene. Set its width to **1920** and height to **1080**. This is the transparent lower-third graphic viewers see. On port 8080, the URL is `http://127.0.0.1:8080/news-lower-third.html?v=20261015-1`.
2. **Controls:** Add the **OBS Custom Browser Dock URL** as a Custom Browser Dock in OBS. This is the compact panel for editing and playing saved headlines; it does not appear in the video. On port 8080, the URL is `http://127.0.0.1:8080/news-obs-dock.html`.

The dock's top bar shows the live headline, a green dot when the overlay is on air, and an eye icon for visibility. Click a cue row to expand and edit its name, label, headline, supporting lines and rotation interval. **Save** keeps the edits in the cue; the separate Play icon takes it live. Playing a cue with unsaved edits saves them first. Hover or focus on an icon to see its label. Use the gear icon to open the full control page.

## Use

- **Stories:** edit a headline and up to four supporting lines, then save a cue. Press **Play Live** beside a saved cue to put it on air. At least two filled supporting lines are needed for rotation.
- **Broadcast settings:** set the shared ticker list, colors, logo, clock, visibility and layout. Press **Save shared settings** to apply them to every story.
- **OBS dock:** click a cue to inspect and edit it, play it with its triangle button, or use the eye button to hide or show the entire lower third and LIVE clock. The dock and full editor stay synchronized through the same server.
- The ticker accepts comma-separated or newline-separated items. Supporting lines can rotate every 5, 7 or 10 seconds.

`news-overlay-state.json` and `news-overlay-cues.json` contain a snapshot of the current broadcast settings and saved cues. The `news-logos` folder contains the uploaded logo assets referenced by the state file. The server writes changes to these files as you use the controls.

The server listens on your own computer (`127.0.0.1`), so the controls and OBS source are local to that computer.

## Check

```powershell
python -m unittest test_news_overlay.py -v
```
