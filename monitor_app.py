#!/usr/bin/env python3
"""
monitor_app.py — Proceso 3: Aplicación cliente de monitorización en tiempo real

Responsabilidad:
- Interfaz gráfica con PyQt6 (QMainWindow)
- Consumir stream de vídeo del Proceso 1 (video_server.py)
- Consumir datos de temperatura del Proceso 2 (sensor externo o temp_simulator.py)
- Mostrar vídeo, temperatura actual, clasificación, gráfico histórico, alertas

Arquitectura:
- QThread #1: VideoWorker — decodifica y emite frames
- QThread #2: SensorWorker — lee datos JSON de temperatura
- Hilo principal: Qt event loop con UI responsiva
"""

import socket
import json
import logging
import sys
import os
import signal
import subprocess
import threading
import time
from collections import deque
from pathlib import Path
from typing import Optional
from datetime import datetime

import numpy as np
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLCDNumber,
    QStatusBar,
    QMessageBox,
    QPushButton,
)
from PyQt6.QtCore import (
    Qt,
    QThread,
    QObject,
    pyqtSignal,
    pyqtSlot,
    QTimer,
    QSize,
    QPointF,
)
from PyQt6.QtGui import QImage, QPixmap, QFont, QColor, QPainter, QLinearGradient, QBrush
import pyqtgraph as pg
import av

# =============================================================================
# CONFIGURACIÓN — modifica estos valores según tu entorno
# =============================================================================
# Conexión vídeo (Proceso 1)
VIDEO_HOST              = "127.0.0.1"
VIDEO_PORT              = 9000
VIDEO_RECONNECT_DELAY   = 3              # segundos entre reintentos

# Conexión sensor (Proceso 2 — externo)
SENSOR_HOST             = "127.0.0.1"
SENSOR_PORT             = 9001
SENSOR_RECONNECT_DELAY  = 3

# UI — panel de vídeo
VIDEO_DISPLAY_WIDTH     = 800            # píxeles de ancho del panel de vídeo
VIDEO_DISPLAY_HEIGHT    = 450            # píxeles de alto del panel de vídeo

# UI — gráfico de temperatura
TEMP_HISTORY_SIZE       = 60            # número de muestras en el gráfico
TEMP_ALERT_THRESHOLD    = 60.0          # °C — umbral de alerta

# Clasificaciones y sus colores (fondo del panel de clasificación)
CLASSIFICATION_COLORS = {
    "frio":           "#4A90D9",   # Azul
    "templado":       "#5BAD6F",   # Verde
    "caliente":       "#E8963A",   # Naranja
    "muy caliente":   "#D95B3A",   # Rojo naranja
    "crítico":        "#C0392B",   # Rojo oscuro
}

LOG_LEVEL           = "INFO"            # Nivel de log: DEBUG, INFO, WARNING
# =============================================================================

# Configurar logging
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=getattr(logging, LOG_LEVEL),
)
logger = logging.getLogger(__name__)


class VideoWorker(QObject):
    """
    Worker que corre en QThread separado.
    
    Responsabilidad:
    - Capturar vídeo de webcam usando FFmpeg directamente
    - Decodificar con PyAV (av.open + container.decode)
    - Convertir VideoFrame → numpy array RGB → QImage
    - Emitir frames via pyqtSignal
    
    Señales:
    - frame_ready(QImage): nuevo frame decodificado
    - connection_status(bool): True si conectado, False si desconectado
    """
    
    frame_ready = pyqtSignal(QImage)
    connection_status = pyqtSignal(bool)
    
    def __init__(self):
        super().__init__()
        self._stop_event = threading.Event()
        self.is_connected = False
        self._ffmpeg_proc = None
    
    def run(self):
        """Bucle principal del worker."""
        while not self._stop_event.is_set():
            try:
                self._capture_and_stream()
            except Exception as e:
                logger.error(f"Error en VideoWorker: {e}")
                self.is_connected = False
                self.connection_status.emit(False)
            
            # Si se paró voluntariamente, salir
            if self._stop_event.is_set():
                break
            
            # Intentar reconectar
            logger.info(f"Reconectando vídeo en {VIDEO_RECONNECT_DELAY}s...")
            self._stop_event.wait(VIDEO_RECONNECT_DELAY)
    
    def _capture_and_stream(self):
        """Captura vídeo de webcam con FFmpeg y procesa el stream."""
        # Comando FFmpeg para capturar de /dev/video2 y codificar a MPEG-TS
        ffmpeg_cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel", "warning",
            "-fflags", "nobuffer",
            "-flags", "low_delay",
            "-max_delay", "0",
            "-input_format", "mjpeg",
            "-i", "/dev/video2",
            "-c:v", "libx264",  # Use CPU encoding for reliability
            "-preset", "ultrafast",
            "-tune", "zerolatency",
            "-b:v", "2000k",
            "-r", "30",
            "-f", "mpegts",
            "pipe:1",
        ]
        
        try:
            logger.info("Iniciando captura de vídeo con FFmpeg...")
            self._ffmpeg_proc = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,
            )
            logger.info(f"Proceso FFmpeg iniciado (PID: {self._ffmpeg_proc.pid})")
            
            self.is_connected = True
            self.connection_status.emit(True)
            logger.info("Conectado a webcam ✓")
            
            # Abrir stream desde FFmpeg stdout
            try:
                container = av.open(
                    self._ffmpeg_proc.stdout,
                    format="mpegts",
                    options={
                        "rtbufsize": "10485760",
                        "max_delay": "0",
                        "probesize": "1024000",
                    },
                )
                logger.info(f"Contenedor abierto: {len(container.streams)} streams")
                
                # Verificar que hay stream de vídeo
                if not container.streams.video:
                    logger.error("No hay streams de vídeo en el contenedor")
                    return
                
                logger.info(f"Stream de vídeo: {container.streams.video[0]}")
                
                # Decodificar stream
                frame_count = 0
                for frame in container.decode(video=0):
                    if self._stop_event.is_set():
                        break
                    
                    frame_count += 1
                    if frame_count % 30 == 0:
                        logger.debug(f"Frame {frame_count} decodificado: {frame.width}x{frame.height}")
                    
                    try:
                        # Convertir a numpy array RGB
                        np_frame = frame.to_ndarray(format="rgb24")
                        
                        # Convertir numpy array a QImage
                        height, width, _ = np_frame.shape
                        bytes_per_line = 3 * width
                        q_image = QImage(
                            np_frame.tobytes(),
                            width,
                            height,
                            bytes_per_line,
                            QImage.Format.Format_RGB888,
                        )
                        
                        # IMPORTANTE: copiar la QImage para evitar corrupción de memoria
                        q_image = q_image.copy()
                        self.frame_ready.emit(q_image)
                    except Exception as e:
                        logger.warning(f"Error convirtiendo frame {frame_count}: {e}")
                        continue
                
                logger.info(f"Stream terminado después de {frame_count} frames")
                
            except Exception as e:
                logger.error(f"Error abriendo contenedor: {e}", exc_info=True)
                raise
        
        except Exception as e:
            logger.error(f"Error capturando vídeo: {e}", exc_info=True)
        finally:
            self.is_connected = False
            self.connection_status.emit(False)
            if self._ffmpeg_proc:
                try:
                    self._ffmpeg_proc.terminate()
                    self._ffmpeg_proc.wait(timeout=2)
                except:
                    try:
                        self._ffmpeg_proc.kill()
                    except:
                        pass
    
    def stop(self):
        """Detener el worker."""
        self._stop_event.set()
        if self._ffmpeg_proc:
            try:
                self._ffmpeg_proc.terminate()
                self._ffmpeg_proc.wait(timeout=2)
            except:
                try:
                    self._ffmpeg_proc.kill()
                except:
                    pass
    
    def _connect_and_stream(self):
        """Conecta al servidor de vídeo y procesa el stream."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        
        try:
            logger.info(f"Conectando al servidor vídeo {VIDEO_HOST}:{VIDEO_PORT}...")
            sock.connect((VIDEO_HOST, VIDEO_PORT))
            logger.info("Socket conectado ✓")
            
            # Leer datos de prueba para verificar que el stream está llegando
            sock.settimeout(5)
            test_data = sock.recv(1024)
            if not test_data:
                logger.error("No se reciben datos del servidor vídeo")
                return
            logger.info(f"Datos recibidos: {len(test_data)} bytes (primeros: {test_data[:20]}...)")
            
            # Crear un buffer para acumular datos del socket
            sock.settimeout(2)
            
            try:
                container = av.open(
                    _SocketReader(sock),
                    format="mpegts",
                    options={
                        "rtbufsize": "10485760",
                        "max_delay": "0",
                        "probesize": "1024000",
                    },
                )
                logger.info(f"Contenedor abierto: {len(container.streams)} streams")
                
                # Verificar que hay stream de vídeo
                if not container.streams.video:
                    logger.error("No hay streams de vídeo en el contenedor")
                    return
                
                logger.info(f"Stream de vídeo: {container.streams.video[0]}")
                
                self.is_connected = True
                self.connection_status.emit(True)
                logger.info("Conectado al servidor vídeo ✓")
                
                # Decodificar stream
                frame_count = 0
                for frame in container.decode(video=0):
                    if self._stop_event.is_set():
                        break
                    
                    frame_count += 1
                    if frame_count % 30 == 0:
                        logger.debug(f"Frame {frame_count} decodificado: {frame.width}x{frame.height}")
                    
                    try:
                        # Convertir a numpy array RGB
                        np_frame = frame.to_ndarray(format="rgb24")
                        
                        # Convertir numpy array a QImage
                        height, width, _ = np_frame.shape
                        bytes_per_line = 3 * width
                        q_image = QImage(
                            np_frame.tobytes(),
                            width,
                            height,
                            bytes_per_line,
                            QImage.Format.Format_RGB888,
                        )
                        
                        # IMPORTANTE: copiar la QImage para evitar corrupción de memoria
                        q_image = q_image.copy()
                        self.frame_ready.emit(q_image)
                    except Exception as e:
                        logger.warning(f"Error convirtiendo frame {frame_count}: {e}")
                        continue
                
                logger.info(f"Stream terminado después de {frame_count} frames")
                
            except Exception as e:
                logger.error(f"Error abriendo contenedor: {e}", exc_info=True)
                raise
        
        except socket.timeout:
            logger.warning("Timeout en socket del servidor vídeo")
        except ConnectionRefusedError:
            logger.warning(f"Conexión rechazada por {VIDEO_HOST}:{VIDEO_PORT}")
        except Exception as e:
            logger.error(f"Error streaming vídeo: {e}", exc_info=True)
        finally:
            self.is_connected = False
            self.connection_status.emit(False)
            try:
                sock.close()
            except:
                pass
    
    def stop(self):
        """Detener el worker."""
        self._stop_event.set()


class _SocketReader:
    """Adaptador para que PyAV lea desde un socket como si fuera un archivo."""
    
    def __init__(self, sock: socket.socket):
        self.sock = sock
        self.buffer = b""
    
    def read(self, size: int) -> bytes:
        """Lee exactamente 'size' bytes del socket (o menos si hay EOF)."""
        try:
            # Si hay datos en el buffer, usarlos primero
            if self.buffer:
                if len(self.buffer) >= size:
                    result = self.buffer[:size]
                    self.buffer = self.buffer[size:]
                    return result
                else:
                    result = self.buffer
                    size -= len(result)
                    self.buffer = b""
                    # Leer más datos
                    data = self.sock.recv(size)
                    return result + data
            
            # Si no hay buffer, leer del socket
            data = self.sock.recv(size)
            return data
        except socket.timeout:
            logger.debug("Socket read timeout")
            return b""
        except Exception as e:
            logger.error(f"Error reading socket: {e}")
            return b""
    
    def seek(self, pos: int, whence: int = 0) -> int:
        """Los sockets no son seekables."""
        raise IOError("Socket stream is not seekable")
    
    def tell(self) -> int:
        """Retorna posición (no aplicable para sockets)."""
        return 0


class SensorWorker(QObject):
    """
    Worker que corre en QThread separado.
    
    Responsabilidad:
    - Conectar al servidor TCP de sensor (Proceso 2) como cliente
    - Leer líneas JSON-lines del socket
    - Parsear JSON
    - Emitir datos via pyqtSignal
    
    Señales:
    - data_ready(dict): {"timestamp": float, "temperature": float, "classification": str}
    - connection_status(bool): True si conectado, False si desconectado
    """
    
    data_ready = pyqtSignal(dict)
    connection_status = pyqtSignal(bool)
    
    def __init__(self):
        super().__init__()
        self._stop_event = threading.Event()
        self.is_connected = False
    
    def run(self):
        """Bucle principal del worker."""
        while not self._stop_event.is_set():
            try:
                self._connect_and_read()
            except Exception as e:
                logger.error(f"Error en SensorWorker: {e}")
                self.is_connected = False
                self.connection_status.emit(False)
            
            if self._stop_event.is_set():
                break
            
            logger.info(f"Reconectando sensor en {SENSOR_RECONNECT_DELAY}s...")
            self._stop_event.wait(SENSOR_RECONNECT_DELAY)
    
    def _connect_and_read(self):
        """Conecta al servidor de sensor y lee datos."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        
        try:
            logger.info(f"Conectando al sensor {SENSOR_HOST}:{SENSOR_PORT}...")
            sock.connect((SENSOR_HOST, SENSOR_PORT))
            self.is_connected = True
            self.connection_status.emit(True)
            logger.info("Conectado al sensor ✓")
            
            # Leer líneas JSON-lines
            sock_file = sock.makefile("r", buffering=1)
            for line in sock_file:
                if self._stop_event.is_set():
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                try:
                    data = json.loads(line)
                    # Validar campos esperados
                    if "temperature" in data and "classification" in data:
                        self.data_ready.emit(data)
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON inválido del sensor: {e}")
        
        except socket.timeout:
            logger.warning("Timeout conectando al sensor")
        except ConnectionRefusedError:
            logger.warning("Sensor no disponible (conexión rechazada)")
        except Exception as e:
            logger.error(f"Error leyendo sensor: {e}")
        finally:
            self.is_connected = False
            self.connection_status.emit(False)
            sock.close()
    
    def stop(self):
        """Detener el worker."""
        self._stop_event.set()


class AlertWindow(QDialog):
    """Ventana de alerta persistente para temperatura alta."""
    
    closed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # Configurar como ventana independiente con atributos especiales
        self.setWindowTitle("⚠ ALERTA DE TEMPERATURA")
        self.setGeometry(400, 200, 600, 350)
        self.setModal(False)  # Non-modal dialog
        
        # Configurar flags para asegurar que se muestre como ventana flotante
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowStaysOnTopHint
        )
        
        self.setStyleSheet("""
            QWidget {
                background-color: #2a1a1a;
                color: #ffffff;
                border: 3px solid #ff0000;
                border-radius: 10px;
            }
            QPushButton {
                background-color: #5f1a1a;
                color: #ffffff;
                border: 2px solid #ff0000;
                padding: 12px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #7f2a2a;
                border: 2px solid #ff6644;
            }
            QPushButton:pressed {
                background-color: #4a1010;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Título
        title = QLabel("¡ALERTA DE TEMPERATURA!")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: #ff0000;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Valor actual
        self.temp_label = QLabel("-- °C")
        self.temp_label.setFont(QFont("Arial", 32, QFont.Weight.Bold))
        self.temp_label.setStyleSheet("color: #ff6644;")
        self.temp_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.temp_label)
        
        # Mensaje
        self.message_label = QLabel(f"La temperatura ha superado {TEMP_ALERT_THRESHOLD}°C")
        self.message_label.setFont(QFont("Arial", 12))
        self.message_label.setStyleSheet("color: #ffaaaa;")
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.message_label)
        
        # Tiempo del estado
        self.time_label = QLabel()
        self.time_label.setFont(QFont("Arial", 10))
        self.time_label.setStyleSheet("color: #888888;")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.time_label)
        
        layout.addStretch()
        
        # Botón para cerrar
        close_btn = QPushButton("Cerrar Alerta")
        close_btn.clicked.connect(self._on_close)
        layout.addWidget(close_btn)
    
    def update_temperature(self, temp: float):
        """Actualiza el valor de temperatura mostrado."""
        self.temp_label.setText(f"{temp:.1f} °C")
        self.time_label.setText(datetime.now().strftime("%H:%M:%S"))
    
    def _on_close(self):
        """Maneja el cierre de la ventana de alerta."""
        self.closed.emit()
        self.close()
    
    def closeEvent(self, event):
        """Maneja el cierre de la ventana."""
        self.closed.emit()
        event.accept()


class MonitorApp(QMainWindow):
    """
    Aplicación principal de monitorización.
    
    Interfaz gráfica con:
    - Panel de vídeo (QLabel con QPixmap)
    - Panel de temperatura (QLCDNumber o QLabel)
    - Panel de clasificación (QLabel con color dinámico)
    - Gráfico histórico de temperatura (pyqtgraph PlotWidget)
    - Barra de estado (conexión vídeo/sensor)
    - Sistema de alertas
    """
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Monitor de Temperatura — Tiempo Real")
        self.setGeometry(100, 100, 1920, 1080)
        
        # Tema oscuro
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1a1a2e;
                color: #e0e0e0;
            }
            QLabel {
                color: #e0e0e0;
            }
            QPushButton {
                background-color: #0f3460;
                color: #00d4ff;
                border: 1px solid #00d4ff;
                padding: 5px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #16213e;
            }
        """)
        
        # Estado
        self.temp_history = deque(maxlen=TEMP_HISTORY_SIZE)
        self.current_temp = 0.0
        self.current_classification = "---"
        self.alert_shown = False
        self.temp_max = -999
        self.temp_min = 999
        self.temp_sum = 0
        self.temp_count = 0
        
        # Ventana de alerta persistente
        self.alert_window = None
        self.sound_process = None  # Proceso de sonido en loop
        
        # Modo de operación: True (Real) o False (Fake)
        self.fake_mode = False
        self.fake_target_temp = None  # Temperatura objetivo en modo Fake
        self.fake_drift_counter = 0    # Contador de samples para drift
        self.fake_drift_samples = 5    # Muestras para completar el drift
        self.fake_base_temp = 25.0     # Temperatura actual en Fake mode
        
        # Crear workers y threads
        self.video_worker = VideoWorker()
        self.video_thread = QThread()
        self.video_worker.moveToThread(self.video_thread)
        
        self.sensor_worker = SensorWorker()
        self.sensor_thread = QThread()
        self.sensor_worker.moveToThread(self.sensor_thread)
        
        # Conectar signals de workers
        self.video_worker.frame_ready.connect(self._on_frame_ready)
        self.video_worker.connection_status.connect(self._on_video_status)
        self.sensor_worker.data_ready.connect(self._on_sensor_data)
        self.sensor_worker.connection_status.connect(self._on_sensor_status)
        
        # Señales de thread para iniciar workers
        self.video_thread.started.connect(self.video_worker.run)
        self.sensor_thread.started.connect(self.sensor_worker.run)
        
        # Crear UI
        self._create_ui()
        
        # Timer para hora
        self.time_timer = QTimer()
        self.time_timer.timeout.connect(self._update_time)
        self.time_timer.start(1000)
        
        # Timer para animación de alerta (parpadeo)
        self.alert_timer = QTimer()
        self.alert_timer.timeout.connect(self._blink_alert)
        self.alert_blink_state = False
        
        # Timer para reproducir sonido continuamente durante la alerta
        # (Ya no se usa - el sonido ahora se maneja como un proceso en loop)
        
        # Timer para generar temperaturas falsas en modo Fake
        self.fake_temp_timer = QTimer()
        self.fake_temp_timer.timeout.connect(self._generate_fake_temperature)
        self.fake_temp_timer.setInterval(2000)  # Cada 2 segundos
        
        # Estados de conexión
        self.video_connected = False
        self.sensor_connected = False
    
    def _create_ui(self):
        """Construye la interfaz gráfica con diseño limpio y moderno."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 10, 15, 15)
        main_layout.setSpacing(10)
        
        # ===== HEADER =====
        header_layout = QHBoxLayout()
        
        # Título
        title = QLabel("Monitor de Temperatura — Tiempo Real")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #00d4ff;")
        header_layout.addWidget(title)
        
        # Separador
        header_layout.addSpacing(30)
        
        # Estado EN DIRECTO
        live_label = QLabel("● EN DIRECTO")
        live_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        live_label.setStyleSheet("color: #ff0000;")
        header_layout.addWidget(live_label)
        
        # Separador
        header_layout.addSpacing(20)
        
        # Sensor OK / Cámara OK badges
        self.sensor_badge = QLabel("● Sensor OK")
        self.sensor_badge.setFont(QFont("Arial", 9))
        self.sensor_badge.setStyleSheet("""
            color: #ffffff;
            background-color: #1a5f3f;
            padding: 4px 8px;
            border-radius: 12px;
            border: 1px solid #00cc66;
        """)
        header_layout.addWidget(self.sensor_badge)
        
        header_layout.addSpacing(10)
        
        self.camera_badge = QLabel("● Cámara OK")
        self.camera_badge.setFont(QFont("Arial", 9))
        self.camera_badge.setStyleSheet("""
            color: #ffffff;
            background-color: #1a3f5f;
            padding: 4px 8px;
            border-radius: 12px;
            border: 1px solid #0066cc;
        """)
        header_layout.addWidget(self.camera_badge)
        
        header_layout.addSpacing(10)
        
        header_layout.addStretch()
        
        # Mostrar SERVIDOR_COMANOV
        server_label = QLabel("SERVIDOR_COMANOV")
        server_label.setFont(QFont("Arial", 9))
        server_label.setStyleSheet("color: #888888;")
        header_layout.addWidget(server_label)
        
        main_layout.addLayout(header_layout)
        
        # ===== CONTENIDO PRINCIPAL =====
        content_layout = QHBoxLayout()
        content_layout.setSpacing(15)
        
        # ===== PANEL IZQUIERDO: VIDEO =====
        left_panel = QVBoxLayout()
        left_panel.setSpacing(10)
        
        # Indicador EN DIRECTO
        left_header = QLabel("EN\nDIRECTO")
        left_header.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        left_header.setStyleSheet("color: #ff0000;")
        left_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_panel.addWidget(left_header)
        
        # Panel de vídeo
        self.video_label = QLabel()
        self.video_label.setMinimumSize(500, 350)
        self.video_label.setStyleSheet("""
            border: 1px solid #333333;
            background-color: #0f0f0f;
            border-radius: 5px;
        """)
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setScaledContents(False)
        self._update_no_signal_placeholder()
        left_panel.addWidget(self.video_label, 1)
        
        # Hora abajo del video
        self.time_label = QLabel(datetime.now().strftime("%H:%M:%S"))
        self.time_label.setFont(QFont("Courier", 18, QFont.Weight.Bold))
        self.time_label.setStyleSheet("color: #00d4ff;")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_panel.addWidget(self.time_label)
        
        content_layout.addLayout(left_panel, 2)
        
        # ===== PANEL DERECHO: DATOS Y GRÁFICO =====
        right_panel = QVBoxLayout()
        right_panel.setSpacing(10)
        
        # ===== SECCIÓN TEMPERATURA ACTUAL =====
        temp_section = QVBoxLayout()
        
        temp_label = QLabel("TEMPERATURA ACTUAL")
        temp_label.setFont(QFont("Arial", 10))
        temp_label.setStyleSheet("color: #888888;")
        temp_section.addWidget(temp_label)
        
        # Valor de temperatura grande
        self.temp_value = QLabel("-- °C")
        self.temp_value.setFont(QFont("Arial", 60, QFont.Weight.Bold))
        self.temp_value.setStyleSheet("color: #ffffff;")
        self.temp_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        temp_section.addWidget(self.temp_value)
        
        # Clasificación con badge
        self.class_value = QLabel("ESPERANDO")
        self.class_value.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.class_value.setStyleSheet("""
            color: #ffffff;
            background-color: #666666;
            padding: 8px 16px;
            border-radius: 16px;
            border: 1px solid #00d4ff;
        """)
        self.class_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        temp_section.addWidget(self.class_value)
        
        right_panel.addLayout(temp_section)
        
        # ===== ESTADÍSTICAS =====
        stats_group_layout = QVBoxLayout()
        
        # Grid 2x2 para MAX/MIN y PROMEDIO/VARIACIÓN
        stats_grid = QVBoxLayout()
        
        # Fila 1: MAX y MIN
        stats_row1 = QHBoxLayout()
        
        # MAX
        max_box = QVBoxLayout()
        max_label = QLabel("MAX. HOY")
        max_label.setFont(QFont("Arial", 9))
        max_label.setStyleSheet("color: #888888;")
        max_box.addWidget(max_label)
        
        self.max_value = QLabel("-- °C")
        self.max_value.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.max_value.setStyleSheet("color: #ff6644;")
        max_box.addWidget(self.max_value)
        
        max_container = QWidget()
        max_container.setLayout(max_box)
        max_container.setStyleSheet("""
            background-color: #252540;
            border: 1px solid #333333;
            border-radius: 5px;
            padding: 8px;
        """)
        stats_row1.addWidget(max_container, 1)
        
        # MIN
        min_box = QVBoxLayout()
        min_label = QLabel("MIN. HOY")
        min_label.setFont(QFont("Arial", 9))
        min_label.setStyleSheet("color: #888888;")
        min_box.addWidget(min_label)
        
        self.min_value = QLabel("-- °C")
        self.min_value.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.min_value.setStyleSheet("color: #5588ff;")
        min_box.addWidget(self.min_value)
        
        min_container = QWidget()
        min_container.setLayout(min_box)
        min_container.setStyleSheet("""
            background-color: #252540;
            border: 1px solid #333333;
            border-radius: 5px;
            padding: 8px;
        """)
        stats_row1.addWidget(min_container, 1)
        
        stats_grid.addLayout(stats_row1)
        
        # Fila 2: PROMEDIO y VARIACIÓN
        stats_row2 = QHBoxLayout()
        
        # PROMEDIO
        avg_box = QVBoxLayout()
        avg_label = QLabel("PROMEDIO")
        avg_label.setFont(QFont("Arial", 9))
        avg_label.setStyleSheet("color: #888888;")
        avg_box.addWidget(avg_label)
        
        self.avg_value = QLabel("-- °C")
        self.avg_value.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.avg_value.setStyleSheet("color: #ffaa44;")
        avg_box.addWidget(self.avg_value)
        
        avg_container = QWidget()
        avg_container.setLayout(avg_box)
        avg_container.setStyleSheet("""
            background-color: #252540;
            border: 1px solid #333333;
            border-radius: 5px;
            padding: 8px;
        """)
        stats_row2.addWidget(avg_container, 1)
        
        # VARIACIÓN
        var_box = QVBoxLayout()
        var_label = QLabel("VARIACIÓN")
        var_label.setFont(QFont("Arial", 9))
        var_label.setStyleSheet("color: #888888;")
        var_box.addWidget(var_label)
        
        self.var_value = QLabel("-- °C")
        self.var_value.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.var_value.setStyleSheet("color: #44ff88;")
        var_box.addWidget(self.var_value)
        
        var_container = QWidget()
        var_container.setLayout(var_box)
        var_container.setStyleSheet("""
            background-color: #252540;
            border: 1px solid #333333;
            border-radius: 5px;
            padding: 8px;
        """)
        stats_row2.addWidget(var_container, 1)
        
        stats_grid.addLayout(stats_row2)
        
        stats_group_layout.addLayout(stats_grid)
        right_panel.addLayout(stats_group_layout)
        
        # ===== GRÁFICO =====
        graph_label = QLabel("HISTORIAL DE TEMPERATURA")
        graph_label.setFont(QFont("Arial", 10))
        graph_label.setStyleSheet("color: #888888;")
        right_panel.addWidget(graph_label)
        
        # Gráfico con pyqtgraph
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setLabel("bottom", "ÚLTIMAS 48 MUESTRAS", color="#888888")
        self.plot_widget.setLabel("left", "°C", color="#888888")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.2)
        self.plot_widget.setStyleSheet("""
            QGraphicsView {
                background-color: #0f0f0f;
                border: 1px solid #333333;
                border-radius: 5px;
            }
        """)
        
        # Curve azul
        self.plot_curve = self.plot_widget.plot(pen=pg.mkPen("#0088ff", width=2))
        right_panel.addWidget(self.plot_widget, 1)
        
        # ===== ESCALA TÉRMICA =====
        scale_label = QLabel("ESCALA TÉRMICA")
        scale_label.setFont(QFont("Arial", 9))
        scale_label.setStyleSheet("color: #888888;")
        right_panel.addWidget(scale_label)
        
        # Barra de gradiente
        self.thermal_bar = QLabel()
        self.thermal_bar.setFixedHeight(15)
        self.thermal_bar.setPixmap(self._create_thermal_scale())
        right_panel.addWidget(self.thermal_bar)
        
        # Rango de temperatura
        range_layout = QHBoxLayout()
        range_layout.addWidget(QLabel("0 °C"), 0)
        range_layout.addStretch()
        range_layout.addWidget(QLabel("50 °C"), 0)
        right_panel.addLayout(range_layout)
        
        content_layout.addLayout(right_panel, 1)
        
        main_layout.addLayout(content_layout, 1)
        
        # ===== FOOTER =====
        footer_layout = QHBoxLayout()
        
        # Estado sensor
        self.status_sensor = QLabel("● Sensor · Conectado")
        self.status_sensor.setFont(QFont("Arial", 9))
        self.status_sensor.setStyleSheet("color: #00cc66;")
        footer_layout.addWidget(self.status_sensor)
        
        footer_layout.addSpacing(20)
        
        # Estado cámara
        self.status_camera = QLabel("● Cámara · Conectada")
        self.status_camera.setFont(QFont("Arial", 9))
        self.status_camera.setStyleSheet("color: #0066cc;")
        footer_layout.addWidget(self.status_camera)
        
        footer_layout.addStretch()
        
        # Actualización
        self.update_label = QLabel("Actualiza cada 2 s")
        self.update_label.setFont(QFont("Arial", 9))
        self.update_label.setStyleSheet("color: #888888;")
        footer_layout.addWidget(self.update_label)
        
        footer_layout.addSpacing(20)
        
        # Timestamp
        self.timestamp_label = QLabel(datetime.now().strftime("%H:%M:%S · %a %d %b %Y"))
        self.timestamp_label.setFont(QFont("Arial", 9))
        self.timestamp_label.setStyleSheet("color: #888888;")
        footer_layout.addWidget(self.timestamp_label)
        
        main_layout.addLayout(footer_layout)
    
    def _update_no_signal_placeholder(self):
        """Muestra placeholder de "sin señal" en el panel de vídeo."""
        pixmap = self._generate_no_signal_image()
        # Usar tamaño actual del widget o fallback
        label_size = self.video_label.size()
        if label_size.width() > 0 and label_size.height() > 0:
            display_width, display_height = label_size.width(), label_size.height()
        else:
            display_width, display_height = VIDEO_DISPLAY_WIDTH, VIDEO_DISPLAY_HEIGHT
        
        self.video_label.setPixmap(
            pixmap.scaled(
                display_width,
                display_height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
    
    @staticmethod
    def _generate_no_signal_image() -> QPixmap:
        """Genera imagen 'sin señal' programáticamente."""
        pixmap = QPixmap(1280, 720)
        pixmap.fill(QColor(15, 15, 15))
        return pixmap
    
    @staticmethod
    def _create_thermal_scale() -> QPixmap:
        """Crea barra de gradiente térmico con QLinearGradient."""
        pixmap = QPixmap(1200, 20)
        pixmap.fill(QColor(15, 15, 15))
        
        painter = QPainter(pixmap)
        
        # Crear gradiente lineal de azul a rojo
        gradient = QLinearGradient(QPointF(0, 0), QPointF(1200, 0))
        
        # Agregar color stops para crear el gradiente suave
        gradient.setColorAt(0.0, QColor(0, 0, 255))           # Azul
        gradient.setColorAt(0.17, QColor(0, 255, 255))        # Cian
        gradient.setColorAt(0.33, QColor(0, 255, 0))          # Verde
        gradient.setColorAt(0.50, QColor(255, 255, 0))        # Amarillo
        gradient.setColorAt(0.67, QColor(255, 165, 0))        # Naranja
        gradient.setColorAt(0.83, QColor(255, 69, 0))         # Rojo-naranja
        gradient.setColorAt(1.0, QColor(255, 0, 0))           # Rojo
        
        brush = QBrush(gradient)
        painter.fillRect(0, 0, 1200, 20, brush)
        
        # Dibujar líneas de referencia
        painter.setPen(QColor(200, 200, 200))
        painter.setFont(QFont("Arial", 8))
        
        # Marcas cada 200 píxeles
        for i in range(0, 1201, 200):
            painter.drawLine(i, 0, i, 3)
        
        painter.end()
        return pixmap
    
    def _update_time(self):
        """Actualiza la hora mostrada."""
        now = datetime.now()
        self.time_label.setText(now.strftime("%H:%M:%S"))
        self.timestamp_label.setText(now.strftime("%H:%M:%S · %a %d %b %Y"))
    
    def keyPressEvent(self, event):
        """Maneja entrada de teclado para cambiar modo y controlar temperatura Fake."""
        key = event.text().lower()
        
        # Cambiar a modo Fake
        if key == 'f' and not self.fake_mode:
            self.fake_mode = True
            self.fake_base_temp = self.current_temp  # Iniciar con la temp actual
            self.fake_target_temp = None
            self.fake_drift_counter = 0
            self.fake_temp_timer.start()
            self.sensor_worker.stop()  # Detener el worker real
            
            # Actualizar UI
            logger.info("🔄 Cambiando a modo FAKE - temperaturas simuladas")
            return
        
        # Controlar temperatura objetivo en modo Fake (1-9)
        if self.fake_mode and key in '123456789':
            target_value = int(key) * 10  # 1→10, 2→20, ..., 9→90
            self.fake_target_temp = float(target_value)
            self.fake_drift_counter = 0
            logger.info(f"📊 Modo FAKE: Drift iniciado hacia {self.fake_target_temp}°C")
            return
        
        super().keyPressEvent(event)
    
    def _generate_fake_temperature(self):
        """Genera temperatura falsa con oscilación y drift."""
        import random
        
        # Si hay un target de drift, interpolar hacia él
        if self.fake_target_temp is not None and self.fake_drift_counter < self.fake_drift_samples:
            # Calcular incremento por sample: (target - base) / 5
            increment = (self.fake_target_temp - self.fake_base_temp) / self.fake_drift_samples
            self.fake_base_temp += increment
            self.fake_drift_counter += 1
            
            if self.fake_drift_counter >= self.fake_drift_samples:
                # Asegurar que llegamos exactamente al target
                self.fake_base_temp = self.fake_target_temp
                logger.info(f"✓ Drift completado: temperatura ahora oscila en {self.fake_target_temp}°C")
                self.fake_target_temp = None  # Completar drift
        
        # Agregar oscilación aleatoria (±2°C)
        oscillation = random.uniform(-2.0, 2.0)
        fake_temp = self.fake_base_temp + oscillation
        
        # Clasificar temperatura
        classification = self._classify_temperature(fake_temp)
        
        # Simular datos de sensor
        fake_data = {
            'timestamp': time.time(),
            'temperature': fake_temp,
            'classification': classification
        }
        
        # Procesar como si viniera del sensor
        self._on_sensor_data(fake_data)
    
    def _classify_temperature(self, temp: float) -> str:
        """Clasifica temperatura en categorías."""
        if temp < 10:
            return "frio"
        elif temp < 20:
            return "frio"
        elif temp < 30:
            return "templado"
        elif temp < 50:
            return "caliente"
        elif temp < 70:
            return "muy caliente"
        else:
            return "crítico"
    
    @pyqtSlot(QImage)
    def _on_frame_ready(self, q_image: QImage):
        """Slot llamado cuando VideoWorker emite un frame."""
        pixmap = QPixmap.fromImage(q_image)
        # Usar tamaño actual del widget para escalar dinámicamente
        label_size = self.video_label.size()
        if label_size.width() > 0 and label_size.height() > 0:
            scaled_pixmap = pixmap.scaled(
                label_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        else:
            # Fallback si el widget aún no tiene tamaño
            scaled_pixmap = pixmap.scaled(
                VIDEO_DISPLAY_WIDTH,
                VIDEO_DISPLAY_HEIGHT,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        self.video_label.setPixmap(scaled_pixmap)
    
    @pyqtSlot(bool)
    def _on_video_status(self, connected: bool):
        """Slot para cambios en estado de conexión de vídeo."""
        self.video_connected = connected
        if connected:
            self.status_camera = QLabel("● Cámara · Conectada")
            self.status_camera.setFont(QFont("Arial", 9))
            self.status_camera.setStyleSheet("color: #0066cc;")
            self.camera_badge.setStyleSheet("""
                color: #ffffff;
                background-color: #1a3f5f;
                padding: 4px 8px;
                border-radius: 12px;
                border: 1px solid #00aa00;
            """)
        else:
            self.status_camera = QLabel("● Cámara · Desconectada")
            self.status_camera.setFont(QFont("Arial", 9))
            self.status_camera.setStyleSheet("color: #ff0000;")
            self.camera_badge.setStyleSheet("""
                color: #ffffff;
                background-color: #5f1a1a;
                padding: 4px 8px;
                border-radius: 12px;
                border: 1px solid #ff0000;
            """)
            self._update_no_signal_placeholder()
    
    @pyqtSlot(dict)
    def _on_sensor_data(self, data: dict):
        """Slot llamado cuando SensorWorker emite datos de temperatura."""
        try:
            temp = float(data.get("temperature", 0))
            classification = data.get("classification", "---").lower()
            
            self.current_temp = temp
            self.current_classification = classification
            
            # Actualizar estadísticas
            if temp > self.temp_max:
                self.temp_max = temp
            if temp < self.temp_min:
                self.temp_min = temp
            
            self.temp_sum += temp
            self.temp_count += 1
            avg = self.temp_sum / self.temp_count if self.temp_count > 0 else 0
            variation = max(0, self.temp_max - self.temp_min)
            
            # Actualizar valores mostrados
            self.temp_value.setText(f"{temp:.1f} °C")
            self.max_value.setText(f"{self.temp_max:.1f}°C")
            self.min_value.setText(f"{self.temp_min:.1f}°C")
            self.avg_value.setText(f"{avg:.1f}°C")
            self.var_value.setText(f"±{variation:.1f}°C")
            
            # Actualizar clasificación con color dinámico
            color_map = {
                "frio": ("#5588ff", "#1a3f5f"),
                "templado": "#5BAD6F",
                "caliente": "#ff8800",
                "muy caliente": "#ff6644",
                "crítico": "#ff0000",
            }
            
            self.class_value.setText(classification.upper())
            
            if classification == "frio":
                self.class_value.setStyleSheet("""
                    color: #ffffff;
                    background-color: #1a3f5f;
                    padding: 8px 16px;
                    border-radius: 16px;
                    border: 1px solid #0088ff;
                """)
            elif classification == "templado":
                self.class_value.setStyleSheet("""
                    color: #ffffff;
                    background-color: #1f5f1f;
                    padding: 8px 16px;
                    border-radius: 16px;
                    border: 1px solid #00cc66;
                """)
            elif classification == "caliente":
                self.class_value.setStyleSheet("""
                    color: #ffffff;
                    background-color: #5f4a1a;
                    padding: 8px 16px;
                    border-radius: 16px;
                    border: 1px solid #ff8800;
                """)
            elif classification == "muy caliente":
                self.class_value.setStyleSheet("""
                    color: #ffffff;
                    background-color: #5f3a2a;
                    padding: 8px 16px;
                    border-radius: 16px;
                    border: 1px solid #ff6644;
                """)
            elif classification == "crítico":
                self.class_value.setStyleSheet("""
                    color: #ffffff;
                    background-color: #5f1a1a;
                    padding: 8px 16px;
                    border-radius: 16px;
                    border: 1px solid #ff0000;
                """)
            
            # Agregar al historial y actualizar gráfico
            self.temp_history.append(temp)
            self._update_plot()
            
            # Verificar si supera umbral de alerta
            logger.info(f"🌡️  Temp: {temp:.1f}°C vs umbral: {TEMP_ALERT_THRESHOLD}°C")
            if temp > TEMP_ALERT_THRESHOLD:
                logger.info(f"⚠️  Temperatura SUPERIOR al umbral - llamando _trigger_alert()")
                if not self.alert_shown:
                    self._trigger_alert()
                elif self.alert_window and self.alert_window.isVisible():
                    # Actualizar temperatura en la ventana existente
                    self.alert_window.update_temperature(temp)
            elif temp <= TEMP_ALERT_THRESHOLD and self.alert_shown:
                # Temperatura volvió a la normalidad, cerrar alerta
                logger.info(f"✓ Temperatura volvió a la normalidad")
                self._stop_alert()
        
        except Exception as e:
            logger.error(f"Error procesando datos de sensor: {e}")
    
    @pyqtSlot(bool)
    def _on_sensor_status(self, connected: bool):
        """Slot para cambios en estado de conexión del sensor."""
        self.sensor_connected = connected
        if connected:
            self.status_sensor.setText("● Sensor · Conectado")
            self.status_sensor.setStyleSheet("color: #00cc66;")
            self.sensor_badge.setStyleSheet("""
                color: #ffffff;
                background-color: #1a5f3f;
                padding: 4px 8px;
                border-radius: 12px;
                border: 1px solid #00cc66;
            """)
        else:
            self.status_sensor.setText("● Sensor · Desconectado")
            self.status_sensor.setStyleSheet("color: #ff0000;")
            self.sensor_badge.setStyleSheet("""
                color: #ffffff;
                background-color: #5f3a2a;
                padding: 4px 8px;
                border-radius: 12px;
                border: 1px solid #ff0000;
            """)
            self.class_value.setText("ESPERANDO")
            self.class_value.setStyleSheet("""
                color: #ffffff;
                background-color: #404050;
                padding: 8px 16px;
                border-radius: 16px;
                border: 1px solid #666666;
            """)
    
    def _update_plot(self):
        """Actualiza el gráfico de temperatura con historial."""
        if len(self.temp_history) > 0:
            self.plot_curve.setData(list(self.temp_history))
    
    def _trigger_alert(self):
        """Dispara alerta de temperatura alta con ventana persistente."""
        logger.info(f"_trigger_alert() called - alert_shown: {self.alert_shown}, temp: {self.current_temp:.1f}°C")
        if not self.alert_shown:
            try:
                logger.info("Creando AlertWindow...")
                # Crear la ventana de alerta sin parent para que sea independiente
                self.alert_window = AlertWindow()
                self.alert_window.closed.connect(self._on_alert_closed)
                logger.info("AlertWindow creada, llamando show()...")
                self.alert_window.show()
                self.alert_window.raise_()
                self.alert_window.activateWindow()
                self.alert_shown = True
                logger.info(f"✓ Alerta activada: Temperatura {self.current_temp:.1f}°C")
                
                # Iniciar reproducción de sonido continuo en loop
                self._start_looping_alert_sound()
            except Exception as e:
                logger.error(f"Error creando AlertWindow: {e}", exc_info=True)
                return
        
        # Actualizar la temperatura en la ventana de alerta
        if self.alert_window and self.alert_window.isVisible():
            self.alert_window.update_temperature(self.current_temp)
        
        # Iniciar parpadeo
        if not self.alert_timer.isActive():
            self.alert_timer.start(500)
    
    def _on_alert_closed(self):
        """Maneja el cierre de la ventana de alerta."""
        logger.info("Alerta cerrada por el usuario")
        self._stop_alert()
    
    def _stop_alert(self):
        """Detiene la alerta y cierra la ventana."""
        if self.alert_window:
            self.alert_window.close()
            self.alert_window = None
        
        self.alert_timer.stop()
        self._stop_looping_alert_sound()  # Detener el sonido en loop
        self.alert_shown = False
        self.alert_blink_state = False
    
    def _start_looping_alert_sound(self):
        """Inicia reproducción de sonido de alerta en loop."""
        try:
            # Si ya hay un proceso de sonido, detenerlo primero
            self._stop_looping_alert_sound()
            
            # Intentar usar paplay (PulseAudio)
            sound_files = [
                "/usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga",
                "/usr/share/sounds/freedesktop/stereo/complete.oga",
                "/usr/share/sounds/freedesktop/stereo/dialog-error.oga",
            ]
            
            # Buscar un archivo de sonido disponible
            sound_file = None
            for path in sound_files:
                if os.path.exists(path):
                    sound_file = path
                    break
            
            if sound_file:
                # Intentar reproducir en loop con paplay (bash wrapper para loop)
                try:
                    self.sound_process = subprocess.Popen(
                        ["bash", "-c", f"while true; do paplay {sound_file}; done"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        preexec_fn=os.setsid,  # Crear nuevo group de procesos
                    )
                    logger.info(f"🔊 Sonido de alerta iniciado (paplay loop, PID: {self.sound_process.pid})")
                    return
                except FileNotFoundError:
                    pass
                
                # Si paplay no está disponible, intentar con aplay (con loop)
                try:
                    self.sound_process = subprocess.Popen(
                        ["bash", "-c", f"while true; do aplay {sound_file}; done"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        preexec_fn=os.setsid,  # Crear nuevo group de procesos
                    )
                    logger.info(f"🔊 Sonido de alerta iniciado (aplay loop, PID: {self.sound_process.pid})")
                    return
                except FileNotFoundError:
                    logger.debug("No audio player found (paplay/aplay)")
            
            # Generar beep programático si no hay archivos de sonido
            logger.info("🔊 Usando beep del sistema para alerta")
            try:
                self.sound_process = subprocess.Popen(
                    ["bash", "-c", "while true; do beep -f 1000 -l 200; sleep 0.2; done"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    preexec_fn=os.setsid,  # Crear nuevo group de procesos
                )
                logger.info(f"🔊 Beep loop iniciado (PID: {self.sound_process.pid})")
            except FileNotFoundError:
                logger.debug("beep command not found")
        
        except Exception as e:
            logger.error(f"Error iniciando sonido de alerta en loop: {e}", exc_info=True)
    
    def _stop_looping_alert_sound(self):
        """Detiene la reproducción de sonido de alerta en loop."""
        if self.sound_process:
            try:
                # Matar el grupo de procesos completo (bash + paplay/aplay/beep)
                try:
                    os.killpg(os.getpgid(self.sound_process.pid), signal.SIGTERM)
                except OSError:
                    # Si el proceso ya terminó, ignorar el error
                    pass
                
                try:
                    self.sound_process.wait(timeout=1)  # Esperar a que termine
                except subprocess.TimeoutExpired:
                    # Si no termina, forzar SIGKILL
                    try:
                        os.killpg(os.getpgid(self.sound_process.pid), signal.SIGKILL)
                    except OSError:
                        pass
                    self.sound_process.wait()
                logger.info("🔇 Sonido de alerta detenido")
            except Exception as e:
                logger.debug(f"Error deteniendo sonido: {e}")
            finally:
                self.sound_process = None
    
    def _blink_alert(self):
        """Anima el parpadeo de alerta."""
        self.alert_blink_state = not self.alert_blink_state
        if self.alert_blink_state:
            self.class_value.setStyleSheet("""
                color: #000000;
                background-color: #ff0000;
                padding: 8px 16px;
                border-radius: 16px;
                border: 1px solid #ff0000;
            """)
        else:
            self.class_value.setStyleSheet("""
                color: #ffffff;
                background-color: #5f1a1a;
                padding: 8px 16px;
                border-radius: 16px;
                border: 1px solid #ff0000;
            """)
    
    def closeEvent(self, event):
        """Maneja el cierre de la aplicación."""
        logger.info("Cerrando aplicación...")
        
        # Detener sonido de alerta
        self._stop_looping_alert_sound()
        
        # Detener workers
        self.video_worker.stop()
        self.sensor_worker.stop()
        
        # Esperar a que terminen los threads
        self.video_thread.quit()
        self.video_thread.wait()
        self.sensor_thread.quit()
        self.sensor_thread.wait()
        
        logger.info("Aplicación cerrada")
        event.accept()


def main():
    """Punto de entrada de la aplicación."""
    app = QApplication(sys.argv)
    
    window = MonitorApp()
    window.show()
    
    # Iniciar threads de workers
    window.video_thread.start()
    window.sensor_thread.start()
    
    logger.info("Aplicación iniciada ✓")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
