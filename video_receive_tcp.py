#!/usr/bin/env python3
"""
Cliente receptor de video H.264 transmitido por TCP.
Reproduce el stream en tiempo real con ffmpeg.
Muestra información en una pestaña rectangular en la esquina superior derecha.
"""

import socket
import subprocess
import sys
import shutil
import threading
import os
import tempfile

TCP_HOST = "127.0.0.1"              # IP del servidor
TCP_PORT = 5002                      # Puerto TCP video
INFO_PORT = 8080                     # Puerto TCP información
BUFFER_SIZE = 4096                   # Tamaño del buffer

# Archivo temporal para almacenar la información
info_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
INFO_FILE = info_file.name
info_file.close()

# Escribir archivo vacío inicial
with open(INFO_FILE, 'w') as f:
    f.write("Esperando info...")

info_lock = threading.Lock()

def info_server():
    """Servidor que recibe información en puerto INFO_PORT y la almacena."""
    info_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    info_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    info_sock.bind(("0.0.0.0", INFO_PORT))
    info_sock.listen(1)
    
    print(f"[*] Servidor de información escuchando en puerto {INFO_PORT}")
    sys.stdout.flush()
    
    try:
        while True:
            try:
                client, addr = info_sock.accept()
                print(f"[+] Cliente de información conectado desde {addr}")
                sys.stdout.flush()
                
                while True:
                    data = client.recv(1024)
                    if not data:
                        break
                    
                    # Actualizar información
                    text = data.decode('utf-8', errors='ignore').strip()
                    with info_lock:
                        with open(INFO_FILE, 'w') as f:
                            f.write(text)
                    
                client.close()
            except:
                pass
    except KeyboardInterrupt:
        pass
    finally:
        info_sock.close()

def check_and_install_dependencies():
    """Verifica si ffmpeg está instalado."""
    print("[*] Verificando dependencias...")
    sys.stdout.flush()
    
    if not shutil.which("ffmpeg"):
        print("[!] ffmpeg no está instalado. Intentando instalar...")
        sys.stdout.flush()
        
        result = subprocess.run(["sudo", "apt-get", "update"], capture_output=True)
        result = subprocess.run(["sudo", "apt-get", "install", "-y", "ffmpeg"], capture_output=True)
        
        if result.returncode != 0:
            print("[!] No se pudo instalar ffmpeg automáticamente.")
            print("[!] Por favor instala ffmpeg manualmente:")
            print("    Ubuntu/Debian: sudo apt-get install ffmpeg")
            sys.exit(1)
        
        print("[+] ffmpeg instalado correctamente")
    else:
        print("[+] ffmpeg encontrado")
    
    sys.stdout.flush()

def main():
    check_and_install_dependencies()
    
    # Iniciar servidor de información en thread
    info_thread = threading.Thread(target=info_server, daemon=True)
    info_thread.start()
    
    print(f"[*] Conectando a {TCP_HOST}:{TCP_PORT}...")
    sys.stdout.flush()
    
    # Conectar al servidor
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        sock.connect((TCP_HOST, TCP_PORT))
        print(f"[+] Conexión establecida")
        sys.stdout.flush()
        
        # Comando ffmpeg con drawtext para mostrar información en esquina superior derecha
        ffmpeg_cmd = [
            "ffmpeg",
            "-f", "h264",
            "-i", "pipe:0",
            "-vf", f"drawtext=textfile='{INFO_FILE}':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:fontsize=16:box=1:boxcolor=black@0.7:fontcolor=white:x=w-text_w-10:y=10:reload=1",
            "-f", "sdl",
            "-"
        ]
        
        process = subprocess.Popen(
            ffmpeg_cmd,
            stdin=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL
        )
        
        print(f"[*] Reproduciendo stream con información...")
        sys.stdout.flush()
        
        # Leer datos del socket y enviarlos a ffmpeg
        try:
            while True:
                data = sock.recv(BUFFER_SIZE)
                if not data:
                    break
                process.stdin.write(data)
                process.stdin.flush()
        except KeyboardInterrupt:
            print("\n[!] Deteniendo...")
        finally:
            process.stdin.close()
            process.wait()
            
    except Exception as e:
        print(f"[-] Error: {e}")
    finally:
        sock.close()
        # Limpiar archivo temporal
        try:
            os.unlink(INFO_FILE)
        except:
            pass

if __name__ == "__main__":
    main()
