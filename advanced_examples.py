#!/usr/bin/env python3
"""
Configuraciones avanzadas y casos de uso especializado.

Este archivo contiene ejemplos de configuración para casos de uso específicos
y patrones avanzados de uso del sistema de captura de video.
"""

from video_capture import WebcamVideoCapture, VideoCaptureConfig
import threading
import time
from pathlib import Path
from datetime import datetime


# =============================================================================
# CONFIGURACIONES PREDEFINIDAS
# =============================================================================

class PresetConfigs:
    """Colección de configuraciones predefinidas para casos de uso comunes."""
    
    # Captura web en vivo (balance calidad/tamaño)
    STREAMING = VideoCaptureConfig(
        width=1280,
        height=720,
        fps=30,
        bitrate="2500k",
        preset="fast",
        crf=28
    )
    
    # Conferencias remotas (prioriza claridad de rostros)
    VIDEO_CALL = VideoCaptureConfig(
        width=960,
        height=720,
        fps=30,
        bitrate="2000k",
        preset="faster",
        crf=26
    )
    
    # Grabación de reuniones (máxima calidad)
    RECORDING_HD = VideoCaptureConfig(
        width=1920,
        height=1080,
        fps=30,
        bitrate="6000k",
        preset="medium",
        crf=22
    )
    
    # Transmisión en vivo (máxima compresión para ancho de banda limitado)
    LIVE_STREAMING = VideoCaptureConfig(
        width=854,
        height=480,
        fps=24,
        bitrate="1500k",
        preset="superfast",
        crf=32
    )
    
    # Análisis de video en tiempo real (baja latencia)
    REAL_TIME_ANALYSIS = VideoCaptureConfig(
        width=640,
        height=480,
        fps=30,
        bitrate="1500k",
        preset="ultrafast",
        crf=35
    )
    
    # Documentación de pantallas (máxima claridad de detalles)
    SCREEN_DOC = VideoCaptureConfig(
        width=1920,
        height=1080,
        fps=60,
        bitrate="8000k",
        preset="slow",
        crf=18
    )
    
    # Vigilancia 24/7 (optimizado para archivo pequeño)
    SURVEILLANCE = VideoCaptureConfig(
        width=640,
        height=480,
        fps=10,
        bitrate="800k",
        preset="ultrafast",
        crf=38
    )
    
    # Juego/ScreenCast (alta calidad y FPS)
    GAMING = VideoCaptureConfig(
        width=1920,
        height=1080,
        fps=60,
        bitrate="10000k",
        preset="faster",
        crf=20
    )


# =============================================================================
# CAPTURA CON ROTACIÓN AUTOMÁTICA DE ARCHIVOS
# =============================================================================

class MultiFileCapture:
    """
    Captura video dividiendo en múltiples archivos por duración.
    
    Útil para grabar sesiones largas sin crear archivos enormes.
    """
    
    def __init__(self, output_dir: str = ".", file_duration: float = 600):
        """
        Args:
            output_dir: Directorio donde guardar los archivos
            file_duration: Duración de cada archivo en segundos (default: 10 minutos)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.file_duration = file_duration
        self.capture = None
    
    def start(self, config: VideoCaptureConfig = None):
        """Inicia la captura."""
        if config is None:
            config = PresetConfigs.STREAMING
        
        self.capture = WebcamVideoCapture(config)
        self.capture.start()
    
    def stop(self):
        """Detiene la captura."""
        if self.capture:
            self.capture.stop()
    
    def record_with_rotation(self, total_duration: float = None):
        """
        Graba video dividiendo en múltiples archivos.
        
        Args:
            total_duration: Duración total en segundos (None = infinito)
        """
        start_time = time.time()
        file_count = 0
        
        while True:
            file_count += 1
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.output_dir / f"video_{timestamp}_{file_count:03d}.h264"
            
            print(f"Grabando archivo {file_count}: {output_file}")
            
            try:
                # Guardar chunk de duración específica
                file_start = time.time()
                bytes_written = 0
                
                with open(output_file, 'wb') as f:
                    for chunk in self.capture.read_frames():
                        if chunk:
                            f.write(chunk)
                            bytes_written += len(chunk)
                        
                        elapsed = time.time() - file_start
                        if elapsed > self.file_duration:
                            break
                        
                        # Verificar duración total
                        if total_duration and (time.time() - start_time) > total_duration:
                            print(f"Duración total completada")
                            return
                
                print(f"  ✓ Archivo guardado: {bytes_written:,} bytes")
            
            except Exception as e:
                print(f"  ✗ Error grabando archivo: {e}")
                break


# =============================================================================
# CAPTURA MULTIHILO CON PROCESAMIENTO EN PARALELO
# =============================================================================

class ParallelCapture:
    """
    Captura video mientras procesa frames en paralelo en otro thread.
    
    Ejemplo:
        processor = frame_processor  # tu función de procesamiento
        capture = ParallelCapture(processor)
        capture.start()
        capture.wait()
    """
    
    def __init__(self, frame_processor, config: VideoCaptureConfig = None):
        """
        Args:
            frame_processor: Función callable que procesa cada chunk
            config: Configuración de captura
        """
        self.frame_processor = frame_processor
        self.config = config or PresetConfigs.REAL_TIME_ANALYSIS
        self.capture = WebcamVideoCapture(self.config)
        self.processing_thread = None
        self.should_stop = False
        self.queue = []
        self.queue_lock = threading.Lock()
    
    def _processing_worker(self):
        """Procesa frames en background."""
        while not self.should_stop:
            chunk = None
            
            with self.queue_lock:
                if self.queue:
                    chunk = self.queue.pop(0)
            
            if chunk:
                try:
                    self.frame_processor(chunk)
                except Exception as e:
                    print(f"Error procesando frame: {e}")
            else:
                time.sleep(0.001)  # Evitar busy waiting
    
    def start(self):
        """Inicia captura y procesamiento."""
        self.capture.start()
        
        self.processing_thread = threading.Thread(
            target=self._processing_worker,
            daemon=True
        )
        self.processing_thread.start()
        
        print("Captura paralela iniciada")
    
    def capture_frames(self, duration: float = None):
        """Captura frames durante el tiempo especificado."""
        start_time = time.time()
        
        for chunk in self.capture.read_frames():
            if chunk:
                with self.queue_lock:
                    self.queue.append(chunk)
            
            if duration and (time.time() - start_time) > duration:
                break
    
    def stop(self):
        """Detiene captura y procesamiento."""
        self.should_stop = True
        self.capture.stop()
        
        if self.processing_thread:
            self.processing_thread.join(timeout=5)
        
        print("Captura paralela detenida")


# =============================================================================
# CAPTURA CON DETECCIÓN DE CAMBIOS
# =============================================================================

class SmartCapture:
    """
    Captura solo cuando detecta cambios significativos en el video.
    
    Útil para vigilancia o para ahorrar espacio en disco.
    """
    
    def __init__(self, config: VideoCaptureConfig = None, 
                 change_threshold: float = 0.05):
        """
        Args:
            config: Configuración de captura
            change_threshold: Porcentaje mínimo de cambio para grabar (0-1)
        """
        self.config = config or PresetConfigs.SURVEILLANCE
        self.capture = WebcamVideoCapture(self.config)
        self.change_threshold = change_threshold
        self.last_frame_hash = None
    
    def _calculate_simple_hash(self, chunk: bytes) -> int:
        """Calcula un hash simple del chunk para detectar cambios."""
        # Implementación simple: suma de bytes cada N posiciones
        return sum(chunk[i:i+1] for i in range(0, len(chunk), len(chunk)//100 or 1))
    
    def start_smart_recording(self, output_file: str, duration: float = None):
        """
        Graba solo cuando detecta cambios significativos.
        """
        self.capture.start()
        
        with open(output_file, 'wb') as f:
            start_time = time.time()
            frames_captured = 0
            frames_saved = 0
            
            for chunk in self.capture.read_frames():
                if chunk:
                    frames_captured += 1
                    
                    # Calcular cambio
                    current_hash = self._calculate_simple_hash(chunk)
                    
                    if self.last_frame_hash is None:
                        should_save = True
                    else:
                        change_ratio = abs(current_hash - self.last_frame_hash) / (self.last_frame_hash or 1)
                        should_save = change_ratio > self.change_threshold
                    
                    if should_save:
                        f.write(chunk)
                        frames_saved += 1
                        self.last_frame_hash = current_hash
                
                if duration and (time.time() - start_time) > duration:
                    break
            
            self.capture.stop()
            
            ratio = (frames_saved / frames_captured * 100) if frames_captured > 0 else 0
            print(f"Grabación completada:")
            print(f"  Frames capturados: {frames_captured}")
            print(f"  Frames guardados: {frames_saved} ({ratio:.1f}%)")


# =============================================================================
# EJEMPLOS DE USO
# =============================================================================

def ejemplo_streaming_webcam():
    """Ejemplo: Setup para streaming en vivo."""
    print("\n" + "="*60)
    print("Ejemplo: Streaming en vivo")
    print("="*60)
    
    config = PresetConfigs.STREAMING
    print(f"Configuración: {config.width}x{config.height} @ {config.fps}fps")
    
    capture = WebcamVideoCapture(config)
    capture.start()
    capture.save_to_file("streaming.h264", duration=5)
    capture.stop()


def ejemplo_vigilancia_24h():
    """Ejemplo: Sistema de vigilancia 24/7."""
    print("\n" + "="*60)
    print("Ejemplo: Vigilancia 24/7 con rotación de archivos")
    print("="*60)
    
    multi_capture = MultiFileCapture(output_dir="surveillance", file_duration=60)
    multi_capture.start(PresetConfigs.SURVEILLANCE)
    
    # Grabar 2 archivos de 30 segundos cada uno (total 1 minuto)
    multi_capture.record_with_rotation(total_duration=60)
    
    multi_capture.stop()


def ejemplo_procesamiento_paralelo():
    """Ejemplo: Procesamiento de video en paralelo."""
    print("\n" + "="*60)
    print("Ejemplo: Captura con procesamiento paralelo")
    print("="*60)
    
    def mi_procesador(chunk):
        """Función de procesamiento personalizada."""
        # Aquí puedes procesar cada chunk de video
        # Por ejemplo: análisis facial, detección de objetos, etc.
        print(f"  Procesando {len(chunk)} bytes...")
    
    parallel = ParallelCapture(mi_procesador)
    parallel.start()
    parallel.capture_frames(duration=3)
    parallel.stop()


def ejemplo_videollamada():
    """Ejemplo: Configuración para videollamadas."""
    print("\n" + "="*60)
    print("Ejemplo: Configuración para videollamadas")
    print("="*60)
    
    config = PresetConfigs.VIDEO_CALL
    print(f"Configuración: {config.width}x{config.height} @ {config.fps}fps, bitrate: {config.bitrate}")
    
    capture = WebcamVideoCapture(config)
    capture.start()
    capture.save_to_file("videollamada.h264", duration=5)
    capture.stop()


if __name__ == "__main__":
    import sys
    
    print("\n" + "="*60)
    print("EJEMPLOS AVANZADOS - CAPTURA DE VIDEO")
    print("="*60)
    
    ejemplos = {
        "1": ("Streaming en vivo", ejemplo_streaming_webcam),
        "2": ("Vigilancia 24/7", ejemplo_vigilancia_24h),
        "3": ("Procesamiento paralelo", ejemplo_procesamiento_paralelo),
        "4": ("Videollamada", ejemplo_videollamada),
    }
    
    print("\nEjemplos disponibles:")
    for key, (nombre, _) in ejemplos.items():
        print(f"  {key}: {nombre}")
    
    print("\nSelecciona un ejemplo (1-4) o 'q' para salir:")
    
    try:
        choice = input().strip()
        
        if choice in ejemplos:
            nombre, func = ejemplos[choice]
            print(f"\nEjecutando: {nombre}")
            func()
        elif choice != 'q':
            print("Opción inválida")
    
    except KeyboardInterrupt:
        print("\n[Programa interrumpido]")
