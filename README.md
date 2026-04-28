# 🎥 Sistema de Captura y Transmisión de Video en Vivo

Sistema H.264 de captura de video en tiempo real desde la cámara web. Transmite video vivo directamente a:
- **FFmpeg pop-up window** (reproducción directa)
- **Navegador web** (transmisión por WebSocket)

## ¿Cómo Funciona?

### Arquitectura General

```
Cámara Integrada
      ↓
[FFmpeg en video_capture.py]
  • Captura en 30 FPS
  • Codifica a H.264
  • Aplica deinterlacing (yadif)
  • Escala a 480x360 con Lanczos
  • Bitrate: 8000k, Calidad CRF: 18
      ↓
[emisor_directo.py]
  • Lee bitstream H.264
  • Envía a puerto TCP 5000
```

### Flujo de Datos

**Opción 1: Sistema Directo (FFmpeg Pop-up)**
```
emisor_directo.py (servidor) 
    ↓ TCP Socket :5000 (H.264 raw)
receptor_directo.py (cliente) 
    ↓
FFmpeg ffplay window (decodificación y reproducción)
```

**Opción 2: Sistema Web (Navegador)**
```
emisor_directo.py (servidor)
    ↓ TCP Socket :5000 (H.264 raw)
receptor_web.py (servidor Flask)
    ↓ Cola Buffer (30 frames máximo)
    ↓ WebSocket :8080
Navegador (Cliente Web)
    ↓ JMuxer (decodificador)
    ↓
Video HTML5 <video> element
```

## Archivos Clave

### `video_capture.py`
**Propósito:** Encapsula FFmpeg para captura y codificación H.264

**Qué hace:**
- Detecta el tipo de SO (Windows/macOS/Linux)
- Inicializa FFmpeg con parámetros de captura
- Lee el bitstream H.264 en chunks
- Maneja errores de conexión con reintentos

**Configuración actual:**
```python
width: 480        # Resolución horizontal
height: 360       # Resolución vertical
fps: 30           # Fotogramas por segundo
bitrate: 8000k    # Calidad de datos
crf: 18           # Nivel de compresión (menor = mejor)
preset: ultrafast # Velocidad de codificación
```

**Filtros FFmpeg:**
- `yadif=0:-1:0` - Deinterlacing (elimina artefactos de video entrelazado)
- `scale=480:360:flags=lanczos` - Escalado de alta calidad

### `emisor_directo.py`
**Propósito:** Captura video y lo transmite a través de TCP socket

**Flujo:**
1. Crea socket TCP escuchando en `localhost:5000`
2. Espera conexión del receptor
3. Inicia FFmpeg y captura video
4. Lee chunks H.264 y envía por socket
5. Continúa indefinidamente hasta desconexión

**Manejo de errores:**
- Reintentos automáticos si hay desconexión
- Límite de 10 errores consecutivos antes de detener

## 🚀 Uso

### Sistema Directo (FFmpeg Pop-up)

En dos terminales:
```powershell
# Terminal 1 (Cliente - receptor de video)
cd c:\CLIENTE_COMMOV
python receptor_directo.py

# Terminal 2 (Servidor - emisor de video)
cd c:\SERVIDOR_COMMOV
python emisor_directo.py
```

Se abrirá una ventana de reproducción FFmpeg con el video en vivo.

### Sistema Web (Navegador)

En una sola terminal:
```powershell
cd c:\SERVIDOR_COMMOV
python iniciar_todo.py
```

Luego abre en tu navegador:
```
http://localhost:8080
```

El script hace todo automáticamente:
1. Inicia `receptor_web.py` en puerto 8080 (Flask + WebSocket)
2. Espera 7 segundos para que el receptor esté listo
3. Inicia `emisor_directo.py` para capturar video

## 📊 Parámetros de Calidad

**Bitrate 8000k** = aproximadamente 1 MB/segundo
- CRF 18 = Alta calidad, mínima compresión
- Deinterlacing = Elimina líneas entrelazadas
- Lanczos scaling = Mejor calidad al redimensionar
- Keyframe cada 2 segundos = Mejor para saltos de conexión

## 🔧 Requisitos

- **Python 3.8+**
- **FFmpeg** instalado y en PATH
- **Flask** (solo para sistema web): `pip install flask flask-sock werkzeug`

## 📝 Notas Técnicas

- Windows usa DirectShow para acceso a cámara: `video=Integrated Camera`
- macOS usa AVFoundation
- Linux usa v4l2 (Video4Linux2)
- H.264 es un codec estándar de máxima compatibilidad
- La transmisión es TCP (no UDP) para garantizar entrega de todos los datos
- No hay almacenamiento - el video es puro stream en vivo
