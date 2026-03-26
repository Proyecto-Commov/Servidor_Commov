# Guía de Instalación y Configuración

## Resumen General

Este sistema requiere:
1. **Python 3.8+** instalado
2. **FFmpeg** instalado en el sistema (no es un paquete de pip)
3. Acceso a la webcam del sistema

---

## 1. Instalación de FFmpeg

### Windows

#### Opción A: Descarga manual desde ffmpeg.org
1. Visita https://ffmpeg.org/download.html
2. Descarga la versión para Windows (precompilada)
3. Extrae el archivo ZIP
4. Copia `ffmpeg.exe` a una carpeta, por ejemplo: `C:\ffmpeg\bin\`
5. **Agrega a las variables de entorno:**
   - Abre "Variables de entorno" (Environment Variables)
   - Edita la variable `Path`
   - Añade la ruta: `C:\ffmpeg\bin\`
6. **Verifica la instalación:** Abre PowerShell y ejecuta:
   ```powershell
   ffmpeg -version
   ```

#### Opción B: Usando Chocolatey (recomendado)
```powershell
# Si no tienes Chocolatey, instálalo primero:
# Abre PowerShell como Administrador

choco install ffmpeg
```

#### Opción C: Usando Scoop
```powershell
scoop install ffmpeg
```

#### Opción D: Usando Windows Subsystem for Linux (WSL)
Si usas WSL2, dentro del subsistema Linux:
```bash
sudo apt update
sudo apt install ffmpeg
```

---

### macOS

#### Opción A: Usando Homebrew (recomendado)
```bash
# Instala Homebrew primero si no lo tienes
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Instala FFmpeg
brew install ffmpeg
```

#### Opción B: Descarga manual
1. Visita https://ffmpeg.org/download.html
2. Descarga para macOS
3. Sigue el archivo README incluido

**Verifica la instalación:**
```bash
ffmpeg -version
```

---

### Linux (Ubuntu/Debian)

#### Instalación rápida
```bash
sudo apt update
sudo apt install ffmpeg
```

#### Compilar desde código (opcional, para máxima compatibilidad)
```bash
sudo apt install build-essential curl git
cd /tmp
git clone https://git.ffmpeg.org/ffmpeg.git ffmpeg
cd ffmpeg
./configure --enable-gpl --enable-libx264
make -j$(nproc)
sudo make install
```

**Verifica la instalación:**
```bash
ffmpeg -version
```

---

## 2. Instalación de Dependencias de Python

Desde la raíz del repositorio:

```bash
# En Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# En macOS/Linux
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 3. Verificación de Cámaras disponibles

### Windows
```powershell
# Usa ffmpeg para listar dispositivos
ffmpeg -list_devices true -f dshow -i dummy
```

### macOS
```bash
ffmpeg -f avfoundation -list_devices true -i ""
```

### Linux
```bash
# Debe haber un dispositivo /dev/video0
ls /dev/video*

# Obtén información con v4l2-ctl
sudo apt install v4l-utils
v4l2-ctl --list-devices
```

---

## 4. Uso del Script

### Ejemplo básico: Capturar 10 segundos de video

```bash
python video_capture.py
```

El script guardará el archivo como `output.h264` por defecto.

### Uso avanzado: En tu propio código

```python
from video_capture import WebcamVideoCapture, VideoCaptureConfig

# Crear configuración personalizada
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
capture.start()

# Guardar 20 segundos
capture.save_to_file("video_20s.h264", duration=20)

# O leer frames manualmente
for chunk in capture.read_frames():
    if chunk:
        process_chunk(chunk)  # Tu lógica aquí

capture.stop()
```

---

## 5. Parámetros Configurables

La clase `VideoCaptureConfig` acepta:

| Parámetro | Por defecto | Descripción |
|-----------|-------------|-------------|
| `width` | 1280 | Ancho de la resolución en píxeles |
| `height` | 720 | Altura de la resolución en píxeles |
| `fps` | 30 | Fotogramas por segundo |
| `bitrate` | "2500k" | Bitrate de salida (ej: "5000k" para más calidad) |
| `preset` | "fast" | Velocidad de codificación (ultrafast/superfast/veryfast/faster/fast/medium/slow/slower/veryslow) |
| `crf` | 28 | Calidad (0-51, menor = mejor calidad pero archivo más grande) |
| `read_timeout` | 5.0 | Timeout para lectura en segundos |

### Ejemplos de configuración

**Alta calidad (archivo grande):**
```python
config = VideoCaptureConfig(
    width=1920,
    height=1080,
    fps=60,
    bitrate="8000k",
    preset="slow",
    crf=18
)
```

**Baja latencia (más rápido):**
```python
config = VideoCaptureConfig(
    width=320,
    height=240,
    fps=15,
    bitrate="1000k",
    preset="ultrafast",
    crf=35
)
```

---

## 6. Solución de Problemas

### Error: "FFmpeg no está instalado"
- Verifica que FFmpeg esté en el PATH
- Windows: `where ffmpeg` o prueba desde una nueva ventana de PowerShell
- macOS/Linux: `which ffmpeg`

### Error: "No se puede abrir la cámara" en Windows
- Asegúrate de que la cámara no esté siendo usada por otra aplicación
- Intenta cambiar el dispositivo: `"video=\"0\""` a `"video=\"1\""` en el código
- Verifica permisos: Configuración > Privacidad > Cámara

### Error: "Timeout leyendo desde FFmpeg"
- La cámara puede estar desconectada
- Intenta aumentar `read_timeout` en la configuración

### Baja calidad o stuttering
- Reduce la resolución o FPS
- Disminuye el valor de `crf` (mejor calidad)
- Cambia `preset` a algo más rápido (ultrafast)

### Alto consumo de CPU
- Aumenta el valor de `crf` (compresión más agresiva)
- Cambia `preset` a `fast` o `ultrafast`
- Reduce la resolución

---

## 7. Explicación del Comando FFmpeg

El script genera un comando como este:

```
ffmpeg \
    -hide_banner -loglevel warning -y \
    -f dshow \
    -framerate 30 \
    -video_size 1280x720 \
    -i "video=0" \
    -vf scale=1280:720 \
    -c:v libx264 \
    -preset fast \
    -crf 28 \
    -b:v 2500k \
    -maxrate 2500k \
    -bufsize 2500k \
    -pix_fmt yuv420p \
    -f h264 \
    pipe:1
```

**Desglose de parámetros:**

- `-hide_banner -loglevel warning`: Suprime output verboso
- `-y`: Sobrescribe archivos sin preguntar
- `-f dshow`: Formato de entrada (en Windows es dshow, en macOS avfoundation, en Linux v4l2)
- `-framerate 30`: Captura a 30 FPS
- `-video_size 1280x720`: Tamaño del sensor de entrada
- `-i "video=0"`: Dispositivo de entrada (primera cámara)
- `-vf scale=1280:720`: Escala el video a 1280x720 (si el sensor es diferente)
- `-c:v libx264`: Códec de salida H.264
- `-preset fast`: Balance entre velocidad y compresión
- `-crf 28`: Factor de calidad constante (0=mejor, 51=peor)
- `-b:v 2500k`: Límite de bitrate en 2500 kbps
- `-maxrate/-bufsize`: Parámetros de buffer para evitar picos
- `-pix_fmt yuv420p`: Formato de píxeles compatible con reprodutores
- `-f h264`: Formato de salida (H.264 puro sin contenedor)
- `pipe:1`: Envía la salida a stdout (podemos capturarla con Python)

---

## 8. Conversión Final a Video Reproducible

El archivo `output.h264` es un bitstream puro. Para convertirlo a MP4 o MKV:

```bash
# H.264 puro a MP4
ffmpeg -i output.h264 -vcodec copy -acodec aac output.mp4

# H.264 puro a MKV
ffmpeg -i output.h264 -vcodec copy output.mkv

# Con especificación de FPS (importante)
ffmpeg -r 30 -i output.h264 -vcodec copy output.mp4
```

---

## 9. Referencias

- FFmpeg Official: https://ffmpeg.org
- FFmpeg Filter Documentation: https://ffmpeg.org/ffmpeg-filters.html
- libx264 Encoding Guide: https://trac.ffmpeg.org/wiki/Encode/H.264
- Python subprocess: https://docs.python.org/3/library/subprocess.html
