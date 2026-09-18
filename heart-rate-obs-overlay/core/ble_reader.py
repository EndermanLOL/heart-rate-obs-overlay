"""
ble_reader.py

Logica de escaneo, conexion y notificaciones BLE para el estandar
Bluetooth Heart Rate Service (0x180D) / Heart Rate Measurement (0x2A37).

Diseñado para poder arrancarse y detenerse limpiamente desde una GUI:
    ble_main_loop(state, stop_event, log) corre hasta que stop_event.set().
"""

import asyncio

try:
    from bleak import BleakScanner, BleakClient
except ImportError:  # pragma: no cover - se valida tambien en main.py
    BleakScanner = None
    BleakClient = None

HEART_RATE_SERVICE_UUID = "0000180d-0000-1000-8000-00805f9b34fb"
HEART_RATE_MEASUREMENT_UUID = "00002a37-0000-1000-8000-00805f9b34fb"

SCAN_TIMEOUT_SECONDS = 8.0        # tiempo de cada escaneo BLE
RECONNECT_DELAY_SECONDS = 5.0     # espera antes de reintentar tras perder conexion
STOP_POLL_INTERVAL = 0.5          # granularidad para revisar si se pidio detener


class StopRequested(Exception):
    """Señal interna para cortar la sesion BLE cuando el usuario detiene el programa."""


def parse_heart_rate_measurement(data: bytearray) -> int:
    """
    Formato segun especificacion Bluetooth SIG "Heart Rate Measurement":

    Byte 0: Flags
        - Bit 0: 0 -> BPM en UINT8 (byte 1)
                 1 -> BPM en UINT16 little-endian (bytes 1-2)
        - Otros bits: sensor contact status, energy expended, RR-interval, etc.
          (no son necesarios para obtener el BPM).
    """
    if not data or len(data) < 2:
        raise ValueError(f"Paquete Heart Rate Measurement demasiado corto: {data!r}")

    flags = data[0]
    hr_format_uint16 = flags & 0x01  # bit 0

    if hr_format_uint16:
        if len(data) < 3:
            raise ValueError(f"Se esperaba UINT16 pero el paquete es corto: {data!r}")
        bpm = int.from_bytes(data[1:3], byteorder="little", signed=False)
    else:
        bpm = data[1]

    return bpm


async def _wait_or_stop(coro_event: asyncio.Event, stop_event, poll: float = STOP_POLL_INTERVAL):
    """Espera un asyncio.Event revisando periodicamente un threading.Event externo."""
    while True:
        if stop_event.is_set():
            raise StopRequested()
        try:
            await asyncio.wait_for(coro_event.wait(), timeout=poll)
            return
        except asyncio.TimeoutError:
            continue


async def find_heart_rate_device(state, stop_event, log, timeout: float = SCAN_TIMEOUT_SECONDS):
    """
    Escanea dispositivos BLE cercanos y devuelve el primer BLEDevice que
    anuncie el Heart Rate Service (0x180D). Compatible con distintas
    versiones de bleak (usa return_adv=True cuando esta disponible).
    """
    state.set_scanning(True)
    log(f"Buscando dispositivos Bluetooth LE (timeout {timeout:.0f}s)...")

    try:
        try:
            discovered = await BleakScanner.discover(timeout=timeout, return_adv=True)
            for address, (device, adv_data) in discovered.items():
                if stop_event.is_set():
                    raise StopRequested()
                service_uuids = [u.lower() for u in (adv_data.service_uuids or [])]
                if HEART_RATE_SERVICE_UUID in service_uuids:
                    name = device.name or adv_data.local_name or "Dispositivo desconocido"
                    log(f"Encontrado: {name} [{device.address}] anuncia Heart Rate Service.")
                    return device, name
        except TypeError:
            # Fallback para versiones antiguas de bleak sin return_adv
            devices = await BleakScanner.discover(timeout=timeout)
            for device in devices:
                if stop_event.is_set():
                    raise StopRequested()
                uuids = [u.lower() for u in (device.metadata.get("uuids") or [])]
                if HEART_RATE_SERVICE_UUID in uuids:
                    name = device.name or "Dispositivo desconocido"
                    log(f"Encontrado: {name} [{device.address}] anuncia Heart Rate Service.")
                    return device, name
    finally:
        state.set_scanning(False)

    return None, None


def _make_notification_handler(state, log):
    def handler(_sender, data: bytearray):
        try:
            bpm = parse_heart_rate_measurement(data)
        except ValueError as e:
            log(f"AVISO: no se pudo interpretar el paquete de frecuencia cardiaca: {e}")
            return
        state.set_bpm(bpm)

    return handler


async def run_ble_session(device, device_name: str, state, stop_event, log) -> bool:
    """
    Se conecta al dispositivo, se suscribe a las notificaciones de HR y
    permanece en el bucle hasta que se pierde la conexion o se pide detener.
    """
    disconnected_event = asyncio.Event()

    def on_disconnect(_client):
        log(f"Conexion perdida con {device_name}.")
        disconnected_event.set()

    connected_ok = False

    try:
        async with BleakClient(device, disconnected_callback=on_disconnect) as client:
            if not client.is_connected:
                log(f"No se pudo establecer conexion con {device_name}.")
                return False

            log(f"Conectado a {device_name} ({device.address}).")
            state.set_connected(True, device_name, device.address)
            connected_ok = True

            services = client.services
            hr_char = services.get_characteristic(HEART_RATE_MEASUREMENT_UUID)
            if hr_char is None:
                log("ERROR: el dispositivo no expone la caracteristica Heart Rate Measurement (0x2A37).")
                return connected_ok

            handler = _make_notification_handler(state, log)
            await client.start_notify(HEART_RATE_MEASUREMENT_UUID, handler)
            log("Suscrito a notificaciones de frecuencia cardiaca. Esperando datos...")

            await _wait_or_stop(disconnected_event, stop_event)

    except StopRequested:
        log("Deteniendo sesion BLE por peticion del usuario...")
    except Exception as e:
        log(f"ERROR durante la sesion BLE: {e}")
    finally:
        state.set_connected(False)

    return connected_ok


async def ble_main_loop(state, stop_event, log):
    """
    Bucle principal: busca el dispositivo, se conecta, y si se pierde la
    conexion (o falla el escaneo), reintenta hasta que stop_event.set().
    """
    log("=== Iniciando lector de frecuencia cardiaca Bluetooth LE ===")
    try:
        while not stop_event.is_set():
            device, device_name = await find_heart_rate_device(state, stop_event, log)

            if stop_event.is_set():
                break

            if device is None:
                log(
                    "No se encontro ningun dispositivo con Heart Rate Service. "
                    f"Reintentando en {RECONNECT_DELAY_SECONDS:.0f}s... "
                    "(verifica que la app de transmision este activa en el iPhone)"
                )
                await _sleep_or_stop(RECONNECT_DELAY_SECONDS, stop_event)
                continue

            await run_ble_session(device, device_name, state, stop_event, log)

            if stop_event.is_set():
                break

            log(f"Reintentando conexion en {RECONNECT_DELAY_SECONDS:.0f} segundos...")
            await _sleep_or_stop(RECONNECT_DELAY_SECONDS, stop_event)
    except StopRequested:
        pass
    finally:
        state.reset_device()
        log("Lector de frecuencia cardiaca detenido.")


async def _sleep_or_stop(seconds: float, stop_event, poll: float = STOP_POLL_INTERVAL):
    elapsed = 0.0
    while elapsed < seconds:
        if stop_event.is_set():
            raise StopRequested()
        await asyncio.sleep(poll)
        elapsed += poll
