# OBS News Lower Third

A 1920 × 1080 browser source for OBS with News, Church and Podcast themes, a live clock, animated headline changes, rotating supporting lines, a shared ticker, a logo, timed speaker name graphics, and a separate control page.

## Start

Requires Python 3.10 or newer. On Windows, run `start-news-overlay.bat`. Alternatively run:

```powershell
python news-overlay-server.py --host 0.0.0.0 --port 8080
```

Keep the server running during the broadcast. Open the control page at `http://127.0.0.1:8080/news-controls.html`. It shows the **OBS Browser Source URL**, **OBS Custom Browser Dock URL**, and this computer's local network controls link under the preview. Copy the links from that page so they use the port your server is actually running on.

1. **Overlay:** Add the **OBS Browser Source URL** as a Browser Source in your scene. Set its width to **1920** and height to **1080**. This is the transparent lower-third graphic viewers see. On port 8080, the URL is `http://127.0.0.1:8080/news-lower-third.html?v=20261025-2`.
2. **Controls:** Add the **OBS Custom Browser Dock URL** as a Custom Browser Dock in OBS. This is the compact panel for editing and playing saved headlines; it does not appear in the video. On port 8080, the URL is `http://127.0.0.1:8080/news-obs-dock.html`.

The dock's top bar shows the live headline, a green dot when the overlay is on air, and an eye icon for visibility. Click a cue row to expand and edit its name, label, headline, supporting lines and rotation interval. **Save** keeps the edits in the cue; the separate Play icon takes it live. Playing a cue with unsaved edits saves them first. Hover or focus on an icon to see its label. Use the gear icon to open the full control page.

## Use

- **Stories:** edit a headline and up to four supporting lines, then save a cue. Press **Play Live** beside a saved cue to put it on air. At least two filled supporting lines are needed for rotation.
- **Speaker ID:** enter a speaker name and optional role, choose one of four motion graphic templates, left or right placement, and a 4–10 second hold. Preview it, then press **Play live** to animate it over the current headline. It enters, stays for the chosen time, and exits automatically. Press Play again to replay; **Take off air** starts its exit early. The last played speaker settings are saved on disk.
- **News themes:** choose News, Church or Podcast. Selecting a card shows a draft preview; **Apply theme live** saves its layout and color palette for every story. You can fine tune the colors in Broadcast settings.
- **Broadcast settings:** set the shared ticker list, colors, logo, clock, visibility and layout. Press **Save shared settings** to apply them to every story.
- **OBS dock:** click a cue to inspect and edit it, play it with its triangle button, or use the eye button to hide or show the entire lower third and LIVE clock. The dock and full editor stay synchronized through the same server.
- The ticker accepts comma-separated or newline-separated items. Supporting lines can rotate every 5, 7 or 10 seconds.

`news-overlay-state.json` and `news-overlay-cues.json` contain a snapshot of the current broadcast settings and saved cues. The `news-logos` folder contains the uploaded logo assets referenced by the state file. The server writes changes to these files as you use the controls.

## Control from another device

The server listens on this computer and its local network by default. In the control page, use the link under **Controls on other devices** on a phone or another computer connected to the same Wi-Fi or Ethernet network. The server also prints the LAN URL when it starts. Keep the OBS Browser Source pointed at `127.0.0.1` on the streaming computer.

The LAN address may change when your network changes. If another device cannot connect, check that the server is running and allow Python through your computer's firewall for the private network. The controls have no sign-in, so use a trusted network and do not forward the server port to the internet. To limit access to this computer again, start with `--host 127.0.0.1`.

## Check

```powershell
python -m unittest test_news_overlay.py -v
```
