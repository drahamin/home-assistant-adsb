import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


EXPORT_SCRIPT = Path(__file__).parents[1] / "export-env-from-config.sh"


class ExportEnvironmentTests(unittest.TestCase):
    def test_options_are_exported_without_leading_newlines(self):
        options = {
            "SERVICE_ENABLE_PIAWARE": True,
            "FR24FEED_FR24KEY": "test-key",
            "HTML_SITE_NAME": "Tenuta Baiamonte Airspace",
            "PLANEFINDER_SHARECODE": "",
        }

        with tempfile.TemporaryDirectory() as tmp:
            options_file = Path(tmp) / "options.json"
            options_file.write_text(json.dumps(options))
            environment = os.environ.copy()
            environment.pop("SUPERVISOR_TOKEN", None)
            environment["BAIAMONTE_OPTIONS_FILE"] = str(options_file)

            command = (
                f'source "{EXPORT_SCRIPT}"; '
                "printf '%s|%s|%s|%s' "
                '"$SERVICE_ENABLE_PIAWARE" "$FR24FEED_FR24KEY" '
                '"$HTML_SITE_NAME" "$PLANEFINDER_SHARECODE"'
            )
            result = subprocess.run(
                ["bash", "-c", command],
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout,
            "true|test-key|Tenuta Baiamonte Airspace|",
        )
        self.assertNotIn("not a valid identifier", result.stderr)

    def test_home_assistant_location_response_is_valid_json(self):
        options = {
            "HTML_SITE_LAT": "HOMEASSISTANT_LATITUDE",
            "HTML_SITE_LON": "HOMEASSISTANT_LONGITUDE",
            "HTML_SITE_ALT": "HOMEASSISTANT_ELEVATION",
        }

        with tempfile.TemporaryDirectory() as tmp:
            options_file = Path(tmp) / "options.json"
            options_file.write_text(json.dumps(options))
            environment = os.environ.copy()
            environment["SUPERVISOR_TOKEN"] = "test-token"
            environment["BAIAMONTE_OPTIONS_FILE"] = str(options_file)

            command = (
                "curl() { "
                "case \"$*\" in "
                "*core/api/config*) printf '%s' "
                "'{\"latitude\":37.847,\"longitude\":14.925,\"elevation\":959}' ;; "
                "*) printf '%s' '{\"data\":{\"version\":\"15.2\"}}' ;; "
                "esac; }; "
                f'source "{EXPORT_SCRIPT}"; '
                "printf '%s|%s|%s' "
                '"$HTML_SITE_LAT" "$HTML_SITE_LON" "$HTML_SITE_ALT"'
            )
            result = subprocess.run(
                ["bash", "-c", command],
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "37.847|14.925|959")
        self.assertNotIn("parse error", result.stderr)


if __name__ == "__main__":
    unittest.main()
