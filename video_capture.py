#!/usr/bin/env python3
"""
Sistema de captura y codificación de video en tiempo real con FFmpeg.

Este módulo proporciona una interfaz para capturar video de la webcam del sistema,
codificarlo en H.264 y obtener el bitstream de forma continua a través de pipes.

Soporta Windows, macOS y Linux automáticamente.
"""

import subprocess
import platform
import threading
import logging
from typing import Optional, Callable, BinaryIO
from dataclasses import dataclass
import time
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class VideoCaptureConfig:
    """Configuración para la captura de video."""
    
    # Resolución
    width: int = 1280
    height: int = 720
    
    # Framerate
    fps: int = 30
    
    # Bitrate (en kbps)
    bitrate: str = "2500k"
    
    # Preset de calidad (ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow)
    preset: str = "fast"
    
    # Nivel de compresión H.264 (0-51, menor = mejor calidad, mayor compresión)
    crf: int = 28
    
    # Timeout para lectura de datos (segundos)
    read_timeout: float = 5.0


class WebcamVideoCapture:
    """
    Captura y codifica video de la webcam en tiempo real usando FFmpeg.
    
    Ejemplo de uso:
    -------
    >>> config = VideoCaptureConfig(width=1280, height=720, fps=30)
    >>> capture = WebcamVideoCapture(config)
    >>> capture.start()
    >>> 
    >>> # Leer datos del bitstream H.264
    >>> with open('output.h264', 'wb') as f:
    ...     for chunk in capture.read_frames(chunk_size=4096):
    ...         if chunk:
    ...             f.write(chunk)
    ...
    >>> capture.stop()
    """
    
    def __init__(self, config: Optional[VideoCaptureConfig] = None):
        """
        Inicializa la captura de video.
        
        Args:
            config: Configuración de captura. Si no se proporciona, usa valores por defecto.
        """
        self.config = config or VideoCaptureConfig()
        self.process: Optional[subprocess.Popen] = None
        self.is_running = False
        self._frame_count = 0
        self._error_count = 0
        self._max_consecutive_errors = 10
        
    def _get_input_device(self) -> tuple[str, str]:
        """
        Detecta e retorna el dispositivo de entrada compatible con el SO.
        
        Returns:
            tuple: (device_name, input_format)
                - Windows: ("video=\"Nombre de cámara\"", "dshow")
                - macOS: ("0", "avfoundation")
                - Linux: ("/dev/video0", "v4l2")
        """
        system = platform.system()
        
        if system == "Windows":
            # En Windows usamos DirectShow (dshow)
            # Por defecto, "video=0" apunta a la primera cámara
            return "video=\"0\"", "dshow"
        
        elif system == "Darwin":
            # En macOS usamos AVFoundation
            # "0" es la primera cámara disponible
            return "0", "avfoundation"
        
        elif system == "Linux":
            # En Linux usamos Video4Linux2 (v4l2)
            # /dev/video0 es típicamente la primera cámara
            # Si no funciona, intenta /dev/video1, /dev/video2, etc.
            return "/dev/video0", "v4l2"
        
        else:
            raise RuntimeError(f"Sistema operativo no soportado: {system}")
    
    def _build_ffmpeg_command(self) -> list[str]:
        """
        Construye el comando de FFmpeg para captura y codificación.
        
        Returns:
            list: Comando completo como lista de argumentos.
        
        Explicación de parámetros:
        -------
        - input_format: Especifica el formato del dispositivo de entrada
        - framerate: Número de fotogramas por segundo
        - video_size: Resolución de entrada (se puede escalar si es necesario)
        - i: Archivo de entrada (dispositivo de cámara)
        - vf (video filter): Redimensiona el video a los valores especificados
        - c:v libx264: Usa el códec H.264 (libx264)
        - preset: Velocidad de codificación vs calidad (fast = 50/50)
        - crf: Calidad (Constant Rate Factor) - valores bajos = mejor calidad
        - b:v: Bitrate máximo para evitar archivos muy grandes
        - pix_fmt yuv420p: Formato de píxeles compatible con la mayoría de players
        - f rawvideo / -: Salida en formato raw H.264 al stdout
        """
        device, input_format = self._get_input_device()
        
        cmd = [
            "ffmpeg",
            # Suprime la entrada interactiva (promt de sobreescritura)
            "-hide_banner",
            "-loglevel", "warning",
            "-y",  # Sobrescribe archivos sin preguntar
            
            # Parámetros de entrada
            "-f", input_format,  # Formato de entrada
            "-framerate", str(self.config.fps),  # FPS de entrada
        ]
        
        # Agregar video_size solo si es necesario (en Linux y macOS puede causar problemas)
        if platform.system() in ["Windows", "Linux"]:
            cmd.extend(["-video_size", f"{self.config.width}x{self.config.height}"])
        
        cmd.extend([
            "-i", device,  # Dispositivo de entrada
            
            # Filtros de video: redimensionar si es necesario
            "-vf", f"scale={self.config.width}:{self.config.height}",
            
            # Codificación H.264
            "-c:v", "libx264",  # Códec de video
            "-preset", self.config.preset,  # Velocidad/calidad
            "-crf", str(self.config.crf),  # Calidad (0-51)
            
            # Bitrate
            "-b:v", self.config.bitrate,  # Bitrate máximo
            "-maxrate", self.config.bitrate,
            "-bufsize", self.config.bitrate,
            
            # Formato de píxeles (compatibilidad)
            "-pix_fmt", "yuv420p",
            
            # Salida en bitstream H.264 puro a stdout
            "-f", "h264",
            "pipe:1"  # stdout en formato binario
        ])
        
        return cmd
    
    def start(self) -> None:
        """
        Inicia el proceso de captura de video.
        
        Raises:
            RuntimeError: Si FFmpeg no está instalado o no se puede iniciar el proceso.
        """
        if self.is_running:
            logger.warning("La captura ya está en ejecución.")
            return
        
        try:
            cmd = self._build_ffmpeg_command()
            logger.info(f"Iniciando FFmpeg en {platform.system()}...")
            logger.debug(f"Comando: {' '.join(cmd)}")
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0  # Sin buffer para obtener datos en tiempo real
            )
            
            self.is_running = True
            self._frame_count = 0
            self._error_count = 0
            logger.info("Captura de video iniciada correctamente.")
            
        except FileNotFoundError:
            error_msg = (
                "FFmpeg no está instalado o no se encuentra en el PATH.\n"
                "Por favor, instala FFmpeg antes de continuar."
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        except Exception as e:
            logger.error(f"Error al iniciar FFmpeg: {e}")
            raise RuntimeError(f"Error al iniciar el proceso de captura: {e}")
    
    def read_frames(self, chunk_size: int = 4096):
        """
        Lee fotogramas (chunks) del bitstream H.264 de forma continua.
        
        Esto es un generador que yield chunks de datos H.264 continuamente
        mientras la captura esté activa.
        
        Args:
            chunk_size: Tamaño del chunk a leer en cada iteración (bytes).
        
        Yields:
            bytes: Datos del bitstream H.264 o None si hay error.
        
        Example:
        -------
        >>> for chunk in capture.read_frames():
        ...     if chunk:
        ...         process_chunk(chunk)
        """
        if not self.is_running or not self.process:
            logger.error("La captura no está en ejecución.")
            return
        
        try:
            while self.is_running:
                try:
                    chunk = self.process.stdout.read(chunk_size)
                    
                    if chunk:
                        self._error_count = 0  # Reset error counter on success
                        self._frame_count += len(chunk)
                        yield chunk
                    else:
                        # EOF o la cámara fue desconectada
                        self._error_count += 1
                        logger.warning(
                            f"FFmpeg retornó EOF. Errores consecutivos: {self._error_count}"
                        )
                        
                        if self._error_count >= self._max_consecutive_errors:
                            logger.error("Demasiados errores consecutivos. Deteniendo captura.")
                            self.stop()
                            break
                        
                        yield None  # Signal error, continue trying
                        time.sleep(0.5)
                
                except Exception as e:
                    self._error_count += 1
                    logger.error(f"Error al leer desde FFmpeg: {e}")
                    
                    if self._error_count >= self._max_consecutive_errors:
                        logger.error("Demasiados errores consecutivos. Deteniendo captura.")
                        self.stop()
                        break
                    
                    yield None
                    time.sleep(0.5)
        
        except KeyboardInterrupt:
            logger.info("Lectura interrumpida por el usuario.")
            self.stop()
        except Exception as e:
            logger.error(f"Error inesperado en read_frames: {e}")
            self.stop()
    
    def stop(self) -> None:
        """Detiene el proceso de captura."""
        if not self.is_running:
            logger.warning("La captura no está en ejecución.")
            return
        
        self.is_running = False
        
        if self.process:
            try:
                # Terminar de forma graciosa
                self.process.terminate()
                self.process.wait(timeout=5)
                logger.info(f"Captura detenida. Total bytes capturados: {self._frame_count}")
            except subprocess.TimeoutExpired:
                # Force kill si no se termina graciosamente
                self.process.kill()
                logger.warning("FFmpeg fue terminado forzosamente.")
            except Exception as e:
                logger.error(f"Error al detener FFmpeg: {e}")
    
    def get_stats(self) -> dict:
        """Retorna estadísticas de la captura."""
        return {
            "is_running": self.is_running,
            "total_bytes": self._frame_count,
            "error_count": self._error_count,
            "config": {
                "resolution": f"{self.config.width}x{self.config.height}",
                "fps": self.config.fps,
                "bitrate": self.config.bitrate,
                "crf": self.config.crf,
            }
        }
    
    def save_to_file(self, output_path: str, duration: Optional[float] = None) -> None:
        """
        Guarda el video capturado a un archivo H.264.
        
        Args:
            output_path: Ruta del archivo de salida.
            duration: Duración máxima en segundos (None = infinito hasta que se detenga).
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Guardando video a: {output_path}")
        
        try:
            with open(output_path, 'wb') as f:
                start_time = time.time()
                
                for chunk in self.read_frames():
                    if chunk:
                        f.write(chunk)
                    
                    # Verificar duración límite
                    if duration and (time.time() - start_time) > duration:
                        logger.info(f"Duración máxima alcanzada: {duration}s")
                        self.stop()
                        break
            
            logger.info(f"Video guardado exitosamente en: {output_path}")
        
        except KeyboardInterrupt:
            logger.info("Guardado interrumpido por el usuario.")
            self.stop()
        except Exception as e:
            logger.error(f"Error al guardar el video: {e}")
            raise


def main():
    """Función principal para demostración."""
    import sys
    
    logger.info("Iniciando captura de video...")
    logger.info(f"Sistema operativo detectado: {platform.system()}")
    
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
    
    try:
        capture.start()
        
        # Método 1: Guardar a archivo por 10 segundos
        capture.save_to_file("output.h264", duration=10)
        
        # Método 2: Lectura manual (descomenta si lo necesitas)
        # for chunk in capture.read_frames():
        #     if chunk:
        #         print(f"Capturados {len(chunk)} bytes")
        
    except KeyboardInterrupt:
        logger.info("Programa interrumpido por el usuario.")
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        capture.stop()
        stats = capture.get_stats()
        logger.info(f"Estadísticas finales: {stats}")


if __name__ == "__main__":
    main()
