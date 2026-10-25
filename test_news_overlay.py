"""Focused regression check for shared settings versus saved story playback."""

import importlib.util
import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


class OverlaySeparationTest(unittest.TestCase):
    def test_saved_story_cannot_replace_shared_settings(self):
        spec = importlib.util.spec_from_file_location("overlay_server", Path(__file__).with_name("news-overlay-server.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            module.STATE_FILE = Path(directory) / "state.json"
            module.CUES_FILE = Path(directory) / "cues.json"
            module.STATE = module.DEFAULTS.copy()
            module.CUES = []
            server = ThreadingHTTPServer(("127.0.0.1", 0), module.Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_port}"

            def post(path, payload):
                body = json.dumps(payload).encode("utf-8")
                request = Request(base + path, body, {"Content-Type": "application/json"})
                with urlopen(request) as response:
                    return json.load(response)

            try:
                core = post("/api/core", {"theme": "church", "accent": "#006acc", "logo": "station.png",
                                          "tickerItems": ["Shared one", "Shared two"]})
                self.assertEqual(core["theme"], "church")
                self.assertEqual(core["storyRevision"], 1)
                self.assertEqual(core["ticker"], "Shared one ◆ Shared two")
                hidden = post("/api/core", {"showOverlay": False})
                self.assertFalse(hidden["showOverlay"])
                self.assertEqual(hidden["storyRevision"], 1)
                saved = post("/api/cues/save", {"name": "Evening lead", "settings": {
                    "headline": "EVENING LEAD", "supportingLines": ["One", "Two", "Three"],
                    "supportingInterval": 5, "tickerItems": ["Alpha", "Beta"],
                    "accent": "#ff0000", "logo": "wrong.png",
                }})
                self.assertNotIn("accent", saved["cue"]["settings"])
                self.assertNotIn("logo", saved["cue"]["settings"])
                self.assertNotIn("tickerItems", saved["cue"]["settings"])
                state = post("/api/activate", {"id": saved["cue"]["id"]})
                self.assertEqual(state["accent"], "#006acc")
                self.assertEqual(state["theme"], "church")
                self.assertEqual(state["logo"], "station.png")
                self.assertEqual(state["supportingLines"], ["One", "Two", "Three"])
                self.assertEqual(state["supportingInterval"], 5)
                self.assertEqual(state["tickerItems"], ["Shared one", "Shared two"])
                self.assertFalse(state["showOverlay"])
                self.assertEqual(state["storyRevision"], 2)
                reloaded = module.load_state()
                self.assertEqual(reloaded["headline"], "EVENING LEAD")
                self.assertEqual(reloaded["theme"], "church")
                self.assertEqual(reloaded["tickerItems"], ["Shared one", "Shared two"])
                self.assertEqual(reloaded["supportingLines"], ["One", "Two", "Three"])
                self.assertFalse(reloaded["showOverlay"])
                edited = post("/api/cues/save", {"id": saved["cue"]["id"], "name": "Updated lead",
                                                   "settings": {"label": "LIVE UPDATE", "headline": "NEW HEADLINE",
                                                                "supportingLines": ["First", "Second"],
                                                                "supportingInterval": 10}})
                self.assertEqual(len(edited["cues"]), 1)
                with urlopen(base + "/api/state") as response:
                    still_live = json.load(response)
                self.assertEqual(still_live["headline"], "EVENING LEAD")
                replayed = post("/api/activate", {"id": saved["cue"]["id"]})
                self.assertEqual(replayed["headline"], "NEW HEADLINE")
                self.assertEqual(replayed["supportingLines"], ["First", "Second"])
                self.assertEqual(replayed["supportingInterval"], 10)
                self.assertEqual(replayed["tickerItems"], ["Shared one", "Shared two"])
                with self.assertRaises(HTTPError) as invalid:
                    post("/api/core", {"theme": "unlisted"})
                self.assertEqual(invalid.exception.code, 400)
            finally:
                server.shutdown()
                server.server_close()

    def test_lan_host_and_same_origin_are_required(self):
        spec = importlib.util.spec_from_file_location("overlay_server", Path(__file__).with_name("news-overlay-server.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        server = ThreadingHTTPServer(("127.0.0.1", 0), module.Handler)
        server.allowed_hosts = {"127.0.0.1", "localhost", "192.168.1.8"}
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            host = f"192.168.1.8:{server.server_port}"
            request = Request(base + "/api/state", headers={"Host": host, "Origin": f"http://{host}"})
            with urlopen(request) as response:
                self.assertIn("theme", json.load(response))
            request = Request(base + "/api/state", headers={"Host": host, "Origin": "http://other.example"})
            with self.assertRaises(HTTPError) as rejected:
                urlopen(request)
            self.assertEqual(rejected.exception.code, 403)
            with urlopen(base + "/api/network") as response:
                self.assertEqual(json.load(response)["port"], server.server_port)
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
