# 📹 Sistema de Captura y Codificación de Video en Tiempo Real

Un sistema robusto en Python para capturar video de la webcam y codificarlo a H.264 usando FFmpeg, con soporte para Windows, macOS y Linux.

## 🎯 Características Principales

✅ **Captura en tiempo real** desde la webcam del sistema  
✅ **Codificación H.264** eficiente con control de calidad  
✅ **Compatibilidad multiplataforma** (Windows, macOS, Linux)  
✅ **Lectura de bitstream** en memoria mediante pipes  
✅ **Configuración flexible** de resolución, FPS, bitrate y calidad  
✅ **Manejo robusto de errores** con reintentos  
✅ **Estadísticas en tiempo real**  
✅ **Interfaz simple y extensible**  

## 📋 Requisitos

- **Python 3.8+**
- **FFmpeg** (instalado en el sistema)
- **Acceso a la webcam**

## 🚀 Inicio Rápido

### 1. Instalación de Dependencias

#### Windows
```powershell
# Instalar FFmpeg (opción recomendada: Chocolatey)
choco install ffmpeg

# O descargarlo manualmente desde https://ffmpeg.org/download.html
```

#### macOS
```bash
brew install ffmpeg
```

#### Linux
```bash
sudo apt install ffmpeg
```

### 2. Clonar/Descargar el Repositorio
```bash
cd c:\SERVIDOR_COMMOV
```

### 3. Crear Entorno Virtual (opcional pero recomendado)
```bash
# Windows
python -m venv venv
.\venv\Scripts\Activate.ps1

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 4. Instalar Dependencias Python
```bash
pip install -r requirements.txt
```

### 5. Ejecutar la Captura
```bash
python video_capture.py
```

Esto capturará 10 segundos de video y lo guardará en `output.h264`.

---

## 📚 Uso

### Ejemplo Básico

```python
from video_capture import WebcamVideoCapture, VideoCaptureConfig

# Crear configuración
config = VideoCaptureConfig(
    width=1280,
    height=720,
    fps=30,
    bitrate="2500k",
    preset="fast",
    crf=28
)

# Crear capturador
capture = WebcamVideoCapture(config)

# Iniciar captura
capture.start()

# Guardar 5 segundos
capture.save_to_file("output.h264", duration=5)

# Detener
capture.stop()
```

### Lectura Manual de Frames

```python
capture = WebcamVideoCapture()
capture.start()

for chunk in capture.read_frames(chunk_size=4096):
    if chunk:
        # Procesar el chunk
        print(f"Capturados {len(chunk)} bytes")

capture.stop()
```

### Obtener Estadísticas

```python
stats = capture.get_stats()
print(f"Bytes capturados: {stats['total_bytes']}")
print(f"Errores: {stats['error_count']}")
print(f"Configuración: {stats['config']}")
```

---

## ⚙️ Parámetros de Configuración

```python
VideoCaptureConfig(
    width=1280,           # Ancho en píxeles
    height=720,           # Alto en píxeles
    fps=30,              # Fotogramas por segundo
    bitrate="2500k",     # Bitrate de salida (ej: "5000k")
    preset="fast",       # Velocidad: ultrafast/superfast/fast/medium/slow
    crf=28,              # Calidad 0-51 (0=mejor, 51=peor)
    read_timeout=5.0     # Timeout en segundos
)
```

### Presets de Configuración Predefinidos

**Alta Calidad (HD 1080p)**
```python
config = VideoCaptureConfig(
    width=1920, height=1080, fps=60,
    bitrate="8000k", preset="slow", crf=18
)
```

**Estándar (720p)**
```python
config = VideoCaptureConfig(
    width=1280, height=720, fps=30,
    bitrate="2500k", preset="fast", crf=28
)
```

**Baja Latencia (480p)**
```python
config = VideoCaptureConfig(
    width=640, height=480, fps=30,
    bitrate="1500k", preset="ultrafast", crf=35
)
```

**Ultra Ligero (240p)**
```python
config = VideoCaptureConfig(
    width=320, height=240, fps=15,
    bitrate="500k", preset="ultrafast", crf=40
)
```

---

## 📁 Estructura del Proyecto

```
SERVIDOR_COMMOV/
├── video_capture.py      # Módulo principal de captura
├── examples.py           # Ejemplos de uso
├── requirements.txt      # Dependencias de Python
├── INSTALL.md           # Instrucciones de instalación detalladas
├── README.md            # Este archivo
└── .git/                # Control de versiones
```

---

## 🔧 Explicación de Parámetros FFmpeg

El script genera un comando FFmpeg como:

```bash
ffmpeg \
    -hide_banner -loglevel warning -y \
    -f dshow \                              # Formato de entrada (Windows)
    -framerate 30 \                         # FPS de entrada
    -video_size 1280x720 \                 # Tamaño del sensor
    -i "video=0" \                          # Dispositivo de entrada
    -vf scale=1280:720 \                   # Filtro de escala
    -c:v libx264 \                         # Códec H.264
    -preset fast \                          # Balance velocidad/compresión
    -crf 28 \                               # Factor de calidad (0-51)
    -b:v 2500k \                           # Bitrate máximo
    -maxrate 2500k -bufsize 2500k \       # Control de buffer
    -pix_fmt yuv420p \                     # Formato de píxeles
    -f h264 \                               # Formato de salida
    pipe:1                                  # Salida a stdout
```

### Detalles de los Parámetros

| Parámetro | Descripción |
|-----------|-------------|
| `-f dshow` | Formato de entrada (dshow=Windows, avfoundation=macOS, v4l2=Linux) |
| `-framerate 30` | FPS capturados del sensor |
| `-video_size 1280x720` | Resolución nativa del sensor |
| `-vf scale=1280:720` | Redimensiona a la resolución deseada |
| `-c:v libx264` | Códec H.264 (libx265 para HEVC/H.265) |
| `-preset fast` | Velocidad: ultrafast=rápido/baja calidad, slow=lento/buena calidad |
| `-crf 28` | 0=máxima calidad, 51=mínima calidad, 28=defecto |
| `-b:v 2500k` | Bitrate objetivo (mayor=mejor calidad) |
| `-pix_fmt yuv420p` | Formato de píxeles compatible con la mayoría de reproductores |
| `-f h264` | Salida como H.264 puro (sin contenedor MP4/MKV) |
| `pipe:1` | Envía stdout a Python para captura en memoria |

---

## 🖥️ Adaptación por Sistema Operativo

El script detecta automáticamente el SO y usa los parámetros correctos:

### Windows
- **Formato de entrada:** `dshow` (DirectShow)
- **Dispositivo:** `"video=0"` (primera cámara)
- **Comando detectado:**
  ```
  -f dshow -i "video=0"
  ```

### macOS
- **Formato de entrada:** `avfoundation`
- **Dispositivo:** `"0"`
- **Comando detectado:**
  ```
  -f avfoundation -i "0"
  ```

### Linux
- **Formato de entrada:** `v4l2` (Video4Linux)
- **Dispositivo:** `/dev/video0`
- **Comando detectado:**
  ```
  -f v4l2 -i /dev/video0
  ```

---

## 🔍 Cómo Funciona

```
┌─────────────┐
│   Webcam    │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  FFmpeg                                 │
│  ├─ Captura video desde dispositivo     │
│  ├─ Escala a resolución deseada        │
│  ├─ Codifica en H.264                   │
│  └─ Envía bitstream a stdout           │
└──────┬──────────────────────────────────┘
       │ (bytes H.264)
       ▼
┌──────────────────────────┐
│  subprocess.PIPE         │
│  (captura en Python)     │
└──────┬───────────────────┘
       │
       ▼
  ┌────────────────────────────┐
  │  Opciones de procesamiento │
  ├─ Guardar a archivo        │
  ├─ Procesar en tiempo real   │
  ├─ Transmitir por red        │
  └─ Análisis de video        │
```

---

## 📊 Ejemplos de Uso Avanzado

### Procesar Video en Tiempo Real

```python
from video_capture import WebcamVideoCapture
import cv2

capture = WebcamVideoCapture()
capture.start()

buffer = bytearray()

for chunk in capture.read_frames():
    if chunk:
        buffer.extend(chunk)
        # Procesar buffer con OpenCV u otra librería
        # frame = parse_h264_frame(buffer)

capture.stop()
```

### Transmitir Video a Servidor

```python
import socket
from video_capture import WebcamVideoCapture

capture = WebcamVideoCapture()
capture.start()

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(("192.168.1.100", 5000))

try:
    for chunk in capture.read_frames():
        if chunk:
            sock.sendall(chunk)
finally:
    sock.close()
    capture.stop()
```

### Guardar con Información de FPS

```python
from video_capture import WebcamVideoCapture

config = VideoCaptureConfig(fps=30)
capture = WebcamVideoCapture(config)
capture.start()
capture.save_to_file("video.h264", duration=30)

# Convertir a MP4 con información de FPS
import subprocess
subprocess.run([
    "ffmpeg", "-r", "30", "-i", "video.h264",
    "-vcodec", "copy", "-acodec", "aac",
    "video.mp4"
])
```

---

## 🛠️ Solución de Problemas

### "FFmpeg no está instalado"
1. Verifica la instalación: `ffmpeg -version`
2. Asegúrate que está en el PATH
3. Reinicia el terminal después de instalar

### "No se puede abrir la cámara"
1. Verifica permisos de cámara en el SO
2. Cierra otras aplicaciones que usen la cámara
3. Intenta cambiar el índice de dispositivo (video=1, video=2, etc.)

### "Alto consumo de CPU"
1. Aumenta `crf` (compresión más agresiva)
2. Reduce `preset` a `ultrafast`
3. Disminuye resolución o FPS

### "Baja calidad de video"
1. Disminuye `crf` (mejor calidad)
2. Aumenta `bitrate`
3. Cambia `preset` a `slow` o `slower`

---

## 📖 Documentación Completa

Ver [INSTALL.md](INSTALL.md) para:
- Instrucciones detalladas de instalación por SO
- Verificación de cámaras disponibles
- Conversión a formato reproducible (MP4/MKV)
- Guía completa de parámetros

---

## 🧪 Ejecutar Ejemplos

```bash
python examples.py
```

Luego elige entre:
1. Captura básica
2. Alta calidad
3. Baja latencia
4. Lectura manual
5. Manejo de errores
6. Comparación de configuraciones
7. Estadísticas en vivo

---

## 📜 Licencia

Este proyecto es de código abierto y está disponible bajo la licencia que configures para tu repositorio.

---

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor, abre un issue o pull request.

---

## 📞 Soporte

Para problemas o preguntas:
1. Revisa la documentación en [INSTALL.md](INSTALL.md)
2. Consulta los ejemplos en [examples.py](examples.py)
3. Abre un issue en el repositorio

---

**Última actualización:** Marzo 2026
