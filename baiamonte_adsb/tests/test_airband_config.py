import importlib.util
import os
import tempfile
import unittest
from pathlib import Path


RENDERER = Path(__file__).parents[1] / "airband" / "render_config.py"
SPEC = importlib.util.spec_from_file_location("baiamonte_airband_config", RENDERER)
renderer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(renderer)


class AirbandConfigTests(unittest.TestCase):
    def setUp(self):
        self.original = os.environ.copy()
        os.environ.update({
            "AIRBAND_FREQUENCIES": "118.700,119.250,129.725,127.675",
            "AIRBAND_LABELS": "Catania Tower,Catania Approach,Catania Ground,Catania ATIS",
            "VHF_DEVICE": "1",
            "RECEIVER_DEVICE_INDEX": "0",
            "AIRBAND_SOURCE_PASSWORD": "local-secret",
        })

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.original)

    def test_local_config_uses_second_radio_and_catania_channels(self):
        config = renderer.render_airband("local-secret")
        self.assertIn("index = 1", config)
        self.assertIn("118.700", config)
        self.assertIn('"Catania Tower"', config)
        self.assertIn('server = "127.0.0.1"', config)

    def test_airnav_output_is_added_without_changing_local_stream(self):
        os.environ.update({
            "AIRNAV_VHF_ENABLED": "true",
            "AIRNAV_VHF_SERVER": "audio.example.test",
            "AIRNAV_VHF_PASSWORD": "airnav-secret",
            "AIRNAV_VHF_MOUNT": "serial-key",
        })
        config = renderer.render_airband("local-secret")
        self.assertIn('server = "127.0.0.1"', config)
        self.assertIn('server = "audio.example.test"', config)
        self.assertIn('mountpoint = "serial-key"', config)

    def test_frequency_outside_civil_airband_is_rejected(self):
        os.environ["AIRBAND_FREQUENCIES"] = "1090.000"
        with self.assertRaisesRegex(ValueError, "outside the 118-137 MHz civil airband"):
            renderer.render_airband("local-secret")

    def test_blank_source_password_is_generated_and_reused(self):
        os.environ["AIRBAND_SOURCE_PASSWORD"] = ""
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "password"
            first = renderer.source_password(path)
            second = renderer.source_password(path)
        self.assertEqual(first, second)
        self.assertGreater(len(first), 20)


if __name__ == "__main__":
    unittest.main()
