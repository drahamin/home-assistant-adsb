#!/usr/bin/env python3
"""Reliable two-way ADSBHub bridge with dynamic-IP and safe status reporting."""

from __future__ import annotations

import hashlib
import json
import os
import signal
import socket
import threading
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


STATUS_FILE = Path(os.getenv("ADSBHUB_STATUS_FILE", "/run/baiamonte/adsbhub.json"))
STOP = threading.Event()
LOCK = threading.Lock()
CLIENTS: set[socket.socket] = set()
STATUS: dict[str, object] = {
    "outbound_connected": False,
    "inbound_connected": False,
    "dynamic_update_ok": False,
    "public_ipv4": "",
    "public_ipv6": "",
    "outbound_bytes": 0,
    "inbound_bytes": 0,
    "inbound_clients": 0,
    "outbound_error": "",
    "inbound_error": "",
    "public_address_error": "",
    "last_update": 0,
    "outbound_connected_at": 0,
    "inbound_connected_at": 0,
    "outbound_last_data_at": 0,
    "inbound_last_data_at": 0,
    "outbound_reconnects": 0,
    "inbound_reconnects": 0,
}


def enabled(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def integer(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def set_status(**values: object) -> None:
    with LOCK:
        STATUS.update(values)


def add_bytes(name: str, count: int) -> None:
    with LOCK:
        STATUS[name] = int(STATUS.get(name, 0)) + count


def write_status() -> None:
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOCK:
        payload = {
            **STATUS,
            "generated_at": time.time(),
            "enabled": enabled("SERVICE_ENABLE_ADSBHUB"),
            "inbound_enabled": enabled("ADSBHUB_INBOUND_ENABLED"),
            "dynamic_update_enabled": enabled("ADSBHUB_DYNAMIC_IP_UPDATE", True),
            "key_configured": bool(os.getenv("ADSBHUB_CKEY", "").strip()),
            "local_inbound_port": integer("ADSBHUB_LOCAL_INBOUND_PORT", 5002),
        }
    temporary = STATUS_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    os.replace(temporary, STATUS_FILE)


def fetch_text(url: str, timeout: float = 10) -> str:
    request = Request(url, headers={"User-Agent": "Tenuta-Baiamonte-ADSB/2.2"})
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8").strip()


def public_addresses() -> tuple[str, str]:
    configured = os.getenv("ADSBHUB_PUBLIC_HOST", "auto").strip()
    ipv4 = "" if configured.lower() in {"", "auto"} else configured
    ipv6 = ""
    if not ipv4:
        try:
            ipv4 = fetch_text("https://ip4.adsbhub.org/getmyip.php")
        except OSError:
            pass
    try:
        ipv6 = fetch_text("https://ip6.adsbhub.org/getmyip.php")
    except OSError:
        pass
    return ipv4, ipv6


def update_dynamic_ip(ckey: str, ipv4: str, ipv6: str) -> bool:
    """Apply ADSBHub's published challenge-response dynamic-IP protocol."""
    challenge = fetch_text("https://www.adsbhub.org/key.php")
    if len(challenge) < 2:
        raise ValueError("ADSBHub returned an invalid challenge")
    digest = hashlib.md5((ckey + challenge[:-1]).encode()).hexdigest() + challenge[-1]
    query = urlencode({"sessid": digest, "myip": ipv4, "myip6": ipv6})
    response = fetch_text(f"https://www.adsbhub.org/updateip.php?{query}")
    return response.strip() == digest


def configure_stream_socket(stream: socket.socket) -> None:
    """Keep an ADSBHub stream open through quiet traffic periods and detect dead peers."""
    stream.settimeout(None)
    stream.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    for option, value in (
        (getattr(socket, "TCP_KEEPIDLE", None), 60),
        (getattr(socket, "TCP_KEEPINTVL", None), 20),
        (getattr(socket, "TCP_KEEPCNT", None), 3),
    ):
        if option is not None:
            try:
                stream.setsockopt(socket.IPPROTO_TCP, option, value)
            except OSError:
                pass


def address_worker() -> None:
    while not STOP.is_set():
        try:
            ipv4, ipv6 = public_addresses()
            values: dict[str, object] = {"public_ipv4": ipv4, "public_ipv6": ipv6, "public_address_error": ""}
            ckey = os.getenv("ADSBHUB_CKEY", "").strip()
            if enabled("ADSBHUB_DYNAMIC_IP_UPDATE", True) and ckey and (ipv4 or ipv6):
                values["dynamic_update_ok"] = update_dynamic_ip(ckey, ipv4, ipv6)
                values["last_update"] = time.time()
            set_status(**values)
        except (OSError, ValueError) as error:
            set_status(dynamic_update_ok=False, public_address_error=str(error))
        STOP.wait(max(60, integer("ADSBHUB_IP_UPDATE_INTERVAL", 300)))


def outbound_worker() -> None:
    source_host = os.getenv("ADSBHUB_SOURCE_HOST", "127.0.0.1").strip() or "127.0.0.1"
    source_port = integer("ADSBHUB_SOURCE_PORT", 30002)
    remote_host = os.getenv("ADSBHUB_OUTBOUND_HOST", "data.adsbhub.org").strip() or "data.adsbhub.org"
    remote_port = integer("ADSBHUB_OUTBOUND_PORT", 5001)
    while not STOP.is_set():
        if not enabled("SERVICE_ENABLE_ADSBHUB"):
            STOP.wait(5)
            continue
        try:
            with socket.create_connection((source_host, source_port), timeout=15) as source, socket.create_connection((remote_host, remote_port), timeout=15) as remote:
                configure_stream_socket(source)
                configure_stream_socket(remote)
                set_status(outbound_connected=True, outbound_connected_at=time.time(), outbound_error="")
                while not STOP.is_set():
                    chunk = source.recv(65536)
                    if not chunk:
                        break
                    remote.sendall(chunk)
                    add_bytes("outbound_bytes", len(chunk))
                    set_status(outbound_last_data_at=time.time())
        except OSError as error:
            set_status(outbound_error=str(error))
        finally:
            with LOCK:
                STATUS["outbound_connected"] = False
                STATUS["outbound_reconnects"] = int(STATUS.get("outbound_reconnects", 0)) + 1
        STOP.wait(5)


def accept_clients(listener: socket.socket) -> None:
    listener.settimeout(2)
    while not STOP.is_set():
        try:
            client, _ = listener.accept()
            client.settimeout(2)
            with LOCK:
                CLIENTS.add(client)
                STATUS["inbound_clients"] = len(CLIENTS)
        except socket.timeout:
            continue
        except OSError:
            break


def broadcast(chunk: bytes) -> None:
    failed = []
    with LOCK:
        clients = list(CLIENTS)
    for client in clients:
        try:
            client.sendall(chunk)
        except OSError:
            failed.append(client)
    if failed:
        with LOCK:
            for client in failed:
                CLIENTS.discard(client)
                try:
                    client.close()
                except OSError:
                    pass
            STATUS["inbound_clients"] = len(CLIENTS)


def inbound_worker() -> None:
    local_port = integer("ADSBHUB_LOCAL_INBOUND_PORT", 5002)
    remote_host = os.getenv("ADSBHUB_INBOUND_HOST", "data.adsbhub.org").strip() or "data.adsbhub.org"
    remote_port = integer("ADSBHUB_INBOUND_PORT", 5002)
    listener: socket.socket | None = None
    try:
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("0.0.0.0", local_port))
        listener.listen(8)
        threading.Thread(target=accept_clients, args=(listener,), daemon=True).start()
        while not STOP.is_set():
            if not enabled("ADSBHUB_INBOUND_ENABLED"):
                STOP.wait(5)
                continue
            try:
                with socket.create_connection((remote_host, remote_port), timeout=15) as remote:
                    configure_stream_socket(remote)
                    set_status(inbound_connected=True, inbound_connected_at=time.time(), inbound_error="")
                    while not STOP.is_set():
                        chunk = remote.recv(65536)
                        if not chunk:
                            break
                        add_bytes("inbound_bytes", len(chunk))
                        set_status(inbound_last_data_at=time.time())
                        broadcast(chunk)
            except OSError as error:
                set_status(inbound_error=str(error))
            finally:
                with LOCK:
                    STATUS["inbound_connected"] = False
                    STATUS["inbound_reconnects"] = int(STATUS.get("inbound_reconnects", 0)) + 1
            STOP.wait(5)
    except OSError as error:
        set_status(inbound_error=f"Local port {local_port}: {error}")
    finally:
        if listener:
            listener.close()


def stop(*_: object) -> None:
    STOP.set()


def main() -> None:
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    workers = [
        threading.Thread(target=address_worker, daemon=True),
        threading.Thread(target=outbound_worker, daemon=True),
        threading.Thread(target=inbound_worker, daemon=True),
    ]
    for worker in workers:
        worker.start()
    while not STOP.wait(2):
        write_status()
    write_status()


if __name__ == "__main__":
    main()
