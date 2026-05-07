#!/usr/bin/env python3
"""
Captura video en directo con ffmpeg y lo transmite por TCP puerto 5002.
Diseñado para Linux. Parámetros editables al inicio del script.
"""

import subprocess
import socket
import sys

# ============ PARÁMETROS DE VIDEO ============
VIDEO_DEVICE = "/dev/video0"        # Dispositivo de video en Linux
WIDTH = 420                           # Ancho en píxeles
HEIGHT = 360                          # Alto en píxeles
FPS = 30                              # Fotogramas por segundo
BITRATE = "2000k"                    # Bitrate H.264
PIXEL_FORMAT = "yuyv422"             # Formato YUYV 4:2:2
CODEC = "h264"                       # Códec de video
TCP_PORT = 5002                      # Puerto TCP para transmisión
# =============================================

def main():
    print(f"[*] Iniciando captura desde {VIDEO_DEVICE}")
    print(f"[*] Resolución: {WIDTH}x{HEIGHT} @ {FPS}fps")
    print(f"[*] Formato: {PIXEL_FORMAT} -> {CODEC}")
    print(f"[*] Escuchando conexiones en puerto {TCP_PORT}...")
    sys.stdout.flush()
    
    # Crear socket servidor TCP
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", TCP_PORT))
    server.listen(1)
    
    try:
        while True:
            print(f"[*] Esperando cliente...")
            sys.stdout.flush()
            client_socket, addr = server.accept()
            print(f"[+] Cliente conectado desde {addr}")
            sys.stdout.flush()
            
            handle_client(client_socket)
            
    except KeyboardInterrupt:
        print("\n[!] Deteniendo...")
    finally:
        server.close()

def handle_client(client_socket):
    # Comando ffmpeg para capturar y codificar
    ffmpeg_cmd = [
        "ffmpeg",
        "-f", "v4l2",                           # Formato v4l2 para Linux
        "-input_format", PIXEL_FORMAT,          # Formato de entrada
        "-video_size", f"{WIDTH}x{HEIGHT}",     # Resolución
        "-framerate", str(FPS),                 # FPS
        "-i", VIDEO_DEVICE,                     # Dispositivo de entrada
        "-c:v", CODEC,                          # Códec de video
        "-b:v", BITRATE,                        # Bitrate
        "-preset", "ultrafast",                 # Velocidad de codificación
        "-f", "h264",                           # Formato de salida (bitstream H.264)
        "pipe:1"                                # Salida a stdout
    ]
    
    try:
        # Iniciar ffmpeg
        process = subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=0
        )
        
        # Leer datos de ffmpeg y enviarlos al cliente
        while True:
            data = process.stdout.read(4096)
            if not data:
                break
            client_socket.sendall(data)
            
    except BrokenPipeError:
        print(f"[-] Cliente desconectado")
    except Exception as e:
        print(f"[-] Error: {e}")
    finally:
        process.terminate()
        client_socket.close()

if __name__ == "__main__":
    main()
