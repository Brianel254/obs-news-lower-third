# OBS News Lower Third

A 1920 × 1080 browser source for OBS with a live clock, animated headline changes, rotating supporting lines, shared ticker, logo, and a separate control page.

## Start

Requires Python 3.10 or newer. On Windows, run `start-news-overlay.bat`. Alternatively run:

```powershell
python news-overlay-server.py --port 8080
```

Keep the server running during the broadcast. Open the controls at `http://127.0.0.1:8080/news-controls.html`. Add `http://127.0.0.1:8080/news-lower-third.html?v=20261015-1` as an OBS Browser Source with width **1920** and height **1080**. If you choose another port, use that same port in both URLs.

For compact controls inside OBS, add a Custom Browser Dock with URL `http://127.0.0.1:8080/news-obs-dock.html`. The dock lists saved cues, lets you play one live, and has an eye button to show or hide the entire overlay. Hover or focus on an icon to see its label. Use the gear icon to open the full editor.

## Use

- **Stories:** edit a headline and up to four supporting lines, then save a cue. Press **Play Live** beside a saved cue to put it on air. At least two filled supporting lines are needed for rotation.
- **Broadcast settings:** set the shared ticker list, colors, logo, clock, visibility and layout. Press **Save shared settings** to apply them to every story.
- **OBS dock:** play a saved cue with its triangle button, or use the eye button to hide or show the entire lower third and LIVE clock. The dock and full editor stay synchronized through the same server.
- The ticker accepts comma-separated or newline-separated items. Supporting lines can rotate every 5, 7 or 10 seconds.

`news-overlay-state.json` and `news-overlay-cues.json` contain a snapshot of the current broadcast settings and saved cues. The `news-logos` folder contains the uploaded logo assets referenced by the state file. The server writes changes to these files as you use the controls.

The server listens on your own computer (`127.0.0.1`), so the controls and OBS source are local to that computer.

## Check

```powershell
python -m unittest test_news_overlay.py -v
```
