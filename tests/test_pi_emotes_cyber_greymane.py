import json
import os
import unittest


class TestPiEmoteCyberGreymaneSet(unittest.TestCase):
    def setUp(self):
        self.repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.set_dir = os.path.join(
            self.repo_root, "emotes", "cyber-greymane"
        )

    def test_emotes_json_exists_and_valid(self):
        emotes_json_path = os.path.join(self.set_dir, "emotes.json")
        self.assertTrue(os.path.isfile(emotes_json_path), emotes_json_path)
        with open(emotes_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("idle", data)
        self.assertIn("think", data)
        self.assertIn("talk", data)
        self.assertIn("default", data["idle"])
        self.assertIn("blink", data["idle"])
        self.assertIn("default", data["think"])
        self.assertIn("hard", data["think"])
        self.assertIn("weights", data["talk"])
        self.assertIsInstance(data["talk"]["weights"], dict)

    def test_required_files_present(self):
        def png(path):
            return os.path.isfile(os.path.join(self.set_dir, path))

        self.assertTrue(png("idle/idle.png"))
        self.assertTrue(png("idle/idle_blink.png"))
        self.assertTrue(png("think/think.png"))
        self.assertTrue(png("think/think_hard.png"))

        # talk: ensure there is at least one filename containing "close"
        talk_dir = os.path.join(self.set_dir, "talk")
        self.assertTrue(os.path.isdir(talk_dir))
        talk_pngs = sorted([f for f in os.listdir(talk_dir) if f.lower().endswith(".png")])
        self.assertGreaterEqual(len(talk_pngs), 1)
        self.assertTrue(any("close" in f.lower() for f in talk_pngs), talk_pngs)

    def test_talk_weights_match_talk_folder(self):
        emotes_json_path = os.path.join(self.set_dir, "emotes.json")
        with open(emotes_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        weights = data["talk"]["weights"]
        self.assertGreaterEqual(len(weights), 1)

        talk_dir = os.path.join(self.set_dir, "talk")
        talk_pngs = sorted([f for f in os.listdir(talk_dir) if f.lower().endswith(".png")])
        weight_keys = sorted(list(weights.keys()))

        # Ensure the widget can deterministically pick from weighted images.
        self.assertEqual(
            weight_keys,
            talk_pngs,
            msg=f"talk.weights keys must match talk/*.png exactly; weights={weight_keys} pngs={talk_pngs}",
        )

        for k, v in weights.items():
            self.assertIsInstance(v, (int, float))
            self.assertGreater(v, 0, f"Weight must be > 0 for {k}")

    def test_other_state_folders_have_pngs(self):
        # These are used by pi-emote for cycling/random selection; keep them non-empty.
        required_non_empty = [
            "hi",
            "read",
            "write",
            "tool",
            "success",
            "failure",
        ]
        optional = ["compact"]

        for folder in required_non_empty + optional:
            path = os.path.join(self.set_dir, folder)
            self.assertTrue(os.path.isdir(path), msg=f"Missing folder {folder}")
            pngs = [f for f in os.listdir(path) if f.lower().endswith(".png")]
            self.assertGreater(len(pngs), 0, msg=f"Folder {folder} must contain at least one .png")


if __name__ == "__main__":
    unittest.main()
