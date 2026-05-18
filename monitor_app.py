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
import subprocess
import threading
from collections import deque
from pathlib import Path
from typing import Optional

import numpy as np
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLCDNumber,
    QStatusBar,
    QMessageBox,
)
from PyQt6.QtCore import (
    Qt,
    QThread,
    QObject,
    pyqtSignal,
    pyqtSlot,
    QTimer,
    QSize,
)
from PyQt6.QtGui import QImage, QPixmap, QFont, QColor
from PyQt6.QtMultimedia import QMediaPlayer
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
        self.setWindowTitle("Monitor de Temperatura en Tiempo Real — SERVIDOR_COMMOV")
        self.setGeometry(100, 100, 1600, 900)
        
        # Estado
        self.temp_history = deque(maxlen=TEMP_HISTORY_SIZE)
        self.current_temp = 0.0
        self.current_classification = "---"
        self.alert_shown = False
        
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
        
        # Timer para animación de alerta (parpadeo)
        self.alert_timer = QTimer()
        self.alert_timer.timeout.connect(self._blink_alert)
        self.alert_blink_state = False
        
        # Estados de conexión
        self.video_connected = False
        self.sensor_connected = False
    
    def _create_ui(self):
        """Construye la interfaz gráfica."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal (horizontal): [vídeo + temperatura] | [gráfico]
        main_layout = QHBoxLayout(central_widget)
        
        # Panel izquierdo: vídeo y temperatura
        left_panel = QVBoxLayout()
        
        # Panel de vídeo
        self.video_label = QLabel()
        self.video_label.setMinimumSize(400, 225)  # Mínimo responsive
        self.video_label.setStyleSheet("border: 2px solid #ccc; background-color: #222;")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setScaledContents(False)  # No escalar automáticamente
        self._update_no_signal_placeholder()
        left_panel.addWidget(QLabel("📹 Vídeo en Directo"), 0)
        left_panel.addWidget(self.video_label, 1)
        
        # Panel de temperatura
        temp_layout = QHBoxLayout()
        self.temp_label = QLabel("Temperatura Actual:")
        self.temp_value = QLabel("-- °C")
        font = QFont()
        font.setPointSize(24)
        font.setBold(True)
        self.temp_value.setFont(font)
        self.temp_value.setStyleSheet(
            "background-color: #f0f0f0; padding: 10px; border-radius: 5px;"
        )
        temp_layout.addWidget(self.temp_label)
        temp_layout.addWidget(self.temp_value, 1)
        left_panel.addLayout(temp_layout)
        
        # Panel de clasificación
        class_layout = QHBoxLayout()
        self.class_label = QLabel("Estado:")
        self.class_value = QLabel("ESPERANDO")
        font_class = QFont()
        font_class.setPointSize(16)
        font_class.setBold(True)
        self.class_value.setFont(font_class)
        self.class_value.setStyleSheet(
            "background-color: #666; color: white; padding: 10px; border-radius: 5px;"
        )
        self.class_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        class_layout.addWidget(self.class_label)
        class_layout.addWidget(self.class_value, 1)
        left_panel.addLayout(class_layout)
        
        main_layout.addLayout(left_panel, 2)
        
        # Panel derecho: gráfico de temperatura
        right_panel = QVBoxLayout()
        right_panel.addWidget(QLabel("📊 Historial de Temperatura"), 0)
        
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setLabel("bottom", "Tiempo (muestras)")
        self.plot_widget.setLabel("left", "Temperatura (°C)")
        self.plot_widget.setTitle("Últimas 60 muestras")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        
        self.plot_curve = self.plot_widget.plot(pen=pg.mkPen("blue", width=2))
        right_panel.addWidget(self.plot_widget, 1)
        
        main_layout.addLayout(right_panel, 1)
        
        # Barra de estado
        self.statusBar().showMessage("Iniciando conexiones...")
        self.status_video = QLabel("📹 Vídeo: Conectando...")
        self.status_sensor = QLabel("🌡 Sensor: Conectando...")
        self.statusBar().addPermanentWidget(self.status_video)
        self.statusBar().addPermanentWidget(self.status_sensor)
    
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
        pixmap = QPixmap(640, 480)
        pixmap.fill(QColor(50, 50, 50))
        
        # Dibuja un rectángulo y texto
        painter = pixmap.fill(QColor(50, 50, 50))
        # Nota: QPixmap.fill() no retorna painter, usar otro método
        # Por simplicidad, dejamos la imagen gris y retornamos
        
        return pixmap
    
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
            self.status_video.setText("📹 Vídeo: ✓ Conectado")
            self.status_video.setStyleSheet("color: green;")
        else:
            self.status_video.setText("📹 Vídeo: ✗ Desconectado")
            self.status_video.setStyleSheet("color: red;")
            self._update_no_signal_placeholder()
    
    @pyqtSlot(dict)
    def _on_sensor_data(self, data: dict):
        """Slot llamado cuando SensorWorker emite datos de temperatura."""
        try:
            temp = float(data.get("temperature", 0))
            classification = data.get("classification", "---").lower()
            
            self.current_temp = temp
            self.current_classification = classification
            
            # Actualizar etiqueta de temperatura
            self.temp_value.setText(f"{temp:.1f} °C")
            
            # Actualizar clasificación con color dinámico
            color = CLASSIFICATION_COLORS.get(classification, "#666")
            self.class_value.setText(classification.upper())
            self.class_value.setStyleSheet(
                f"background-color: {color}; color: white; padding: 10px; border-radius: 5px;"
            )
            
            # Agregar al historial y actualizar gráfico
            self.temp_history.append(temp)
            self._update_plot()
            
            # Verificar si supera umbral de alerta
            if temp > TEMP_ALERT_THRESHOLD and not self.alert_timer.isActive():
                self._trigger_alert()
            elif temp <= TEMP_ALERT_THRESHOLD:
                self.alert_timer.stop()
                self.temp_value.setStyleSheet(
                    "background-color: #f0f0f0; padding: 10px; border-radius: 5px;"
                )
                self.alert_shown = False
        
        except Exception as e:
            logger.error(f"Error procesando datos de sensor: {e}")
    
    @pyqtSlot(bool)
    def _on_sensor_status(self, connected: bool):
        """Slot para cambios en estado de conexión del sensor."""
        self.sensor_connected = connected
        if connected:
            self.status_sensor.setText("🌡 Sensor: ✓ Conectado")
            self.status_sensor.setStyleSheet("color: green;")
        else:
            self.status_sensor.setText("🌡 Sensor: ✗ Desconectado")
            self.status_sensor.setStyleSheet("color: red;")
            self.temp_value.setText("-- °C")
            self.class_value.setText("ESPERANDO")
            self.class_value.setStyleSheet(
                "background-color: #666; color: white; padding: 10px; border-radius: 5px;"
            )
    
    def _update_plot(self):
        """Actualiza el gráfico de temperatura con historial."""
        if len(self.temp_history) > 0:
            self.plot_curve.setData(list(self.temp_history))
    
    def _trigger_alert(self):
        """Dispara alerta de temperatura alta."""
        if not self.alert_shown:
            QMessageBox.warning(
                self,
                "⚠ ALERTA DE TEMPERATURA",
                f"¡La temperatura ha superado {TEMP_ALERT_THRESHOLD}°C!\n"
                f"Temperatura actual: {self.current_temp:.1f}°C",
                QMessageBox.StandardButton.Ok,
            )
            self.alert_shown = True
        
        # Emitir beep del sistema
        QApplication.beep()
        
        # Iniciar parpadeo
        self.alert_timer.start(500)  # Parpadeo cada 500ms
    
    def _blink_alert(self):
        """Anima el parpadeo de alerta."""
        self.alert_blink_state = not self.alert_blink_state
        if self.alert_blink_state:
            self.temp_value.setStyleSheet(
                "background-color: #ff0000; padding: 10px; border-radius: 5px;"
            )
        else:
            self.temp_value.setStyleSheet(
                "background-color: #cc0000; padding: 10px; border-radius: 5px;"
            )
    
    def closeEvent(self, event):
        """Maneja el cierre de la aplicación."""
        logger.info("Cerrando aplicación...")
        
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
