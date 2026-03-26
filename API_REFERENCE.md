# API Reference - Sistema de Captura de Video

## Índice
1. [Clase VideoCaptureConfig](#videocaptureconfig)
2. [Clase WebcamVideoCapture](#webcamvideocapture)
3. [Métodos Principales](#métodos-principales)
4. [Ejemplos Rápidos](#ejemplos-rápidos)
5. [Referencia de Plataformas](#referencia-de-plataformas)

---

## VideoCaptureConfig

### Descripción
Clase de configuración que almacena todos los parámetros de captura y codificación.

### Constructor
```python
VideoCaptureConfig(
    width: int = 1280,
    height: int = 720,
    fps: int = 30,
    bitrate: str = "2500k",
    preset: str = "fast",
    crf: int = 28,
    read_timeout: float = 5.0
)
```

### Parámetros

| Parámetro | Tipo | Por defecto | Descripción |
|-----------|------|-------------|-------------|
| `width` | int | 1280 | Ancho de resolución en píxeles |
| `height` | int | 720 | Alto de resolución en píxeles |
| `fps` | int | 30 | Fotogramas por segundo (1-60) |
| `bitrate` | str | "2500k" | Bitrate de salida (ej: "1000k", "5000k", "10000k") |
| `preset` | str | "fast" | Velocidad: ultrafast/superfast/veryfast/faster/fast/medium/slow/slower/veryslow |
| `crf` | int | 28 | Calidad H.264 (0-51, 0=mejor, 51=peor, 23=ref) |
| `read_timeout` | float | 5.0 | Timeout de lectura en segundos |

### Ejemplo
```python
from video_capture import VideoCaptureConfig

# Configuración personalizada
config = VideoCaptureConfig(
    width=1920,
    height=1080,
    fps=60,
    bitrate="8000k",
    preset="slow",
    crf=18
)

# Usar con capturador
capture = WebcamVideoCapture(config)
```

---

## WebcamVideoCapture

### Descripción
Clase principal para captura y codificación de video desde la webcam.

### Constructor
```python
WebcamVideoCapture(config: Optional[VideoCaptureConfig] = None)
```

**Parámetros:**
- `config` (VideoCaptureConfig): Configuración de captura. Si no se pasa, usa valores por defecto.

### Ejemplo de Inicialización
```python
from video_capture import WebcamVideoCapture, VideoCaptureConfig

# Con configuración por defecto
capture = WebcamVideoCapture()

# Con configuración personalizada
config = VideoCaptureConfig(width=1920, height=1080)
capture = WebcamVideoCapture(config)
```

---

## Métodos Principales

### start()
Inicia el proceso de captura de video.

**Firma:**
```python
def start(self) -> None
```

**Retorna:** None

**Excepciones:**
- `RuntimeError`: Si FFmpeg no está instalado o no se puede iniciar el proceso.

**Ejemplo:**
```python
capture = WebcamVideoCapture()
try:
    capture.start()
    print("Captura iniciada")
except RuntimeError as e:
    print(f"Error: {e}")
```

---

### read_frames(chunk_size: int = 4096)
Lee fotogramas (chunks) del bitstream H.264 de forma continua.

**Firma:**
```python
def read_frames(self, chunk_size: int = 4096) -> Generator[bytes, None, None]
```

**Parámetros:**
- `chunk_size` (int): Tamaño en bytes de cada chunk a leer

**Retorna:** Generator que yields bytes del bitstream H.264 o None si hay error

**Ejemplo:**
```python
capture = WebcamVideoCapture()
capture.start()

total_bytes = 0
for chunk in capture.read_frames(chunk_size=8192):
    if chunk:
        total_bytes += len(chunk)
        print(f"Capturados {total_bytes} bytes")

capture.stop()
```

**Notas:**
- Es un generador (usa `yield`), permite lectura continua y eficiente de memoria
- Retorna `None` si hay error temporal (reintentos automáticos)
- Se detiene cuando `capture.stop()` es llamado o se alcanzan máximos errores

---

### save_to_file(output_path: str, duration: Optional[float] = None)
Guarda el video capturado a un archivo H.264.

**Firma:**
```python
def save_to_file(self, output_path: str, duration: Optional[float] = None) -> None
```

**Parámetros:**
- `output_path` (str): Ruta del archivo de salida (ej: "video.h264")
- `duration` (float, optional): Duración máxima en segundos. None = captura indefinida

**Retorna:** None

**Excepciones:**
- `TypeError`: Si output_path no es válido
- `IOError`: Si no se puede escribir el archivo
- `KeyboardInterrupt`: Si el usuario interrumpe (Ctrl+C)

**Ejemplo:**
```python
capture = WebcamVideoCapture()
capture.start()

# Guardar 10 segundos
capture.save_to_file("video.h264", duration=10)

capture.stop()
```

---

### stop()
Detiene el proceso de captura.

**Firma:**
```python
def stop(self) -> None
```

**Retorna:** None

**Comportamiento:**
- Termina graciosamente el proceso FFmpeg
- Si no responde en 5 segundos, lo mata forzosamente
- Actualiza estadísticas

**Ejemplo:**
```python
capture = WebcamVideoCapture()
capture.start()

# ... capturar video ...

capture.stop()
print("Captura detenida")
```

---

### get_stats()
Retorna estadísticas de la captura actual.

**Firma:**
```python
def get_stats(self) -> dict
```

**Retorna:** Diccionario con estructura:
```python
{
    "is_running": bool,
    "total_bytes": int,
    "error_count": int,
    "config": {
        "resolution": str,    # ej: "1280x720"
        "fps": int,
        "bitrate": str,
        "crf": int
    }
}
```

**Ejemplo:**
```python
capture = WebcamVideoCapture()
capture.start()

# ... capturar video ...

stats = capture.get_stats()
print(f"Bytes capturados: {stats['total_bytes']:,}")
print(f"Resolución: {stats['config']['resolution']}")
print(f"FPS: {stats['config']['fps']}")
```

---

## Ejemplos Rápidos

### Captura Simple
```python
from video_capture import WebcamVideoCapture

capture = WebcamVideoCapture()
capture.start()
capture.save_to_file("output.h264", duration=10)
capture.stop()
```

### Captura con Configuración Personalizada
```python
from video_capture import WebcamVideoCapture, VideoCaptureConfig

config = VideoCaptureConfig(
    width=1920,
    height=1080,
    fps=60,
    bitrate="8000k",
    preset="slow",
    crf=18
)

capture = WebcamVideoCapture(config)
capture.start()
capture.save_to_file("hd_video.h264", duration=30)
capture.stop()
```

### Procesar Frames Manualmente
```python
capture = WebcamVideoCapture()
capture.start()

# Procesamiento personalizado
for chunk in capture.read_frames(chunk_size=16384):
    if chunk:
        # Aquí puedes:
        # - Guardar a archivo
        # - Enviar por red
        # - Procesar con OpenCV
        # - Análisis de video
        process_video_chunk(chunk)

capture.stop()
```

### Captura con Duración Máxima
```python
capture = WebcamVideoCapture()
capture.start()

# Capturar hasta 60 segundos o hasta que se detenga
capture.save_to_file("limited.h264", duration=60)

capture.stop()
```

### Monitorizar Estadísticas
```python
import time
from video_capture import WebcamVideoCapture

capture = WebcamVideoCapture()
capture.start()

for _ in range(10):  # Monitorizar cada segundo por 10 segundos
    time.sleep(1)
    stats = capture.get_stats()
    print(f"Bytes: {stats['total_bytes']:,}, Errores: {stats['error_count']}")

capture.stop()
```

---

## Referencia de Plataformas

### Windows (DirectShow)

**Dispositivo de entrada:** `video="0"`, `video="1"`, etc.

**Comando FFmpeg generado:**
```bash
ffmpeg -f dshow -framerate 30 -video_size 1280x720 \
       -i "video=0" -vf scale=1280:720 \
       -c:v libx264 -preset fast -crf 28 \
       -b:v 2500k -pix_fmt yuv420p \
       -f h264 pipe:1
```

**Listar cámaras:**
```bash
ffmpeg -list_devices true -f dshow -i dummy
```

---

### macOS (AVFoundation)

**Dispositivo de entrada:** `"0"`, `"1"`, etc.

**Comando FFmpeg generado:**
```bash
ffmpeg -f avfoundation -framerate 30 \
       -i "0" -vf scale=1280:720 \
       -c:v libx264 -preset fast -crf 28 \
       -b:v 2500k -pix_fmt yuv420p \
       -f h264 pipe:1
```

**Listar cámaras:**
```bash
ffmpeg -f avfoundation -list_devices true -i ""
```

---

### Linux (Video4Linux2)

**Dispositivo de entrada:** `/dev/video0`, `/dev/video1`, etc.

**Comando FFmpeg generado:**
```bash
ffmpeg -f v4l2 -framerate 30 -video_size 1280x720 \
       -i /dev/video0 -vf scale=1280:720 \
       -c:v libx264 -preset fast -crf 28 \
       -b:v 2500k -pix_fmt yuv420p \
       -f h264 pipe:1
```

**Listar cámaras:**
```bash
ls /dev/video*
v4l2-ctl --list-devices
```

---

## Parámetros de Preset FFmpeg

| Preset | Velocidad | Compresión | Calidad | CPU |
|--------|-----------|-----------|---------|-----|
| ultrafast | ⚡⚡⚡⚡⚡ | 📦 | ⭐ | ✅ |
| superfast | ⚡⚡⚡⚡ | 📦📦 | ⭐⭐ | ✅ |
| veryfast | ⚡⚡⚡ | 📦📦 | ⭐⭐ | ✅ |
| faster | ⚡⚡ | 📦📦📦 | ⭐⭐⭐ | ≈ |
| fast | ⚡ | 📦📦📦 | ⭐⭐⭐ | ≈ |
| medium | ≈ | 📦📦📦📦 | ⭐⭐⭐⭐ | 🔴 |
| slow | 🐢 | 📦📦📦📦 | ⭐⭐⭐⭐⭐ | 🔴🔴 |
| slower | 🐢🐢 | 📦📦📦📦📦 | ⭐⭐⭐⭐⭐ | 🔴🔴🔴 |
| veryslow | 🐢🐢🐢 | 📦📦📦📦📦 | ⭐⭐⭐⭐⭐ | 🔴🔴🔴🔴 |

---

## Parámetros CRF (Constant Rate Factor)

**CRF (Calidad)**

| Valor | Calidad | Tamaño | Caso de uso |
|-------|---------|--------|-------------|
| 0-10 | Excelente | Muy grande | Archivos maestros |
| 11-17 | Muy buena | Grande | Grabaciones importantes |
| 18-24 | Buena | Medio | Estándar (18 es valor ref) |
| 25-31 | Aceptable | Pequeño | Streaming/múltiples copias |
| 32-38 | Baja | Muy pequeño | Vigilancia/datos no críticos |
| 39-51 | Muy baja | Mínimo | Pruebas/desarrollo |

---

## Bitrates Recomendados

| Resolución | FPS | Baja (Streaming) | Media | Alta |
|-----------|-----|-----------------|-------|------|
| 320x240 | 15 | 300k | 500k | 800k |
| 640x480 | 24 | 800k | 1500k | 2500k |
| 854x480 | 30 | 1500k | 2500k | 4000k |
| 1280x720 | 30 | 2500k | 4000k | 6000k |
| 1920x1080 | 30 | 5000k | 8000k | 12000k |
| 1920x1080 | 60 | 8000k | 12000k | 18000k |

---

## Troubleshooting

### Problema: RuntimeError al iniciar
**Causa:** FFmpeg no está instalado o no está en el PATH
**Solución:** 
```bash
# Windows
choco install ffmpeg

# macOS
brew install ffmpeg

# Linux
sudo apt install ffmpeg
```

### Problema: Bajo throughput o cortes
**Causa:** Resolución o FPS demasiado altos, CPU insuficiente
**Solución:** 
- Reduce resolución (720p en lugar de 1080p)
- Reduce fps (24 en lugar de 30)
- Cambia preset a ultrafast
- Aumenta crf (compresión más agresiva)

### Problema: Archivo corrupto
**Causa:** El archivo H.264 es bitstream puro, necesita conversión
**Solución:**
```bash
ffmpeg -r 30 -i output.h264 -vcodec copy output.mp4
```

### Problema: Alto consumo de memoria
**Causa:** chunk_size muy grande o múltiples capturas en paralelo
**Solución:**
- Reduce chunk_size (por defecto 4096)
- Detén capturas previas antes de iniciar nuevas
- Asegúrate de que `read_frames()` se procesa rápidamente

---

## Recursos Adicionales

- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)
- [libx264 Encoding Guide](https://trac.ffmpeg.org/wiki/Encode/H.264)
- [Python subprocess](https://docs.python.org/3/library/subprocess.html)
- [Video Codecs Comparison](https://www.researchgate.net/publication/272505555_Video_compression_technique)

---

**Última actualización:** Marzo 2026
