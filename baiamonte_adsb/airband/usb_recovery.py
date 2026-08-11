#!/usr/bin/env python3
"""Locate and reset one RTL-SDR without disturbing an identical second radio."""

from __future__ import annotations

import ctypes
import ctypes.util
import fcntl
import os
from pathlib import Path


USBDEVFS_RESET = 0x5514


def rtlsdr_serials() -> list[str]:
    library_name = ctypes.util.find_library("rtlsdr") or "librtlsdr.so.0"
    library = ctypes.CDLL(library_name)
    library.rtlsdr_get_device_count.restype = ctypes.c_uint32
    library.rtlsdr_get_device_usb_strings.argtypes = [
        ctypes.c_uint32,
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.c_char_p,
    ]
    serials: list[str] = []
    for index in range(int(library.rtlsdr_get_device_count())):
        vendor = ctypes.create_string_buffer(256)
        product = ctypes.create_string_buffer(256)
        serial = ctypes.create_string_buffer(256)
        if library.rtlsdr_get_device_usb_strings(index, vendor, product, serial) == 0:
            serials.append(serial.value.decode("utf-8", errors="replace"))
    return serials


def selected_serial(serial: str, index: int) -> str:
    serial = serial.strip()
    serials = rtlsdr_serials()
    if serial:
        matches = [value for value in serials if value == serial]
        if not matches:
            raise OSError(f"RTL-SDR serial {serial} was not found")
        if len(matches) > 1:
            raise OSError(f"RTL-SDR serial {serial} is duplicated; assign unique serials with rtl_eeprom")
        return serial
    if index < 0 or index >= len(serials):
        raise OSError(f"RTL-SDR index {index} was not found")
    if serials.count(serials[index]) > 1:
        raise OSError("Selected RTL-SDR has a duplicated serial; configure a unique VHF serial")
    return serials[index]


def usb_device_for_serial(serial: str, sysfs_root: Path = Path("/sys/bus/usb/devices")) -> Path:
    for candidate in sysfs_root.iterdir():
        try:
            if (candidate / "serial").read_text(encoding="utf-8").strip() != serial:
                continue
            bus = int((candidate / "busnum").read_text(encoding="utf-8").strip())
            device = int((candidate / "devnum").read_text(encoding="utf-8").strip())
            return Path(f"/dev/bus/usb/{bus:03d}/{device:03d}")
        except (OSError, ValueError):
            continue
    raise OSError(f"USB device for RTL-SDR serial {serial} was not found")


def reset_radio(serial: str, index: int) -> str:
    chosen = selected_serial(serial, index)
    device = usb_device_for_serial(chosen)
    descriptor = os.open(device, os.O_WRONLY)
    try:
        fcntl.ioctl(descriptor, USBDEVFS_RESET, 0)
    finally:
        os.close(descriptor)
    return chosen
