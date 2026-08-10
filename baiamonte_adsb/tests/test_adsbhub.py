import hashlib
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SERVICE = Path(__file__).parents[1] / "adsbhub" / "service.py"
SPEC = importlib.util.spec_from_file_location("baiamonte_adsbhub", SERVICE)
adsbhub = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(adsbhub)


class ADSBHubTests(unittest.TestCase):
    def test_dynamic_ip_uses_published_challenge_protocol(self):
        challenge = "challengeX"
        key = "private-station-key"
        expected = hashlib.md5((key + challenge[:-1]).encode()).hexdigest() + challenge[-1]
        with patch.object(adsbhub, "fetch_text", side_effect=[challenge, "OK"]) as fetch:
            self.assertTrue(adsbhub.update_dynamic_ip(key, "203.0.113.8", ""))
        update_url = fetch.call_args_list[1].args[0]
        self.assertIn(f"sessid={expected}", update_url)
        self.assertIn("myip=203.0.113.8", update_url)
        self.assertNotIn(key, update_url)

    def test_status_file_never_contains_private_key(self):
        old_file = adsbhub.STATUS_FILE
        with tempfile.TemporaryDirectory() as tmp:
            adsbhub.STATUS_FILE = Path(tmp) / "adsbhub.json"
            os.environ["ADSBHUB_CKEY"] = "do-not-publish-this"
            os.environ["SERVICE_ENABLE_ADSBHUB"] = "true"
            try:
                adsbhub.write_status()
                payload = adsbhub.STATUS_FILE.read_text()
                self.assertNotIn("do-not-publish-this", payload)
                self.assertTrue(json.loads(payload)["key_configured"])
            finally:
                adsbhub.STATUS_FILE = old_file
                os.environ.pop("ADSBHUB_CKEY", None)
                os.environ.pop("SERVICE_ENABLE_ADSBHUB", None)

    def test_auto_public_address_uses_adsbhub_endpoint(self):
        os.environ["ADSBHUB_PUBLIC_HOST"] = "auto"
        try:
            with patch.object(adsbhub, "fetch_text", side_effect=["203.0.113.9", "2001:db8::9"]) as fetch:
                self.assertEqual(adsbhub.public_addresses(), ("203.0.113.9", "2001:db8::9"))
            self.assertIn("ip4.adsbhub.org", fetch.call_args_list[0].args[0])
        finally:
            os.environ.pop("ADSBHUB_PUBLIC_HOST", None)


if __name__ == "__main__":
    unittest.main()
