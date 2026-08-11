#!/usr/bin/env python3
"""Run RTLSDR-Airband and optionally reset only its selected USB receiver."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import threading
import time
from pathlib import Path

from usb_recovery import reset_radio


STOP = threading.Event()
CHILD: subprocess.Popen | None = None
STATUS_FILE = Path("/run/baiamonte/vhf-recovery.json")


def truthy(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def integer(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def write_status(**values: object) -> None:
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = STATUS_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps({**values, "updated_at": time.time()}, separators=(",", ":")), encoding="utf-8")
    os.replace(temporary, STATUS_FILE)


def reset_selected(reason: str, attempt: int) -> bool:
    serial = os.getenv("VHF_DEVICE_SERIAL", "").strip()
    index = integer("VHF_DEVICE", 1)
    try:
        chosen = reset_radio(serial, index)
        print(f"Baiamonte VHF reset RTL-SDR {chosen} ({reason}, attempt {attempt})", flush=True)
        write_status(state="reset", serial=chosen, reason=reason, attempt=attempt, error="")
        return True
    except OSError as error:
        print(f"Baiamonte VHF USB reset unavailable: {error}", flush=True)
        write_status(state="reset_failed", serial=serial, reason=reason, attempt=attempt, error=str(error))
        return False


def stop(*_: object) -> None:
    STOP.set()
    if CHILD and CHILD.poll() is None:
        CHILD.terminate()


def main() -> int:
    global CHILD
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    max_resets = max(0, min(5, integer("VHF_USB_RESET_ATTEMPTS", 2)))
    recovery = truthy("VHF_USB_RECOVERY", True)
    resets_used = 0
    if truthy("VHF_USB_RESET_ON_START", False):
        reset_selected("manual start reset", 1)
        STOP.wait(3)
    while not STOP.is_set():
        started = time.monotonic()
        write_status(state="starting", serial=os.getenv("VHF_DEVICE_SERIAL", "").strip(), attempt=resets_used, error="")
        CHILD = subprocess.Popen(["rtl_airband", "-F", "-e", "-c", "/etc/rtl_airband.conf"])
        result = CHILD.wait()
        CHILD = None
        runtime = time.monotonic() - started
        if STOP.is_set():
            break
        if runtime >= 300:
            resets_used = 0
        if recovery and resets_used < max_resets:
            resets_used += 1
            reset_selected(f"receiver exited with status {result}", resets_used)
            STOP.wait(3)
        else:
            write_status(state="waiting", serial=os.getenv("VHF_DEVICE_SERIAL", "").strip(), attempt=resets_used, error=f"rtl_airband exited with status {result}")
            STOP.wait(30)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
