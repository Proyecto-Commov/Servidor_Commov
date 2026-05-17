#!/usr/bin/env python3
"""
video_server.py — Proceso 1: Servidor de vídeo en tiempo real

Responsabilidad:
- Capturar la webcam mediante FFmpeg
- Codificar en H.264 usando h264_nvenc (con fallback a libx264)
- Emitir el stream en formato MPEG-TS por socket TCP
- Actuar como servidor TCP escuchando conexiones

Maneja reconexiones de cliente de forma limpia.
"""

import socket
import subprocess
import threading
import logging
import sys
import signal
import atexit
from typing import Optional
from pathlib import Path

# =============================================================================
# CONFIGURACIÓN — modifica estos valores según tu entorno
# =============================================================================
VIDEO_DEVICE        = "/dev/video2"      # Dispositivo de captura V4L2 (USB externo; /dev/video0 = laptop)
VIDEO_PORT          = 9000               # Puerto TCP en el que escucha este servidor
VIDEO_BIND_HOST     = "0.0.0.0"         # Interfaz de escucha ("0.0.0.0" = todas)
VIDEO_BITRATE       = "2000k"           # Bitrate de codificación H.264
VIDEO_FRAMERATE     = 30                 # FPS de captura y codificación
VIDEO_WIDTH         = 0                  # 0 = resolución nativa de la webcam
VIDEO_HEIGHT        = 0                  # 0 = resolución nativa de la webcam
FFMPEG_ENCODER      = "h264_nvenc"      # Encoder principal (fallback: libx264)
FFMPEG_PRESET_NVENC = "llhq"            # Preset para nvenc (low-latency high quality)
FFMPEG_PRESET_CPU   = "ultrafast"       # Preset para libx264
LOG_LEVEL           = "INFO"            # Nivel de log: DEBUG, INFO, WARNING
# =============================================================================

# Configurar logging
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=getattr(logging, LOG_LEVEL),
)
logger = logging.getLogger(__name__)

# Global variables for cleanup
_ffmpeg_proc: Optional[subprocess.Popen] = None
_server_socket: Optional[socket.socket] = None
_shutdown_event = threading.Event()


def cleanup():
    """Limpia todos los recursos antes de salir."""
    global _ffmpeg_proc, _server_socket
    
    logger.info("Iniciando limpieza de recursos...")
    _shutdown_event.set()
    
    # Cerrar socket servidor
    if _server_socket:
        try:
            _server_socket.close()
            logger.info("Socket servidor cerrado")
        except Exception as e:
            logger.warning(f"Error cerrando socket servidor: {e}")
    
    # Terminar proceso FFmpeg
    if _ffmpeg_proc and _ffmpeg_proc.poll() is None:
        try:
            logger.info(f"Terminando proceso FFmpeg (PID: {_ffmpeg_proc.pid})...")
            _ffmpeg_proc.terminate()
            try:
                _ffmpeg_proc.wait(timeout=5)
                logger.info("Proceso FFmpeg terminado correctamente")
            except subprocess.TimeoutExpired:
                logger.warning("Timeout esperando FFmpeg, enviando KILL...")
                _ffmpeg_proc.kill()
                _ffmpeg_proc.wait()
                logger.info("Proceso FFmpeg forzado a terminar (kill)")
        except Exception as e:
            logger.error(f"Error terminando FFmpeg: {e}")
    
    logger.info("Limpieza completada")


def signal_handler(signum, frame):
    """Maneja señales de terminación (SIGINT, SIGTERM)."""
    logger.info(f"Señal {signum} recibida, cerrando...")
    cleanup()
    sys.exit(0)


# Registrar handlers para signals
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
atexit.register(cleanup)


def check_encoder_availability() -> str:
    """
    Verifica qué encoder está disponible (h264_nvenc primero, fallback a libx264).
    
    Returns:
        str: nombre del encoder disponible ("h264_nvenc" o "libx264")
    """
    try:
        result = subprocess.run(
            ["ffmpeg", "-encoders"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        encoders_output = result.stdout + result.stderr
        
        if "h264_nvenc" in encoders_output:
            logger.info("Encoder h264_nvenc disponible — usando GPU NVIDIA")
            return "h264_nvenc"
        elif "libx264" in encoders_output:
            logger.warning(
                "h264_nvenc NO disponible — fallback a libx264 (CPU, más lento)"
            )
            return "libx264"
        else:
            raise RuntimeError("Ningún encoder H.264 disponible")
    except Exception as e:
        logger.error(f"Error comprobando encoders: {e}")
        raise


def build_ffmpeg_command(encoder: str) -> list[str]:
    """
    Construye el comando ffmpeg según el encoder seleccionado.
    
    Args:
        encoder: "h264_nvenc" o "libx264"
        
    Returns:
        list[str]: comando ffmpeg como lista de argumentos
    """
    base_cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "warning",
        "-fflags", "nobuffer",
        "-flags", "low_delay",
        "-max_delay", "0",
        "-i", VIDEO_DEVICE,
        "-c:v", encoder,
        "-b:v", VIDEO_BITRATE,
        "-r", str(VIDEO_FRAMERATE),
        "-f", "mpegts",
        "pipe:1",  # Salida a stdout (se redireccionará al socket)
    ]
    
    # Agregar parámetros específicos del encoder
    if encoder == "h264_nvenc":
        base_cmd.extend(["-preset", FFMPEG_PRESET_NVENC])
    elif encoder == "libx264":
        base_cmd.extend(["-preset", FFMPEG_PRESET_CPU, "-tune", "zerolatency"])
    
    # Agregar resolución si está configurada
    if VIDEO_WIDTH > 0 and VIDEO_HEIGHT > 0:
        base_cmd.extend(["-s", f"{VIDEO_WIDTH}x{VIDEO_HEIGHT}"])
    
    return base_cmd


def handle_client_connection(
    client_socket: socket.socket,
    client_addr: tuple,
    ffmpeg_proc: subprocess.Popen,
) -> None:
    """
    Maneja la conexión de un cliente: envía el stream MPEG-TS desde FFmpeg.
    
    Args:
        client_socket: socket del cliente conectado
        client_addr: tupla (ip, puerto) del cliente
        ffmpeg_proc: proceso subprocess de FFmpeg
    """
    logger.info(f"Cliente conectado: {client_addr}")
    try:
        # Leer bytes de FFmpeg stdout y enviar al cliente
        while True:
            chunk = ffmpeg_proc.stdout.read(65536)  # 64KB chunks
            if not chunk:
                logger.warning("FFmpeg stream terminado inesperadamente")
                break
            
            try:
                client_socket.sendall(chunk)
            except (BrokenPipeError, ConnectionResetError):
                logger.info(f"Cliente desconectado: {client_addr}")
                break
    except Exception as e:
        logger.error(f"Error enviando vídeo a {client_addr}: {e}")
    finally:
        try:
            client_socket.close()
        except:
            pass
        logger.info(f"Conexión cerrada: {client_addr}")


def run_server() -> None:
    """
    Inicia el servidor TCP que escucha conexiones de clientes y emite el stream.
    """
    global _ffmpeg_proc, _server_socket
    
    # Verificar disponibilidad de encoder
    encoder = check_encoder_availability()
    
    # Construir comando FFmpeg
    ffmpeg_cmd = build_ffmpeg_command(encoder)
    logger.info(f"Comando FFmpeg: {' '.join(ffmpeg_cmd)}")
    
    # Iniciar proceso FFmpeg
    try:
        _ffmpeg_proc = subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,  # Sin buffer
        )
        logger.info(f"Proceso FFmpeg iniciado (PID: {_ffmpeg_proc.pid})")
    except Exception as e:
        logger.error(f"Error iniciando FFmpeg: {e}")
        sys.exit(1)
    
    # Crear socket TCP servidor
    _server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        _server_socket.bind((VIDEO_BIND_HOST, VIDEO_PORT))
        _server_socket.listen(1)
        logger.info(f"Servidor TCP escuchando en {VIDEO_BIND_HOST}:{VIDEO_PORT}")
        
        # Bucle de aceptación de conexiones
        while not _shutdown_event.is_set():
            try:
                _server_socket.settimeout(1)  # Timeout para poder verificar shutdown
                client_socket, client_addr = _server_socket.accept()
                # Crear thread para manejar este cliente (permite que se desconecte sin matar FFmpeg)
                client_thread = threading.Thread(
                    target=handle_client_connection,
                    args=(client_socket, client_addr, _ffmpeg_proc),
                    daemon=True,
                )
                client_thread.start()
            except socket.timeout:
                continue  # Verificar shutdown_event
            except KeyboardInterrupt:
                logger.info("Interrupción del usuario detectada")
                break
            except Exception as e:
                logger.error(f"Error aceptando conexión: {e}")
    except KeyboardInterrupt:
        logger.info("Servidor interrumpido por el usuario")
    except Exception as e:
        logger.error(f"Error en servidor TCP: {e}")
    finally:
        cleanup()


if __name__ == "__main__":
    run_server()
