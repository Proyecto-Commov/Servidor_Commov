#!/usr/bin/env python3
"""
temp_simulator.py — Simulador del Proceso 2 (servidor de temperatura)

PROPÓSITO:
Este script simula un servidor TCP externo (Proceso 2) que emite datos de temperatura
en formato JSON-lines. Se utiliza para pruebas y desarrollo cuando el sensor real no
está disponible.

EMISIÓN:
- Actúa como servidor TCP escuchando en SENSOR_HOST:SENSOR_PORT
- Emite un objeto JSON por línea (JSON-lines format)
- Cada mensaje contiene: timestamp, temperature, classification
- Frecuencia: aproximadamente 1 mensaje por segundo

TODO: Implementar en fase posterior
- Conectar con datos de sensor real
- Integrar con API de sensor external
- Agregar persistencia de datos
"""

import socket
import json
import time
import logging
import sys
import random
import threading
import signal
import atexit
from typing import Generator

# =============================================================================
# CONFIGURACIÓN — modifica estos valores según tu entorno
# =============================================================================
SENSOR_BIND_HOST     = "0.0.0.0"        # Interfaz de escucha
SENSOR_PORT          = 9001              # Puerto TCP del servidor
SENSOR_INTERVAL      = 1.0               # Segundos entre emisiones de datos
SENSOR_TEMP_BASE     = 65.0              # Temperatura base (°C) — alta para pruebas de alerta
SENSOR_TEMP_NOISE    = 5.0               # Variación aleatoria (±)
LOG_LEVEL            = "INFO"            # Nivel de log
# =============================================================================

# Configurar logging
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=getattr(logging, LOG_LEVEL),
)
logger = logging.getLogger(__name__)


# Global variables for cleanup
_server_socket: socket.socket = None
_shutdown_event = threading.Event()


def cleanup():
    """Limpia todos los recursos antes de salir."""
    global _server_socket
    
    logger.info("Iniciando limpieza de recursos...")
    _shutdown_event.set()
    
    # Cerrar socket servidor
    if _server_socket:
        try:
            _server_socket.close()
            logger.info("Socket servidor cerrado")
        except Exception as e:
            logger.warning(f"Error cerrando socket servidor: {e}")
    
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


def classify_temperature(temp: float) -> str:
    """
    Clasifica la temperatura en categorías.
    
    Args:
        temp: Temperatura en °C
        
    Returns:
        str: Clasificación ("frio", "templado", "caliente", "muy caliente", "crítico")
    """
    if temp < 10:
        return "frio"
    elif temp < 20:
        return "templado"
    elif temp < 40:
        return "caliente"
    elif temp < 60:
        return "muy caliente"
    else:
        return "crítico"


def generate_temperature_data() -> Generator[dict, None, None]:
    """
    Genera datos de temperatura simulados de forma continua.
    
    Yields:
        dict: {"timestamp": float, "temperature": float, "classification": str}
    """
    current_temp = SENSOR_TEMP_BASE
    
    while True:
        # Simular deriva aleatoria de temperatura (paseo aleatorio)
        drift = random.uniform(-5, 7)
        current_temp += drift
        
        # Agregar ruido aleatorio
        noise = random.uniform(-SENSOR_TEMP_NOISE, SENSOR_TEMP_NOISE)
        temp = current_temp + noise
        
        # Limitar rango realista
        temp = max(0, min(80, temp))
        
        data = {
            "timestamp": time.time(),
            "temperature": round(temp, 1),
            "classification": classify_temperature(temp),
        }
        
        yield data
        time.sleep(SENSOR_INTERVAL)


def handle_client_connection(client_socket: socket.socket, client_addr: tuple) -> None:
    """
    Maneja la conexión de un cliente: emite datos de temperatura en JSON-lines.
    
    Args:
        client_socket: socket del cliente conectado
        client_addr: tupla (ip, puerto) del cliente
    """
    logger.info(f"Cliente conectado: {client_addr}")
    try:
        gen = generate_temperature_data()
        for data in gen:
            try:
                json_line = json.dumps(data) + "\n"
                client_socket.sendall(json_line.encode())
            except (BrokenPipeError, ConnectionResetError):
                logger.info(f"Cliente desconectado: {client_addr}")
                break
    except Exception as e:
        logger.error(f"Error enviando datos a {client_addr}: {e}")
    finally:
        try:
            client_socket.close()
        except:
            pass
        logger.info(f"Conexión cerrada: {client_addr}")


def run_server() -> None:
    """Inicia el servidor TCP que emite datos de temperatura simulados."""
    global _server_socket
    
    _server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        _server_socket.bind((SENSOR_BIND_HOST, SENSOR_PORT))
        _server_socket.listen(5)
        logger.info(f"Servidor de temperatura escuchando en {SENSOR_BIND_HOST}:{SENSOR_PORT}")
        
        while not _shutdown_event.is_set():
            try:
                _server_socket.settimeout(1)  # Timeout para poder verificar shutdown
                client_socket, client_addr = _server_socket.accept()
                client_thread = threading.Thread(
                    target=handle_client_connection,
                    args=(client_socket, client_addr),
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
        logger.error(f"Error en servidor: {e}")
    finally:
        cleanup()


if __name__ == "__main__":
    run_server()
