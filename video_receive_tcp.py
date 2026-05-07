#!/usr/bin/env python3
"""
Cliente receptor de video H.264 transmitido por TCP.
Reproduce el stream en tiempo real con ffplay.
"""

import socket
import subprocess
import sys

TCP_HOST = "127.0.0.1"              # IP del servidor
TCP_PORT = 5002                      # Puerto TCP
BUFFER_SIZE = 4096                   # Tamaño del buffer

def main():
    print(f"[*] Conectando a {TCP_HOST}:{TCP_PORT}...")
    sys.stdout.flush()
    
    # Conectar al servidor
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        sock.connect((TCP_HOST, TCP_PORT))
        print(f"[+] Conexión establecida")
        sys.stdout.flush()
        
        # Iniciar ffplay para reproducir el stream
        ffplay_cmd = [
            "ffplay",
            "-f", "h264",
            "-"
        ]
        
        process = subprocess.Popen(
            ffplay_cmd,
            stdin=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL
        )
        
        print(f"[*] Reproduciendo stream...")
        sys.stdout.flush()
        
        # Leer datos del socket y enviarlos a ffplay
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

if __name__ == "__main__":
    main()
