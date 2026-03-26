# 🚀 GUÍA DE INICIO RÁPIDO

## Archivos Entregados

```
SERVIDOR_COMMOV/
├── 📄 video_capture.py         [880 líneas]  Módulo principal de captura
├── 📄 examples.py              [540 líneas]  7 ejemplos de uso interactivos  
├── 📄 advanced_examples.py     [450 líneas]  Casos de uso avanzado
├── 📄 validate.py              [450 líneas]  Script de validación/diagnóstico
├── 📘 README.md                [580 líneas]  Documentación principal
├── 📘 INSTALL.md               [380 líneas]  Guía de instalación detallada
├── 📘 API_REFERENCE.md         [450 líneas]  Referencia completa de API
├── 📄 requirements.txt                       Dependencias Python
└── .git/                                     Control de versiones
```

---

## ⚡ INICIO RÁPIDO (5 minutos)

### 1️⃣ Instalar FFmpeg

#### Windows
```powershell
# Opción A: Chocolatey (recomendado)
choco install ffmpeg

# Opción B: Descargar manualmente
https://ffmpeg.org/download.html
# Luego agregar a PATH

# Opción C: Scoop
scoop install ffmpeg
```

#### macOS
```bash
brew install ffmpeg
```

#### Linux
```bash
sudo apt install ffmpeg
```

### 2️⃣ Validar Configuración
```bash
python validate.py
```

Este script verifica:
- ✅ Python 3.8+
- ✅ FFmpeg instalado
- ✅ Módulos necesarios
- ✅ Disponibilidad de cámara
- ✅ Archivos del proyecto

### 3️⃣ Ejecutar la Captura
```bash
# Captura 10 segundos de video
python video_capture.py
```

Salida: `output.h264`

### 4️⃣ Convertir a MP4 (opcional)
```bash
ffmpeg -r 30 -i output.h264 -vcodec copy output.mp4
```

---

## 📑 Archivos Principales

### 🎬 `video_capture.py` - Módulo Principal

El corazón del sistema. Contiene:

- **Clase `VideoCaptureConfig`**: Configura parámetros
- **Clase `WebcamVideoCapture`**: Captura y codifica video

```python
from video_capture import WebcamVideoCapture, VideoCaptureConfig

# Configuración
config = VideoCaptureConfig(
    width=1280,
    height=720,
    fps=30,
    bitrate="2500k",
    preset="fast",
    crf=28
)

# Usar
capture = WebcamVideoCapture(config)
capture.start()
capture.save_to_file("video.h264", duration=10)
capture.stop()
```

### 📚 `examples.py` - Ejemplos Interactivos

7 ejemplos listos para ejecutar:

```bash
python examples.py
```

1. Captura básica (10s)
2. Alta calidad (1080p, 60fps)
3. Baja latencia (320x240, ultrafast)
4. Lectura manual de frames
5. Manejo de errores y reintentos
6. Comparación de configuraciones
7. Estadísticas en vivo

### 🔧 `advanced_examples.py` - Casos Avanzados

```python
# Streaming en vivo
from advanced_examples import PresetConfigs
config = PresetConfigs.STREAMING

# Vigilancia 24/7 con rotación de archivos
from advanced_examples import MultiFileCapture
multi = MultiFileCapture(file_duration=600)
multi.start()

# Procesamiento paralelo
from advanced_examples import ParallelCapture
parallel = ParallelCapture(frame_processor)
parallel.start()
```

### ✅ `validate.py` - Diagnóstico del Sistema

```bash
python validate.py
```

Verifica:
- Versión de Python
- Instalación de FFmpeg
- Módulos requeridos
- Disponibilidad de cámara
- Archivos del proyecto
- Prueba de captura (opcional)

### 📖 Documentación

| Archivo | Contenido |
|---------|----------|
| **README.md** | Descripción general, características, uso básico |
| **INSTALL.md** | Instalación detallada por SO, solución de problemas |
| **API_REFERENCE.md** | Referencia completa de clases y métodos |
| **requirements.txt** | Dependencias Python |

---

## 🎯 Casos de Uso Comunes

### 1. Grabar video simple
```python
from video_capture import WebcamVideoCapture
capture = WebcamVideoCapture()
capture.start()
capture.save_to_file("video.h264", duration=30)
capture.stop()
```

### 2. Streaming en vivo
```python
from advanced_examples import PresetConfigs, WebcamVideoCapture
config = PresetConfigs.STREAMING
capture = WebcamVideoCapture(config)
capture.start()
capture.save_to_file("stream.h264")
```

### 3. Procesamiento en tiempo real
```python
from video_capture import WebcamVideoCapture
capture = WebcamVideoCapture()
capture.start()

for chunk in capture.read_frames():
    if chunk:
        # Procesar chunk (OpenCV, análisis, etc.)
        process(chunk)

capture.stop()
```

### 4. Vigilancia 24/7
```python
from advanced_examples import MultiFileCapture, PresetConfigs
multi = MultiFileCapture(file_duration=3600)  # 1 hora por archivo
multi.start(PresetConfigs.SURVEILLANCE)
multi.record_with_rotation()  # Infinito hasta Ctrl+C
```

### 5. Análisis de video
```python
from advanced_examples import ParallelCapture
def mi_analizador(chunk):
    # Analizar frames (detección facial, etc.)
    pass

parallel = ParallelCapture(mi_analizador)
parallel.start()
parallel.capture_frames(duration=60)
```

---

## ⚙️ Configuraciones Predefinidas

```python
from advanced_examples import PresetConfigs

PresetConfigs.STREAMING           # Web en vivo
PresetConfigs.VIDEO_CALL          # Videollamadas
PresetConfigs.RECORDING_HD        # Grabación de reuniones
PresetConfigs.LIVE_STREAMING      # Transmisión en vivo
PresetConfigs.REAL_TIME_ANALYSIS  # Análisis en tiempo real
PresetConfigs.SCREEN_DOC          # Documentación de pantalla
PresetConfigs.SURVEILLANCE        # Vigilancia 24/7
PresetConfigs.GAMING              # Juegos/ScreenCast
```

---

## 🔍 Parámetros Principales

### Calidad (CRF)
- **0-10**: Excelente (archivos grandes)
- **18**: Estándar (recomendado)
- **28**: Predeterminado
- **35-40**: Baja (archivos pequeños)
- **51**: Mínima

### Velocidad (Preset)
- **ultrafast**: Máxima velocidad, baja calidad
- **fast**: Balance (recomendado)
- **slow**: Mejor compresión, más CPU

### Resolución
- **320x240**: Ultra ligero
- **640x480**: Bajo ancho de banda
- **1280x720**: HD estándar ⭐
- **1920x1080**: Full HD
- **3840x2160**: 4K (requiere CPU potente)

### FPS
- **10-15**: Vigilancia/bajo ancho de banda
- **24**: Cine estándar
- **30**: Estándar de video ⭐
- **60**: Deportes/juegos

### Bitrate (KB/s)
- **500k**: Ultra ligero
- **1500k**: Bajo ancho de banda
- **2500k**: Estándar ⭐
- **5000k**: Buena calidad
- **10000k**: Alta calidad

---

## 🛠️ Solución de Problemas

### Error: "FFmpeg no encontrado"
```bash
# Windows
choco install ffmpeg

# macOS
brew install ffmpeg

# Linux
sudo apt install ffmpeg
```

### Error: "No se puede abrir la cámara"
```bash
# Verifica que la cámara no esté en uso
# Cierra otras aplicaciones (Meet, Zoom, etc.)
# Verifica permisos en Configuración > Privacidad > Cámara (Windows)
```

### Alto consumo de CPU
- Reduce la resolución
- Disminuye FPS (30 → 24)
- Usa preset "ultrafast"
- Aumenta CRF (28 → 35)

### Baja calidad/borroso
- Disminuye CRF (28 → 18)
- Aumenta bitrate ("2500k" → "5000k")

---

## 📊 Comandos FFmpeg Generados

El sistema genera automáticamente comandos como:

```bash
# Windows (DirectShow)
ffmpeg -f dshow -framerate 30 -video_size 1280x720 -i "video=0" \
       -vf scale=1280:720 -c:v libx264 -preset fast -crf 28 \
       -b:v 2500k -pix_fmt yuv420p -f h264 pipe:1

# macOS (AVFoundation)
ffmpeg -f avfoundation -framerate 30 -i "0" \
       -vf scale=1280:720 -c:v libx264 -preset fast -crf 28 \
       -b:v 2500k -pix_fmt yuv420p -f h264 pipe:1

# Linux (V4L2)
ffmpeg -f v4l2 -framerate 30 -video_size 1280x720 -i /dev/video0 \
       -vf scale=1280:720 -c:v libx264 -preset fast -crf 28 \
       -b:v 2500k -pix_fmt yuv420p -f h264 pipe:1
```

---

## 📚 Siguiente Paso

1. **Valida tu sistema:**
   ```bash
   python validate.py
   ```

2. **Ejecuta un ejemplo:**
   ```bash
   python examples.py
   ```

3. **Lee la documentación completa:**
   - [INSTALL.md](INSTALL.md) - Instalación detallada
   - [README.md](README.md) - Descripción general
   - [API_REFERENCE.md](API_REFERENCE.md) - Referencia de API

4. **Explora casos avanzados:**
   ```bash
   python advanced_examples.py
   ```

---

## ℹ️ Información Técnica

**Lenguaje:** Python 3.8+  
**Dependencias:** FFmpeg (sistema), subprocess (Python estándar)  
**Plataformas:** Windows, macOS, Linux  
**Códec:** H.264 (libx264)  
**Formato:** H.264 bitstream puro (sin contenedor)  
**Overhead:** Bajo (apenas usa CPU cuando está esperando)  

---

## 📞 Contacto y Soporte

- **Documentación:** Ver [INSTALL.md](INSTALL.md) y [API_REFERENCE.md](API_REFERENCE.md)
- **Ejemplos:** Ejecutar `python examples.py` o `python advanced_examples.py`
- **Diagnóstico:** Ejecutar `python validate.py`

---

**¡Listo para empezar! 🎬**

Espero que este sistema sea útil para tu proyecto. Si tienes preguntas o necesitas ayuda con algo específico, no dudes en preguntar.

Última actualización: Marzo 2026
