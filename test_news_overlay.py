"""Focused regression check for shared settings versus saved story playback."""

import importlib.util
import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
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
                core = post("/api/core", {"accent": "#006acc", "logo": "station.png",
                                          "tickerItems": ["Shared one", "Shared two"]})
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
                self.assertEqual(state["logo"], "station.png")
                self.assertEqual(state["supportingLines"], ["One", "Two", "Three"])
                self.assertEqual(state["supportingInterval"], 5)
                self.assertEqual(state["tickerItems"], ["Shared one", "Shared two"])
                self.assertFalse(state["showOverlay"])
                self.assertEqual(state["storyRevision"], 2)
                reloaded = module.load_state()
                self.assertEqual(reloaded["headline"], "EVENING LEAD")
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
            finally:
                server.shutdown()
                server.server_close()


if __name__ == "__main__":
    unittest.main()
