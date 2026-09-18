"""
state.py

Estado compartido (thread-safe) entre el hilo BLE (asyncio), el hilo del
servidor HTTP y el hilo de la GUI (Tkinter).
"""

import threading
import time

NO_DATA_TIMEOUT_SECONDS = 20.0  # si no llegan datos en este tiempo, se considera "sin senal"


class SharedState:
    def __init__(self):
        self._lock = threading.Lock()
        self._bpm = 0
        self._connected = False
        self._scanning = False
        self._device_name = ""
        self._device_address = ""
        self._last_update_ts = 0.0
        self._last_log = ""

    # ---- escritura (hilo BLE) ----------------------------------------

    def set_bpm(self, bpm: int):
        with self._lock:
            self._bpm = bpm
            self._last_update_ts = time.time()

    def set_scanning(self, scanning: bool):
        with self._lock:
            self._scanning = scanning

    def set_connected(self, connected: bool, device_name: str = "", device_address: str = ""):
        with self._lock:
            self._connected = connected
            if device_name:
                self._device_name = device_name
            if device_address:
                self._device_address = device_address
            if not connected:
                self._bpm = 0

    def reset_device(self):
        with self._lock:
            self._connected = False
            self._scanning = False
            self._bpm = 0
            self._device_name = ""
            self._device_address = ""

    # ---- lectura (hilo HTTP / hilo GUI) -------------------------------

    def snapshot(self) -> dict:
        with self._lock:
            age = time.time() - self._last_update_ts if self._last_update_ts else None
            live = self._connected and age is not None and age < NO_DATA_TIMEOUT_SECONDS
            return {
                "bpm": self._bpm,
                "connected": self._connected,
                "scanning": self._scanning,
                "live": live,
                "device": self._device_name,
                "address": self._device_address,
            }
