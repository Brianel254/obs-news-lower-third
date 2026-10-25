"""OBS lower-third control server for this computer and its local network."""

from __future__ import annotations

import json
import argparse
import ipaddress
import os
import re
import socket
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4


ROOT = Path(__file__).resolve().parent
STATE_FILE = ROOT / "news-overlay-state.json"
LOGO_FILE = ROOT / "news-logo-upload.bin"
LOGO_DIR = ROOT / "news-logos"
CUES_FILE = ROOT / "news-overlay-cues.json"
DEFAULT_HOST = os.environ.get("NEWS_OVERLAY_HOST", "0.0.0.0")
DEFAULT_PORT = int(os.environ.get("NEWS_OVERLAY_PORT", "8080"))
LOCK = threading.Lock()

DEFAULTS = {
    "theme": "news",
    "label": "BREAKING NEWS",
    "headline": "YOUR HEADLINE HERE",
    "subtitle": "Your supporting line stays on screen",
    "ticker": "Replace this message with your scrolling update",
    "supportingLines": ["Your supporting line stays on screen"],
    "supportingInterval": 7,
    "tickerItems": ["Replace this message with your scrolling update"],
    "timeZone": "Africa/Nairobi",
    "zoneLabel": "EAT",
    "logo": "logo.png",
    "logoMime": "image/png",
    "tickerSeconds": 34,
    "accent": "#c90013",
    "accentDark": "#87000c",
    "panelLight": "#ffffff",
    "panelDark": "#b6b9bc",
    "headlineColor": "#292a2d",
    "subtitleColor": "#616367",
    "tickerColor": "#ffffff",
    "logoBg": "#38393d",
    "showLive": True,
    "showOverlay": True,
    "showLabel": True,
    "showSubtitle": True,
    "showTicker": True,
    "showLogo": True,
    "showSeconds": True,
    "bottomOffset": 54,
    "sideInset": 48,
    "cornerTop": 42,
    "cornerLeft": 48,
    "revision": 1,
    "storyRevision": 1,
    "activeCueId": "",
}

STORY_KEYS = {"label", "headline", "supportingLines", "supportingInterval"}
CORE_KEYS = set(DEFAULTS) - STORY_KEYS - {"subtitle", "ticker", "revision", "storyRevision", "activeCueId", "logoMime"}

TEXT_LIMITS = {
    "label": 48,
    "headline": 180,
    "subtitle": 220,
    "ticker": 500,
    "timeZone": 80,
    "zoneLabel": 12,
    "logo": 2048,
}
COLORS = {
    "accent", "accentDark", "panelLight", "panelDark", "headlineColor",
    "subtitleColor", "tickerColor", "logoBg",
}
BOOLEANS = {
    "showLive", "showOverlay", "showLabel", "showSubtitle", "showTicker", "showLogo", "showSeconds",
}
NUMBERS = {
    "tickerSeconds": (8, 180),
    "bottomOffset": (0, 300),
    "sideInset": (0, 300),
    "cornerTop": (0, 300),
    "cornerLeft": (0, 300),
}


def checked_value(key: str, value: object) -> object:
    if key == "theme":
        if value not in {"news", "church", "podcast"}:
            raise ValueError("Theme must be news, church or podcast")
        return value
    if key == "supportingLines":
        if not isinstance(value, list) or len(value) > 4 or any(
            not isinstance(item, str) or not item.strip() or len(item) > 220 for item in value
        ):
            raise ValueError("Use up to four non-empty supporting lines (220 characters each)")
        return [item.strip() for item in value]
    if key == "tickerItems":
        if not isinstance(value, list) or len(value) > 40 or sum(len(str(item)) for item in value) > 4000 or any(
            not isinstance(item, str) or not item.strip() or len(item) > 300 for item in value
        ):
            raise ValueError("Use up to 40 non-empty ticker items (300 characters each)")
        return [item.strip() for item in value]
    if key == "supportingInterval":
        if type(value) is not int or value not in {5, 7, 10}:
            raise ValueError("Supporting line interval must be 5, 7 or 10 seconds")
        return value
    if key in TEXT_LIMITS:
        if not isinstance(value, str) or len(value) > TEXT_LIMITS[key]:
            raise ValueError(f"Invalid {key}")
        return value
    if key in COLORS:
        if not isinstance(value, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
            raise ValueError(f"Invalid {key}")
        return value.lower()
    if key in BOOLEANS:
        if not isinstance(value, bool):
            raise ValueError(f"Invalid {key}")
        return value
    if key in NUMBERS:
        low, high = NUMBERS[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= value <= high:
            raise ValueError(f"Invalid {key}")
        return int(value)
    raise ValueError(f"Unknown setting: {key}")


def load_state() -> dict:
    state = DEFAULTS.copy()
    if STATE_FILE.exists():
        try:
            saved = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            for key, value in saved.items():
                if key in DEFAULTS and key not in {"revision", "storyRevision", "logoMime", "activeCueId"}:
                    state[key] = checked_value(key, value)
            if saved.get("logoMime") in {"image/png", "image/jpeg", "image/webp"}:
                state["logoMime"] = saved["logoMime"]
            if isinstance(saved.get("revision"), int):
                state["revision"] = saved["revision"]
            if isinstance(saved.get("storyRevision"), int):
                state["storyRevision"] = saved["storyRevision"]
            else:
                state["storyRevision"] = state["revision"]
            if isinstance(saved.get("activeCueId"), str):
                state["activeCueId"] = saved["activeCueId"][:32]
            if "supportingLines" not in saved:
                state["supportingLines"] = [state["subtitle"]] if state["subtitle"].strip() else []
            if "tickerItems" not in saved:
                state["tickerItems"] = [item.strip() for item in state["ticker"].split(",") if item.strip()]
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            print(f"State file could not be loaded; using defaults: {exc}")
    return state


STATE = load_state()


def load_cues() -> list[dict]:
    if not CUES_FILE.exists():
        return []
    try:
        saved = json.loads(CUES_FILE.read_text(encoding="utf-8"))
        if not isinstance(saved, list):
            raise ValueError("Cue library must be a list")
        for cue in saved:
            if not isinstance(cue, dict) or not isinstance(cue.get("settings"), dict):
                raise ValueError("Invalid saved cue")
            cue["settings"] = checked_story(cue["settings"], legacy=True)
        return saved
    except (OSError, ValueError, TypeError) as exc:
        print(f"Cue library could not be loaded: {exc}")
        return []


def save_state(state: dict) -> None:
    temporary = STATE_FILE.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(STATE_FILE)


def save_cues(cues: list[dict]) -> None:
    temporary = CUES_FILE.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(cues, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(CUES_FILE)


def checked_story(value: object, legacy: bool = False) -> dict:
    if not isinstance(value, dict):
        raise ValueError("Story settings must be an object")
    story = {key: checked_value(key, item) for key, item in value.items() if key in STORY_KEYS}
    if legacy and "supportingLines" not in story and isinstance(value.get("subtitle"), str):
        story["supportingLines"] = checked_value("supportingLines", [value["subtitle"]] if value["subtitle"].strip() else [])
    return story


def checked_core(value: object) -> dict:
    if not isinstance(value, dict):
        raise ValueError("Broadcast settings must be an object")
    return {key: checked_value(key, item) for key, item in value.items() if key in CORE_KEYS}


def with_legacy_copy(state: dict) -> dict:
    """Keep old already-open overlays readable until OBS loads the new page."""
    state["subtitle"] = state["supportingLines"][0] if state["supportingLines"] else ""
    state["ticker"] = " ◆ ".join(state["tickerItems"])
    return state


CUES = load_cues()


def network_ipv4_addresses() -> list[str]:
    """Find private IPv4 addresses that another device on the LAN can open."""
    addresses = set()
    try:
        for address in socket.gethostbyname_ex(socket.gethostname())[2]:
            addresses.add(address)
        for item in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            addresses.add(item[4][0])
    except OSError:
        pass
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("8.8.8.8", 80))  # Selects a local interface; sends no packet.
            addresses.add(probe.getsockname()[0])
    except OSError:
        pass
    return sorted(address for address in addresses if (
        (ip := ipaddress.ip_address(address)).is_private
        and not ip.is_loopback and not ip.is_link_local and not ip.is_unspecified
    ))


class Handler(BaseHTTPRequestHandler):
    def allowed_request(self) -> bool:
        names = getattr(self.server, "allowed_hosts", {"127.0.0.1", "localhost"})
        allowed = {f"{name}:{self.server.server_port}" for name in names}
        host = self.headers.get("Host", "").lower()
        origin = self.headers.get("Origin")
        return host in allowed and (origin is None or origin in {f"http://{name}" for name in allowed})

    def log_message(self, format: str, *args: object) -> None:
        if not self.path.startswith(("/api/state", "/api/cues")):
            super().log_message(format, *args)

    def send_bytes(self, body: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, value: object, status: int = 200) -> None:
        self.send_bytes(json.dumps(value).encode("utf-8"), "application/json; charset=utf-8", status)

    def do_GET(self) -> None:
        if not self.allowed_request():
            self.send_json({"error": "Local requests only"}, 403)
            return
        path = urlsplit(self.path).path
        if path == "/":
            self.send_response(302)
            self.send_header("Location", "/news-controls.html")
            self.end_headers()
            return
        if path == "/api/state":
            with LOCK:
                self.send_json(STATE.copy())
            return
        if path == "/api/cues":
            with LOCK:
                self.send_json({"cues": CUES.copy()})
            return
        if path == "/api/network":
            addresses = network_ipv4_addresses() if self.server.server_address[0] != "127.0.0.1" else []
            self.send_json({"port": self.server.server_port, "addresses": addresses})
            return
        if path.startswith("/media/logo/"):
            name = path.removeprefix("/media/logo/")
            if not re.fullmatch(r"[0-9a-f]{32}\.(png|jpg|webp)", name):
                self.send_json({"error": "Not found"}, 404)
                return
            file_path = LOGO_DIR / name
            if not file_path.is_file():
                self.send_json({"error": "Not found"}, 404)
                return
            mime = {"png": "image/png", "jpg": "image/jpeg", "webp": "image/webp"}[name.rsplit(".", 1)[1]]
            self.send_bytes(file_path.read_bytes(), mime)
            return
        files = {
            "/news-lower-third.html": (ROOT / "news-lower-third.html", "text/html; charset=utf-8"),
            "/news-controls.html": (ROOT / "news-controls.html", "text/html; charset=utf-8"),
            "/news-obs-dock.html": (ROOT / "news-obs-dock.html", "text/html; charset=utf-8"),
            "/logo.png": (ROOT / "logo.png", "image/png"),
        }
        if path == "/media/logo":
            with LOCK:
                mime = STATE["logoMime"]
            files[path] = (LOGO_FILE, mime)
        if path not in files or not files[path][0].is_file():
            self.send_json({"error": "Not found"}, 404)
            return
        file_path, mime = files[path]
        self.send_bytes(file_path.read_bytes(), mime)

    def do_POST(self) -> None:
        global STATE, CUES
        if not self.allowed_request():
            self.send_json({"error": "Local requests only"}, 403)
            return
        path = urlsplit(self.path).path
        if path not in {"/api/state", "/api/core", "/api/logo", "/api/cues/save", "/api/cues/delete", "/api/activate"}:
            self.send_json({"error": "Not found"}, 404)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            limit = 6_000_000 if path == "/api/logo" else 65_536
            if not 0 < size <= limit:
                raise ValueError("Request size is invalid")
            body = self.rfile.read(size)
            if len(body) != size:
                raise ValueError("Incomplete request")
            if path == "/api/state":
                incoming = json.loads(body)
                changes = checked_story(incoming, legacy=True)
                with LOCK:
                    next_state = with_legacy_copy({**STATE, **changes, "revision": STATE["revision"] + 1,
                                                   "storyRevision": STATE["storyRevision"] + 1, "activeCueId": ""})
                    save_state(next_state)
                    STATE = next_state
                    answer = STATE.copy()
            elif path == "/api/core":
                changes = checked_core(json.loads(body))
                with LOCK:
                    next_state = with_legacy_copy({**STATE, **changes, "revision": STATE["revision"] + 1})
                    save_state(next_state)
                    STATE = next_state
                    answer = STATE.copy()
            elif path == "/api/activate":
                incoming = json.loads(body)
                if not isinstance(incoming, dict):
                    raise ValueError("Activation must be an object")
                with LOCK:
                    cue_id = incoming.get("id", "")
                    if cue_id:
                        cue = next((item for item in CUES if item["id"] == cue_id), None)
                        if cue is None:
                            raise ValueError("Saved cue not found")
                        changes = checked_story(cue["settings"], legacy=True)
                    else:
                        changes = checked_story(incoming.get("settings"), legacy=True)
                    next_state = with_legacy_copy({**STATE, **changes, "revision": STATE["revision"] + 1,
                                                   "storyRevision": STATE["storyRevision"] + 1, "activeCueId": cue_id})
                    save_state(next_state)
                    STATE = next_state
                    answer = STATE.copy()
            elif path == "/api/cues/save":
                incoming = json.loads(body)
                if not isinstance(incoming, dict):
                    raise ValueError("Cue must be an object")
                name = incoming.get("name", "")
                if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80:
                    raise ValueError("Enter a cue name (up to 80 characters)")
                settings = checked_story(incoming.get("settings"), legacy=True)
                with LOCK:
                    cue_id = incoming.get("id")
                    updated = CUES.copy()
                    if cue_id:
                        index = next((i for i, item in enumerate(updated) if item["id"] == cue_id), None)
                        if index is None:
                            raise ValueError("Saved cue not found")
                    else:
                        if len(updated) >= 100:
                            raise ValueError("Cue library is full (100 maximum)")
                        cue_id = uuid4().hex
                        index = len(updated)
                    cue = {"id": cue_id, "name": name.strip(), "settings": settings,
                           "savedAt": datetime.now(timezone.utc).isoformat()}
                    if index == len(updated):
                        updated.append(cue)
                    else:
                        updated[index] = cue
                    save_cues(updated)
                    CUES = updated
                    answer = {"cue": cue, "cues": CUES.copy()}
            elif path == "/api/cues/delete":
                incoming = json.loads(body)
                cue_id = incoming.get("id") if isinstance(incoming, dict) else None
                with LOCK:
                    updated = [item for item in CUES if item["id"] != cue_id]
                    if len(updated) == len(CUES):
                        raise ValueError("Saved cue not found")
                    save_cues(updated)
                    CUES = updated
                    if STATE["activeCueId"] == cue_id:
                        next_state = {**STATE, "activeCueId": "", "revision": STATE["revision"] + 1}
                        save_state(next_state)
                        STATE = next_state
                    answer = {"cues": CUES.copy()}
            else:  # /api/logo uploads an asset for a future cue; it does not change the live output.
                if body.startswith(b"\x89PNG\r\n\x1a\n"):
                    extension = "png"
                elif body.startswith(b"\xff\xd8\xff"):
                    extension = "jpg"
                elif body.startswith(b"RIFF") and body[8:12] == b"WEBP":
                    extension = "webp"
                else:
                    raise ValueError("Choose a PNG, JPEG, or WebP image")
                LOGO_DIR.mkdir(exist_ok=True)
                filename = f"{uuid4().hex}.{extension}"
                (LOGO_DIR / filename).write_bytes(body)
                answer = {"logo": f"/media/logo/{filename}"}
            self.send_json(answer)
        except (ValueError, TypeError, json.JSONDecodeError, OSError) as exc:
            self.send_json({"error": str(exc)}, 400)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OBS lower-third control server")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Bind address (default: 0.0.0.0 for local network)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port (default: 8080)")
    args = parser.parse_args()
    try:
        server = ThreadingHTTPServer((args.host, args.port), Handler)
        addresses = network_ipv4_addresses() if args.host != "127.0.0.1" else []
        server.allowed_hosts = {"127.0.0.1", "localhost", *addresses}
        if args.host not in {"0.0.0.0", "127.0.0.1"}:
            server.allowed_hosts.add(args.host)
        actual_port = server.server_port
        print(f"Control page: http://127.0.0.1:{actual_port}/news-controls.html")
        print(f"OBS source:   http://127.0.0.1:{actual_port}/news-lower-third.html")
        for address in addresses:
            print(f"LAN controls: http://{address}:{actual_port}/news-controls.html")
        print("Keep this window open while streaming. Press Ctrl+C to stop.")
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
