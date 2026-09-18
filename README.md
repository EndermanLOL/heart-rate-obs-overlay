# Heart Rate OBS Overlay ❤️

Muestra tu frecuencia cardiaca en vivo (Apple Watch u otro sensor Bluetooth LE
compatible) como overlay para **OBS Studio**, con una interfaz gráfica de
escritorio para configurarlo sin tocar la terminal.

```
Apple Watch → app de iPhone que retransmite por BLE → este programa (GUI) → OBS Browser Source
```

![status](https://img.shields.io/badge/estado-open--source-brightgreen)
![python](https://img.shields.io/badge/python-3.9%2B-blue)
![platform](https://img.shields.io/badge/plataforma-Windows-lightgrey)
![license](https://img.shields.io/badge/licencia-MIT-yellow)

## ✨ Características

- **GUI de escritorio** (Tkinter, sin dependencias extra): botón de
  Iniciar/Detener, estado de conexión, BPM en vivo y un log de eventos.
- **Overlay web listo para OBS** con:
  - Corazón animado cuyo latido sigue el BPM real (velocidad e intensidad).
  - Tres modos de fondo intercambiables con un clic: **transparente**
    (recomendado, OBS Browser Source soporta canal alfa nativo), **negro** o
    **verde para chroma key** (por si lo necesitas en otro programa/hardware).
  - Panel de **estadísticas** opcional: hora en vivo, mínimo/promedio/máximo
    y una **gráfica de líneas** con el historial reciente de BPM.
- Reconexión automática si se pierde la señal Bluetooth.
- Sin servicios en la nube: todo corre localmente en tu máquina.
- Compilable como **un solo .exe portable** para Windows (no requiere que el
  usuario final tenga Python instalado).

## 📋 Requisitos

- Windows 10/11 con Bluetooth LE (para leer el sensor).
- Un iPhone (con iOS 26+) y, opcionalmente, un Apple Watch (watchOS 11+)
  con la app **[HeartRate Broadcaster](https://github.com/tankbottoms/HeartRateBroadcaster)**
  instalada, que retransmite el HR del Apple Watch (y opcionalmente de unos
  AirPods Pro 3) como un **Bluetooth LE Heart Rate Service (0x180D)**
  estándar — exactamente lo que este programa espera leer.

  Formas de instalarla en tu iPhone (elige una):

  | Ruta | Costo | Requiere | Notas |
  |------|-------|----------|-------|
  | [App Store](https://apps.apple.com/app/id6797897649) | US$4.99 (pago único) | Nada extra | La más simple, se actualiza sola. |
  | [TestFlight](https://testflight.apple.com/join/VUJCa5Gw) | Gratis | La app TestFlight | Beta pública, sin invitación. Cada build dura 90 días. |
  | [Sideload (.ipa)](https://github.com/tankbottoms/HeartRateBroadcaster/releases) | Gratis | Cuenta de Apple Developer de pago | Descarga el `.ipa` del release y firma con Xcode, Sideloadly o AltStore. |

  Después de instalarla, instala también la app del **Apple Watch** desde la
  app Watch del iPhone (el reloj es el sensor, ese paso no es opcional).

- Para correr desde el código fuente: Python 3.9+ y el paquete [`bleak`](https://github.com/hbldh/bleak).
- OBS Studio (o cualquier software que soporte una fuente de tipo *Browser Source*).

## 🚀 Instalación (desde el código fuente)

```bash
git clone https://github.com/YOUR_USERNAME/heart-rate-obs-overlay.git
cd heart-rate-obs-overlay
pip install -r requirements.txt
python main.py
```

Se abrirá la ventana de la aplicación.

## 🖥️ Uso

1. En tu iPhone, abre **HeartRate Broadcaster** (ver requisitos arriba) con
   tu Apple Watch emparejado y deja que empiece a transmitir el pulso.
2. Abre **Heart Rate OBS Overlay** en tu PC.
3. Ajusta **Host** (`127.0.0.1` por defecto) y **Puerto** (`8765` por
   defecto) si lo necesitas, y pulsa **Iniciar**.
4. El programa buscará automáticamente cualquier dispositivo BLE cercano que
   anuncie el Heart Rate Service y se conectará. Verás el estado y el BPM
   actualizarse en la ventana.
5. Copia el **enlace del overlay** que aparece en la app (botón *Copiar*) y
   pégalo en OBS como se explica abajo.

### Opciones del enlace del overlay

En la misma ventana puedes activar/desactivar estas opciones antes de copiar
el enlace (se agregan como parámetros en la URL):

| Opción                          | Parámetro en la URL | Efecto                                             |
|----------------------------------|----------------------|-----------------------------------------------------|
| Mostrar estadísticas por defecto | `?stats=1`           | Abre el panel de hora/BPM/gráfica ya desplegado.     |
| Fondo transparente (por defecto) | `?bg=transparent`    | Sin fondo, ideal para OBS Browser Source.            |
| Fondo negro                      | `?bg=black`          | Fondo sólido negro.                                  |
| Fondo verde (chroma key)         | `?bg=chroma`         | Fondo verde `#00ff00` para hacer chroma key.         |

También puedes cambiar el fondo y mostrar/ocultar estadísticas con los
botones que aparecen directamente en la esquina del overlay.

## 🎬 Configurar la fuente en OBS Studio

1. En OBS, en el panel **Fuentes**, haz clic en **+** → **Navegador**
   (*Browser Source*).
2. Dale un nombre (por ejemplo, "Heart Rate") y crea la fuente.
3. En **URL**, pega el enlace que copiaste desde la app (por ejemplo
   `http://127.0.0.1:8765/`).
4. Ajusta **Ancho** y **Alto** (por ejemplo `400x200`) según el tamaño que
   quieras que ocupe el overlay en tu escena.
5. Si dejaste el fondo en modo **transparente** (recomendado), no necesitas
   ningún filtro adicional: OBS soporta transparencia real en fuentes de
   navegador.
6. Si en cambio usas el modo **verde (chroma key)**, agrega el filtro
   **Chroma Key** a la fuente (clic derecho → *Filtros* → **+** → *Chroma
   Key*) y selecciona el color verde.
7. Mueve y redimensiona la fuente donde quieras dentro de tu escena.

> 💡 Tip: si cambias las opciones de la URL (estadísticas, fondo) después de
> haber creado la fuente en OBS, solo edita la URL de la fuente existente —
> no hace falta crear una nueva.

## 🛠️ Compilar a un .exe portable

Puedes generar un único ejecutable de Windows que no requiere Python
instalado, usando [PyInstaller](https://pyinstaller.org/).

### Opción A: en tu propia máquina Windows

```bat
build.bat
```

Esto crea un entorno virtual, instala las dependencias y genera
`dist\HeartRateOBSOverlay.exe`. Puedes distribuir ese único archivo.

> ⚠️ PyInstaller **no cruza plataformas**: para producir un `.exe` de
> Windows necesitas ejecutar el build en Windows (una VM o máquina física
> sirven). No es posible compilarlo desde Linux o macOS directamente.

### Opción B: automático con GitHub Actions (recomendado para releases)

Este repositorio incluye `.github/workflows/build-windows.yml`, que compila
el `.exe` en un runner de Windows de GitHub cada vez que subes un tag de
versión:

```bash
git tag v1.0.0
git push origin v1.0.0
```

El workflow sube el `.exe` como artefacto descargable y, si el push fue un
tag, lo adjunta automáticamente a un Release de GitHub. Así cualquiera puede
descargar el ejecutable sin instalar nada.

## 🧩 Estructura del proyecto

```
heart-rate-obs-overlay/
├── main.py                      # GUI (Tkinter) y orquestación de hilos
├── core/
│   ├── state.py                 # Estado compartido thread-safe (BPM, conexión)
│   ├── ble_reader.py            # Escaneo/conexión BLE y parseo del HR Measurement
│   ├── http_server.py           # Servidor HTTP local (overlay + /bpm)
│   └── overlay_html.py          # HTML/CSS/JS del overlay
├── requirements.txt
├── build.bat                    # Compilación local a .exe (Windows)
├── .github/workflows/
│   └── build-windows.yml        # Compilación automática en CI
├── LICENSE
└── README.md
```

## 🩺 Cómo funciona (para curiosos / contribuidores)

- El "servidor" es un `http.server.ThreadingHTTPServer` puro de la librería
  estándar de Python — sin frameworks externos.
- La lectura BLE usa [`bleak`](https://github.com/hbldh/bleak), que
  implementa el estándar Bluetooth SIG *Heart Rate Measurement*
  (característica `0x2A37`) tal como lo transmite
  [HeartRate Broadcaster](https://github.com/tankbottoms/HeartRateBroadcaster)
  (u otro sensor/app compatible con el mismo estándar).
- El endpoint `GET /bpm` devuelve JSON (`{"bpm": 72, "connected": true,
  "live": true, "device": "..."}`) y el overlay HTML lo consulta cada
  segundo por `fetch`.
- La GUI y el hilo BLE se comunican a través de un objeto `SharedState`
  protegido por un lock, y de una cola (`queue.Queue`) para el log.

## 🐛 Solución de problemas

- **"No se encontró ningún dispositivo con Heart Rate Service"**: confirma
  que **HeartRate Broadcaster** esté abierta en el iPhone y transmitiendo
  (y que el Apple Watch esté emparejado y con su app también corriendo),
  que el Bluetooth esté activo en ambos dispositivos, y que estén cerca uno
  del otro.
- **El overlay no carga en OBS**: verifica que la app siga corriendo
  (Iniciar) y que el puerto de la URL coincida con el configurado en la
  app.
- **El puerto ya está en uso**: cambia el puerto en la app (por ejemplo
  `8766`) antes de pulsar Iniciar.
- **Falta el paquete 'bleak'**: `pip install bleak` (o vuelve a correr
  `build.bat` si usas el ejecutable compilado desde cero).

## 🤝 Contribuir

Los *pull requests* son bienvenidos. Ideas abiertas:

- Soporte para otros sistemas operativos (macOS/Linux, donde Bleak también
  funciona, aunque el `.exe` de este README es específico de Windows).
- Más temas visuales para el overlay.
- Exportar el historial de BPM a CSV.

## ⚖️ Aviso

Este proyecto no está afiliado a Apple Inc. ni al autor de HeartRate
Broadcaster. "Apple Watch" es una marca registrada de Apple Inc. Este
software simplemente lee datos Bluetooth LE estándar (Heart Rate Service
0x180D) que **HeartRate Broadcaster** — u otra app/dispositivo compatible
con el mismo estándar — transmite.

## 📄 Licencia

[MIT](LICENSE) — úsalo, modifícalo y distribúyelo libremente.
