#!/usr/bin/env python3
import socket
import time
import sys
from video_capture import WebcamVideoCapture, VideoCaptureConfig

def iniciar_emision():
    print("=" * 50)
    print("[START] EMISOR DE VIDEO EN DIRECTO")
    print("=" * 50)
    sys.stdout.flush()

    # 1. Usar tu configuración de baja latencia para el directo
    config = VideoCaptureConfig(
        width=480,
        height=360,
        fps=24,
        bitrate="2500k",
        preset="superfast",  # Balance entre velocidad y calidad
        crf=28
    )
    
    capture = WebcamVideoCapture(config)
    
    # 2. Configuración de red
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # IMPORTANTE: Pon aquí la IP del ordenador donde ejecutaste el Receptor.
    # Si vas a probar ambos códigos en el mismo ordenador, usa "127.0.0.1".
    IP_RECEPTOR = "127.0.0.1" 
    PUERTO = 5000
    
    try:
        print(f"[INIT] Conectando al receptor en {IP_RECEPTOR}:{PUERTO}...")
        sys.stdout.flush()
        
        # Dar tiempo extra para que el receptor esté listo
        time.sleep(2)
        
        # Intentamos conectar. El receptor debe estar encendido ANTES de correr este script.
        sock.connect((IP_RECEPTOR, PUERTO))
        print("[OK] Conexion establecida! Iniciando camara...")
        sys.stdout.flush()
        
        capture.start()
        
        bytes_enviados = 0
        print("[RUNNING] Transmitiendo video... (Presiona Ctrl+C para detener)")
        sys.stdout.flush()
        
        # 3. Leer los frames de tu librería y enviarlos directamente por el socket
        for chunk in capture.read_frames():
            if chunk:
                sock.sendall(chunk)
                bytes_enviados += len(chunk)
                
    except ConnectionRefusedError:
        print("\n[ERROR] Error: No se pudo conectar.")
        print("Asegúrate de ejecutar PRIMERO el código del RECEPTOR en el otro repositorio.")
    except KeyboardInterrupt:
        print(f"\n[STOP] Transmision detenida por el usuario. (Enviados {bytes_enviados / 1_000_000:.1f} MB)")
    except Exception as e:
        print(f"\n[ERROR] Ocurrio un error inesperado: {e}")
    finally:
        print("[CLEANUP] Cerrando conexiones...")
        sock.close()
        capture.stop()

if __name__ == "__main__":
    iniciar_emision()