# Sistema de Monitorización en Tiempo Real — SERVIDOR_COMMOV

## 📋 Descripción del Proyecto

Sistema integrado de monitorización que captura vídeo en directo desde una webcam y lo combina con datos de temperatura de un sensor externo, presentando toda la información en una interfaz gráfica unificada con alertas visuales y sonoras.

### Arquitectura General

```
┌─────────────────────┐         TCP :9000         ┌────────────────────────────────┐
│   PROCESO 1         │   H.264 encapsulado en    │   PROCESO 3                    │
│   video_server.py   │ ─────── MPEG-TS ────────▶ │   monitor_app.py               │
│                     │                            │   (Aplicación cliente — UI)    │
│   Webcam → FFmpeg   │                            │                                │
│   subprocess        │         TCP :9001          │   - Reproduce vídeo en tiempo  │
└─────────────────────┘   JSON-lines (sensor) ──▶ │     real                       │
                                                   │   - Muestra temperatura actual │
┌─────────────────────┐                            │   - Gráfico histórico de temp. │
│   PROCESO 2         │                            │   - Sistema de alertas         │
│   temp_simulator.py │                            │     (visual + sonora)          │
│   (Simulador TCP)   │ ─────────────────────────▶ │                                │
│                     │    o sensor real externo   └────────────────────────────────┘
│   Emite JSON-lines  │
│   con temperatura   │
│   y clasificación   │
└─────────────────────┘
```

---

## 🖥 Requisitos del Sistema

### Hardware
- **Máquina**: GIGABYTE G6 KF (o compatible)
- **CPU**: Intel Core i7-13620H × 10 (13ª generación) — o similar
- **GPU**: NVIDIA RTX 4060 Max-Q/Mobile (con soporte NVENC) — recomendado pero no obligatorio
- **RAM**: 16.1 GB (mínimo 4 GB)
- **Webcam**: USB estándar V4L2 (ej: /dev/video0)

### Software
- **OS**: Linux Mint 22.3 (Cinnamon 6.6.7, 64-bit)
- **Kernel**: 6.17.0-20-generic (o compatible)
- **Display Server**: X11 (Wayland no soportado)
- **Python**: 3.8+ (se recomienda usar el venv incluido)
- **FFmpeg**: 6.1+ con soporte para h264_nvenc (NVIDIA NVENC)

### Dependencias Python
- PyQt6 >= 6.7.1 — Framework gráfico
- av (PyAV) >= 12.1.1 — Decodificación de vídeo
- pyqtgraph >= 0.13.7 — Gráficos en tiempo real
- numpy >= 1.26.4 — Procesamiento de arrays

---

## 📦 Instalación Paso a Paso

### 1. Clonar/Descargar el Repositorio

```bash
cd /home/avatarloren/Commov
ls SERVIDOR_COMMOV/
```

### 2. Crear Entorno Virtual Python

```bash
cd SERVIDOR_COMMOV
python3 -m venv venv
source venv/bin/activate
```

Deberías ver el prompt cambiar a `(venv)`.

### 3. Actualizar pip

```bash
pip install --upgrade pip setuptools wheel
```

### 4. Instalar Dependencias Python

```bash
pip install -r requirements.txt
```

### 5. Verificar Instalación (ver siguiente sección)

---

## ✅ Verificación del Entorno

Ejecuta estos comandos para comprobar que todo está configurado correctamente:

### Verificar FFmpeg y NVENC

```bash
ffmpeg -encoders 2>&1 | grep h264
```

**Esperado**: Debe listar `h264_nvenc` y `libx264`. Si solo ves `libx264`, el sistema funcionará pero más lentamente (CPU en lugar de GPU).

```
V....D libx264              libx264 H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10
V....D h264_nvenc           NVIDIA NVENC H.264 encoder
```

### Verificar Webcam

```bash
ls -la /dev/video*
```

**Esperado**: Debe listar al menos `/dev/video0` con permisos de lectura/escritura.

```
crw-rw----+ 1 root video 81, 0 May 17 18:04 /dev/video0
```

Si tu usuario no está en el grupo `video`, agrega el siguiente comando y reinicia sesión:

```bash
sudo usermod -aG video $USER
```

### Verificar Instalación de PyQt6

```bash
source venv/bin/activate
python3 -c "from PyQt6.QtWidgets import QApplication; print('PyQt6 OK ✓')"
```

### Verificar Instalación de PyAV

```bash
source venv/bin/activate
python3 -c "import av; print('PyAV OK ✓'); print(f'Codecs: {av.codec.codecs}')"
```

---

## 🚀 Ejecución

El sistema está compuesto por 3 procesos independientes que deben ejecutarse en orden.

### Paso 1: Activar Entorno Virtual

En cada terminal, antes de ejecutar los scripts:

```bash
cd /home/avatarloren/Commov/SERVIDOR_COMMOV
source venv/bin/activate
```

### Paso 2: Lanzar el Simulador de Temperatura (o usar sensor real)

**Opción A: Usar simulador (recomendado para pruebas)**

```bash
python3 temp_simulator.py
```

Verás:
```
2026-05-17 12:34:56,123 [INFO] __main__: Servidor de temperatura escuchando en 0.0.0.0:9001
```

El servidor seguirá ejecutándose esperando conexiones.

**Opción B: Usar tu sensor real**

Si tienes un sensor externo que emite JSON-lines en puerto 9001, simplemente corre ese proceso en lugar del simulador.

### Paso 3: Lanzar el Servidor de Vídeo

En otra terminal:

```bash
source venv/bin/activate
python3 video_server.py
```

Verás:
```
2026-05-17 12:34:57,456 [INFO] __main__: Encoder h264_nvenc disponible — usando GPU NVIDIA
2026-05-17 12:34:57,789 [INFO] __main__: Servidor TCP escuchando en 0.0.0.0:9000
```

El servidor esperará a que el cliente (Proceso 3) se conecte.

### Paso 4: Lanzar la Aplicación de Monitorización

En una tercera terminal:

```bash
source venv/bin/activate
python3 monitor_app.py
```

Se abrirá una ventana gráfica que mostrará:
- Panel de vídeo en directo (izquierda superior)
- Panel de temperatura actual (izquierda central)
- Panel de clasificación con color dinámico (izquierda inferior)
- Gráfico histórico de temperatura (derecha)
- Barra de estado con conexiones (abajo)

La aplicación automáticamente se conectará a:
- **Servidor de vídeo** en `127.0.0.1:9000`
- **Servidor de temperatura** en `127.0.0.1:9001`

Si alguna conexión falla, intentará reconectar automáticamente cada 3 segundos.

---

## ⚙ Configuración

Cada script tiene un bloque de constantes configurables al inicio. Puedes modificarlas según tu entorno:

### `video_server.py`

| Variable | Valor por Defecto | Descripción |
|----------|-------------------|-------------|
| `VIDEO_DEVICE` | `/dev/video0` | Dispositivo de captura V4L2 |
| `VIDEO_PORT` | `9000` | Puerto TCP del servidor de vídeo |
| `VIDEO_BIND_HOST` | `0.0.0.0` | Interfaz de escucha (0.0.0.0 = todas) |
| `VIDEO_BITRATE` | `2000k` | Bitrate de codificación H.264 |
| `VIDEO_FRAMERATE` | `30` | FPS de captura y codificación |
| `VIDEO_WIDTH` | `0` | Ancho (0 = resolución nativa) |
| `VIDEO_HEIGHT` | `0` | Alto (0 = resolución nativa) |
| `FFMPEG_ENCODER` | `h264_nvenc` | Encoder principal (fallback: libx264) |
| `FFMPEG_PRESET_NVENC` | `llhq` | Preset para NVENC |
| `FFMPEG_PRESET_CPU` | `ultrafast` | Preset para libx264 |
| `LOG_LEVEL` | `INFO` | Nivel de log: DEBUG, INFO, WARNING |

### `monitor_app.py`

| Variable | Valor por Defecto | Descripción |
|----------|-------------------|-------------|
| `VIDEO_HOST` | `127.0.0.1` | Host del servidor de vídeo |
| `VIDEO_PORT` | `9000` | Puerto del servidor de vídeo |
| `VIDEO_RECONNECT_DELAY` | `3` | Segundos entre reintentos de conexión |
| `SENSOR_HOST` | `127.0.0.1` | Host del servidor de sensor |
| `SENSOR_PORT` | `9001` | Puerto del servidor de sensor |
| `SENSOR_RECONNECT_DELAY` | `3` | Segundos entre reintentos de conexión |
| `VIDEO_DISPLAY_WIDTH` | `800` | Ancho del panel de vídeo (px) |
| `VIDEO_DISPLAY_HEIGHT` | `450` | Alto del panel de vídeo (px) |
| `TEMP_HISTORY_SIZE` | `60` | Número de muestras en el gráfico |
| `TEMP_ALERT_THRESHOLD` | `60.0` | Umbral de alerta (°C) |

### `temp_simulator.py`

| Variable | Valor por Defecto | Descripción |
|----------|-------------------|-------------|
| `SENSOR_BIND_HOST` | `0.0.0.0` | Interfaz de escucha |
| `SENSOR_PORT` | `9001` | Puerto TCP del servidor |
| `SENSOR_INTERVAL` | `1.0` | Segundos entre emisiones |
| `SENSOR_TEMP_BASE` | `30.0` | Temperatura base simulada (°C) |
| `SENSOR_TEMP_NOISE` | `3.0` | Variación aleatoria (±) |

---

## 🔧 Solución de Problemas

### "h264_nvenc NO disponible"

**Síntoma**: En la salida de `video_server.py` ves:
```
WARNING] __main__: h264_nvenc NO disponible — fallback a libx264 (CPU, más lento)
```

**Causa**: Tu sistema no tiene NVIDIA NVENC habilitado, o los drivers NVIDIA no están instalados.

**Solución**:
1. Verifica que tienes tarjeta NVIDIA: `nvidia-smi`
2. Instala drivers NVIDIA: `sudo apt install nvidia-driver-XXX` (reemplaza XXX con tu versión)
3. Reinicia: `sudo reboot`

El sistema seguirá funcionando con `libx264`, pero será más lento.

### "Webcam no aparece en /dev/video0"

**Síntoma**: `ls /dev/video*` no muestra `/dev/video0`.

**Causa**: Webcam no conectada, no reconocida por el kernel, o problemas de permisos.

**Solución**:
1. Verifica conexión física: conecta la webcam a un puerto USB diferente
2. Comprueba reconocimiento: `lsusb | grep -i camera`
3. Recarga módulo V4L2: `sudo modprobe -r uvcvideo && sudo modprobe uvcvideo`
4. Agrega tu usuario al grupo `video`: `sudo usermod -aG video $USER` y reinicia sesión

### "Permission denied" en /dev/video0

**Síntoma**: Al ejecutar `video_server.py`:
```
Permission denied: /dev/video0
```

**Solución**:
```bash
sudo usermod -aG video $USER
# Reinicia sesión o ejecuta:
newgrp video
```

### "ModuleNotFoundError: No module named 'PyQt6'"

**Síntoma**: Al ejecutar `monitor_app.py`:
```
ModuleNotFoundError: No module named 'PyQt6'
```

**Causa**: El venv no está activado o las dependencias no se instalaron.

**Solución**:
```bash
cd /home/avatarloren/Commov/SERVIDOR_COMMOV
source venv/bin/activate
pip install -r requirements.txt
```

### "QXcbConnection: Could not connect to display"

**Síntoma**: Al ejecutar `monitor_app.py` en servidor sin X11:
```
QXcbConnection: Could not connect to display :0
```

**Causa**: No hay servidor X11 disponible.

**Solución**:
1. Asegúrate de estar en X11: `echo $DISPLAY` debe mostrar `:0` o `:1`
2. Si usas SSH, habilita X11 forwarding: `ssh -X user@host`
3. Si no tienes display local, considera usar VNC.

### "Connection refused" en el cliente

**Síntoma**: En la barra de estado de `monitor_app.py`:
```
📹 Vídeo: ✗ Desconectado
🌡 Sensor: ✗ Desconectado
```

**Causa**: Los servidores (Proceso 1 y 2) no están ejecutándose.

**Solución**:
1. Asegúrate de haber lanzado `video_server.py` y `temp_simulator.py` en otras terminales
2. Verifica que los puertos no estén en uso: `netstat -tulpn | grep 9000` y `netstat -tulpn | grep 9001`
3. Si un puerto está ocupado, cambia el número en las constantes de configuración

---

## 📊 Formato del Protocolo de Temperatura (Proceso 2)

El servidor de temperatura (Proceso 2) debe emitir mensajes JSON-lines con la siguiente estructura:

```json
{"timestamp": 1716000000.123, "temperature": 45.7, "classification": "caliente"}
```

- **timestamp**: Número flotante (segundos desde epoch Unix)
- **temperature**: Temperatura en °C (número flotante)
- **classification**: Clasificación como string. Valores permitidos:
  - `"frio"` — temperatura < 10°C (azul)
  - `"templado"` — 10°C ≤ temperatura < 20°C (verde)
  - `"caliente"` — 20°C ≤ temperatura < 40°C (naranja)
  - `"muy caliente"` — 40°C ≤ temperatura < 60°C (rojo naranja)
  - `"crítico"` — temperatura ≥ 60°C (rojo oscuro)

Cada mensaje debe terminar con `\n` (salto de línea).

**Nota**: Si usas `temp_simulator.py`, estas reglas se aplican automáticamente.

---

## 🎯 Casos de Uso

### Modo Desarrollo/Prueba (Recomendado para Empezar)

```bash
# Terminal 1: Simulador de temperatura
python3 temp_simulator.py

# Terminal 2: Servidor de vídeo
python3 video_server.py

# Terminal 3: Aplicación de monitorización
python3 monitor_app.py
```

Esto te permite ver:
- Vídeo en directo desde la webcam
- Datos de temperatura simulados (cambian aleatoriamente)
- Gráfico histórico llenándose en tiempo real
- Alertas al superar 60°C

### Integración con Sensor Real

Una vez tengas un servidor de sensor real que emita JSON-lines en puerto 9001:

1. Reemplaza `temp_simulator.py` con tu servidor
2. Los datos se consumirán automáticamente en `monitor_app.py`
3. No hay cambios necesarios en el código

---

## 📝 Arquitectura de Código

### Proceso 1: `video_server.py`

- **Entrada**: Webcam (/dev/video0)
- **Procesamiento**: FFmpeg + subprocess
- **Salida**: Socket TCP con stream MPEG-TS
- **Patrón**: Servidor TCP con threading por cliente

### Proceso 2: `temp_simulator.py` (o sensor externo)

- **Entrada**: Sensor real (o simulación aleatoria)
- **Procesamiento**: Clasificación de temperatura
- **Salida**: Socket TCP con JSON-lines
- **Patrón**: Servidor TCP con threading por cliente

### Proceso 3: `monitor_app.py`

- **Entrada**: Socket TCP vídeo + Socket TCP sensor
- **Procesamiento**: PyQt6 + PyAV + pyqtgraph
- **Salida**: Interfaz gráfica
- **Patrón**: QMainWindow con QThread workers (VideoWorker, SensorWorker)

---

## 🔐 Consideraciones de Seguridad

- Los servidores escuchan en `0.0.0.0` (todas las interfaces). Para red local, cambia a `127.0.0.1`.
- No hay autenticación. Implementa firewalls si expones a red pública.
- Los streams de vídeo no están encriptados. Usa VPN o conexiones locales.

---

## 📄 Licencia

Este proyecto es software de código abierto. Úsalo libremente en tu entorno.

---

## 🆘 Soporte

Si encuentras problemas:

1. Revisa la sección de **Solución de Problemas** arriba
2. Verifica logs en consola (nivel `DEBUG` en constantes si necesitas más detalle)
3. Abre un terminal y ejecuta en orden: verificaciones de entorno, then servidores, then cliente

---

**Última actualización**: 17 de Mayo de 2026
**Versión del Sistema**: 1.0
