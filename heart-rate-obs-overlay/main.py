#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Heart Rate OBS Overlay
=======================

GUI de escritorio que lee la frecuencia cardiaca en tiempo real desde un
dispositivo Bluetooth LE que expone el estandar Bluetooth Heart Rate
Service (0x180D) -- por ejemplo, un Apple Watch retransmitido por una app
de iPhone -- y la publica en un servidor web local para usarla como
overlay (Fuente de Navegador) en OBS Studio.

Repositorio / documentacion: ver README.md

Ejecucion:
    python main.py

Para generar un ejecutable .exe portable, ve la seccion "Compilar a .exe"
del README.md (usa PyInstaller).
"""

import queue
import sys
import threading
import time
import tkinter as tk
import webbrowser
from datetime import datetime
from tkinter import ttk, messagebox

try:
    import bleak  # noqa: F401
    BLEAK_AVAILABLE = True
except ImportError:
    BLEAK_AVAILABLE = False

import asyncio

from core.state import SharedState
from core.http_server import create_server
from core import ble_reader

APP_TITLE = "Heart Rate OBS Overlay"
APP_VERSION = "1.0.0"
GITHUB_URL = "https://github.com/YOUR_USERNAME/heart-rate-obs-overlay"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


class HeartRateOverlayApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_TITLE} v{APP_VERSION}")
        self.geometry("560x620")
        self.minsize(520, 560)

        self.state_obj = SharedState()
        self.log_queue: "queue.Queue[str]" = queue.Queue()
        self.stop_event = threading.Event()

        self.http_server = None
        self.http_thread = None
        self.ble_thread = None
        self.running = False

        self._build_menu()
        self._build_widgets()
        self._poll_ui()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        if not BLEAK_AVAILABLE:
            self._log(
                "ERROR: falta el paquete 'bleak'. Instalalo con: pip install bleak"
            )
            messagebox.showerror(
                APP_TITLE,
                "Falta el paquete 'bleak'.\n\nInstalalo con:\n    pip install bleak\n\n"
                "y vuelve a abrir el programa.",
            )

    # ------------------------------------------------------------------
    # Construccion de la interfaz
    # ------------------------------------------------------------------

    def _build_menu(self):
        menubar = tk.Menu(self)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Salir", command=self._on_close)
        menubar.add_cascade(label="Archivo", menu=file_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(
            label="Repositorio en GitHub",
            command=lambda: webbrowser.open(GITHUB_URL),
        )
        help_menu.add_command(label="Acerca de", command=self._show_about)
        menubar.add_cascade(label="Ayuda", menu=help_menu)

        self.config(menu=menubar)

    def _build_widgets(self):
        pad = {"padx": 10, "pady": 6}

        # ---- Estado ----------------------------------------------------
        status_frame = ttk.LabelFrame(self, text="Estado")
        status_frame.pack(fill="x", **pad)

        self.bpm_var = tk.StringVar(value="--")
        self.status_var = tk.StringVar(value="Detenido")
        self.device_var = tk.StringVar(value="Ningun dispositivo conectado")

        bpm_label = ttk.Label(status_frame, textvariable=self.bpm_var, font=("Segoe UI", 42, "bold"))
        bpm_label.grid(row=0, column=0, rowspan=2, padx=(14, 20), pady=10, sticky="w")

        ttk.Label(status_frame, textvariable=self.status_var, font=("Segoe UI", 11, "bold")).grid(
            row=0, column=1, sticky="w", pady=(10, 0)
        )
        ttk.Label(status_frame, textvariable=self.device_var, font=("Segoe UI", 9)).grid(
            row=1, column=1, sticky="w", pady=(0, 10)
        )

        # ---- Controles de conexion --------------------------------------
        conn_frame = ttk.LabelFrame(self, text="Servidor")
        conn_frame.pack(fill="x", **pad)

        ttk.Label(conn_frame, text="Host:").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        self.host_var = tk.StringVar(value=DEFAULT_HOST)
        ttk.Entry(conn_frame, textvariable=self.host_var, width=14).grid(row=0, column=1, sticky="w", pady=6)

        ttk.Label(conn_frame, text="Puerto:").grid(row=0, column=2, sticky="w", padx=8, pady=6)
        self.port_var = tk.StringVar(value=str(DEFAULT_PORT))
        ttk.Entry(conn_frame, textvariable=self.port_var, width=8).grid(row=0, column=3, sticky="w", pady=6)

        btn_frame = ttk.Frame(conn_frame)
        btn_frame.grid(row=1, column=0, columnspan=4, sticky="w", padx=8, pady=(0, 8))

        self.start_btn = ttk.Button(btn_frame, text="Iniciar", command=self._start)
        self.start_btn.pack(side="left")
        self.stop_btn = ttk.Button(btn_frame, text="Detener", command=self._stop, state="disabled")
        self.stop_btn.pack(side="left", padx=(8, 0))

        # ---- Enlace del overlay -----------------------------------------
        link_frame = ttk.LabelFrame(self, text="Enlace del overlay (para OBS Browser Source)")
        link_frame.pack(fill="x", **pad)

        opts = ttk.Frame(link_frame)
        opts.pack(fill="x", padx=8, pady=(8, 4))

        self.stats_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            opts, text="Mostrar estadisticas por defecto", variable=self.stats_var,
            command=self._update_link,
        ).pack(side="left")

        ttk.Label(opts, text="   Fondo:").pack(side="left")
        self.bg_var = tk.StringVar(value="transparent")
        bg_combo = ttk.Combobox(
            opts, textvariable=self.bg_var, state="readonly", width=14,
            values=["transparent", "black", "chroma"],
        )
        bg_combo.pack(side="left", padx=(4, 0))
        bg_combo.bind("<<ComboboxSelected>>", lambda e: self._update_link())

        link_row = ttk.Frame(link_frame)
        link_row.pack(fill="x", padx=8, pady=(4, 8))

        self.link_var = tk.StringVar(value="")
        link_entry = ttk.Entry(link_row, textvariable=self.link_var, state="readonly")
        link_entry.pack(side="left", fill="x", expand=True)

        ttk.Button(link_row, text="Copiar", command=self._copy_link).pack(side="left", padx=(6, 0))
        ttk.Button(link_row, text="Abrir", command=self._open_link).pack(side="left", padx=(6, 0))

        # ---- Log ----------------------------------------------------------
        log_frame = ttk.LabelFrame(self, text="Registro")
        log_frame.pack(fill="both", expand=True, **pad)

        text_container = ttk.Frame(log_frame)
        text_container.pack(fill="both", expand=True, padx=8, pady=8)

        self.log_text = tk.Text(text_container, height=12, wrap="word", state="disabled",
                                 bg="#111111", fg="#dddddd", insertbackground="#dddddd")
        self.log_text.pack(side="left", fill="both", expand=True)

        scroll = ttk.Scrollbar(text_container, command=self.log_text.yview)
        scroll.pack(side="right", fill="y")
        self.log_text.config(yscrollcommand=scroll.set)

        self._update_link()

    def _show_about(self):
        messagebox.showinfo(
            APP_TITLE,
            f"{APP_TITLE} v{APP_VERSION}\n\n"
            "Lee la frecuencia cardiaca de un Apple Watch (u otro sensor BLE "
            "compatible con el Bluetooth Heart Rate Service) y la publica "
            "como overlay para OBS Studio.\n\n"
            f"Codigo abierto en:\n{GITHUB_URL}",
        )

    # ------------------------------------------------------------------
    # Logica de arranque / apagado
    # ------------------------------------------------------------------

    def _log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_queue.put(f"[{ts}] {msg}")

    def _start(self):
        if self.running:
            return
        if not BLEAK_AVAILABLE:
            messagebox.showerror(APP_TITLE, "Falta el paquete 'bleak'. Instalalo con: pip install bleak")
            return

        host = self.host_var.get().strip() or DEFAULT_HOST
        try:
            port = int(self.port_var.get().strip())
        except ValueError:
            messagebox.showerror(APP_TITLE, "El puerto debe ser un numero valido.")
            return

        self.stop_event.clear()

        try:
            self.http_server = create_server(host, port, self.state_obj)
        except OSError as e:
            messagebox.showerror(APP_TITLE, f"No se pudo abrir el puerto {port} en {host}:\n{e}")
            return

        self.http_thread = threading.Thread(target=self.http_server.serve_forever, daemon=True)
        self.http_thread.start()
        self._log(f"Servidor web iniciado en http://{host}:{port}/")

        self.ble_thread = threading.Thread(target=self._run_ble_loop, daemon=True)
        self.ble_thread.start()

        self.running = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.status_var.set("Buscando dispositivo...")
        self._update_link()

    def _run_ble_loop(self):
        try:
            asyncio.run(ble_reader.ble_main_loop(self.state_obj, self.stop_event, self._log))
        except Exception as e:
            self._log(f"ERROR fatal en el hilo BLE: {e}")

    def _stop(self):
        if not self.running:
            return
        self.stop_btn.config(state="disabled")
        self._log("Deteniendo...")
        threading.Thread(target=self._stop_worker, daemon=True).start()

    def _stop_worker(self):
        self.stop_event.set()

        if self.ble_thread is not None:
            self.ble_thread.join(timeout=10)

        if self.http_server is not None:
            self.http_server.shutdown()
            self.http_server.server_close()
        if self.http_thread is not None:
            self.http_thread.join(timeout=5)

        self.state_obj.reset_device()
        self._log("Servidor web detenido.")
        self.after(0, self._on_stopped)

    def _on_stopped(self):
        self.running = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.status_var.set("Detenido")
        self.device_var.set("Ningun dispositivo conectado")
        self.bpm_var.set("--")

    def _on_close(self):
        if self.running:
            self.stop_event.set()
            if self.http_server is not None:
                try:
                    self.http_server.shutdown()
                except Exception:
                    pass
        self.destroy()
        sys.exit(0)

    # ------------------------------------------------------------------
    # Enlace del overlay
    # ------------------------------------------------------------------

    def _current_link(self) -> str:
        host = self.host_var.get().strip() or DEFAULT_HOST
        port = self.port_var.get().strip() or str(DEFAULT_PORT)
        params = []
        if self.stats_var.get():
            params.append("stats=1")
        bg = self.bg_var.get()
        if bg and bg != "transparent":
            params.append(f"bg={bg}")
        query = ("?" + "&".join(params)) if params else ""
        return f"http://{host}:{port}/{query}"

    def _update_link(self):
        self.link_var.set(self._current_link())

    def _copy_link(self):
        self.clipboard_clear()
        self.clipboard_append(self.link_var.get())
        self._log("Enlace copiado al portapapeles.")

    def _open_link(self):
        webbrowser.open(self.link_var.get())

    # ------------------------------------------------------------------
    # Actualizacion periodica de la UI
    # ------------------------------------------------------------------

    def _poll_ui(self):
        # Vaciar cola de logs
        try:
            while True:
                line = self.log_queue.get_nowait()
                self.log_text.config(state="normal")
                self.log_text.insert("end", line + "\n")
                self.log_text.see("end")
                self.log_text.config(state="disabled")
        except queue.Empty:
            pass

        # Refrescar estado / BPM
        if self.running:
            snap = self.state_obj.snapshot()
            if snap["live"] and snap["bpm"] > 0:
                self.bpm_var.set(str(snap["bpm"]))
            else:
                self.bpm_var.set("--")

            if snap["connected"]:
                self.status_var.set("Conectado")
                self.device_var.set(f"{snap['device']}  ({snap['address']})")
            elif snap["scanning"]:
                self.status_var.set("Buscando dispositivo...")
                self.device_var.set("Ningun dispositivo conectado")
            else:
                self.status_var.set("Esperando...")
                self.device_var.set("Ningun dispositivo conectado")

        self.after(500, self._poll_ui)


def main():
    app = HeartRateOverlayApp()
    app.mainloop()


if __name__ == "__main__":
    main()
