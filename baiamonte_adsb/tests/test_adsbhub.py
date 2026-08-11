import hashlib
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


SERVICE = Path(__file__).parents[1] / "adsbhub" / "service.py"
SPEC = importlib.util.spec_from_file_location("baiamonte_adsbhub", SERVICE)
adsbhub = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(adsbhub)


class ADSBHubTests(unittest.TestCase):
    class Stream:
        def __init__(self, chunks=()):
            self.chunks = list(chunks)
            self.sent = []

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def recv(self, _size):
            if self.chunks:
                return self.chunks.pop(0)
            adsbhub.STOP.set()
            return b""

        def sendall(self, chunk):
            self.sent.append(chunk)

        def settimeout(self, _value):
            pass

        def setsockopt(self, *_values):
            pass

        def close(self):
            pass

    def test_dynamic_ip_uses_published_challenge_protocol(self):
        challenge = "challengeX"
        key = "private-station-key"
        expected = hashlib.md5((key + challenge[:-1]).encode()).hexdigest() + challenge[-1]
        with patch.object(adsbhub, "fetch_text", side_effect=[challenge, expected]) as fetch:
            self.assertTrue(adsbhub.update_dynamic_ip(key, "203.0.113.8", ""))
        update_url = fetch.call_args_list[1].args[0]
        self.assertIn(f"sessid={expected}", update_url)
        self.assertIn("myip=203.0.113.8", update_url)
        self.assertNotIn(key, update_url)

    def test_dynamic_ip_rejects_unexpected_response(self):
        with patch.object(adsbhub, "fetch_text", side_effect=["challengeX", "OK"]):
            self.assertFalse(adsbhub.update_dynamic_ip("private-station-key", "203.0.113.8", ""))

    def test_stream_socket_has_no_idle_timeout_and_uses_keepalive(self):
        stream = Mock()
        adsbhub.configure_stream_socket(stream)
        stream.settimeout.assert_called_once_with(None)
        stream.setsockopt.assert_any_call(adsbhub.socket.SOL_SOCKET, adsbhub.socket.SO_KEEPALIVE, 1)

    def test_inbound_access_failure_uses_bounded_backoff(self):
        source = Path(adsbhub.__file__).read_text()
        self.assertIn("retry_delay = min(60.0, max(10.0, retry_delay * 2))", source)
        self.assertIn("STOP.wait(retry_delay)", source)
        self.assertIn("while not STOP.wait(5):", source)

    def test_outbound_route_forwards_raw_port_30002_to_adsbhub_5001(self):
        source = self.Stream([b"*8d4ca12358c382d690c8ac2863a7;\n"])
        remote = self.Stream()
        os.environ["SERVICE_ENABLE_ADSBHUB"] = "true"
        adsbhub.STOP.clear()
        try:
            with patch.object(adsbhub.socket, "create_connection", side_effect=[source, remote]) as connect:
                adsbhub.outbound_worker()
            self.assertEqual(connect.call_args_list[0].args[0], ("127.0.0.1", 30002))
            self.assertEqual(connect.call_args_list[1].args[0], ("data.adsbhub.org", 5001))
            self.assertEqual(remote.sent, [b"*8d4ca12358c382d690c8ac2863a7;\n"])
        finally:
            adsbhub.STOP.clear()
            os.environ.pop("SERVICE_ENABLE_ADSBHUB", None)

    def test_inbound_route_relays_adsbhub_5002_sbs_to_local_clients(self):
        class Listener(self.Stream):
            def bind(self, address):
                self.address = address

            def listen(self, count):
                self.backlog = count

            def accept(self):
                raise OSError("test listener complete")

        listener = Listener()
        remote = self.Stream([b"MSG,3,1,1,4CA123,1,2026/08/10,16:00:00.000\r\n"])
        local_client = self.Stream()
        os.environ["ADSBHUB_INBOUND_ENABLED"] = "true"
        adsbhub.STOP.clear()
        adsbhub.CLIENTS.clear()
        adsbhub.CLIENTS.add(local_client)
        try:
            with patch.object(adsbhub.socket, "socket", return_value=listener), patch.object(
                adsbhub.socket, "create_connection", return_value=remote
            ) as connect:
                adsbhub.inbound_worker()
            self.assertEqual(connect.call_args.args[0], ("data.adsbhub.org", 5002))
            self.assertEqual(listener.address, ("0.0.0.0", 5002))
            self.assertEqual(local_client.sent, [b"MSG,3,1,1,4CA123,1,2026/08/10,16:00:00.000\r\n"])
        finally:
            adsbhub.CLIENTS.clear()
            adsbhub.STOP.clear()
            os.environ.pop("ADSBHUB_INBOUND_ENABLED", None)

    def test_inbound_sbs_messages_become_display_only_targets(self):
        adsbhub.INBOUND_TARGETS.clear()
        first = b"MSG,3,1,1,4CA123,1,2026/08/10,16:00:00.000,2026/08/10,16:00:00.000,RYR43ET,18500,310.5,92.0,37.9123,15.2045,0,4721,0,0,0,0\r\n"
        second = b"MSG,4,1,1,4CA123,1,2026/08/10,16:00:01.000,2026/08/10,16:00:01.000,,18600,312.0,93.0,,,,,0,0,0,0\r\n"
        remainder = adsbhub.ingest_sbs_chunk(b"", first[:50])
        self.assertNotIn("4ca123", adsbhub.INBOUND_TARGETS)
        remainder = adsbhub.ingest_sbs_chunk(remainder, first[50:] + second)
        self.assertEqual(remainder, b"")
        target = adsbhub.INBOUND_TARGETS["4ca123"]
        self.assertEqual(target["flight"], "RYR43ET")
        self.assertEqual(target["altitude"], 18600)
        self.assertEqual(target["lat"], 37.9123)
        self.assertEqual(target["messages"], 2)
        adsbhub.INBOUND_TARGETS.clear()

    def test_zero_byte_inbound_close_reports_inactive_access(self):
        class Listener(self.Stream):
            def bind(self, _address):
                pass

            def listen(self, _count):
                pass

            def accept(self):
                raise OSError("test listener complete")

        os.environ["ADSBHUB_INBOUND_ENABLED"] = "true"
        adsbhub.STOP.clear()
        adsbhub.STATUS["inbound_error"] = ""
        remote = self.Stream([])
        try:
            with patch.object(adsbhub.socket, "socket", return_value=Listener()), patch.object(
                adsbhub.socket, "create_connection", return_value=remote
            ):
                adsbhub.inbound_worker()
            self.assertIn("closed port 5002 without sending data", adsbhub.STATUS["inbound_error"])
        finally:
            adsbhub.STOP.clear()
            os.environ.pop("ADSBHUB_INBOUND_ENABLED", None)

    def test_shortened_sbs_message_without_trailing_fields_is_accepted(self):
        adsbhub.INBOUND_TARGETS.clear()
        self.assertTrue(adsbhub.ingest_sbs_line("MSG,1,1,1,ABC123,1,d,t,d,t,BAI123"))
        self.assertEqual(adsbhub.INBOUND_TARGETS["abc123"]["flight"], "BAI123")
        adsbhub.INBOUND_TARGETS.clear()

    def test_adsbhub_sharing_defaults_to_two_way_with_outbound_only_opt_out(self):
        os.environ["SERVICE_ENABLE_ADSBHUB"] = "true"
        os.environ["ADSBHUB_INBOUND_ENABLED"] = "false"
        try:
            self.assertTrue(adsbhub.inbound_enabled())
            os.environ["ADSBHUB_OUTBOUND_ONLY"] = "true"
            self.assertFalse(adsbhub.inbound_enabled())
        finally:
            os.environ.pop("SERVICE_ENABLE_ADSBHUB", None)
            os.environ.pop("ADSBHUB_INBOUND_ENABLED", None)
            os.environ.pop("ADSBHUB_OUTBOUND_ONLY", None)

    def test_status_exposes_targets_without_any_station_key(self):
        old_file = adsbhub.STATUS_FILE
        with tempfile.TemporaryDirectory() as tmp:
            adsbhub.STATUS_FILE = Path(tmp) / "adsbhub.json"
            adsbhub.INBOUND_TARGETS.clear()
            adsbhub.ingest_sbs_line("MSG,3,1,1,ABC123,1,d,t,d,t,BAI1,9000,210,180,37.8,14.9,0,7000,0,0,0,0")
            os.environ["ADSBHUB_CKEY"] = "do-not-publish-this"
            try:
                adsbhub.write_status()
                payload = json.loads(adsbhub.STATUS_FILE.read_text())
                self.assertEqual(payload["inbound_target_count"], 1)
                self.assertEqual(payload["inbound_targets"][0]["source"], "ADSBHub")
                self.assertNotIn("do-not-publish-this", json.dumps(payload))
            finally:
                adsbhub.STATUS_FILE = old_file
                adsbhub.INBOUND_TARGETS.clear()
                os.environ.pop("ADSBHUB_CKEY", None)

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
                self.assertEqual(adsbhub.public_addresses(), ("203.0.113.9", "2001:db8::9", "203.0.113.9"))
            self.assertEqual(fetch.call_args_list[0].args[0], "https://www.adsbhub.org/getmyip.php")
        finally:
            os.environ.pop("ADSBHUB_PUBLIC_HOST", None)

    def test_manual_public_address_is_compared_with_detected_ip(self):
        os.environ["ADSBHUB_PUBLIC_IP_MODE"] = "manual"
        os.environ["ADSBHUB_PUBLIC_HOST"] = "198.51.100.44"
        try:
            with patch.object(adsbhub, "fetch_text", side_effect=["203.0.113.9", ""]):
                self.assertEqual(adsbhub.public_addresses(), ("198.51.100.44", "", "203.0.113.9"))
        finally:
            os.environ.pop("ADSBHUB_PUBLIC_IP_MODE", None)
            os.environ.pop("ADSBHUB_PUBLIC_HOST", None)


if __name__ == "__main__":
    unittest.main()
